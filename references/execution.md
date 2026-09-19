# Local Fiji execution

Prefer Fiji's scripting/API operations for reproducible processing and its graphical interface for review. State which stages actually run in Fiji and which run in Python or R. A hybrid workflow is acceptable when transparent and reproducible.

The bundled helpers use Python 3's standard library. The Java helper uses the local `ij-*.jar`, Java runtime and compiler; it does not install or update Fiji, download plugins, or change user preferences. Image decoding, segmentation and R plotting may require additional dependencies; inspect available tools and use an isolated environment for missing packages when authorised.

`fiji_foci.py doctor` reports the selected Fiji path, ImageJ jar, Java, javac and version. Prefer an explicit user-selected Fiji path. Otherwise the helper checks common local application/Desktop locations and refuses ambiguity. When no bundled Java/compiler is available, it can use the runtime/compiler on PATH and reports that choice. Compatibility is established by compiling and probing; do not assume Apple Silicon and x86 Java are interchangeable.

The Python launcher passes arguments as a list, uses a timeout and records the exact command and process output. Numerical settings come from validated JSON. It never builds a shell command from filenames. Compilation occurs in a temporary directory and source files are hashed. Outputs are marked started/complete/failed in `execution.json`; only a zero exit and the complete expected file set yield complete status. This is execution status, not scientific validation.

For operations beyond the maxima helper, use available parameterised SciJava scripts, ImageJ macros or supported plugin APIs. Test required operations on a pilot before batch execution. Include script identity, parameters, software/plugins, channel mapping and preprocessing in the workflow and additional run records. Do not depend on the “current image” in headless code.

Original ImageJ ROI Manager and WindowManager functionality is restricted in headless mode. Use explicit ImagePlus references, Overlay and ROI encoding for batch outputs; use a graphical session for user interaction. PyImageJ also has macOS interactive-mode constraints. If a plugin requires UI, use a tested GUI path or explain the limitation. Do not silently substitute a different measurement.

To review, open the generated `review.tif` in Fiji using the host's available app/file tools. It contains the reviewed scalar image and overlay; use the source manifest to open other original channels as needed. Verify overlay alignment and ROI encoding on representative outputs. Do not clear existing user windows, reset the ROI Manager or change installation settings to make a demonstration work.

## Efficient batch execution

Use the same JSON schema as single-image execution:

```bash
python3 scripts/fiji_foci.py batch --fiji /path/to/Fiji.app \
  --configs /run/Analysis_scripts/configs/RepA_field-01.json /run/Analysis_scripts/configs/RepB_field-01.json \
  --out /run/Additional_material/Editable_masks_and_ROIs --workers 2
```

The batch validates configurations and unique IDs before starting, compiles Java and probes versions once, then runs isolated image processes with per-image timeouts and output/hash/status records. Default workers is 1; explicitly raise it only within available RAM/CPU (maximum 8). Results stay in input order. Failed images remain failed and other valid images continue; the CLI exits nonzero if any image fails. The helper refuses existing per-image folders rather than assuming they are valid checkpoints. Resume orchestration must first verify input, configuration, code/software and output hashes, skip only matching complete images, and place changed/failed revisions in a new run.

Python callers can reuse `prepared_helper(env)` and pass its context to `run(..., prepared=helper)`; all workers must finish before that context closes. No persistent global class cache or monkey-patching is needed. This saves compilation/probing overhead; each image still starts its own JVM and produces full native annotations. It is not a measurement-algorithm change or a guaranteed wall-clock speedup.

Decode images and compute masks once per unchanged source/settings during pilot trials. Keep bulky intermediate data in scratch with bounded memory, retaining exact transformation code and regeneration paths. Batch log/artifact writes with `project.py ... --no-render`; one final render checks registered hashes and links. Do not concurrently mutate a single project's event/artifact registry.

For delivery, follow [outputs.md](outputs.md): measurement code belongs in `Analysis_scripts/`, graph code in `R_scripts/`. Write the study-specific workflow, script and UI guides from the actual tested execution path; do not invent menu equivalence for stages executed outside Fiji.

## Smoke test

```
python3 scripts/test_helpers.py --fiji /path/to/Fiji.app
```

The test makes synthetic scalar images and nuclear labels in a temporary directory, runs the installed Fiji code and checks known detections, zero-count objects, strict input rejection, source preservation, native ROI/TIFF outputs, parameter effects and project logs/report links. It uses no experimental data and leaves the requested test results only when `--keep` is supplied. It does not validate a biological assay or provide manual-annotation accuracy.

## Authoritative references

- ImageJ parameterised headless scripting: https://imagej.net/scripting/headless
- PyImageJ limitations and local-runtime troubleshooting: https://py.imagej.net/en/latest/Troubleshooting.html
- ImageJ MaximumFinder API: https://imagej.net/ij/developer/api/ij/ij/plugin/filter/MaximumFinder.html
- OpenAI skill structure and tool workflow guidance: https://developers.openai.com/plugins/build/skills

Check current documentation when a version-specific problem arises; avoid adding speculative compatibility fixes to the skill.
