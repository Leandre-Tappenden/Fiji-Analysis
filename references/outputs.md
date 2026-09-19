# Outputs and records

Deliver one clearly named results folder outside the raw directory. Default entry point: `report.html`. Honour explicitly requested formats. Keep supporting files discoverable without making the user navigate provenance to find R code.

```text
run-001/
  report.html
  r_scripts/                      Editable R scripts, one per graph or related panel set
    01_nuclear_foci_by_repeat.R
  csv/
    main_results/                 Image/nucleus/focus measurements and graph data
      image_counts.csv
      01_nuclear_foci_by_repeat.csv
    qc_segmentation/              Included/excluded objects, boundary/split trials
    qc_counting_sensitivity/       Threshold trials with exact parameter columns
    stats/                        Repeat summaries, effects, tests, uncertainty
  qc_images/
    channel_testing/<image_id>/
    segmentation/<image_id>/
    foci_counts/<image_id>/
  analysis_scripts/               Exact executed Fiji macros, Java, Python, configs
    SCRIPT_GUIDE.md
    REPRODUCE_IN_FIJI.md
  graphs/                         Presentation-ready PNGs; PDF/SVG when useful/requested
    01_nuclear_foci_by_repeat.png
  annotations/<image_id>/         Editable ROI ZIPs, masks, overlay TIFFs
  provenance/                    Compact manifest, settings, decisions and execution records
```

`project.py init` creates these folders; populate only what the analysis uses. Keep logs, intermediate planes, compiler output and caches in work/scratch space unless needed to reproduce or audit a result. Preserve native execution bundles (including their configurations and per-image CSVs) under `annotations/<image_id>/`; publish the user-facing consolidated CSVs under `csv/`. Do not copy raw images by default or dump every temporary threshold-trial overlay into delivery. Keep the source manifest, consumed settings and raw-file identity sufficient to regenerate omitted intermediates.

### Naming and the graph-to-data contract

Use short descriptive lowercase filenames with underscores and a stable figure number. Share the stem across the graph, R script and its plotted CSV, e.g. `01_nuclear_foci_by_repeat`. Do not duplicate a large source CSV for each graph: a shared source such as `image_counts.csv` is fine when explicitly mapped. A plotted-data CSV is useful when it records an aggregation the user needs to inspect. Name QC previews with source ID, stage and variant, e.g. `img012_segmentation_primary.png`; connect IDs to original filenames in the manifest and captions. Avoid anonymous screenshots.

For each graph, register the R script and input CSVs, then register the figure with `--graph-id` and repeatable `--uses` paths. The report displays the graph-to-script-to-data mapping with clickable relative paths. All registered dependencies must exist and be registered before rendering; no guessed links. State whether each CSV contains image observations, individual nuclei, independent-repeat summaries or statistical effects.

### Editable R scripts

Each delivered graph script must run using the saved CSVs without rerunning Fiji or requiring hidden session objects. Use paths relative to the results folder, resolve them from the script location or an explicit run-root argument, and document both `Rscript` and RStudio use. Do not hard-code a user's home directory or install packages automatically. Save dependencies/versions once.

Include short human-readable comments explaining:

- Which CSV(s) and columns are read, the row unit and measurement units.
- Filters, missing values, zero counts, exclusions, group mapping, independent unit, weighting and aggregation.
- Statistics, pairing, error bars and any multiple-testing adjustment used for this graph.
- How the plot is built and which labels, colours, dimensions and formats the user can edit near the top.
- Exactly which graph and optional plotted-data/statistics files are written. Keep canonical measurement CSVs read-only; provide a configurable output directory for experiments with styling/analysis.

Use a shared R helper only for genuinely reused logic; save it alongside the graph scripts. Avoid a single opaque mega-script or identical copied calculations in every graph. Re-run the delivered script(s) from another working directory against saved CSVs and inspect representative results. Preserve native numeric values, sample labels and statistical units when matching a visual reference. Default PNGs should have readable labels and presentation-appropriate dimensions/resolution (for example 2400 × 1600 px); do not force every graph to the same aspect ratio.

### Analysis scripts and manual reproduction

Save every executed measurement/preprocessing script in `analysis_scripts/` (including Python stages outside Fiji), with used configurations or links to their canonical location. Create two study-specific guides, not generic placeholders:

- **`SCRIPT_GUIDE.md`:** for each file explain its purpose, whether newly written/adapted/reused and from where, execution order, inputs/axes/dtypes, outputs, algorithm steps, actual parameters and units, dependencies, command to run, checks, and limitations. Separate Fiji work from Python/R work. Tie commands to delivered files and source-manifest entries.
- **`REPRODUCE_IN_FIJI.md`:** choose one representative source by ID and filename; explain prerequisites and how to open it safely, verify import order/bit depth, prepare channels, segment, detect, inspect overlays and export. Include installed-version-verified menu paths/buttons and actual settings for UI-supported steps; label untested menu paths. Explain how to open/run the supplied macro or script, or give the exact terminal command for Java/Python helpers that cannot run in Fiji's Script Editor. Name the script language and working directory. Show expected intermediate checks, output paths and a slow single-image retry before batch use.

Do not imply that Fiji menu commands reproduce a Python segmentation algorithm exactly, or that “Find Maxima” alone implements custom amplitude/separation/assignment rules. Identify non-equivalent steps and provide the exact saved code route. Never silently convert a high-bit-depth RGB microscopy TIFF to 8-bit through an unsuitable importer. Do not reset the user's ROI Manager or overwrite raw images. Record GUI verification separately from headless execution.

### Report summary

Keep the report readable offline, with a linked table of contents near the top:

1. Summary and validation status.
2. Inferred experiment/question, confirmed design and remaining unknowns.
3. Channel attribution and evidence.
4. Results and graphs, linking each to its R script and CSVs.
5. Method, exclusions and counting/segmentation sensitivity.
6. QC findings, limitations and representative images.
7. Reproduction guides, organised file index and original prompt when requested.

Use the brief's `design`, `channel_mapping`, `measurement`, `summary` and `open_questions` fields, rather than putting scientific prose only into an opaque JSON dump. The helper renders these sections and a grouped file index. Include the literal relative filename in links so users can find it on disk. Keep all-image evidence linked behind selected previews instead of embedding hundreds of images. Report completion separately from biological validation. Preserve the original request via `init --prompt` when requested. Check TOC anchors and local file links after final render.

## Tables

Use UTF-8 CSV with explicit column names and units. Use `NA` or an empty field for missing measurements, with a status/reason column; reserve numeric zero for a valid measured absence. Avoid using filenames alone as relational keys. Keep stable source IDs backed by the manifest, and run-specific object IDs with explicit mappings for split/merge edits.

Suggested image table columns:

`run_id,image_id,source_file,sample_id,repeat_id,condition,assay,status,n_nuclei,total_foci,mean_foci_per_nucleus,qc_flags`

Suggested nucleus table columns:

`run_id,image_id,nucleus_id,included,exclusion_reason,area_px2,area_um2,foci_count,edu_status,qc_flags`

Only populate physical units when calibration is trustworthy. A generic default of 1 pixel/unit does not establish micrometres. Record the coordinate convention (the maxima helper uses top-left origin and zero-based x/y pixel indices). For stacks include C/Z/T and preserve the actual axis mapping.

Summaries must state whether they are cell-weighted or image-weighted. Graphs must identify the experimental unit, n and uncertainty measure. A table row should be traceable to its original image, object mask and focus coordinates.

## Brief and logs

`project.py init` creates a draft brief (layout/schema version 2 for new runs; existing version-1 reports remain readable). Fill the measurement and design fields from user input and inspection. Mark inferred details explicitly. Set `status` to `complete` only after outputs and coverage have been checked; `validation` separately describes whether there is expert annotation or only visual/technical review.

QC events require `stage`, `code`, `severity`, `scope`, `finding`, `action`, and `affected_metrics`. Severity is `info`, `warning` or `error`. Add measured values, units, criterion, image IDs and evidence paths when available. Resolve an event with a new event referencing the earlier event ID; do not erase history. Log missing data when discovered, even if other measurements can proceed.

Decision events require `stage`, `parameter`, `value`, `units`, `scope`, `reason`, `evidence`, and `chosen_by`. Add `alternatives`, `configuration_sha256` and whether the decision is provisional. Values must be the actual values used, including per-batch values where applicable. A statement such as “default threshold” is insufficient.

For a maxima decision, report in plain language: “Find local peaks on the background-subtracted antibody plane. Prominence 18 ADU; absolute cutoff 30 ADU; minimum separation 3 pixels. Chosen from the pilot comparison; applied to acquisition batch B.” These numbers are illustrative, not a recommended preset.

## Preview and correction records

Register each preview with image ID, stage, caption and display scaling. Label original versus processed channels. Log whether display limits are shared or individual. Never use a stretched PNG as quantitative input. Stage views should include exclusions and difficult cases, not only accepted detections.

Preview and annotation files supplied with `--image-id` are stored in a subfolder for that image (previews also grouped by category), so repeated names such as `preview.png` do not collide. Use different filenames for multiple stages of the same image. Registered files are hashed; the renderer rejects changed files until they are preserved and registered as an explicit revision.

The review TIFF and ROI ZIPs from `fiji_foci.py` are editable ImageJ outputs. They do not implement automatic round-trip ingestion of user edits. After edits, export a new mask/ROI set, identify added/deleted/split/merged objects, rerun assignment and aggregation, and make a new version. Do not imply that editing a TIFF automatically updates a CSV.

## Helper use

Run `python3 scripts/project.py --help` for commands. Paths below are examples, to be substituted with actual authorised locations.

```
python3 scripts/project.py init --run /project/run-001 --source /project/raw --title "Foci study" --mode report
python3 scripts/project.py event --run /project/run-001 --kind decision --json /scratch/decision.json
python3 scripts/project.py event --run /project/run-001 --kind quality --json /scratch/quality.json
python3 scripts/project.py add --run /project/run-001 --file /scratch/segmentation.png --role preview --stage segmentation --image-id image-001 --category segmentation --caption "Nuclear boundaries; orange marks exclusions" --scaling "DAPI 0–1800 ADU; display only"
python3 scripts/project.py add --run /project/run-001 --file /scratch/counts.csv --role table --category main_results --caption "Image-level counts" --no-render
python3 scripts/project.py add --run /project/run-001 --file /scratch/01_nuclear_foci_by_repeat.R --role r_script --caption "Plot repeat-level nuclear foci" --graph-id 01_nuclear_foci_by_repeat --uses csv/main_results/counts.csv --no-render
python3 scripts/project.py add --run /project/run-001 --file /scratch/01_nuclear_foci_by_repeat.png --role figure --caption "Nuclear foci by independent repeat" --graph-id 01_nuclear_foci_by_repeat --uses csv/main_results/counts.csv --uses r_scripts/01_nuclear_foci_by_repeat.R --no-render
python3 scripts/project.py render --run /project/run-001
```

The renderer is deliberately small and offline: no external fonts, JavaScript or network assets. It does not certify correctness. It displays the supplied completion and validation states, selected previews, links and logs; the agent remains responsible for checking the scientific content.

For bulk registration and log writes use `--no-render`, then render once; registration still hashes each file and the final renderer verifies all hashes/dependency links. CSV categories are `main_results`, `qc_segmentation`, `qc_counting_sensitivity`, `stats`; preview categories are `channel_testing`, `segmentation`, `foci_counts`. Use roles `analysis_script` and `guide` for the analysis code and its two guides. A PNG, PDF or SVG may be the primary figures output. Old runs retain their original folder layout; do not silently migrate them.
