"""User-approved counterfactual: fixed August boundary/start, date-varying candidate masks."""
import json
from itertools import combinations
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_io import DIRECTORY,read
from access import shortest_access
from access import frontier
from compare_access import compare_path_results


def fill_candidates(review,policy):
    if policy not in ('offshore_only', 'all_retained'):
        raise ValueError(f'Unknown obstacle policy: {policy}')
    selected=(review==1) if policy=='offshore_only' else (review>0)
    contours,_=cv2.findContours(selected.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    filled=np.zeros(review.shape,np.uint8)
    cv2.drawContours(filled,contours,-1,1,cv2.FILLED)
    return filled>0


def main():
    dates=sorted(p.stem[4:] for p in DIRECTORY.glob('sar_????????.tif'))
    surface,p=read(DIRECTORY/'paper_scenario_surface_20250821.tif')
    paper=json.loads((DIRECTORY/'paper_access_scenario.json').read_text())
    common=np.ones(surface.shape,bool);reviews={};reference=None
    for date in dates:
        im,_=read(DIRECTORY/f'sar_{date}.tif',p);common&=np.isfinite(im)
        if date == '20250821':reference=im
        reviews[date],_=read(DIRECTORY/f'review_classes_{date}.tif',p)
    xy=(~p['transform'])*tuple(paper['start_projected']);h,w=surface.shape
    experiments=[]
    for factor in (2,5):
        spacing=40*factor
        def blocks(a):return a.reshape(h//factor,factor,w//factor,factor)
        allowed=blocks((surface>0)&common).all(axis=(1,3))
        ribbon=blocks(surface==2).any(axis=(1,3))&allowed
        approach=allowed&~ribbon
        # Fix targets BEFORE date-varying obstacles: no moving the goalposts.
        target=frontier(ribbon,approach)
        traversable=approach|target
        start=(int(xy[1])//factor,int(xy[0])//factor)
        baseline=shortest_access(np.where(traversable,1.,np.inf),target,start,spacing)
        for policy in ('offshore_only','all_retained'):
            results=[]
            for date in dates:
                obstacles=fill_candidates(reviews[date],policy)
                obstacles[~common|(surface==0)]=False
                blocked=blocks(obstacles).any(axis=(1,3))
                result=shortest_access(np.where(traversable&~blocked,1.,np.inf),target,start,spacing)
                path=result.get('path',[])
                # Domain proximity warning distinct from known coastline.
                contact=any(r in (0,traversable.shape[0]-1) or c in (0,traversable.shape[1]-1) for r,c in path)
                if path:
                    assert not any(blocked[r,c] or not traversable[r,c] for r,c in path)
                    assert target[tuple(path[-1])]
                result.update(date=date,grid_edge_contact=contact)
                if result['status']==baseline['status']=='model_path_found':
                    result['extra_distance_vs_fixed_baseline_m']=result['distance_m']-baseline['distance_m']
                results.append(result)
            comparisons=[dict(compare_path_results(a,b),earlier_date=a['date'],later_date=b['date']) for a,b in combinations(results,2)]
            experiments.append(dict(spacing_m=spacing,policy=policy,baseline=baseline,dates=results,comparisons=comparisons))
    report=dict(status='fixed_boundary_counterfactual_not_observed_temporal_access',approval_date='2026-10-18',
        fixed_boundary_date='20250821',fixed_start_projected=paper['start_projected'],
        source='https://www.nature.com/articles/s43247-026-03764-w/figures/5',experiments=experiments,
        limitations=['August boundary/passability held fixed hypothetically for July; not July water evidence.',
        'Differences reflect candidate masks including detection errors, not proven iceberg motion alone.',
        'Common valid coverage, fixed start, fixed target and fixed rules within each experiment.',
        'Offshore-only excludes suspect coastal regions; all-retained includes potential false positives.',
        'No GPS, biological cost or independent water classification claim.'])
    (DIRECTORY/'fixed_boundary_scenario.json').write_text(json.dumps(report,indent=2))
    fig,axes=plt.subplots(2,2,figsize=(13,12),layout='constrained');t=p['transform']
    extent=(t.c/1000,(t.c+w*40)/1000,(t.f-h*40)/1000,t.f/1000)
    lo,hi=np.nanpercentile(reference,[2,98]);allpoints=[]
    for ax,experiment in zip(axes.flat,experiments):
        ax.imshow(reference,cmap='gray',vmin=lo,vmax=hi,extent=extent)
        for result in experiment['dates']:
            if result['path']:
                cells=np.asarray(result['path']);s=experiment['spacing_m']
                x=(t.c+(cells[:,1]+.5)*s)/1000;y=(t.f-(cells[:,0]+.5)*s)/1000
                allpoints.extend(zip(x,y));ax.plot(x,y,lw=1.6,label=f"{result['date']}: {result['distance_m']/1000:.2f} km")
            else:ax.plot([],[],label=f"{result['date']}: {result['status']}")
        ax.set_title(f"{experiment['policy']} / {experiment['spacing_m']} m")
        ax.legend(fontsize=8);ax.set_aspect('equal');ax.set(xlabel='Easting (km)',ylabel='Northing (km)')
    if allpoints:
        a=np.array(allpoints);low=a.min(axis=0)-3;high=a.max(axis=0)+3
        for ax in axes.flat:ax.set_xlim(low[0],high[0]);ax.set_ylim(low[1],high[1])
    fig.suptitle('Fixed August boundary/start — date-varying candidate obstacles\nAugust background for orientation only; NOT actual July water conditions')
    fig.savefig(DIRECTORY/'fixed_boundary_scenario.png',dpi=130);plt.close(fig)
    for e in experiments:print(e['spacing_m'],e['policy'],[(r['date'],round(r['distance_m']) if 'distance_m' in r else r['status']) for r in e['dates']])

if __name__=='__main__':main()
