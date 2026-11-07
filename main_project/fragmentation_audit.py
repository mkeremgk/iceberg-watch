"""Screen nearby offshore components, without merging them or changing tracks."""
import csv
import json
import cv2
import numpy as np
from map_io import DIRECTORY,read


def nearby_pairs(labels, ids, radius):
    pairs=set();allowed=set(ids)
    y,x=np.ogrid[-radius:radius+1,-radius:radius+1]
    kernel=(x*x+y*y<=radius*radius).astype('uint8')
    for identity in ids:
        rows,cols=np.where(labels==identity)
        if not len(rows):continue
        r0=max(0,int(rows.min())-radius);r1=min(labels.shape[0],int(rows.max())+radius+1)
        c0=max(0,int(cols.min())-radius);c1=min(labels.shape[1],int(cols.max())+radius+1)
        crop=labels[r0:r1,c0:c1]
        expanded=cv2.dilate((crop==identity).astype('uint8'),kernel)>0
        for other in np.unique(crop[expanded]):
            if int(other) in allowed and other!=identity:pairs.add(tuple(sorted((int(identity),int(other)))))
    return sorted(pairs)


def main():
    land,p=read(DIRECTORY/'land_mask.tif');scenes=[]
    for path in sorted(DIRECTORY.glob('sar_????????.tif')):
        date=path.stem[4:];im,_=read(path,p);proposal,_=read(DIRECTORY/f'proposals_{date}.tif',p)
        _,labels,stats,_=cv2.connectedComponentsWithStats(((proposal>0)&(land==0)&np.isfinite(im)).astype('uint8'),connectivity=8)
        with (DIRECTORY/f'review_candidates_{date}.csv').open() as f:records=list(csv.DictReader(f))
        ids=[int(r['component_id']) for r in records if r['class_code']=='1']
        for row in records:
            identity=int(row['component_id'])
            assert abs(stats[identity,cv2.CC_STAT_AREA]*1600/1e6-float(row['area_km2']))<1e-9
        trials=[{'max_pixel_centre_gap_m':radius*40,'pairs':nearby_pairs(labels,ids,radius)} for radius in (1,2,4)]
        scenes.append(dict(date=date,offshore_components=len(ids),trials=trials))
    result=dict(scenes=scenes,interpretation='Nearby regions are screening candidates, not proven fragments of one object.',
        limitations=['Distances refer to pixel centres on the 40 m grid, not exact physical coastlines.',
            'Different true icebergs can be close; proximity alone cannot justify merging.',
            'Wide dark gaps can split one object without triggering the screen.',
            'No production label, association or obstacle mask is modified.'])
    folder=DIRECTORY/'fragmentation_audit';folder.mkdir(exist_ok=True)
    (folder/'results.json').write_text(json.dumps(result,indent=2))
    lines=['# Fragmentation screening','',result['interpretation'],'',
           '| Date | Offshore components | Pairs <=40 m | Pairs <=80 m | Pairs <=160 m |',
           '|---|---:|---:|---:|---:|']
    for scene in scenes:lines.append('| '+scene['date']+' | '+str(scene['offshore_components'])+' | '+' | '.join(str(len(t['pairs'])) for t in scene['trials'])+' |')
    lines+=['','## Limits','']+['- '+s for s in result['limitations']]
    (folder/'summary.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__=='__main__':main()
