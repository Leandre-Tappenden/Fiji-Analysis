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

Use the same algorithm and predefined adaptation rule across comparable groups. If settings vary by batch, record each actual value and its calibration evidence. Compare detection overlays at plausible low/primary/high settings on pilot images, and quantify sensitivity when it affects conclusions. Do not select a threshold from treatment p-values or expected biological direction.

## Executable helper

`scripts/fiji_foci.py` compiles the bundled Java class against the selected local Fiji ImageJ jar. It needs Java and javac. Run `doctor` first. Pass a JSON configuration; all its processing values are consumed by the code and saved with file hashes and software version.

Required configuration fields:

| Field | Meaning |
|---|---|
| `image_id` | Stable source identifier, safe letters/digits/underscore/hyphen |
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
python3 scripts/fiji_foci.py run --fiji /path/to/Fiji.app --config /project/provenance/detection.json --out /project/review/annotations/image-001
```

Each image output contains `foci.csv`, `nuclei.csv` (including zero-count labels), `foci.zip`, `nuclei.zip` when applicable, `review.tif` with editable overlay, `preview.png`, the executed configuration, hashes, software information and stdout/stderr. A new output folder is required; a failed run stays marked failed. Register a selected preview and record the threshold decision in the project log. Aggregate per-image files using sample/repeat mappings from the manifest; the helper cannot infer those mappings.

The overlay is saved on a duplicate of the review channel. Raw files remain unchanged. Green point ROIs are detected peaks; yellow outlines are included nuclear labels. The overlay TIFF opens directly in Fiji, without resetting any existing ROI Manager. For detailed editing, load the generated ROI ZIPs into a saved or separate Fiji session. Recalculate after edits as described in outputs.md.

## Analysis

Retain focus coordinates, counts per included nucleus and totals per image. Preserve zero-count nuclei. Keep per-repeat summaries separate from pooled cell-level distributions; specify image versus cell weighting and pairing. If using EdU, validate the classification on its own channel, preserve ambiguous/missing states, and do not use antibody outcome to select an EdU gate.

Save R code when producing R graphs. Show individual biological repeats and effect sizes with uncertainty where appropriate; do not manufacture statistical power from the number of nuclei. State that detected antibody puncta are image-based measurements; molecular specificity requires appropriate experimental controls.
