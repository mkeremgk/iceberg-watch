"""Fixed reference-path corridor scenarios; no claim that the corridor is solid ice."""
import hashlib
import json
from itertools import combinations
import cv2
import numpy as np
from map_io import DIRECTORY,read
from access import shortest_access
from compare_access import compare_path_results
from fixed_boundary_scenario import fill_candidates
from access import frontier
from validate_fixed_boundary import check_path


def corridor_mask(shape, path, spacing_m, full_width_m):
    if spacing_m<=0 or full_width_m<=0 or not path:
        raise ValueError('Positive width/spacing and reference path required')
    seed=np.ones(shape,np.uint8)
    for r,c in path:
        if not (0<=r<shape[0] and 0<=c<shape[1]):raise ValueError('Reference path outside grid')
        seed[r,c]=0
    distance=cv2.distanceTransform(seed,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)*spacing_m
    return distance<=full_width_m/2


def main():
    source=DIRECTORY/'fixed_boundary_scenario.json';nominal=json.loads(source.read_text())
    surface,p=read(DIRECTORY/'paper_scenario_surface_20250821.tif');h,w=surface.shape
    dates=[r['date'] for r in nominal['experiments'][0]['dates']]
    common=np.ones(surface.shape,bool);reviews={};input_hashes={}
    for name in ['paper_scenario_surface_20250821.tif']+[f'{kind}_{date}.tif' for kind in ('sar','review_classes') for date in dates]:
        path=DIRECTORY/name;input_hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    for date in dates:
        image,_=read(DIRECTORY/f'sar_{date}.tif',p);common&=np.isfinite(image)
        reviews[date],_=read(DIRECTORY/f'review_classes_{date}.tif',p)
    xy=(~p['transform'])*tuple(nominal['fixed_start_projected']);experiments=[];checked=0
    for original in nominal['experiments']:
        spacing=original['spacing_m'];factor=spacing//40;policy=original['policy']
        def blocks(a):return a.reshape(h//factor,factor,w//factor,factor)
        allowed=blocks((surface>0)&common).all(axis=(1,3));ribbon=blocks(surface==2).any(axis=(1,3))&allowed
        approach=allowed&~ribbon;target=frontier(ribbon,approach);domain=approach|target
        start=(int(xy[1])//factor,int(xy[0])//factor)
        reference=original['baseline'];by_date={r['date']:r for r in original['dates']}
        obstacles={}
        for date in dates:
            mask=fill_candidates(reviews[date],policy);mask[~common|(surface==0)]=False
            obstacles[date]=blocks(mask).any(axis=(1,3))
        previous={}
        for width in (500,1000,2000):
            corridor=corridor_mask(domain.shape,reference['path'],spacing,width)
            fixed_domain=domain&corridor;fixed_target=target&corridor
            baseline=shortest_access(np.where(fixed_domain,1.,np.inf),fixed_target,start,spacing)
            check_path(baseline,fixed_domain,fixed_target,start,spacing)
            assert baseline['status']=='model_path_found'
            assert abs(baseline['distance_m']-reference['distance_m'])<1e-6
            results=[]
            for date in dates:
                passable=fixed_domain&~obstacles[date]
                result=shortest_access(np.where(passable,1.,np.inf),fixed_target,start,spacing)
                found=check_path(result,passable,fixed_target,start,spacing)
                if found:
                    checked+=1
                    result['extra_vs_baseline_m']=result['distance_m']-baseline['distance_m']
                    result['extra_vs_unrestricted_m']=result['distance_m']-by_date[date]['distance_m']
                    assert result['extra_vs_unrestricted_m']>=-1e-6
                    if date in previous:assert result['distance_m']<=previous[date]+1e-6
                    previous[date]=result['distance_m']
                    result['endpoint_shift_from_baseline_m']=float(np.linalg.norm(np.array(result['end'])-reference['end'])*spacing)
                elif date in previous:raise AssertionError('Wider nested corridor lost a previously feasible path')
                result['date']=date;results.append(result)
            comparisons=[dict(earlier_date=a['date'],later_date=b['date'],**compare_path_results(a,b)) for a,b in combinations(results,2)]
            experiments.append(dict(spacing_m=spacing,policy=policy,full_width_m=width,
                half_width_m=width/2,baseline=baseline,dates=results,comparisons=comparisons))
    output=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),input_sha256=input_hashes,
        status='reference_path_corridor_counterfactual',experiments=experiments,paths_checked=checked,
        limitations=['Corridor is around the no-candidate model path, not a surveyed coastline or known ice corridor.',
        'Width is total width; cell centres within half-width of reference path cell centres are admitted.',
        'Reference path and corridor are fixed across dates within each grid/policy experiment.',
        'Same August target set is clipped to the corridor; no target relocation or obstacle removal.',
        'No-path means infeasible under these assumptions, not observed colony isolation.',
        'Visual agreement with a preferred route is not validation. No liquid-water classification added.'])
    folder=DIRECTORY/'corridor_scenario';folder.mkdir(exist_ok=True)
    (folder/'results.json').write_text(json.dumps(output,indent=2))
    lines=['# Fixed reference-path corridors','', 'Widths are total widths; this is NOT a verified ice corridor.','',
           '| Grid | Policy | Width (m) | Date | Route (km) | Extra vs unrestricted (m) | Status |',
           '|---:|---|---:|---|---:|---:|---|']
    for e in experiments:
        for r in e['dates']:
            distance=f"{r['distance_m']/1000:.3f}" if 'distance_m' in r else 'unavailable'
            extra=f"{r['extra_vs_unrestricted_m']:.1f}" if 'extra_vs_unrestricted_m' in r else 'unavailable'
            lines.append(f"| {e['spacing_m']} | {e['policy']} | {e['full_width_m']} | {r['date']} | {distance} | {extra} | {r['status']} |")
    lines+=['','## Limits','']+['- '+item for item in output['limitations']]
    (folder/'summary.md').write_text('\n'.join(lines)+'\n')
    print('Corridor trials:',sum(len(e['dates']) for e in experiments),'paths found/checked:',checked)

if __name__=='__main__':main()
