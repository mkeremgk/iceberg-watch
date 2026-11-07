"""Distance comparison helpers; callers must first establish comparable scenarios."""
from math import isfinite
from numbers import Real


def compare_distances(earlier_distance_m, later_distance_m):
    for name, value in (("earlier_distance_m", earlier_distance_m),
                        ("later_distance_m", later_distance_m)):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError(f"{name} must be a number in metres")
        if not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and non-negative")
    if earlier_distance_m == 0:
        raise ValueError("Earlier distance must be positive for percentage change")

    distance_change_m = later_distance_m - earlier_distance_m
    relative_change_pct = (distance_change_m / earlier_distance_m) * 100

    return {
        "distance_change_m": distance_change_m,
        "relative_change_pct": relative_change_pct,
    }


def compare_path_results(earlier_result, later_result):
    """Compare solver results, not entire scene reports or scientific validity."""
    statuses = {
        "earlier_status": earlier_result.get("status", "missing_status"),
        "later_status": later_result.get("status", "missing_status"),
    }
    if any(status != "model_path_found" for status in statuses.values()):
        return {
            "status": "comparison_unavailable",
            **statuses,
            "distance_change_m": None,
            "relative_change_pct": None,
        }

    changes = compare_distances(
        earlier_result.get("distance_m"), later_result.get("distance_m")
    )
    return {"status": "distance_comparison_computed", **statuses, **changes}


# Explicit model metadata prevents unrelated scenarios being subtracted.
COMPARISON_FIELDS = (
    "coordinate_crs", "grid_transform", "grid_shape", "grid_spacing_m",
    "movement_model", "obstacle_policy", "candidate_buffer_m", "start_projected",
)


def compare_scenarios(earlier, later):
    """Compare normalized, fixed-start scenarios after metadata/evidence checks.

    Each record contains date (YYYYMMDD), the COMPARISON_FIELDS, evidence
    (boundary_source, surface_source, interpretation), boundary_contact (bool),
    and result (one shortest_access output). Evidence presence is not validation
    of scientific correctness. Date-specific colony movement is not supported.
    """
    from datetime import datetime
    issues = []
    parsed_dates = []
    for label, record in (("earlier", earlier), ("later", later)):
        date = record.get("date")
        try:
            if not isinstance(date, str) or len(date) != 8:
                raise ValueError
            parsed_dates.append(datetime.strptime(date, "%Y%m%d"))
        except ValueError:
            issues.append(f"{label}: invalid date")
        for field in COMPARISON_FIELDS:
            if field not in record or record[field] is None:
                issues.append(f"{label}: missing {field}")
        evidence = record.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
        for field in ("boundary_source", "surface_source", "interpretation"):
            value = evidence.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(f"{label}: missing evidence.{field}")
        if record.get("boundary_contact") is not False:
            issues.append(f"{label}: analysis boundary contact absent or unsafe")
        if not isinstance(record.get("result"), dict):
            issues.append(f"{label}: missing solver result")
    if len(parsed_dates) == 2 and parsed_dates[0] >= parsed_dates[1]:
        issues.append("Dates must be distinct and increasing")
    for field in COMPARISON_FIELDS:
        if field in earlier and field in later and earlier[field] != later[field]:
            issues.append(f"Different {field}")
    if issues:
        return {"status": "incomparable_scenarios", "issues": issues,
                "distance_change_m": None, "relative_change_pct": None}
    result = compare_path_results(earlier["result"], later["result"])
    return {**result, "earlier_date": earlier["date"], "later_date": later["date"],
            "interpretation": "Conditional fixed-start model comparison; not observed penguin movement"}
