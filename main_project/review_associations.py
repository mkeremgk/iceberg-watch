"""Validate human decisions separately from automatic associations; never rewrite tracks."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from map_io import DIRECTORY
from review_provenance import verify_binding

KEYS = ('from_date', 'from_id', 'to_date', 'to_id')
DECISIONS = {'unreviewed', 'accepted', 'rejected', 'uncertain'}


def key(row):
    return tuple(str(row[k]) for k in KEYS)


def validate_reviews(links, rows):
    current = {key(link): link for link in links}
    if len(current) != len(links):
        raise ValueError('Duplicate automatic association keys')
    reviewed = {}
    for row in rows:
        identity = key(row)
        if identity not in current:
            raise ValueError(f'Stale or unknown association: {identity}')
        if identity in reviewed:
            raise ValueError(f'Duplicate review: {identity}')
        decision = row.get('decision', '').strip()
        if decision not in DECISIONS:
            raise ValueError(f'Invalid decision: {decision}')
        reviewer = row.get('reviewer', '').strip()
        if decision != 'unreviewed' and not reviewer:
            raise ValueError('A reviewer is required for a human decision')
        reviewed[identity] = dict(decision=decision, reviewer=reviewer,
                                  notes=row.get('notes', '').strip())
    records = [dict(link, **reviewed.get(key(link), dict(
        decision='unreviewed', reviewer='', notes=''))) for link in links]
    return dict(counts=dict(Counter(r['decision'] for r in records)), links=records,
                missing_review_rows=len(current.keys() - reviewed.keys()),
                interpretation='Human association opinions; not verified iceberg identities or GPS tracks. Automatic tracks unchanged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=DIRECTORY/'association_review/human_review.csv')
    args = parser.parse_args()
    bound=verify_binding(DIRECTORY)
    source = DIRECTORY/'association_report.json'
    links = json.loads(source.read_text())['links']
    with args.csv.open(newline='') as handle:
        result = validate_reviews(links, list(csv.DictReader(handle)))
    result['geometry_binding_verified']=bound
    result['association_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    result['review_sha256'] = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    output = DIRECTORY/'association_review/review_summary.json'
    output.write_text(json.dumps(result, indent=2))
    print('Human review:', result['counts'])


if __name__ == '__main__':
    main()
