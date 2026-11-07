"""Descriptive single-reviewer assessment, not held-out tracking accuracy."""
import json
from collections import Counter
from map_io import DIRECTORY


def summarize(records):
    counts=Counter(r['decision'] for r in records)
    total=len(records)
    return {'total':total,'counts':dict(counts),
            'acceptance_fraction_all':counts['accepted']/total if total else None,
            'unresolved_fraction':(counts['uncertain']+counts['unreviewed'])/total if total else None}


def main():
    folder=DIRECTORY/'association_review'
    review=json.loads((folder/'review_summary.json').read_text())
    records=review['links']
    groups={}
    for row in records:
        groups.setdefault(row['from_date']+'_'+row['to_date'],[]).append(row)
    result={'overall':summarize(records),'date_pairs':{k:summarize(v) for k,v in groups.items()},
            'source_association_sha256':review['association_sha256'],
            'source_review_sha256':review['review_sha256'],
            'limitations':['One reviewer; no independent ground truth.',
                'Decisions may concern object identity, segmentation or whether the region is an iceberg.',
                'Rejected proposals are not necessarily incorrect temporal matches.',
                'Unproposed matches and missed icebergs are not evaluated; no recall estimate.',
                'Any tuning on these reviews requires a separate test set.'],
            'needs_attention':[r for r in records if r['decision'] in ('rejected','uncertain')]}
    (folder/'evaluation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    text=['# Human review assessment','', 'Descriptive review outcomes, not tracking accuracy.','',
          '| Date pair | Accepted | Rejected | Uncertain | Unreviewed |',
          '|---|---:|---:|---:|---:|']
    for pair,group in result['date_pairs'].items():
        c=group['counts'];text.append('| '+pair+' | '+' | '.join(str(c.get(k,0)) for k in ('accepted','rejected','uncertain','unreviewed'))+' |')
    text+=['','## Interpretation','']+['- '+s for s in result['limitations']]
    text+=['','## Attention queue','']
    for r in result['needs_attention']:
        text.append(f"- {r['from_date']}:{r['from_id']} → {r['to_date']}:{r['to_id']} — {r['decision']}: {r['notes']}")
    (folder/'evaluation.md').write_text('\n'.join(text)+'\n')
    print(result['overall'])

if __name__=='__main__': main()
