# Outputs and records

Choose one main deliverable with the user: review report, results CSV or figures PDF. A request already specifying CSV, R graphs, PDF or another format is sufficient direction. The choice changes presentation, not the availability of source-linked measurements and QC. Do not create multiple redundant formats by default.

Use a user-readable project and run name, such as `foci-study/run-001`. Put no results into the raw directory. The helpers refuse to initialise an existing run. Later processing may add files to that run, but must not replace earlier scientific results silently.

```
run-001/
  report.html                 Single review entry point; main output in report mode
  tables/                     Counts and summaries; main CSV in table mode
  figures/                    Requested graphs; figures.pdf is main in figures mode
  review/
    images/                   Selected channel, segmentation and detection previews
    annotations/              Full-resolution masks, overlay TIFFs and new ROI ZIPs
  provenance/
    brief.json                Measurement, sample design, output choice, validation state
    events.jsonl              Append-only record of QC findings and decisions
    quality_log.csv           Readable view of QC events
    decision_log.csv          Readable view of decisions
    artifacts.json            Registered previews and supporting files
    parameters.json           Actual configuration consumed by analysis scripts
    source_manifest.csv       Source identity, original filename, SHA-256, metadata, status
    scripts/                  Executed analysis and R scripts, if produced for this run
```

Keep caches and temporary intermediates outside the user-facing tree, in the host's work/scratch space. Do not copy raw datasets into output bundles by default. Large per-focus tables and all-image previews can be supporting files without appearing as hundreds of links in the main report.

## Tables

Use UTF-8 CSV with explicit column names and units. Use `NA` or an empty field for missing measurements, with a status/reason column; reserve numeric zero for a valid measured absence. Avoid using filenames alone as relational keys. Keep stable source IDs backed by the manifest, and run-specific object IDs with explicit mappings for split/merge edits.

Suggested image table columns:

`run_id,image_id,source_file,sample_id,repeat_id,condition,assay,status,n_nuclei,total_foci,mean_foci_per_nucleus,qc_flags`

Suggested nucleus table columns:

`run_id,image_id,nucleus_id,included,exclusion_reason,area_px2,area_um2,foci_count,edu_status,qc_flags`

Only populate physical units when calibration is trustworthy. A generic default of 1 pixel/unit does not establish micrometres. Record the coordinate convention (the maxima helper uses top-left origin and zero-based x/y pixel indices). For stacks include C/Z/T and preserve the actual axis mapping.

Summaries must state whether they are cell-weighted or image-weighted. Graphs must identify the experimental unit, n and uncertainty measure. A table row should be traceable to its original image, object mask and focus coordinates.

## Brief and logs

`project.py init` creates a draft brief. Fill the measurement and design fields from user input and inspection. Mark inferred details explicitly. Set `status` to `complete` only after outputs and coverage have been checked; `validation` separately describes whether there is expert annotation or only visual/technical review.

QC events require `stage`, `code`, `severity`, `scope`, `finding`, `action`, and `affected_metrics`. Severity is `info`, `warning` or `error`. Add measured values, units, criterion, image IDs and evidence paths when available. Resolve an event with a new event referencing the earlier event ID; do not erase history. Log missing data when discovered, even if other measurements can proceed.

Decision events require `stage`, `parameter`, `value`, `units`, `scope`, `reason`, `evidence`, and `chosen_by`. Add `alternatives`, `configuration_sha256` and whether the decision is provisional. Values must be the actual values used, including per-batch values where applicable. A statement such as “default threshold” is insufficient.

For a maxima decision, report in plain language: “Find local peaks on the background-subtracted antibody plane. Prominence 18 ADU; absolute cutoff 30 ADU; minimum separation 3 pixels. Chosen from the pilot comparison; applied to acquisition batch B.” These numbers are illustrative, not a recommended preset.

## Preview and correction records

Register each preview with image ID, stage, caption and display scaling. Label original versus processed channels. Log whether display limits are shared or individual. Never use a stretched PNG as quantitative input. Stage views should include exclusions and difficult cases, not only accepted detections.

Preview and annotation files supplied with `--image-id` are stored in a subfolder for that image, so repeated names such as `preview.png` do not collide. Use different filenames for multiple stages of the same image. Registered files are hashed; the renderer rejects changed files until they are preserved and registered as an explicit revision.

The review TIFF and ROI ZIPs from `fiji_foci.py` are editable ImageJ outputs. They do not implement automatic round-trip ingestion of user edits. After edits, export a new mask/ROI set, identify added/deleted/split/merged objects, rerun assignment and aggregation, and make a new version. Do not imply that editing a TIFF automatically updates a CSV.

## Helper use

Run `python3 scripts/project.py --help` for commands. Paths below are examples, to be substituted with actual authorised locations.

```
python3 scripts/project.py init --run /project/run-001 --source /project/raw --title "Foci study" --mode report
python3 scripts/project.py event --run /project/run-001 --kind decision --json /scratch/decision.json
python3 scripts/project.py event --run /project/run-001 --kind quality --json /scratch/quality.json
python3 scripts/project.py add --run /project/run-001 --file /scratch/segmentation.png --role preview --stage segmentation --image-id image-001 --caption "Nuclear boundaries; orange marks exclusions" --scaling "DAPI 0–1800 ADU; display only"
python3 scripts/project.py add --run /project/run-001 --file /scratch/counts.csv --role table --caption "Image-level counts"
python3 scripts/project.py render --run /project/run-001
```

The renderer is deliberately small and offline: no external fonts, JavaScript or network assets. It does not certify correctness. It displays the supplied completion and validation states, selected previews, links and logs; the agent remains responsible for checking the scientific content.
