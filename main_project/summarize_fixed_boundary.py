"""Descriptive sensitivity across fixed-boundary experiments, not confidence intervals."""
import json
from map_io import DIRECTORY


def summarize(experiments):
    pairs={}
    for experiment in experiments:
        for comparison in experiment['comparisons']:
            key=comparison['earlier_date']+'_'+comparison['later_date']
            pairs.setdefault(key,[]).append(dict(policy=experiment['policy'],spacing_m=experiment['spacing_m'],**comparison))
    result=[]
    for pair,trials in pairs.items():
        valid=[t for t in trials if t['status']=='distance_comparison_computed']
        values=[t['distance_change_m'] for t in valid]
        complete=len(valid)==len(trials)
        direction=('increase' if all(v>0 for v in values) else 'decrease' if all(v<0 for v in values) else 'unchanged' if all(v==0 for v in values) else 'mixed') if values and complete else 'incomplete'
        result.append(dict(date_pair=pair,valid_experiments=len(valid),total_experiments=len(trials),
            min_change_m=min(values) if values else None,max_change_m=max(values) if values else None,
            direction_across_tested_settings=direction,trials=trials))
    return result


def main():
    source=json.loads((DIRECTORY/'fixed_boundary_scenario.json').read_text())
    pairs=summarize(source['experiments'])
    (DIRECTORY/'fixed_boundary_summary.json').write_text(json.dumps(dict(pairs=pairs,
        interpretation='Ranges across tested settings only; not confidence intervals or independently verified physical effects.'),indent=2))
    lines=['# Fixed-boundary sensitivity','', 'Same August target/start; date-varying candidate masks. Not actual July open-water access.','',
           '| Dates | Min change (m) | Max change (m) | Direction across tested settings |','|---|---:|---:|---|']
    for p in pairs:
        lines.append(f"| {p['date_pair']} | {p['min_change_m']:.1f} | {p['max_change_m']:.1f} | {p['direction_across_tested_settings']} |" if p['min_change_m'] is not None else f"| {p['date_pair']} | unavailable | unavailable | incomplete |")
    lines+=['','Small differences can arise from segmentation and discretization. Agreement of direction is not statistical significance. Identical lengths do not imply identical obstacle masks or routes.']
    (DIRECTORY/'fixed_boundary_summary.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
