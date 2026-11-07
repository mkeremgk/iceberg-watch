"""Compare explicitly normalized date scenarios; never substitute paper assumptions."""
import json
from itertools import combinations
from html import escape
from compare_access import compare_scenarios
from plot_temporal import plot_pair
from map_io import DIRECTORY


def compare_records(records):
    dates=[r['date'] for r in records]
    if len(set(dates))!=len(dates):
        raise ValueError('Duplicate dates for one comparison policy')
    pairs=[]
    for a,b in combinations(sorted(records,key=lambda r:r['date']),2):
        result=compare_scenarios(a,b)
        pairs.append(dict(result,earlier_date=a['date'],later_date=b['date']))
    return pairs


def main():
    records=[]
    for path in sorted(DIRECTORY.glob('access_????????.json')):
        report=json.loads(path.read_text())
        # Missing normalized metadata is reported, not reconstructed by guessing.
        records.append(report.get('temporal_scenario',dict(date=report['date'],result=report['baseline'])))
    pairs=compare_records(records)
    result={'policy':'offshore candidates, zero buffer, fixed historical reference',
            'interpretation':'Conditional model comparison, not observed penguin movement.',
            'pairs':pairs}
    (DIRECTORY/'temporal_comparison.json').write_text(json.dumps(result,indent=2))
    rows=[]
    by_date={r['date']:r for r in records}
    # Remove prior pair plots so unavailable results cannot retain a stale visual.
    for old in DIRECTORY.glob('temporal_pair_*.png'):old.unlink()
    figures=[]
    for pair in pairs:
        if pair['status']=='distance_comparison_computed':
            name=f"temporal_pair_{pair['earlier_date']}_{pair['later_date']}.png"
            plot_pair(by_date[pair['earlier_date']],by_date[pair['later_date']],DIRECTORY/name)
            figures.append(f'<img style="max-width:100%" src="{name}" alt="Conditional paired model paths">')
    for pair in pairs:
        delta=pair.get('distance_change_m');pct=pair.get('relative_change_pct')
        reason='; '.join(pair.get('issues',[])) or pair['status']
        rows.append(f"<tr><td>{pair['earlier_date']} → {pair['later_date']}</td><td>{escape(pair['status'])}</td><td>{'Unavailable' if delta is None else f'{delta:.1f} m'}</td><td>{'Unavailable' if pct is None else f'{pct:.1f}%'}</td><td>{escape(reason)}</td></tr>")
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Temporal access comparison</title><style>body{font:16px system-ui;margin:40px;color:#183047}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}</style><h1>Temporal access comparison</h1><p>Missing evidence is not zero distance or proof of no access. August paper scenarios are separate and are not substituted into this series.</p><table><tr><th>Dates</th><th>Status</th><th>Distance change</th><th>Relative change</th><th>Reason</th></tr>'''+''.join(rows)+'</table>'+''.join(figures)+'</html>'
    (DIRECTORY/'temporal_comparison.html').write_text(page)
    print('Date pairs checked:',len(pairs))

if __name__=='__main__':main()
