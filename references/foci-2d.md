# 2D fluorescence foci recipe

This is a method-selection guide, not a fixed assay protocol. The bundled helper implements only the deterministic maxima/assignment/export step. The agent must inspect data, construct and validate segmentation and preprocessing, and save their actual configuration and scripts.

## Measurement definition and decoding

Determine whether the endpoint is foci per nucleus, per cell, density or fluorescence intensity. Specify border treatment, subnuclear inclusions, eligible cells, and handling of merged/unresolved foci. Confirm whether EdU stratification is requested; record classification uncertainty instead of forcing every cell into a class.

Identify the source axes and stored samples before splitting channels. RGB photometric metadata can coexist with higher-bit-depth microscopy planes; do not let a convenience importer silently convert quantitative data to 8-bit. Verify representative pixel values across import paths. Decode original channels into scalar TIFFs with preserved numerical values and record the transformation. Do not treat acquisition-slot order as array order. Never project Z stacks or select a time point without a specified method.

## Nuclear segmentation

Use DAPI to define nuclear objects where appropriate. Candidate approaches include background correction, smoothing, thresholding, hole filling and watershed; learned models may be used if supported and validated. Choose scales from image resolution and observed objects, not numbers copied from a prior study.

Inspect over-splitting and merges before counting foci. Shape/size filters and border erosion change the sampled population and compartment: justify them and show excluded objects. Preserve full segmentation separately from the accepted counting mask. The accepted mask uses integer labels, 0 for background, one unique positive label per included nucleus. Label values must remain exactly representable; the helper rejects values above 16,777,216.

## Foci detection

Use the antibody plane in original numerical units. If applying background subtraction, a difference-of-Gaussians filter or other preprocessing, record exact parameters and units and preserve the resulting detection plane. Do not quantify a contrast-stretched preview. Saturation or insufficient resolution may prevent separating adjacent foci.

Fiji MaximumFinder prominence is a peak-to-surrounding-valley criterion. An absolute amplitude cutoff is a separate criterion on the detection plane; both must be named and reported. The bundled helper requires both explicitly. It uses strict maxima, configurable image-edge exclusion, a post-detection amplitude test, optional minimum peak separation, and optional assignment to an accepted nuclear mask. It does not implement an implicit support-pixel filter, automatic thresholds or automatic boundary erosion.

Choose a consistent assay-specific recipe from a condition-blinded representative pilot, then freeze it before looking at group outcomes. G4 and R-loop staining may require different settings; do not force a shared threshold simply because both are fluorescent puncta. Keep numerical preprocessing/detection settings constant within each assay and comparable acquisition group across treatment conditions and biological repeats. Varying image paths or display stretches is not varying the measurement. Per-image adaptive detection requires explicit user agreement and supporting validation; it is not the default. Fixed segmentation rules such as Otsu can yield image-specific thresholds: disclose this explicitly, save realised values, and use a fixed numerical boundary threshold if the user requires all numerical thresholds to be identical.

## Expert judgement during the pilot

Define a focus using distinct local contrast and spatially plausible punctate morphology in the original antibody image. Inspect accepted AND rejected candidates: dim credible puncta, diffuse staining, granular texture and saturated clusters. A local maximum alone is not proof of a focus. Avoid inflating counts by resolving texture into many peaks, while checking that a conservative choice does not discard genuine dim puncta. Select on image evidence or expert reference annotations, never agreement with an expected biological effect.

Prefer fixed within-assay detection thresholds when acquisition is comparable. Technical background noise is different from biological texture: a noise estimator can respond to treatment-dependent diffuse signal. Only propose adaptation when independent background evidence supports it; inspect whether it changes with biology, explain the trade-off, and ask before departing from the constant-settings default. Acquisition changes may justify separately calibrated groups; document their scope and comparability, not silent image-specific tuning.

For DAPI, derive plausible object sizes and smoothing scales from representative intact nuclei. Compare boundaries against original DAPI, including dim edges and bright internal structures. Watershed markers are candidate splits, not evidence of separate cells. Split touching objects when visible nuclear morphology supports separate nuclei; preserve irregular single nuclei. Inspect missed merges and artificial splits. Check small objects for debris or fragmentation before admitting them, without indiscriminately excluding biologically small nuclei. No hard-coded minimum size or watershed parameter is universally correct.

Write a short method rationale before batch execution: representative evidence, chosen approach, rejected alternatives, fixed settings scope and remaining ambiguity. Use a small predeclared sensitivity range to assess stability, not optimise treatment differences. Changes in the sign of an effect warrant uncertainty/review, not selecting whichever threshold recovers the preferred conclusion. Expert example crops should explain why a boundary/focus is accepted or rejected; keep those development examples separate from benchmark test images.

## Executable helper

`scripts/fiji_foci.py` compiles the bundled Java class against the selected local Fiji ImageJ jar. It needs Java and javac. Run `doctor` first. Pass a JSON configuration; all its processing values are consumed by the code and saved with file hashes and software version.

Required configuration fields:

| Field | Meaning |
|---|---|
| `image_id` | Source-derived filename stem with repeat tag where needed; safe punctuation supported, no path separators |
| `detection_image` | Absolute path to one scalar 2D TIFF, original or explicitly preprocessed |
| `review_image` | Absolute path to the corresponding unprocessed scalar channel for the overlay |
| `nuclei_labels` | Absolute path to accepted label TIFF, or null for image-wide detection |
| `amplitude` | Explicit finite absolute cutoff in detection-image units |
| `prominence` | Explicit finite nonnegative MaximumFinder prominence in those units |
| `min_distance_px` | Explicit finite nonnegative minimum distance; brighter peaks win, ties sorted y then x |
| `exclude_image_edges` | Boolean; passed to MaximumFinder |
| `display_min`, `display_max` | Explicit display range for the review channel; no effect on measurements |
| `units` | Detection image units, such as ADU or background-subtracted ADU |
| `preprocessing` | Plain-language description linking to the preprocessing parameters/script |

No unrecognised configuration keys are accepted, so misspelled thresholds cannot quietly fall back to defaults. The helper rejects stacks, RGB input, mismatched dimensions, nonfinite pixels and invalid labels. It assigns focus centres, not spot extents, to nuclei; any inward boundary exclusion belongs in the recorded counting mask. Minimum-distance suppression is applied within each nucleus when a mask is supplied.

```
python3 scripts/fiji_foci.py doctor --fiji /path/to/Fiji.app
python3 scripts/fiji_foci.py run --fiji /path/to/Fiji.app --config /project/Analysis_scripts/detection.json --out /project/Additional_material/Editable_masks_and_ROIs/RepA_source-name
```

Each image output contains `foci.csv`, `nuclei.csv` (including zero-count labels), `foci.zip`, `nuclei.zip` when applicable, `review.tif` with editable overlay, `preview.png`, the executed configuration, hashes, software information and stdout/stderr. A new output folder is required; a failed run stays marked failed. Register a selected preview and record the threshold decision in the project log. Aggregate per-image files using sample/repeat mappings from the manifest; the helper cannot infer those mappings.

The overlay is saved on a duplicate of the review channel. Raw files remain unchanged. Green point ROIs are detected peaks; yellow outlines are included nuclear labels. The overlay TIFF opens directly in Fiji, without resetting any existing ROI Manager. For detailed editing, load the generated ROI ZIPs into a saved or separate Fiji session. Recalculate after edits as described in outputs.md.

## Analysis

Retain focus coordinates, counts per included nucleus and totals per image. Preserve zero-count nuclei. Keep per-repeat summaries separate from pooled cell-level distributions; specify image versus cell weighting and pairing. If using EdU, validate the classification on its own channel, preserve ambiguous/missing states, and do not use antibody outcome to select an EdU gate.

Save commented R code in `R_scripts/`, CSV inputs in `Tables/`, and matching PNGs in `Graphs/`; map graph IDs to code/data using [outputs.md](outputs.md). Show individual biological repeats and effect sizes with uncertainty where appropriate; do not manufacture statistical power from the number of nuclei. State that detected antibody puncta are image-based measurements; molecular specificity requires appropriate experimental controls.
