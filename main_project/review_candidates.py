"""Separate bright proposals needing coastal/reference-ice review; not classification."""
import csv
import json
from pathlib import Path

import cv2
import numpy as np
from rasterio.features import rasterize


def review_regions(filtered, land_mask, features, transform, valid, output_dir, date="20250716"):
    ice_shapes = [(f["geometry"], 1) for f in features
                  if f["surface"] in {"ice shelf", "ice tongue", "rumple"}]
    reference_ice = rasterize(ice_shapes, out_shape=filtered.shape,
                             transform=transform, fill=0, dtype="uint8")
    resolution = abs(transform.a)
    if not np.isclose(abs(transform.e), resolution) or transform.b or transform.d:
        raise ValueError("Review distances require square north-up projected pixels")
    # This is a screening distance, NOT an estimated positional confidence bound.
    distance_m = cv2.distanceTransform((land_mask == 0).astype(np.uint8),
                                      cv2.DIST_L2, cv2.DIST_MASK_PRECISE) * resolution
    coastal_review_m = 500
    n, labels, stats, centers = cv2.connectedComponentsWithStats(
        filtered.astype(np.uint8), connectivity=8)
    class_lookup = np.zeros(n, dtype=np.uint8)
    near_invalid = cv2.dilate((~valid).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    records = []
    for label in range(1, n):
        x, y, w, h, area = stats[label]
        area_km2 = float(area * resolution ** 2 / 1e6)
        if area_km2 < 0.1:
            continue
        sl = np.s_[y:y+h, x:x+w]
        region = labels[sl] == label
        coast_distance = float(distance_m[sl][region].min())
        ice_fraction = float(reference_ice[sl][region].mean())
        coastal = coast_distance <= coastal_review_m
        ice = ice_fraction > 0
        # Entire components are retained for review; do not manufacture offshore fragments.
        code = 4 if coastal and ice else 3 if ice else 2 if coastal else 1
        edge = bool(x == 0 or y == 0 or x+w == filtered.shape[1]
                    or y+h == filtered.shape[0] or near_invalid[sl][region].any())
        if edge:
            code = 5
        class_lookup[label] = code
        records.append({"component_id": label, "area_km2": area_km2,
                        "class_code": code, "minimum_land_distance_m": coast_distance,
                        "reference_ice_overlap_fraction": ice_fraction,
                        "touches_data_edge": edge,
                        "easting_m": float((transform * (centers[label][0]+0.5, centers[label][1]+0.5))[0]),
                        "northing_m": float((transform * (centers[label][0]+0.5, centers[label][1]+0.5))[1])})
    classes = class_lookup[labels]
    output_dir = Path(output_dir)
    with (output_dir / f"review_candidates_{date}.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["component_id", "area_km2", "class_code",
            "minimum_land_distance_m", "reference_ice_overlap_fraction", "touches_data_edge", "easting_m", "northing_m"])
        writer.writeheader()
        writer.writerows(records)
    report = {"date": date, "coastal_review_m": coastal_review_m,
              "minimum_area_km2": 0.1,
              "classes": {"0": "not retained", "1": "offshore unverified proposal",
                          "2": "coastal review", "3": "historical ice overlap review",
                          "4": "coastal and historical ice review", "5": "data edge review"},
              "counts": {str(i): sum(r["class_code"] == i for r in records) for i in range(1,6)},
              "coastal_sensitivity_counts": {str(m): sum(r["minimum_land_distance_m"] <= m
                    for r in records) for m in [250, 500, 1000]},
              "limitations": ["500 m is a heuristic review distance, not accuracy calibration",
                  "2024 reference ice may have changed by July 2025",
                  "No review class is an automatic route barrier or confirmed iceberg"]}
    (output_dir / f"candidate_review_report_{date}.json").write_text(json.dumps(report, indent=2))
    return classes, report
