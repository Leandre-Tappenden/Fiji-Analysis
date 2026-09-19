#!/usr/bin/env python3
"""Exercise helper behaviour with synthetic data, not experimental image accuracy."""
import argparse
import csv
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import unquote
import zipfile

import fiji_foci as ff


FIXTURE = r'''
import ij.*;
import ij.process.*;
import ij.io.*;
import java.nio.file.*;
public class Fixture {
 public static void main(String[] a) throws Exception {
  if(a[0].equals("roi")) {
   ij.gui.Roi r=new RoiDecoder(a[1]).getRoi();
   if(r==null)throw new Exception("Cannot decode ROI");
   System.out.println(r.getName()+":"+r.getBounds().x+","+r.getBounds().y);return;
  }
  String dir=a[0]+"/";
  FloatProcessor p=new FloatProcessor(64,64);
  for(int i=0;i<4096;i++)p.setf(i,10);
  p.setf(12,12,100);p.setf(15,12,70);p.setf(22,20,60);p.setf(45,15,80);
  p.setf(50,50,120);p.setf(0,32,110);
  new FileSaver(new ImagePlus("signal",p)).saveAsTiff(dir+"signal.tif");
  ShortProcessor mask=new ShortProcessor(64,64);
  for(int y=4;y<28;y++)for(int x=4;x<28;x++)mask.set(x,y,1);
  for(int y=4;y<28;y++)for(int x=36;x<60;x++)mask.set(x,y,2);
  for(int y=36;y<60;y++)for(int x=4;x<28;x++)mask.set(x,y,3);
  new FileSaver(new ImagePlus("labels",mask)).saveAsTiff(dir+"labels.tif");
  new FileSaver(new ImagePlus("empty",new FloatProcessor(64,64))).saveAsTiff(dir+"empty.tif");
  new FileSaver(new ImagePlus("wrong",new FloatProcessor(32,32))).saveAsTiff(dir+"wrong.tif");
  FloatProcessor bad=(FloatProcessor)p.duplicate();bad.setf(4,4,Float.NaN);
  new FileSaver(new ImagePlus("nan",bad)).saveAsTiff(dir+"nan.tif");
  FloatProcessor fraction=mask.convertToFloatProcessor();fraction.setf(4,4,0.5f);
  new FileSaver(new ImagePlus("fraction",fraction)).saveAsTiff(dir+"fraction.tif");
  ImageStack stack=new ImageStack(64,64);stack.addSlice(p);stack.addSlice(p.duplicate());
  new FileSaver(new ImagePlus("stack",stack)).saveAsTiffStack(dir+"stack.tif");
 }
}
'''


def rows(path):
    with Path(path).open(newline='') as f:
        return list(csv.DictReader(f))


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.paths=[]
    def handle_starttag(self, tag, attrs):
        for key,value in attrs:
            if key in ('href','src'):
                self.paths.append(value)


def exercise(root, fiji):
    env=ff.discover(fiji)
    raw=root/'raw images'; raw.mkdir()
    classes=root/'classes'; classes.mkdir()
    source=root/'Fixture.java'; source.write_text(FIXTURE)
    ff.call([env['javac'],'-cp',env['ij_jar'],'-d',str(classes),str(source)])
    base=ff.compile_helper(env, classes)
    fixture=base[:-1]+['Fixture']
    ff.call(fixture+[str(raw)])
    hashes={str(p):ff.sha(p) for p in raw.iterdir()}
    checks=[]
    config={'image_id':'synthetic-001','detection_image':str(raw/'signal.tif'),
            'review_image':str(raw/'signal.tif'),'nuclei_labels':str(raw/'labels.tif'),
            'amplitude':30,'prominence':20,'min_distance_px':0,'exclude_image_edges':True,
            'display_min':0,'display_max':140,'units':'synthetic ADU','preprocessing':'None; synthetic impulses'}
    def execute(name, updates=None, failure=False):
        c=dict(config,**(updates or {})); path=root/(name+'.json'); ff.save(path,c)
        out=root/name
        try:
            ff.run(env,ff.configuration(path),out,60)
        except (ValueError,RuntimeError) as error:
            if not failure: raise
            if out.exists():
                assert json.loads((out/'execution.json').read_text())['status']=='failed'
            return str(error)
        if failure: raise AssertionError('Invalid input unexpectedly accepted: '+name)
        return out
    normal=execute('normal')
    peaks=rows(normal/'foci.csv'); nuclei=rows(normal/'nuclei.csv')
    assert {(int(p['x_px']),int(p['y_px'])) for p in peaks}=={(12,12),(15,12),(22,20),(45,15)}
    checks.append('Known peak locations and mask assignment')
    assert {n['nucleus_id']:int(n['foci_count']) for n in nuclei}=={'1':3,'2':1,'3':0}
    checks.append('Zero-count nucleus is retained; totals reconcile')
    assert len(rows(execute('strict',{'amplitude':90})/'foci.csv'))==1
    checks.append('Changing absolute cutoff changes detections as expected')
    assert len(rows(execute('distance',{'min_distance_px':4})/'foci.csv'))==3
    checks.append('Minimum-distance suppression selects brighter peaks')
    assert len(rows(execute('prominence',{'prominence':95})/'foci.csv'))==0
    checks.append('Prominence has an independent tested effect')
    empty=execute('empty-result',{'detection_image':str(raw/'empty.tif')})
    assert not rows(empty/'foci.csv') and all(n['foci_count']=='0' for n in rows(empty/'nuclei.csv'))
    checks.append('Valid empty signal produces zero counts, not missing data')
    repeat=execute('repeat')
    assert (normal/'foci.csv').read_bytes()==(repeat/'foci.csv').read_bytes()
    assert (normal/'nuclei.csv').read_bytes()==(repeat/'nuclei.csv').read_bytes()
    checks.append('Deterministic repeated measurements')
    for name,key,file in [('stack','detection_image','stack.tif'),('dimensions','review_image','wrong.tif'),
                          ('nonfinite','detection_image','nan.tif'),('fractional','nuclei_labels','fraction.tif')]:
        execute('reject-'+name,{key:str(raw/file)},True)
        checks.append('Reject '+name+' input and preserve failed-run record')
    execute('reject-typo',{'prominance':20},True)
    checks.append('Reject unrecognised configuration field')
    try: ff.run(env,config,normal,60)
    except FileExistsError: pass
    else: raise AssertionError('Existing run was overwritten')
    checks.append('Refuse output overwrite')
    assert json.loads(ff.call(base+['inspect',str(normal/'review.tif')])[0])['overlay_rois']==7
    checks.append('Native overlay TIFF reopens in ImageJ with all seven ROIs')
    with zipfile.ZipFile(normal/'foci.zip') as z:
        assert len(z.namelist())==4
        roi=root/'first.roi'; roi.write_bytes(z.read(z.namelist()[0]))
    assert ff.call(fixture+['roi',str(roi)])[0].endswith(':12,12')
    with zipfile.ZipFile(normal/'nuclei.zip') as z: assert len(z.namelist())==3
    checks.append('Native ROI ZIP count and point coordinate round-trip')
    assert all(ff.sha(p)==h for p,h in hashes.items())
    checks.append('All synthetic source files unchanged')
    project=Path(__file__).with_name('project.py')
    run=root/'example-run'
    def command(*args, failure=False):
        result=subprocess.run([sys.executable,str(project)]+list(args),capture_output=True,text=True)
        assert (result.returncode!=0) if failure else (result.returncode==0), result.stderr
        return result
    prompt=root/'request.txt'; prompt.write_text('Count <nuclear> foci; retain this request.')
    command('init','--run',str(run),'--source',str(raw),'--title','Synthetic foci review',
            '--mode','table','--prompt',str(prompt))
    decision=root/'decision.json'
    ff.save(decision,{'stage':'detection','parameter':'prominence','value':20,'units':'synthetic ADU',
                     'scope':'synthetic-001','reason':'Known synthetic peak test','evidence':['normal/preview.png'],
                     'chosen_by':'test fixture'})
    command('event','--run',str(run),'--kind','decision','--json',str(decision))
    quality=root/'quality.json'
    ff.save(quality,{'stage':'preflight','code':'MISSING_EDU','severity':'warning','scope':'synthetic-001',
                    'finding':'Synthetic EdU is absent <script>alert(1)</script>',
                    'action':'Keep foci; mark EdU missing','affected_metrics':['edu_status']})
    command('event','--run',str(run),'--kind','quality','--json',str(quality))
    command('add','--run',str(run),'--file',str(normal/'preview.png'),'--role','preview','--stage','detection',
            '--image-id','synthetic-001','--caption','Synthetic detections; green points, yellow nuclei',
            '--scaling','0–140 synthetic ADU; display only')
    command('add','--run',str(run),'--file',str(normal/'preview.png'),'--role','preview','--stage','detection',
            '--image-id','synthetic-002','--caption','Second registration tests per-image folders',
            '--scaling','0–140 synthetic ADU; display only')
    assert (run/'QC_images/Foci_counts/synthetic-001/preview.png').is_file()
    assert (run/'QC_images/Foci_counts/synthetic-002/preview.png').is_file()
    checks.append('Same preview filename remains distinct across image folders')
    command('add','--run',str(run),'--file',str(normal/'nuclei.csv'),'--role','table','--caption','Per-nucleus counts','--primary')
    command('add','--run',str(run),'--file',str(normal/'nuclei.csv'),'--role','table','--caption','Duplicate',failure=True)
    brief=json.loads((run/'Additional_material/Run_records/brief.json').read_text())
    brief.update(status='complete',validation='Synthetic technical test only; no biological accuracy claim',
                 summary=['Four synthetic peaks assigned to three nuclei, including one nucleus with zero foci.'])
    ff.save(run/'Additional_material/Run_records/brief.json',brief)
    command('render','--run',str(run))
    report=(run/'Reports/Experiment_report.html').read_text()
    assert '<script>alert' not in report and '&lt;script&gt;' in report
    assert len(rows(run/'Additional_material/Run_records/quality_log.csv'))==1 and len(rows(run/'Additional_material/Run_records/decision_log.csv'))==1
    links=Links(); links.feed(report)
    assert all(('id="'+p[1:]+'"' in report) if p.startswith('#') else
               (run/'Reports'/unquote(p)).is_file() for p in links.paths)
    assert json.loads((run/'Additional_material/Run_records/brief.json').read_text())['primary_artifact']=='Tables/Main_results/nuclei.csv'
    checks += ['Structured quality and decision logs exported', 'One main CSV selected; supporting report retained',
               'All report links resolve; user text is HTML-escaped', 'Duplicate artifact cannot overwrite existing output']
    modified=run/'QC_images/Foci_counts/synthetic-002/preview.png'
    original=modified.read_bytes(); modified.write_bytes(original+b'changed')
    command('render','--run',str(run),failure=True)
    modified.write_bytes(original)
    command('render','--run',str(run))
    checks.append('Modified registered artifact detected before report regeneration')
    # New layout: routing, graph dependencies, deferred render and portable report links.
    for folder in ('R_scripts', 'Tables/Segmentation_checks', 'Tables/Counting_sensitivity',
                   'Tables/Statistics', 'QC_images/Channel_checks', 'QC_images/Segmentation',
                   'Analysis_scripts', 'Graphs', 'Additional_material/Editable_masks_and_ROIs'):
        assert (run/folder).is_dir()
    graph_script=root/'01_counts.R'; graph_script.write_text('# Input: Tables/Main_results/nuclei.csv\n')
    before=(run/'Reports/Experiment_report.html').read_bytes()
    command('add','--run',str(run),'--file',str(graph_script),'--role','r_script',
            '--caption','Editable plot code','--graph-id','01_counts',
            '--uses','Tables/Main_results/nuclei.csv','--no-render')
    assert (run/'Reports/Experiment_report.html').read_bytes()==before
    command('event','--run',str(run),'--kind','decision','--json',str(decision),'--no-render')
    assert (run/'Reports/Experiment_report.html').read_bytes()==before
    command('add','--run',str(run),'--file',str(normal/'preview.png'),'--role','figure',
            '--caption','Synthetic graph fixture','--graph-id','01_counts',
            '--uses','Tables/Main_results/nuclei.csv','--uses','R_scripts/01_counts.R','--no-render')
    command('add','--run',str(run),'--file',str(normal/'nuclei.csv'),'--role','table',
            '--category','../../escape','--caption','Reject unsafe category',failure=True)
    command('add','--run',str(run),'--file',str(normal/'nuclei.csv'),'--role','table',
            '--category','stats','--caption','Reject unregistered input',
            '--uses','Additional_material/Run_records/brief.json',failure=True)
    assert not (run/'Tables/Statistics/nuclei.csv').exists()
    command('render','--run',str(run))
    report=(run/'Reports/Experiment_report.html').read_text(); links=Links();links.feed(report)
    assert all(('id="'+p[1:]+'"' in report) if p.startswith('#') else
               (run/'Reports'/unquote(p)).is_file() for p in links.paths)
    assert 'R_scripts/01_counts.R' in report and 'Tables/Main_results/nuclei.csv' in report
    assert 'Count &lt;nuclear&gt; foci' in report
    for category in ('qc_segmentation','qc_counting_sensitivity','stats'):
        command('add','--run',str(run),'--file',str(normal/'nuclei.csv'),'--role','table',
                '--category',category,'--caption','Synthetic QC/statistics fixture','--no-render')
        assert (run/'Tables'/{'qc_segmentation':'Segmentation_checks', 'qc_counting_sensitivity':'Counting_sensitivity', 'stats':'Statistics'}[category]/'nuclei.csv').is_file()
    for role, name, destination in [('analysis_script','processing.py','Analysis_scripts'),
                                   ('guide','Workflow_and_settings.md','Reports'),
                                   ('guide','Reproduce_in_Fiji.html','Reports')]:
        file=root/name;file.write_text('Synthetic registration fixture only.\n')
        command('add','--run',str(run),'--file',str(file),'--role',role,
                '--caption',name,'--no-render')
        assert (run/destination/name).is_file()
    command('render','--run',str(run))
    checks += ['New output categories and graph/script/CSV links resolve',
               'Deferred rendering leaves report untouched until requested',
               'Unsafe categories and unregistered dependencies rejected']
    # Legacy schema-1/2 runs render in place, without moving any user files.
    for version, table_folder in [(1, 'tables'), (2, 'csv/main_results')]:
        legacy=root/('legacy-'+str(version))
        command('init','--run',str(legacy),'--source',str(raw),'--title','Legacy')
        (legacy/'Additional_material/Run_records').rename(legacy/'provenance')
        legacy_brief=json.loads((legacy/'provenance/brief.json').read_text())
        legacy_brief['schema_version']=version
        ff.save(legacy/'provenance/brief.json',legacy_brief)
        command('add','--run',str(legacy),'--file',str(normal/'nuclei.csv'),
                '--role','table','--caption','Legacy CSV')
        assert (legacy/table_folder/'nuclei.csv').is_file()
        legacy_report=(legacy/'report.html').read_text()
        links=Links(); links.feed(legacy_report)
        assert all(('id="'+p[1:]+'"' in legacy_report) if p.startswith('#') else
                   (legacy/unquote(p)).is_file() for p in links.paths)
    checks.append('Version-1 and version-2 runs retain their original paths and links')
    assert set(p.name for p in run.iterdir()) == {
        'Reports','R_scripts','Tables','QC_images','Analysis_scripts','Graphs','Additional_material'}
    # Source names with meaningful punctuation survive actual Fiji execution and CSV output.
    named_config = dict(config, image_id='RepA_siCTRL_DRB+_R-loop_48 (field.1)')
    named_config_file=root/'named-config.json'; ff.save(named_config_file,named_config)
    ff.run(env,ff.configuration(named_config_file),root/'named-source',60)
    assert all(row['image_id']==named_config['image_id'] for row in rows(root/'named-source/foci.csv'))
    for invalid_id in ('../escape','a/b','a\\b','..','field,1','field\n1'):
        invalid_file=root/'invalid-name.json'; ff.save(invalid_file,dict(config,image_id=invalid_id))
        try: ff.configuration(invalid_file)
        except ValueError: pass
        else: raise AssertionError('Unsafe source name accepted: '+invalid_id)
    command('add','--run',str(run),'--file',str(normal/'preview.png'),'--role','preview',
            '--stage','detection','--image-id',named_config['image_id'],
            '--caption','Original source stem retained','--scaling','Display only')
    report=(run/'Reports/Experiment_report.html').read_text();links=Links();links.feed(report)
    assert all(('id="'+p[1:]+'"' in report) if p.startswith('#') else
               (run/'Reports'/unquote(p)).is_file() for p in links.paths)
    checks.append('Simple top-level folders and source-derived names survive Fiji and report linking')
    # Batches reuse one compilation but preserve single-image measurements and failures.
    c1=root/'batch-one.json'; c2=root/'batch-two.json'; bad=root/'batch-bad.json'
    ff.save(c1,config); ff.save(c2,dict(config,image_id='synthetic-002'))
    ff.save(bad,dict(config,image_id='synthetic-bad',detection_image=str(raw/'stack.tif')))
    from unittest.mock import patch
    with patch.object(ff,'compile_helper',wraps=ff.compile_helper) as compiler:
        result=ff.batch(env,[c1,c2,bad],root/'batch',60,workers=2)
        assert compiler.call_count==1
    assert result['status']=='failed'
    assert [r['status'] for r in result['images']]==['complete','complete','failed']
    assert (normal/'foci.csv').read_bytes()==(root/'batch/synthetic-001/foci.csv').read_bytes()
    assert json.loads((root/'batch/synthetic-bad/execution.json').read_text())['status']=='failed'
    try:ff.batch(env,[c1,c1],root/'duplicate-batch',60)
    except ValueError:pass
    else:raise AssertionError('Duplicate IDs accepted')
    assert not (root/'duplicate-batch').exists()
    try:ff.batch(env,[c1],root/'batch',60)
    except ValueError:pass
    else:raise AssertionError('Existing batch output overwritten')
    checks += ['Batch compiles once, matches single-image counts and retains partial failures',
               'Batch rejects duplicate IDs and existing outputs before work']
    result={'passed':len(checks),'checks':checks,'environment':env,
            'scope':'Synthetic software behaviour only; no experimental segmentation/counting accuracy assessment.'}
    ff.save(root/'test_results.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fiji'); parser.add_argument('--keep',help='New folder in which to retain synthetic test outputs')
    args=parser.parse_args()
    if args.keep:
        root=Path(args.keep).resolve(); root.mkdir(parents=True,exist_ok=False)
        result=exercise(root,args.fiji)
    else:
        with tempfile.TemporaryDirectory(prefix='fiji-skill-test-') as temp:
            result=exercise(Path(temp),args.fiji)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
