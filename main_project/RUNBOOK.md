# Running Iceberg Watch

Run commands from the repository root with the Python environment activated. The current comparison fixes the August boundary, colony start and passability assumptions while varying candidate barriers between dates. Installation is described in the root README, and external inputs are listed in [Data setup](submission/DATA_SETUP.md).

## Analysis and recorded outputs

```sh
python main_project/run_pipeline.py --paper-scenario
python main_project/corridor_scenario.py
python main_project/plot_corridor_scenario.py
python main_project/obstacle_sensitivity.py
python main_project/plot_obstacle_sensitivity.py
python main_project/fragmentation_audit.py
python main_project/plot_fragmentation_audit.py
python main_project/build_report.py --paper-scenario
```

The batch starts from prepared common grid maps and runs candidate extraction, environmental filtering, provisional association, conditional paths, candidate interventions, route geometry checks and review validation. The subsequent commands reproduce the corridor, mask sensitivity and fragmentation studies before refreshing `main_project/outputs/common_grid/index.html`. They do not change the nominal routing inputs.

Use `--rebuild-maps` only when intentionally regenerating the common grid from raw TIFF and XML inputs. Use `--with-sea-ice` for regional AMSR2 context, which is not a fine scale passability mask. The same prepared map command runs on AWS EC2 without a graphical interface. Raw map preparation was performed locally for the recorded submission results.

Each invocation writes stage order, source hashes, timestamps and success or failure under `main_project/outputs/common_grid/pipeline_runs/`. A failed stage stops the batch. These records establish execution, not environmental truth; a snapshot manifest only inventories files and does not prove that the current code generated every output. The 23 October AWS record describes 26 stages and 56 tests. The current distribution retains 53 tests after removing three checks belonging only to retired water experiments, and its documentation cleanup does not replace the historical execution record.

## Tests and route contracts

```sh
python main_project/submission/smoke_test.py
python main_project/validate_fixed_boundary.py
python main_project/validate_outputs.py
```

The smoke test needs no Antarctic inputs. The other checks require generated results and validate geometry, blocked cells, diagonal corners, target membership and distance sums. They cannot establish safe ice or independently verify water. `candidate_impact.py`, already included in the batch, tests each retained object alone and by removal, and stores source hashes, domain coverage and effects in `candidate_impact/results.json` beneath the output directory.

To refresh the local report without repeating analysis, run:

```sh
python main_project/delivery_readiness.py
python main_project/build_report.py --paper-scenario
python main_project/create_manifest.py
```

Refreshing a report does not make old evidence current. If source hashes no longer match an AWS execution record, retain that record as historical evidence rather than relabelling it as a new validation. Equal route lengths can also conceal different endpoints because the destination is a set of boundary cells; consult the route geometry results before interpreting a change.

## Association and detection review

The association form reviews proposed temporal identities, while the blinded detection form collects independent visual marks. Neither produces verified physical labels. Generate the forms with:

```sh
python main_project/build_review_ui.py
python main_project/build_detection_review.py
```

Open the HTML paths printed by the commands. The browser saves decisions through an explicit CSV or JSON download and does not silently update working files. For association decisions, retain `from_date`, `from_id`, `to_date` and `to_id`, then use `unreviewed`, `accepted`, `rejected` or `uncertain`. Reviewed rows require a reviewer name, with evidence recorded in notes. Validate a downloaded CSV before deliberately replacing the working review:

```sh
python main_project/review_associations.py --csv /path/to/review.csv
python main_project/evaluate_reviews.py
```

The validator rejects duplicate or unknown keys, unsupported decisions and missing reviewer fields. Review bindings check image pixels, proposal geometry, reference grids and association identities, so a new segmentation cannot silently inherit earlier opinions just because numeric IDs repeat. When a binding fails, preserve the earlier decisions and review the changed objects rather than regenerating the binding to bypass the error. These opinions do not alter automatic masks or tracks.

For blinded detection marks, the importer preserves the original JSON in a hash named archive:

```sh
python main_project/import_detection_review.py /path/to/annotations.json --reviewer reviewer_name
```

The optional `--completion-confirmed-in-conversation` flag is appropriate only when the annotator explicitly confirmed that every tile was reviewed. It retains the original checkbox states and records the confirmation rather than inferring missing labels. The current uncertain marks support descriptive overlap counts, not precision or recall.

## Independent environmental evidence

The general `run_access.py --date YYYYMMDD` path uses a reviewed environment when supplied and otherwise reports missing evidence. This is separate from the fixed August comparison and can legitimately report `no_reviewed_open_water_target` while the conditional comparison succeeds. Environmental labels are 0 for unknown, 1 for reference land, 2 for reviewed water, 3 for reviewed sea ice and 255 for missing data; a zero outside the land mask is not a water label.

`annotate_environment.py --help` describes dated surface annotations with source and reviewer fields. The optional `run_access.py --evidence PATH` input binds a declaration to the exact environment raster. Its fields are `date`, `environment_sha256`, `status` set to `human_reviewed_scenario`, `boundary_source`, `surface_source`, `interpretation`, `reviewer` and `limitations`. Missing or mismatched evidence prevents temporal comparison. This verifies bookkeeping and does not certify a source's scientific interpretation.

## Website export and checks

After preparing the recorded analysis and its AWS evidence, run:

```sh
python main_project/web_demo/build_exports.py
node --check main_project/web_demo/app.mjs
node main_project/web_demo/test_routing.mjs
node main_project/web_demo/test_route_geometry.mjs
node main_project/web_demo/test_explorer.mjs
python -m http.server 8765 --bind 127.0.0.1 --directory main_project/web_demo/dist
```

Open http://127.0.0.1:8765/ to inspect the exported site. The exporter validates scene geometry, saved path lengths and the relationship between nominal, corridor and intervention results. It copies only selected satellite previews, candidate overlays, calculated coordinates, aggregate results and the four final report documents. The paper image and digitised boundary layer are excluded.

The browser checks cover routing contracts, coordinate projection and the actual selection handlers using a minimal DOM. They do not certify pixel layout on every device. Yellow baseline dashes are painted over the pink selected path where both coincide, without shifting geographic coordinates. The separate synthetic panel recomputes in the browser; the Antarctic panel selects saved results and never starts an AWS job.

## Source archive

The delivery archive contains the analysis and website source, tests, final documentation, selected recorded evidence and a SHA256 manifest. The submission form draft and the maintainer's packaging script are omitted, together with local learning material, raw scenes, personal reviews and generated research directories. After extracting the ZIP, run `python3 main_project/submission/verify_package.py`, then the smoke test described above. The manifest verifies the delivered bytes; running the tests or analysis can subsequently create local output files. The research output folder contains additional reference material and should not be uploaded wholesale.
