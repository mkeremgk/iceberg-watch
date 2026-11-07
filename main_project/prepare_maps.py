"""Audit source geolocation and build provisional common-grid SAR inspection maps.

These are uncalibrated GRD amplitude images, not terrain-corrected SAR products.
TPS geolocation is an inspection baseline; held-out errors are reported explicitly.
"""
import argparse
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.transform import GCPTransformer, from_origin
from rasterio.warp import Resampling, reproject, transform

ROOT = Path(__file__).resolve().parent.parent
COLONY = (169.636085, -73.348581)
CRS = "EPSG:32759"


def audit(dataset, annotation):
    gcps, gcp_crs = dataset.gcps
    if not gcps or gcp_crs.to_epsg() != 4326:
        raise ValueError("Expected geographic GCPs in EPSG:4326")
    xml_points = ET.parse(annotation).getroot().findall(".//geolocationGridPoint")
    xml = {(int(p.findtext("line")), int(p.findtext("pixel"))):
           (float(p.findtext("longitude")), float(p.findtext("latitude")),
            float(p.findtext("height"))) for p in xml_points}
    if len(xml) != len(gcps):
        raise ValueError("XML and TIFF GCP counts disagree")
    differences = np.array([
        np.array(xml[(int(p.row), int(p.col))]) - (p.x, p.y, p.z)
        for p in gcps
    ])
    if not np.allclose(differences, 0, atol=1e-7, rtol=0):
        raise ValueError("XML and TIFF geolocation disagree")
    train = [p for i, p in enumerate(gcps) if i % 5 != 2]
    test = [p for i, p in enumerate(gcps) if i % 5 == 2]
    near_sea_level = np.array([abs(p.z) < 1 for p in test])
    result = {"gcp_count": len(gcps), "xml_tiff_max_abs_difference":
              np.abs(differences).max(axis=0).tolist(), "held_out_count": len(test)}
    for name, tps in [("polynomial", False), ("tps", True)]:
        with GCPTransformer(train, tps=tps) as converter:
            rows, cols = converter.rowcol([p.x for p in test], [p.y for p in test],
                                          op=lambda value: value)
        error = np.hypot(np.asarray(rows) - [p.row for p in test],
                         np.asarray(cols) - [p.col for p in test])
        result[name] = {"rmse_px": float(np.sqrt(np.mean(error ** 2))),
                        "max_px": float(error.max()),
                        "near_sea_level_count": int(near_sea_level.sum()),
                        "near_sea_level_rmse_px": float(np.sqrt(
                            np.mean(error[near_sea_level] ** 2)))}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dates", nargs="+", default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "main_project/outputs/common_grid")
    args = parser.parse_args()
    if args.dates is None:
        args.dates = sorted({re.search(r"_(\d{8})T", path.parent.parent.name).group(1)
                             for path in (ROOT / "data/raw").rglob("*.tiff")
                             if path.parent.name == "measurement" and re.search(r"_(\d{8})T", path.parent.parent.name)})
    if not args.dates:
        raise FileNotFoundError("No dated SAFE measurement files found")
    args.output.mkdir(parents=True, exist_ok=True)
    cx, cy = transform("EPSG:4326", CRS, [COLONY[0]], [COLONY[1]])
    cx, cy = cx[0], cy[0]
    # A 100 km search context, not a validated ecological analysis boundary.
    size, resolution = 2500, 40
    grid = from_origin(cx - 50000, cy + 50000, resolution, resolution)
    report = {"crs": CRS, "resolution_m": resolution, "size": [size, size],
              "colony_reference_lon_lat": COLONY, "colony_verified_for_2025": False,
              "transform": list(grid)[:6], "status": "provisional_inspection_only",
              "method": "GDAL TPS GCP warp; bilinear resampling; uncalibrated amplitude",
              "dates": {}}
    images, samples = [], []
    for date in args.dates:
        matches = [p for p in (ROOT / "data/raw").rglob(f"*{date}*.tiff")
                   if p.parent.name == "measurement"]
        if len(matches) != 1:
            raise ValueError(f"Expected one measurement for {date}, found {len(matches)}")
        path = matches[0]
        annotation = path.parent.parent / "annotation" / (path.stem + ".xml")
        with rasterio.open(path) as src:
            metrics = audit(src, annotation)
            output = np.full((size, size), np.nan, dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1), destination=output,
                gcps=src.gcps[0], src_crs=src.gcps[1], src_nodata=0,
                dst_transform=grid, dst_crs=CRS, dst_nodata=np.nan,
                resampling=Resampling.bilinear, warp_mem_limit=128,
                num_threads=2, MAX_GCP_ORDER=-1, ERROR_THRESHOLD=0.0,
            )
        valid = np.isfinite(output)
        if not valid.any():
            raise ValueError(f"No valid data after reprojection for {date}")
        metrics["valid_fraction"] = float(valid.mean())
        metrics["source"] = str(path.relative_to(ROOT))
        report["dates"][date] = metrics
        with rasterio.open(args.output / f"sar_{date}.tif", "w", driver="GTiff",
                           height=size, width=size, count=1, dtype="float32",
                           crs=CRS, transform=grid, nodata=np.nan, compress="deflate",
                           tiled=True) as dst:
            dst.write(output, 1)
            dst.update_tags(status="provisional_inspection_only",
                            quantity="uncalibrated_amplitude", geolocation="GCP_TPS")
        images.append(output)
        samples.append(output[::10, ::10].ravel())
        print(f"Prepared {date}: {100 * valid.mean():.1f}% valid")
    common = np.logical_and.reduce([np.isfinite(im) for im in images])
    with rasterio.open(args.output / "common_valid.tif", "w", driver="GTiff",
                       height=size, width=size, count=1, dtype="uint8", crs=CRS,
                       transform=grid, nodata=0, compress="deflate") as dst:
        dst.write(common.astype(np.uint8), 1)
    report["common_valid_fraction"] = float(common.mean())
    report["limitations"] = [
        "Held-out GCP errors are internal diagnostics, not independent positional accuracy.",
        "No terrain correction, radiometric calibration or precise cross-date registration.",
        "No validated water, land, iceberg or route classification.",
        "Historical colony point; no observed penguin GPS routes.",
        "40 m is output sampling, not guaranteed spatial resolution or accuracy.",
    ]
    (args.output / "geolocation_report.json").write_text(json.dumps(report, indent=2))
    values = np.concatenate(samples)
    low, high = np.percentile(values[np.isfinite(values)], (2, 98))
    fig, axes = plt.subplots(1, len(images), figsize=(6 * len(images), 7),
                             squeeze=False, layout="constrained")
    for ax, date, im in zip(axes[0], args.dates, images):
        ax.imshow(im, cmap="gray", vmin=low, vmax=high, extent=(-50, 50, -50, 50))
        ax.scatter(0, 0, color="red", marker="*", s=90)
        ax.set_title(date)
        ax.set_xlabel("Grid easting from reference (km)")
        ax.set_ylabel("Grid northing from reference (km)")
    fig.suptitle("Common 40 m grid — provisional geolocation\n"
                 "Star: historical approximate colony reference; not verified for 2025")
    fig.savefig(args.output / "comparison.png", dpi=140)
    plt.close(fig)
    print(f"Saved comparison and geolocation report to {args.output}")


if __name__ == "__main__":
    main()
