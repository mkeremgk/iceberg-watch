"""Rebuild solver masks and independently check fixed-boundary route contracts."""
import json
import math
import numpy as np
from map_io import DIRECTORY,read
from access import frontier
from fixed_boundary_scenario import fill_candidates


def check_path(result,allowed,target,start,spacing):
    if result['status']!='model_path_found':
        if result.get('path'):raise ValueError('Failed route contains path')
        return False
    path=result['path']
    if not path or tuple(path[0])!=tuple(start):raise ValueError('Wrong route start')
    if not target[tuple(path[-1])]:raise ValueError('Route misses fixed target')
    total=0.
    for i,(r,c) in enumerate(path):
        if not (0<=r<allowed.shape[0] and 0<=c<allowed.shape[1]) or not allowed[r,c]:
            raise ValueError('Route crosses blocked cell')
        if i:
            a,b=path[i-1];dr,dc=r-a,c-b
            if max(abs(dr),abs(dc))!=1:raise ValueError('Non-neighbour route step')
            if dr and dc and (not allowed[a,c] or not allowed[r,b]):raise ValueError('Corner cutting')
            total+=math.hypot(dr,dc)*spacing
    if not math.isclose(total,result['distance_m'],abs_tol=1e-6):raise ValueError('Wrong route distance')
    return True


def main():
    report=json.loads((DIRECTORY/'fixed_boundary_scenario.json').read_text())
    surface,p=read(DIRECTORY/'paper_scenario_surface_20250821.tif');h,w=surface.shape
    dates=sorted({r['date'] for e in report['experiments'] for r in e['dates']})
    common=np.ones(surface.shape,bool);reviews={}
    for date in dates:
        image,_=read(DIRECTORY/f'sar_{date}.tif',p);common&=np.isfinite(image)
        reviews[date],_=read(DIRECTORY/f'review_classes_{date}.tif',p)
    xy=(~p['transform'])*tuple(report['fixed_start_projected']);checked=0
    for experiment in report['experiments']:
        spacing=experiment['spacing_m'];f=int(spacing/40)
        def blocks(a):return a.reshape(h//f,f,w//f,f)
        allowed=blocks((surface>0)&common).all(axis=(1,3))
        ribbon=blocks(surface==2).any(axis=(1,3))&allowed
        approach=allowed&~ribbon;target=frontier(ribbon,approach);domain=approach|target
        start=(int(xy[1])//f,int(xy[0])//f)
        check_path(experiment['baseline'],domain,target,start,spacing)
        by_date={}
        for result in experiment['dates']:
            mask=fill_candidates(reviews[result['date']],experiment['policy']);mask[~common|(surface==0)]=False
            passable=domain&~blocks(mask).any(axis=(1,3))
            if check_path(result,passable,target,start,spacing):
                checked+=1
                extra=result['distance_m']-experiment['baseline']['distance_m']
                if extra < -1e-6 or not math.isclose(extra,result['extra_distance_vs_fixed_baseline_m'],abs_tol=1e-6):raise ValueError('Invalid baseline detour')
            by_date[result['date']]=result
        for comparison in experiment['comparisons']:
            if comparison['status']=='distance_comparison_computed':
                a=by_date[comparison['earlier_date']]['distance_m'];b=by_date[comparison['later_date']]['distance_m']
                if not math.isclose(b-a,comparison['distance_change_m'],abs_tol=1e-6):raise ValueError('Invalid date delta')
    output=dict(status='software_contracts_passed_not_scientific_validation',date_routes_checked=checked,
                experiments_checked=len(report['experiments']),checks=['fixed target and start','same common coverage','blocked cells','corner cutting','step length','baseline detour','date deltas'])
    (DIRECTORY/'fixed_boundary_validation.json').write_text(json.dumps(output,indent=2));print(output)

if __name__=='__main__':main()
