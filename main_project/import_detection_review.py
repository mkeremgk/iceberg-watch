"""Preserve user annotations and describe point/mask agreement, without accuracy claims."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from map_io import DIRECTORY, read
from build_detection_review import validate_annotations


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('annotations', type=Path)
    parser.add_argument('--reviewer', required=True)
    parser.add_argument('--completion-confirmed-in-conversation', action='store_true')
    args=parser.parse_args()
    raw=args.annotations.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    original=json.loads(raw)
    pack_id=original['pack_id']
    # The identifier is a content hash, never an arbitrary filesystem path.
    if len(pack_id)!=16 or any(c not in '0123456789abcdef' for c in pack_id):
        raise ValueError('Invalid pack identifier')
    folder=DIRECTORY/'detection_review'/pack_id
    pack=json.loads((folder/'pack.json').read_text())
    for name, expected in pack['source_sha256'].items():
        if Path(name).name!=name:
            raise ValueError('Invalid source filename')
        if hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Review image source changed: {name}')
    normalized=json.loads(raw)
    adjustments=[]
    if not str(normalized.get('reviewer','')).strip():
        normalized['reviewer']=args.reviewer
        adjustments.append('Blank reviewer supplied from conversation ownership; original retained.')
    unchecked=[t['id'] for t in normalized['tiles'] if t.get('reviewed') is not True]
    if unchecked and args.completion_confirmed_in_conversation:
        for tile in normalized['tiles']:tile['reviewed']=True
        adjustments.append('Completion based on explicit user statement that all tiles were reviewed; original checkbox states retained in archive.')
    validate_annotations(normalized,pack)
    archive=folder/'imports';archive.mkdir(exist_ok=True)
    archive_path=archive/f'{digest}.json'
    if archive_path.exists() and archive_path.read_bytes()!=raw:
        raise ValueError('Archive collision')
    archive_path.write_bytes(raw)
    normalized['provenance']={'original_sha256':digest,'adjustments':adjustments,
        'original_unchecked_tiles':unchecked,
        'global_qualification':'User stated no annotations are fully certain; retain class choices but treat all as unverified visual opinions.'}
    (folder/'annotations_imported.json').write_text(json.dumps(normalized,indent=2,ensure_ascii=False))
    tiles={t['id']:t for t in pack['tiles']};rasters={};raster_hashes={};rows=[]
    for tile in normalized['tiles']:
        meta=tiles[tile['id']];date=meta['date']
        if date not in rasters:
            proposal_path=DIRECTORY/f'proposals_{date}.tif';review_path=DIRECTORY/f'review_classes_{date}.tif'
            labels,profile=read(proposal_path)
            review,_=read(review_path,profile)
            read(DIRECTORY/f'sar_{date}.tif',profile)
            rasters[date]=(labels,review)
            for path in (proposal_path,review_path):raster_hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        labels,review=rasters[date]
        for n,point in enumerate(tile['points'],1):
            row=meta['row']+int(np.floor(point['y']));col=meta['col']+int(np.floor(point['x']))
            rows.append(dict(tile_id=tile['id'],point_number=n,date=date,
                user_class=point['class'],evidence_status='unverified_visual_opinion',
                source_row=row,source_column=col,raw_proposal_id=int(labels[row,col]),
                retained_review_class=int(review[row,col])))
    fields=['tile_id','point_number','date','user_class','evidence_status','source_row','source_column','raw_proposal_id','retained_review_class']
    with (folder/'point_mask_comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    counts=Counter(r['user_class'] for r in rows)
    summary={'pack_id':pack_id,'source_annotations_sha256':digest,'comparison_raster_sha256':raster_hashes,
        'reviewed_tiles':len(normalized['tiles']),'marks':len(rows),'user_class_counts':dict(counts),
        'points_on_raw_proposals':sum(r['raw_proposal_id']>0 for r in rows),
        'points_on_retained_regions':sum(r['retained_review_class']>0 for r in rows),
        'limitations':['All marks remain unverified visual opinions per user qualification.',
            'No precision, recall, segmentation IoU or confirmed iceberg count.',
            'A centre point outside a mask does not prove a missed object: dark interiors, uncertain class and segmentation all matter.',
            'Multiple points can refer to one object; one mask can merge objects.',
            'Empty tiles mean no user marks, not independently verified absence.',
            'Same reviewer and same SAR source; four spatial tiles repeated across dates.']}
    (folder/'comparison_summary.json').write_text(json.dumps(summary,indent=2))
    lines=['# Visual annotation / mask comparison','',f"{len(rows)} unverified marks across {len(normalized['tiles'])} tiles.",
        f"User-selected classes: {dict(counts)}.",
        f"Marks directly on raw proposal pixels: {summary['points_on_raw_proposals']}.",
        f"Marks directly on retained review-region pixels: {summary['points_on_retained_regions']}.",'',
        'These are point-overlap counts, NOT correct/incorrect object detections.','',
        '## Import provenance','']+['- '+s for s in adjustments]+['','## Interpretation','']+['- '+s for s in summary['limitations']]
    (folder/'comparison_summary.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('comparison_raster_sha256','limitations')},indent=2))


if __name__=='__main__':main()
