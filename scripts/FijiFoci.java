import ij.IJ;
import ij.ImagePlus;
import ij.gui.Overlay;
import ij.gui.PointRoi;
import ij.gui.Roi;
import ij.io.FileSaver;
import ij.io.RoiEncoder;
import ij.plugin.filter.MaximumFinder;
import ij.plugin.filter.ThresholdToSelection;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import java.awt.Color;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/** Explicit scalar-plane maxima, labelled-mask assignment, and native Fiji exports. */
public class FijiFoci {
    static ImagePlus scalar(String path) throws IOException {
        ImagePlus im = IJ.openImage(path);
        if (im == null) throw new IOException("Cannot read image: " + path);
        if (im.getStackSize() != 1 || im.getNChannels() != 1 || im.getBitDepth() == 24)
            throw new IOException("Expected one scalar 2D plane (no RGB or stack): " + path);
        ImageProcessor ip = im.getProcessor();
        for (int i=0; i<ip.getPixelCount(); i++)
            if (!Float.isFinite(ip.getf(i))) throw new IOException("Nonfinite pixel: " + path);
        return im;
    }
    static PrintWriter csv(Path p) throws IOException {
        return new PrintWriter(Files.newBufferedWriter(p, StandardCharsets.UTF_8, StandardOpenOption.CREATE_NEW));
    }
    static void zipRoi(ZipOutputStream zip, Roi roi) throws IOException {
        zip.putNextEntry(new ZipEntry(roi.getName() + ".roi"));
        byte[] bytes = RoiEncoder.saveAsByteArray(roi);
        if (bytes == null) throw new IOException("ROI encoding failed: " + roi.getName());
        zip.write(bytes); zip.closeEntry();
    }
    static class Peak {
        int x,y,label; float value;
        Peak(int x, int y, int label, float value) {
            this.x=x; this.y=y; this.label=label; this.value=value;
        }
    }
    public static void main(String[] a) throws Exception {
        if (a.length==1 && a[0].equals("probe")) {
            System.out.println("ImageJ " + IJ.getVersion()); return;
        }
        if (a.length==2 && a[0].equals("inspect")) {
            ImagePlus im=IJ.openImage(a[1]);
            if(im==null) throw new IOException("Unreadable image");
            System.out.println("{\"width\":"+im.getWidth()+",\"height\":"+im.getHeight()+
                ",\"planes\":"+im.getStackSize()+",\"overlay_rois\":"+
                (im.getOverlay()==null ? 0 : im.getOverlay().size())+"}");
            im.close(); return;
        }
        if(a.length!=13) throw new IllegalArgumentException("Use the Python JSON launcher");
        String id=a[0];
        ImagePlus detection=scalar(a[1]), review=scalar(a[2]);
        ImagePlus labels=a[3].equals("-") ? null : scalar(a[3]);
        double amplitude=Double.parseDouble(a[4]), prominence=Double.parseDouble(a[5]);
        double minDistance=Double.parseDouble(a[6]);
        boolean excludeEdges=Boolean.parseBoolean(a[7]);
        double displayMin=Double.parseDouble(a[8]), displayMax=Double.parseDouble(a[9]);
        Path out=Paths.get(a[10]);
        // Arguments 11 and 12 carry the explicit units and preprocessing description in the launch log.
        int w=detection.getWidth(), h=detection.getHeight();
        if(review.getWidth()!=w || review.getHeight()!=h ||
            (labels!=null && (labels.getWidth()!=w || labels.getHeight()!=h)))
            throw new IOException("Image/mask dimensions disagree");
        ImageProcessor ip=detection.getProcessor(), lp=labels==null ? null : labels.getProcessor();
        TreeMap<Integer,Long> areas=new TreeMap<Integer,Long>();
        TreeMap<Integer,Integer> counts=new TreeMap<Integer,Integer>();
        if(lp!=null) for(int i=0;i<lp.getPixelCount();i++) {
            double v=lp.getf(i);
            if(v<0 || v>16777216 || v!=Math.rint(v)) throw new IOException("Invalid integer label mask");
            int label=(int)v;
            if(label>0) {areas.put(label, areas.containsKey(label)? areas.get(label)+1:1L); counts.put(label,0);}
        }
        ByteProcessor maxima=new MaximumFinder().findMaxima(ip,prominence,true,amplitude,
            MaximumFinder.SINGLE_POINTS,excludeEdges,false);
        if(maxima==null) throw new IOException("MaximumFinder did not return a result");
        ArrayList<Peak> candidates=new ArrayList<Peak>();
        for(int y=0;y<h;y++) for(int x=0;x<w;x++) {
            int label=lp==null ? 0 : (int)lp.getf(x,y);
            if(maxima.get(x,y)>0 && ip.getf(x,y)>=amplitude && (lp==null || label>0))
                candidates.add(new Peak(x,y,label,ip.getf(x,y)));
        }
        Collections.sort(candidates,new Comparator<Peak>() {
            public int compare(Peak p,Peak q) {
                int c=Float.compare(q.value,p.value);
                if(c==0)c=Integer.compare(p.y,q.y);
                if(c==0)c=Integer.compare(p.x,q.x);
                return c;
            }
        });
        // Spatial buckets avoid quadratic suppression on dense images.
        HashMap<String,ArrayList<Peak>> buckets=new HashMap<String,ArrayList<Peak>>();
        ArrayList<Peak> accepted=new ArrayList<Peak>();
        double cell=Math.max(1,minDistance), radius2=minDistance*minDistance;
        for(Peak p:candidates) {
            int bx=(int)Math.floor(p.x/cell), by=(int)Math.floor(p.y/cell);
            boolean close=false;
            for(int dy=-1;dy<=1&&!close;dy++) for(int dx=-1;dx<=1&&!close;dx++) {
                ArrayList<Peak> nearby=buckets.get(p.label+":"+(bx+dx)+":"+(by+dy));
                if(nearby!=null) for(Peak q:nearby) {
                    double xx=p.x-q.x, yy=p.y-q.y;
                    if(xx*xx+yy*yy<radius2){close=true;break;}
                }
            }
            if(close)continue;
            accepted.add(p);
            String key=p.label+":"+bx+":"+by;
            if(!buckets.containsKey(key))buckets.put(key,new ArrayList<Peak>());
            buckets.get(key).add(p);
            if(lp!=null)counts.put(p.label,counts.get(p.label)+1);
        }
        Overlay overlay=new Overlay();
        if(lp!=null) {
            try(ZipOutputStream zip=new ZipOutputStream(Files.newOutputStream(out.resolve("nuclei.zip"),StandardOpenOption.CREATE_NEW));
                PrintWriter table=csv(out.resolve("nuclei.csv"))) {
                table.println("image_id,nucleus_id,area_px2,foci_count");
                for(int label:areas.keySet()) {
                    lp.setThreshold(label,label,ImageProcessor.NO_LUT_UPDATE);
                    Roi roi=new ThresholdToSelection().convert(lp);
                    if(roi==null)throw new IOException("Cannot encode nucleus "+label);
                    roi.setName(id+"_nucleus_"+label); roi.setStrokeColor(Color.YELLOW);
                    overlay.add(roi); zipRoi(zip,roi);
                    table.println(id+","+label+","+areas.get(label)+","+counts.get(label));
                }
            }
            lp.resetThreshold();
            if(!new FileSaver(labels).saveAsTiff(out.resolve("nuclei_labels.tif").toString()))
                throw new IOException("Cannot save label TIFF");
        }
        try(PrintWriter table=csv(out.resolve("foci.csv"));
            ZipOutputStream zip=new ZipOutputStream(Files.newOutputStream(out.resolve("foci.zip"),StandardOpenOption.CREATE_NEW))) {
            table.println("image_id,focus_id,nucleus_id,x_px,y_px,peak_value,amplitude,prominence,min_distance_px");
            int n=0;
            for(Peak p:accepted) {
                n++;
                table.printf(Locale.US,"%s,%d,%s,%d,%d,%.9g,%.9g,%.9g,%.9g%n",id,n,
                    lp==null?"":Integer.toString(p.label),p.x,p.y,(double)p.value,amplitude,prominence,minDistance);
                PointRoi roi=new PointRoi(p.x,p.y);
                roi.setName(id+"_focus_"+n); roi.setStrokeColor(Color.GREEN);
                overlay.add(roi); zipRoi(zip,roi);
            }
        }
        ImagePlus annotated=review.duplicate();
        annotated.setTitle(id+" — review");
        annotated.setDisplayRange(displayMin,displayMax);
        annotated.setOverlay(overlay);
        if(!new FileSaver(annotated).saveAsTiff(out.resolve("review.tif").toString()))
            throw new IOException("Cannot save review TIFF");
        ImagePlus flat=annotated.flatten();
        if(!new FileSaver(flat).saveAsPng(out.resolve("preview.png").toString()))
            throw new IOException("Cannot save preview");
        System.out.println("ImageJ "+IJ.getVersion()+"; image="+id+"; foci="+accepted.size()+
            "; nuclei="+areas.size()+"; coordinates=top-left,zero-based,pixels");
        flat.close(); annotated.close(); review.close(); detection.close(); if(labels!=null)labels.close();
    }
}
