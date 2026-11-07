"""Extract unverified bright-region proposals, including possible land false positives.

Land filtering is applied in the next pipeline stage.
Output IDs are per-scene labels, NOT track IDs.
"""
import argparse
import csv
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path,
                        default=Path(__file__).parent / "outputs/common_grid")
    parser.add_argument("--min-area-km2", type=float, default=0.1)
    args = parser.parse_args()
    if args.min_area_km2 <= 0:
        raise ValueError("Minimum proposal area must be positive")
    files = sorted(args.directory.glob("sar_*.tif"))
    if not files:
        raise FileNotFoundError("Run prepare_maps.py first")
    records, summaries = [], {}
    fig, axes = plt.subplots(1, len(files), squeeze=False,
                             figsize=(6 * len(files), 7), layout="constrained")
    for path, ax in zip(files, axes[0]):
        date = path.stem.removeprefix("sar_")
        with rasterio.open(path) as src:
            im = src.read(1)
            profile, affine = src.profile, src.transform
            crs = src.crs.to_string()
        valid = np.isfinite(im)
        low, high = np.percentile(im[valid], (2, 98))
        if high <= low:
            raise ValueError(f"No contrast in {path}")
        scaled = np.clip((np.nan_to_num(im, nan=low) - low) / (high-low), 0, 1)
        gray = np.round(scaled * 255).astype(np.uint8)
        filtered = cv2.medianBlur(gray, 5)
        threshold, _ = cv2.threshold(filtered[valid].reshape(-1, 1), 0, 255,
                                     cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binary = ((filtered > threshold) & valid).astype(np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        binary[~valid] = 0
        count, labels, stats, centers = cv2.connectedComponentsWithStats(binary, 8)
        pixel_area = abs(affine.a * affine.e - affine.b * affine.d)
        lookup = np.zeros(count, dtype=np.int32)
        scene_count = 0
        for label in range(1, count):
            x, y, width, height, area = stats[label]
            area_km2 = float(area * pixel_area / 1e6)
            if area_km2 < args.min_area_km2:
                continue
            scene_count += 1
            lookup[label] = scene_count
            col, row = centers[label]
            easting, northing = affine * (col + 0.5, row + 0.5)
            records.append({"date": date, "candidate_id": scene_count,
                            "area_km2": area_km2, "easting_m": easting,
                            "northing_m": northing, "crs": crs,
                            "status": "unverified_bright_region",
                            "touches_raster_edge": bool(x == 0 or y == 0 or
                                x + width == im.shape[1] or y + height == im.shape[0])})
        proposals = lookup[labels]
        profile.update(dtype="int32", nodata=0)
        with rasterio.open(args.directory / f"proposals_{date}.tif", "w", **profile) as dst:
            dst.write(proposals, 1)
            dst.update_tags(status="unverified_bright_regions", track_ids="false",
                            land_excluded="false")
        contours, _ = cv2.findContours((proposals > 0).astype(np.uint8),
                                       cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        display = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        display[~valid] = (230, 230, 230)
        cv2.drawContours(display, contours, -1, (255, 140, 0), 2)
        ax.imshow(display)
        ax.set_title(f"{date}: {scene_count} unverified proposals")
        ax.set_axis_off()
        summaries[date] = {"count": scene_count, "otsu_uint8": threshold}
    fields = ["date", "candidate_id", "area_km2", "easting_m", "northing_m", "crs",
              "status", "touches_raster_edge"]
    with (args.directory / "candidates.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    fig.suptitle("Bright-region proposals — NOT an iceberg inventory\n"
                 "Land/ice shelves included; no tracking or route inference")
    fig.savefig(args.directory / "candidate_review.png", dpi=140)
    plt.close(fig)
    (args.directory / "candidate_report.json").write_text(json.dumps({
        "min_area_km2": args.min_area_km2, "dates": summaries,
        "limitations": ["No land exclusion", "No validated precision or recall",
                        "Scene IDs are not tracking identities", "Not a navigation mask",
                        "Thresholds vary by scene; amplitudes not radiometrically calibrated"]}, indent=2))
    print(json.dumps(summaries))


if __name__ == "__main__":
    main()
