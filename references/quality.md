# QC and validation

Distinguish three questions: did the program run, do the images support this measurement, and how accurate is the measurement against an independent reference? Report each honestly. Passing file/table checks is not proof of biological accuracy.

## Before and during processing

Preflight all images before an expensive batch. Inventory readability, file identity, axes/C/Z/T, dtype, stored bit depth, acquisition metadata and calibration. Check channel availability at the pixel level as well as in metadata. A three-channel container can have an entirely empty channel. Check duplicate content and possible repeated fields; stage metadata may not establish independence.

Calculate per-image and per-object QC metrics appropriate to the assay: saturation at the camera's actual ceiling, background/noise, signal distribution, blur/focus flags, occupancy, object size and shape, touching objects, border exclusions and segmentation failure. Preserve these metrics even when no threshold is crossed. Flag criteria are assay-specific and must be recorded. Bright biology, treatment-dependent morphology or dense foci must not be silently removed as “bad quality”.

For each finding, log scope, evidence, affected endpoints and action. Examples:

| Finding | Proportionate action |
|---|---|
| Missing EdU, usable DAPI/antibody | Keep valid counts; EdU status missing; flag affected subgroup analysis |
| Antibody saturation | Flag unreliable intensity and potentially unresolved peaks; assess count usability in review |
| Unknown pixel size | Use pixels; do not invent physical areas or separation distances |
| Channel mapping unresolved | Resolve before a definitive named-channel measurement, or label an explicitly exploratory result |
| Corrupt image | Keep manifest row; record failure and missing measurements; continue independent usable images |
| New acquisition settings | Review compatibility and pilot; do not silently reuse a protocol outside its validated range |

## Pilot review

Sample across repeat, condition and acquisition regime; add random fields and difficult flagged examples. Avoid selecting only bright, isolated objects. Use original-resolution crops to inspect over-splitting, merging, boundary errors, dim false positives, clustered peaks and cytoplasmic signal. Keep condition labels hidden during tuning when practical. Treat inferred biological expectations as unavailable to the parameter selection step.

For a new method, compare a small number of plausible parameter settings, documenting the tradeoff. Sensitivity checks should cover both segmentation and detection when both can affect the endpoint. Freeze settings before comparing conditions. Keep numerical detection settings constant within each assay/comparable acquisition group. Per-image adaptation is an explicit user-agreed exception with a validated technical-background estimator; biological texture can contaminate noise estimates. See foci-2d.md for selection principles and workflow-reuse.md when applying a saved protocol.

## Quantitative validation

For a reusable protocol, obtain independently annotated representative images. Reserve held-out fields or an experiment that is not used for tuning. If available, have two experts annotate a subset to estimate disagreement. Do not call the earlier automated analysis ground truth.

Measure nucleus detection/split/merge errors, focus precision and recall with a justified spatial matching tolerance, and count bias per nucleus across signal/density strata. Check both localisation and counts: matching totals can conceal offsetting false positives and false negatives. Define how ambiguous or unresolved clusters are annotated. Choose acceptance limits from the intended use and expert agreement; do not invent a universal accuracy percentage.

Human checking of every focus is not the default workflow. After validation, automatically check all inputs and metrics, review all exceptions and a recorded random sample, and expand review when errors appear. Save the sampling seed/list. Show the validation status prominently when only visual QC is available.

## Before delivery

- Every source has a manifest/status row, including exclusions and failures.
- All included nuclei have rows, including zero foci. Missing channels do not become zeros.
- Per-focus assignment, per-nucleus totals and per-image totals reconcile. Excluded objects cannot silently contribute to included summaries.
- IDs, dimensions and coordinate conventions agree across original image, masks, overlays and tables. Reopen representative TIFFs and ROI ZIPs in Fiji and verify positions; previews alone cannot validate annotation encoding.
- Rerunning identical inputs/configuration/software yields the same output measurements; resume rejects changed inputs or settings.
- Exclusion and missingness rates are shown by group/repeat. Experimental units and pairing are correctly specified. With few biological repeats, report uncertainty and avoid treating cells as independent replicate experiments.
- The main output opens, figures have meaningful labels, and decisions are readable without examining source code.

## Skill evaluation scenarios

Exercise complete requests and requests missing channel/endpoint/output information. Include permuted channel order, missing EdU, empty but valid detection planes, zero-count nuclei, dense/touching objects, unknown calibration, corrupt files, mixed dimensions and interrupted processing. Check that earlier user choices persist, no source is overwritten, excluded analyses stay unread and unsupported 3D input is not silently flattened.

Use the bundled executable-helper test for technical regressions. Add expert-labelled data before declaring a biological protocol validated. Record software versions and the test scope; a synthetic maxima test says nothing about antibody specificity or segmentation accuracy on experimental images.
