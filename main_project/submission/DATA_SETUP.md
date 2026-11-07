# Antarctic inputs and reproduction

The repository’s tests and synthetic demo require no external data. The real analysis
requires the following inputs. No credentials are included; authenticate with
the provider using your own account where required.

## Satellite scenes

Find these exact products in https://search.asf.alaska.edu/ (ASF Vertex) and
extract each SAFE directory under `data/raw/` at the repository root:

```
S1A_IW_GRDH_1SSH_20250716T100554_20250716T100623_060107_0777E2_DF98.SAFE
S1C_IW_GRDH_1SSH_20250722T100500_20250722T100529_003331_006B6A_E0AA.SAFE
S1A_IW_GRDH_1SSH_20250728T100554_20250728T100623_060282_077DE4_454A.SAFE
S1A_IW_GRDH_1SSH_20250821T100554_20250821T100623_060632_078B0E_346B.SAFE
```

Keep `measurement/*.tiff`, matching `annotation/*.xml`, calibration/noise
subdirectories and the SAFE manifest. Do not rename individual measurement files.

```sh
python main_project/prepare_maps.py --dates 20250716 20250722 20250728 20250821
```

This generates `main_project/outputs/common_grid/sar_DATE.tif` and geolocation
diagnostics. It uses experimental GCP/TPS resampling at 40 m in EPSG:32759,
not terrain-corrected calibrated science products. Disk and RAM requirements are
larger than the data-free test; this raw preprocessing was originally local.
The clean-room AWS validation starts from separately copied prepared maps.

## Reference surfaces

The clipped `data/reference/add/coulman_surfaces.json` and its SOURCE.md are
included under the source dataset's CC BY 4.0 terms. It is a project-created
clip/reprojection of v7.10, not a current observed coastline. The source and
transformation are documented in SOURCE.md. Do not substitute a newer coastline
and expect the recorded candidate IDs/results to remain identical.

## Supplying the approximate paper reference

`register_paper.py` expects a locally obtained, rights-cleared Figure 5 image at:
`data/reference/paper/figure5_reference_large.png` (1200 pixels wide, 1699 high).
Source: https://www.nature.com/articles/s43247-026-03764-w/figures/5 .
The source dimensions, extraction windows and colony-marker pixel are part of
this exploratory registration method. A different rendition is not interchangeable.
The prepared submission archive records its input hashes in `INPUT_HASHES.json`; the public website separately records hashes of the artifacts used for its export in `results.json`.
Do not merely resize a different rendition to pass the dimension check.

The image and digitised geometry are withheld from the public package pending distribution
rights clarification. Full Antarctic reproduction is therefore conditional on
lawfully supplying the exact reference, or implementing and validating an
independent reference workflow. See ASSET_RIGHTS.md.

## Running the analysis

```sh
python main_project/run_pipeline.py --paper-scenario
python main_project/corridor_scenario.py
python main_project/plot_corridor_scenario.py
python main_project/build_report.py --paper-scenario
```

Open `main_project/outputs/common_grid/index.html`. First run creates an
unreviewed association CSV. Historical human decisions are not bundled and must
not be fabricated. This does not prevent reproducing automatic candidate or
route results. Review opinions never alter automatic masks or tracks.

Optional sensitivity: `obstacle_sensitivity.py`, then `plot_obstacle_sensitivity.py`.
Optional recorded fragmentation study: `fragmentation_audit.py`, then
`plot_fragmentation_audit.py`. These do not change nominal production inputs.

## Colony and boundary interpretation

The locating reference at longitude 169.636085 and latitude -73.348581 comes from the approximate Coulman entry in the [SAR Emperor dataset](https://github.com/mla150/SAR-Emperor/blob/main/mcp_emperors_dissolve2.csv), whose huddle observations concern winter 2024. It is a historical reference rather than a measured July 2025 colony position. The fixed comparison instead uses the approximate colony marker registered from the August figure, at longitude 169.61303542 and latitude -73.37551599. Their roughly 3.09 kilometre separation is not evidence of colony movement, and the July counterfactuals use the same August start as the August scenario.

The figure supplies a literature supported interpretation of the August fast ice edge. It does not supply pixelwise truth for a synthetic target ribbon or independent July boundaries. The study's simplified access estimates and the project's obstacle following grid paths are different measurements, so numerical proximity between them is not independent validation. The paper's inferred route is not used as GPS ground truth or fitted to the calculated path.

Map preparation writes GCP residual diagnostics to `geolocation_report.json`, using withheld control points to evaluate the coordinate transformation. Those residuals measure agreement with the supplied control points rather than independent geographic accuracy. The 100 by 100 kilometre study grid is an inspection region rather than a validated ecological range, and its 40 metre sampling does not guarantee 40 metre positional accuracy.
