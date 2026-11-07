"""Separate boundary-perturbation experiment; never edits production masks or paths."""
import hashlib
import json
from itertools import combinations
import cv2
import numpy as np
from map_io import DIRECTORY, read
from access import shortest_access
from access import frontier
from fixed_boundary_scenario import fill_candidates
from validate_fixed_boundary import check_path


def perturb(mask, offset_m, pixel_m=40):
    radius=abs(offset_m)/pixel_m
    if radius!=int(radius):raise ValueError('Offset must align with source pixels')
    radius=int(radius)
    if radius==0:return mask.copy()
    y,x=np.ogrid[-radius:radius+1,-radius:radius+1]
    kernel=(x*x+y*y<=radius*radius).astype('uint8')
    op=cv2.dilate if offset_m>0 else cv2.erode
    return op(mask.astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=0)>0


def bounds(earlier,later):
    if not earlier or not later:return None
    return [min(later)-max(earlier),max(later)-min(earlier)]


def main():
    source=DIRECTORY/'fixed_boundary_scenario.json';reference=json.loads(source.read_text())
    surface,p=read(DIRECTORY/'paper_scenario_surface_20250821.tif');h,w=surface.shape
    dates=[r['date'] for r in reference['experiments'][0]['dates']]
    common=np.ones(surface.shape,bool);reviews={}
    for date in dates:
        image,_=read(DIRECTORY/f'sar_{date}.tif',p);common&=np.isfinite(image)
        reviews[date],_=read(DIRECTORY/f'review_classes_{date}.tif',p)
    xy=(~p['transform'])*tuple(reference['fixed_start_projected']);trials=[];comparisons=[]
    offsets=[-80,-40,0,40,80]
    for experiment in reference['experiments']:
        spacing=experiment['spacing_m'];factor=spacing//40;policy=experiment['policy']
        def blocks(a):return a.reshape(h//factor,factor,w//factor,factor)
        allowed=blocks((surface>0)&common).all(axis=(1,3))
        ribbon=blocks(surface==2).any(axis=(1,3))&allowed
        approach=allowed&~ribbon;target=frontier(ribbon,approach);domain=approach|target
        start=(int(xy[1])//factor,int(xy[0])//factor);lengths={};nominal={r['date']:r for r in experiment['dates']}
        for date in dates:
            base=fill_candidates(reviews[date],policy);base[~common|(surface==0)]=False
            lengths[date]={}
            for offset in offsets:
                mask=perturb(base,offset);mask[~common|(surface==0)]=False
                passable=domain&~blocks(mask).any(axis=(1,3))
                result=shortest_access(np.where(passable,1.,np.inf),target,start,spacing)
                check_path(result,passable,target,start,spacing)
                if offset==0:
                    assert result['status']==nominal[date]['status']
                    if 'distance_m' in result:assert abs(result['distance_m']-nominal[date]['distance_m'])<1e-6
                if result['status']=='model_path_found':lengths[date][offset]=result['distance_m']
                trials.append(dict(date=date,spacing_m=spacing,policy=policy,offset_m=offset,**result))
            # Nested obstacle masks cannot reduce the optimum when expanded.
            found=[lengths[date][o] for o in offsets if o in lengths[date]]
            assert all(b>=a-1e-6 for a,b in zip(found,found[1:]))
        for a,b in combinations(dates,2):
            paired=[lengths[b][o]-lengths[a][o] for o in offsets if o in lengths[a] and o in lengths[b]]
            comparisons.append(dict(earlier=a,later=b,spacing_m=spacing,policy=policy,
                paired_range_m=[min(paired),max(paired)] if paired else None,
                independent_range_m=bounds(list(lengths[a].values()),list(lengths[b].values())),
                complete=len(lengths[a])==len(lengths[b])==len(offsets)))
    report=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),offsets_m=offsets,
        trials=trials,comparisons=comparisons,
        interpretation='Stress test of candidate boundaries, not an uncertainty distribution or confidence interval.',
        limitations=['Offsets are chosen one/two-source-pixel perturbations, not measured geolocation error.',
            'Paired range uses the same offset on both dates; independent range allows different offsets.',
            'Incomplete settings must retain failed-route statuses, not treat them as zero distance.',
            'Only candidate boundaries vary; water reference, start and domain stay fixed.'])
    folder=DIRECTORY/'obstacle_sensitivity';folder.mkdir(exist_ok=True)
    (folder/'results.json').write_text(json.dumps(report,indent=2))
    lines=['# Candidate-boundary sensitivity','',report['interpretation'],'',
           '| Dates | Grid / policy | Same-offset change (m) | Independent-offset change (m) | Complete |',
           '|---|---|---|---|---|']
    def fmt(v):return 'Unavailable' if v is None else f'{v[0]:.1f} to {v[1]:.1f}'
    for row in comparisons:
        lines.append(f"| {row['earlier']}–{row['later']} | {row['spacing_m']} / {row['policy']} | {fmt(row['paired_range_m'])} | {fmt(row['independent_range_m'])} | {row['complete']} |")
    lines+=['','## Limits','']+['- '+s for s in report['limitations']]
    (folder/'summary.md').write_text('\n'.join(lines)+'\n')
    print('Boundary trials:',len(trials),'failed:',sum(t['status']!='model_path_found' for t in trials))


if __name__=='__main__':main()
