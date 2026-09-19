# Fiji-Analysis

A Codex skill for reproducible microscopy analysis with local Fiji/ImageJ.
Start with [SKILL.md](SKILL.md). The first interaction offers a choice between
providing study/graph preferences and letting the agent use documented judgement.

New analysis runs use one results folder:

```text
report.html          Summary, contents and links to code, data and QC
r_scripts/           Commented, editable graph scripts
csv/                 Main results, segmentation QC, threshold trials and statistics
qc_images/           Channel testing, segmentation and foci-count previews
analysis_scripts/    Executed code, SCRIPT_GUIDE.md and REPRODUCE_IN_FIJI.md
graphs/              Presentation-ready PNGs and requested additional formats
annotations/         Native editable Fiji overlays, ROIs and masks
provenance/          Source manifest, configurations and execution/decision records
```

See [output conventions](references/outputs.md) for naming and graph-to-data links,
and [execution guidance](references/execution.md) for local requirements.
The guides in each run must describe that study's actual code and settings; they
are not automatically generated biological protocols.

The maxima helper supports `run` for one image and `batch` to compile Java once
for several images. `project.py add/event --no-render` defers report generation
until `project.py render`. Older runs retain their original paths.

Run the technical checks against a local Fiji installation:

```sh
python3 scripts/test_helpers.py --fiji /path/to/Fiji.app
```

These synthetic checks verify software behaviour, not segmentation accuracy or
antibody specificity. The skill does not supply a universally validated nuclear
segmentation model or a 3D foci method.
