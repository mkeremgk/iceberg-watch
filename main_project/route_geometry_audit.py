"""Compare existing model paths; equal distance alone does not imply equal routes."""
import hashlib
import json
from itertools import combinations
import numpy as np
from map_io import DIRECTORY


def geometry(a, b, spacing):
    if not a or not b:
        return {'status': 'unavailable_path'}
    def edges(path):
        return {tuple(sorted((tuple(x), tuple(y)))) for x, y in zip(path, path[1:])}
    def length(segments):
        return sum(float(np.linalg.norm(np.subtract(x, y))) * spacing for x, y in segments)
    ea, eb = edges(a), edges(b)
    pa, pb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    distances = np.linalg.norm(pa[:, None, :] - pb[None, :, :], axis=2) * spacing
    return {'status': 'computed', 'identical_ordered_cells': a == b,
            'shared_edge_length_m': length(ea & eb),
            'earlier_only_edge_length_m': length(ea - eb),
            'later_only_edge_length_m': length(eb - ea),
            'endpoint_shift_m': float(np.linalg.norm(pa[-1] - pb[-1]) * spacing),
            'max_nearest_vertex_distance_m': float(max(distances.min(axis=0).max(), distances.min(axis=1).max()))}


def main():
    source = DIRECTORY / 'fixed_boundary_scenario.json'
    data = json.loads(source.read_text())
    rows = []
    for experiment in data['experiments']:
        for a, b in combinations(experiment['dates'], 2):
            rows.append(dict(policy=experiment['policy'], spacing_m=experiment['spacing_m'],
                             earlier_date=a['date'], later_date=b['date'],
                             **geometry(a.get('path'), b.get('path'), experiment['spacing_m'])))
    result = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'comparisons': rows,
              'limitations': ['Same fixed-boundary counterfactual; not observed animal movement.',
                             'Shared lengths compare exact grid edges within the same resolution.',
                             'Nearest-vertex distance is a discrete path metric, not continuous-curve Hausdorff distance.',
                             'Unique edges are counted once; solver paths are simple.',
                             'Identical paths do not imply identical obstacle masks.']}
    (DIRECTORY / 'route_geometry_audit.json').write_text(json.dumps(result, indent=2))
    lines = ['# Model route geometry comparison', '',
             'Same fixed boundary/start. Distances in metres; no observed penguin tracks.', '',
             '| Dates | Grid | Policy | Same cells | Shared length | Earlier only | Later only | Endpoint shift | Max nearest vertex |',
             '|---|---:|---|---|---:|---:|---:|---:|---:|']
    for row in rows:
        if row['status'] != 'computed':
            continue
        values = ' | '.join(f'{row[k]:.1f}' for k in ('shared_edge_length_m', 'earlier_only_edge_length_m',
                            'later_only_edge_length_m', 'endpoint_shift_m', 'max_nearest_vertex_distance_m'))
        lines.append(f"| {row['earlier_date']}–{row['later_date']} | {row['spacing_m']} | {row['policy']} | {row['identical_ordered_cells']} | {values} |")
    lines += ['', '## Limits', ''] + ['- ' + item for item in result['limitations']]
    (DIRECTORY / 'route_geometry_audit.md').write_text('\n'.join(lines) + '\n')
    print('Path geometry comparisons:', len(rows))


if __name__ == '__main__':
    main()
