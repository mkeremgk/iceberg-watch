"""Export a minimal website using saved research results, without the paper image or digitised reference boundary."""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
from PIL import Image
import rasterio

ROOT = Path(__file__).resolve().parents[2]
WEB = Path(__file__).resolve().parent
DATA = ROOT / 'main_project/outputs/common_grid'
OUT = WEB / 'dist'
DATES = ['20250716', '20250722', '20250728', '20250821']


def main():
    OUT.mkdir(exist_ok=True)
    assets = OUT / 'assets'
    assets.mkdir(exist_ok=True)
    hashes = {}

    def record(path):
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    dates = []
    common_grid = None
    for date in DATES:
        with rasterio.open(record(DATA / f'sar_{date}.tif')) as src:
            sar = src.read(1)
            shape, transform, crs = src.shape, src.transform, src.crs
            bounds = list(src.bounds)
        grid = (shape, transform, crs)
        if common_grid is not None and grid != common_grid:
            raise ValueError("Scene grids differ; route overlays would be misplaced")
        common_grid = grid
        with rasterio.open(record(DATA / f'review_classes_{date}.tif')) as src:
            if (src.shape, src.transform, src.crs) != (shape, transform, crs):
                raise ValueError(f'Mismatched candidate grid for {date}')
            classes = src.read(1)
        valid = np.isfinite(sar)
        lo, hi = np.percentile(sar[valid], [2, 98])
        gray = np.uint8(np.clip(np.nan_to_num((sar-lo)/(hi-lo), nan=0), 0, 1)*255)
        rgba = np.stack([gray, gray, gray, valid.astype(np.uint8)*255], axis=-1)
        Image.fromarray(rgba).resize((1100, 1100), Image.Resampling.BILINEAR).save(assets / f'{date}_sar.webp', quality=86)
        for name, mask, color in [('offshore', classes == 1, [255, 151, 71, 205]), ('review', classes >= 2, [111, 183, 224, 160])]:
            overlay = np.zeros((*shape, 4), dtype=np.uint8)
            overlay[mask] = color
            Image.fromarray(overlay).resize((1100, 1100), Image.Resampling.NEAREST).save(assets / f'{date}_{name}.png')
        report = json.loads(record(DATA / f'candidate_review_report_{date}.json').read_text())
        dates.append({'date': date, 'offshore_count': report['counts']['1'],
                      'review_count': sum(v for k,v in report['counts'].items() if k not in ['0','1']),
                      'bounds_m': bounds, 'crs': str(crs)})
    source = json.loads(record(DATA / 'fixed_boundary_scenario.json').read_text())
    def export_routes(experiments):
        rows = []
        for experiment in experiments:
            spacing = experiment['spacing_m']
            def coordinates(result):
                path = result.get('path', [])
                xy = [[bounds[0] + (c+.5)*spacing, bounds[3] - (r+.5)*spacing] for r,c in path]
                if xy:
                    length = sum(float(np.hypot(b[0]-a[0], b[1]-a[1])) for a,b in zip(xy, xy[1:]))
                    if abs(length-result['distance_m']) > 1e-5:
                        raise ValueError('Exported geometry disagrees with saved distance')
                elif result.get('distance_m') is not None:
                    raise ValueError('Distance without a saved path')
                return xy
            baseline = experiment['baseline']
            for result in experiment['dates']:
                rows.append({'date': result['date'], 'spacing_m': spacing,
                             'policy': experiment['policy'], 'status': result['status'],
                             'corridor_m': experiment.get('full_width_m', 0),
                             'distance_m': result.get('distance_m'),
                             'baseline_m': baseline.get('distance_m'),
                             'extra_m': result.get('extra_distance_vs_fixed_baseline_m', result.get('extra_vs_baseline_m')),
                             'path_xy_m': coordinates(result), 'baseline_xy_m': coordinates(baseline)})
        return rows
    routes = export_routes(source['experiments'])
    corridor_source = json.loads(record(DATA / 'corridor_scenario/results.json').read_text())
    if corridor_source['source_sha256'] != hashes[str((DATA / 'fixed_boundary_scenario.json').relative_to(ROOT))]:
        raise ValueError('Corridor results do not match the nominal source')
    corridors = export_routes(corridor_source['experiments'])
    impact = json.loads(record(DATA / 'candidate_impact/results.json').read_text())
    for name, digest in impact['input_sha256'].items():
        if hashlib.sha256((DATA/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Stale candidate impact input: {name}')
    evidence = json.loads(record(sorted(DATA.glob('aws_pipeline_validation_????????.json'))[-1]).read_text())
    public = {'scope': 'Fixed August boundary and colony start; changing candidate barriers. Not observed penguin routes.',
              'dates': dates, 'routes': routes, 'corridors': corridors, 'impact': impact,
              'aws': {k: evidence[k] for k in ['status', 'checked_date', 'unit_tests_passed', 'result_comparisons', 'limitations']},
              'aws_stage_count': len(evidence['execution']['steps']),
              'provenance': hashes}
    (OUT / 'results.json').write_text(json.dumps(public, indent=2)+'\n')
    for name in ['index.html', 'styles.css', 'app.mjs', 'routing.mjs', 'route_geometry.mjs']:
        shutil.copyfile(WEB / name, OUT / name)
    for name, source_name in [('technical-report.md','TECHNICAL_REPORT.md'),('architecture.md','ARCHITECTURE.md'),('data-setup.md','DATA_SETUP.md'),('sources.md','ASSET_RIGHTS.md')]:
        shutil.copyfile(ROOT / 'main_project/submission' / source_name, OUT / name)
    from render_documents import render_documents
    render_documents(OUT)
    print(f'Exported {len(dates)} dates and {len(routes)} recorded scenarios to {OUT}')


if __name__ == '__main__':
    main()
