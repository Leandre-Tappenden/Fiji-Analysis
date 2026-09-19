# Simple results folders

Deliver one folder outside the raw directory, normally beside the user's project: `Fiji-Analysis-Results-YYYY-MM-DD-HHMMSS` in local time. Record timezone in the workflow. An informative study suffix is optional; respect a user-supplied name and never overwrite an existing run. Keep the main view understandable to someone who does not program.

```text
Fiji-Analysis-Results-2026-09-20-143000/
  Reports/
    Experiment_report.html
    Reproduce_in_Fiji.html
    Workflow_and_settings.md
  R_scripts/
    01_foci_by_repeat.R
  Tables/
    Main_results/                 Image/nucleus counts and plotted summaries
    Segmentation_checks/          Inclusion/exclusion and boundary/split checks
    Counting_sensitivity/         Threshold trials with actual settings
    Statistics/                   Effects, tests and uncertainty, when used
  QC_images/
    Channel_checks/
    Segmentation/
    Foci_counts/
  Analysis_scripts/
    Script_guide.md
    [exact executed code and consumed configurations]
  Graphs/
    01_foci_by_repeat.png
  Additional_material/
    Editable_masks_and_ROIs/       Per-source native masks, coordinates and overlays
    Run_records/                  Input index, file hashes, decisions and execution logs
    [other supporting material only when needed]
```

These are the default top-level folders; do not add `provenance`, `annotations`, `csv`, duplicate reports or a second result tree. Keep full-resolution masks, per-image helper bundles, exhaustive coordinate dumps, intermediate diagnostics and revision history in named subfolders of `Additional_material/`. Do not copy raw images or disposable caches by default. Publish consolidated useful measurements under `Tables/`, not every intermediate table. Keep source identity, consumed settings and scripts sufficient to regenerate omitted intermediates. No automatic migration of old runs.

`project.py init` creates schema-3 runs with this layout; it continues to read schema-1/2 runs in place. Internal role/category names are API vocabulary, not user-facing directory names. `annotation` routes to `Additional_material/Editable_masks_and_ROIs`; `provenance` routes to `Additional_material/Run_records`; `guide` routes to `Reports`. Register `Script_guide.md` as `analysis_script` to keep it beside the code.

## Recognisable source names

Preserve the original image stem in output folders, masks, previews and table columns. If repeated across experiments, prefix the repeat tag, e.g. `RepA_siCTRL_DRB+_R-loop_48`, not `img219` or `image001`. Retain meaningful punctuation when safe. Always save the exact original filename, relative source path and repeat label; derived names must be collision-checked before processing. If repeat plus stem is still ambiguous, append a meaningful folder/series tag (or a short hash as a last resort), preserving the readable stem. Map any necessary internal numeric ID explicitly; never make users consult a manifest just to recognise an image.

Use names such as `RepA_siCTRL_DRB+_R-loop_48_segmentation.png`. Multiple C/Z/T series require explicit series/plane tags. Keep original names in captions too. Per-image configuration files may differ in paths, IDs and display ranges without differing in scientific settings; document this distinction and keep a canonical assay/group settings configuration.

## Graphs, tables and editable R

Share a descriptive numbered stem across each PNG, R script and plotted summary CSV, e.g. `01_foci_by_repeat`. Shared input tables are preferable to unnecessary duplication. Register input CSVs and scripts before graphs, using `--graph-id` and repeatable `--uses` with run-relative paths. State row units (image, nucleus, independent repeat, statistical contrast) and measurement units.

R scripts are for a human to open and edit. Do not deliver minified code with a comment header. Use ordinary `#` comments throughout, generous blank lines, consistent indentation, descriptive variable names, section dividers and one meaningful operation per line. Avoid semicolon-packed statements and long nested expressions. Separate these sections visibly:

1. Purpose, exact input files/columns and row/measurement units; Rscript and RStudio instructions.
2. **EDIT HERE:** run folder, output folder, group order, labels, colours, point size, fonts, dimensions, resolution, legend and axis limits. Keep scientific choices distinct from cosmetic controls.
3. Read and validate saved tables; explain zeros, missing values and exclusions.
4. Prepare/aggregate plot data, with comments on independent units, weighting, pairing, error bars and statistics. Avoid single-letter data variables.
5. Build the graph in clearly commented stages.
6. Save named PNGs (and any requested extra formats), without overwriting canonical measurement tables.

See [editable-graph.R](editable-graph.R) for the expected formatting style; adapt its schema and design to the actual study, not its illustrative statistics blindly. Each graph or related panel set gets its own independently runnable script. A small shared helper is appropriate only for reused logic. Use saved CSVs; no hidden session objects, private absolute paths or package auto-installation. Resolve paths from the script or an explicit run folder, document RStudio use, and record dependencies once. Re-run delivered scripts from a different working directory and inspect the output. Labels must identify biological n and uncertainty; showing individual nuclei does not change the inferential unit.

## Reports and reproduction

`Reports/Experiment_report.html` is the main entry point, readable offline. Use a linked table of contents: summary/validation, experiment/question, channel evidence, results/graphs, method/sensitivity, selected QC/limitations, reproduction. Link graphs directly to their R scripts and input tables using paths relative to `Reports/`. Keep the original request and clarifications when requested. Explain consequential choices in prose; collapse detailed logs and full file lists rather than drowning the reader in records. Keep exhaustive all-image evidence in additional material.

`Reports/Workflow_and_settings.md` is mandatory and detailed enough for another agent to reapply the exact analysis. Follow [workflow-reuse.md](workflow-reuse.md). It must describe executed code and settings, not aspirational steps or a generic checklist. Include links to machine-readable configurations in `Analysis_scripts/`.

`Reports/Reproduce_in_Fiji.html` is a readable, offline, step-by-step guide with contents. Choose an original source filename/repeat, explain prerequisites, import order/bit depth, channel preparation, segmentation, detection, overlay review and export. Include actual settings and version-verified menus/buttons; label untested UI paths. Explain exactly how to open and run a supplied macro/script, its language, or the terminal commands required for Java/Python stages. Offer a slow single-image retry before batching. Do not imply menu commands reproduce non-equivalent Python segmentation or custom amplitude/separation rules. Never silently convert high-bit-depth RGB to 8-bit, reset ROI Manager or overwrite raw images. Distinguish GUI review from headless verification.

`Analysis_scripts/Script_guide.md` explains each executed file: newly written/adapted/reused origin, purpose, execution order, inputs/outputs/axes/dtypes, algorithm, configuration, dependencies, invocation, checks and limits. Put exact macro/Java/Python/R processing code and consumed configuration here as appropriate (graph R lives in `R_scripts/`). Reused scripts remain unchanged unless necessary; report all edits as described in workflow-reuse.md.

The helper does not invent a scientific workflow or automatically author these guides. The agent must create and inspect the study-specific documents before declaring the analysis complete. Check all local links, report images and table-of-contents anchors after final rendering.

## Tables and technical records

UTF-8 CSV, explicit column names/units; missing values are NA/empty with a reason, never zero. Retain valid zero-count nuclei. Suggested image columns:
`run_id,image_id,source_file,source_relative_path,repeat_id,condition,assay,status,n_nuclei,total_foci,mean_foci_per_nucleus,qc_flags`.
Nucleus rows add `nucleus_id,included,exclusion_reason,area_px2,area_um2,foci_count` as applicable. Report physical units only with verified calibration. Record zero-based top-left coordinates and any C/Z/T mapping. State cell versus image weighting and biological n.

The helper's draft brief is `Additional_material/Run_records/brief.json`: populate `design`, `channel_mapping`, `measurement`, `summary`, `open_questions`, `status` and `validation`. Completion and validation are separate. QC events require `stage,code,severity,scope,finding,action,affected_metrics`; decision events require `stage,parameter,value,units,scope,reason,evidence,chosen_by`. Save actual settings and reasons, resolve by appending events, and never erase previous records. Register selected previews with original source-derived ID, stage, caption and display scaling. Display stretching never changes measurement inputs.

Registered files are hashed and changed files require explicit revisions. Editing ROIs does not automatically update counts: preserve originals, record added/deleted/split/merged objects and rerun assignment/aggregation in a new version. Keep raw files unchanged.

## Helper commands

Run `python3 scripts/project.py --help`. Use `add/event --no-render` in loops, then `render` once at meaningful checkpoints. Commands below use placeholder paths and a source-derived ID:

```sh
python3 scripts/project.py init --run /project/Fiji-Analysis-Results-2026-09-20-143000 --source /project/raw --title "Foci study"
python3 scripts/project.py add --run /project/Fiji-Analysis-Results-2026-09-20-143000 --file /scratch/image_counts.csv --role table --category main_results --caption "Counts per original field" --no-render
python3 scripts/project.py add --run /project/Fiji-Analysis-Results-2026-09-20-143000 --file /scratch/01_foci_by_repeat.R --role r_script --graph-id 01_foci_by_repeat --uses Tables/Main_results/image_counts.csv --caption "Editable repeat plot" --no-render
python3 scripts/project.py render --run /project/Fiji-Analysis-Results-2026-09-20-143000
```

Table categories remain `main_results,qc_segmentation,qc_counting_sensitivity,stats`; preview categories remain `channel_testing,segmentation,foci_counts`. They map to the readable folder names above. `--image-id RepA_siCTRL_DRB+_R-loop_48` groups source-specific previews/native annotations. For graph registration pass its actual table/script dependencies via `--uses`. All dependencies must already exist and be registered. The renderer is offline and verifies file integrity; it does not certify scientific correctness.
