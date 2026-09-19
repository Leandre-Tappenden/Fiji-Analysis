# Fiji-Analysis

A Codex skill for microscopy analysis with local Fiji/ImageJ. Start with
[SKILL.md](SKILL.md). First choose whether to reuse a previous run; otherwise
choose autonomous judgement, your own detailed request, or short guided questions.

New runs use `Fiji-Analysis-Results-YYYY-MM-DD-HHMMSS/`:

```text
Reports/              Experiment_report.html, Reproduce_in_Fiji.html,
                      Workflow_and_settings.md (the reusable protocol)
R_scripts/            Readable, commented scripts with an EDIT HERE section
Tables/               Main results, segmentation checks, sensitivity, statistics
QC_images/            Channel checks, segmentation and foci-count previews
Analysis_scripts/     Exact executed code/configuration and Script_guide.md
Graphs/               Presentation-ready PNGs
Additional_material/  Editable masks/ROIs and detailed run records
```

Original image names remain recognisable, with repeat tags where needed.
Keep scientific settings constant within each assay/comparable acquisition group;
per-image adaptive detection is an explicit exception. The skill guides method
selection from morphology and QC, not fixed universal thresholds or expected effects.

See [outputs](references/outputs.md), [workflow reuse](references/workflow-reuse.md),
[readable R example](references/editable-graph.R), and [execution](references/execution.md).
Reusing a protocol preserves scripts unchanged where compatible and reports every
necessary deviation. Guides must describe the actual analysis, not a generic template.

The maxima helper supports single-image `run` and `batch` with one Java compilation.
`project.py add/event --no-render` defers rendering until `project.py render`.
New runs use schema 3; old schema-1/2 runs retain their original paths.

```sh
python3 scripts/test_helpers.py --fiji /path/to/Fiji.app
```

Synthetic checks verify software behaviour, not biological accuracy. The skill does
not supply a universally validated nuclear segmentation model or 3D foci method.
