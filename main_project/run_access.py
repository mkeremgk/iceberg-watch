"""Run explicit geometric access scenarios on reviewed environmental labels."""
from scenario_evidence import load_evidence, touches_unknown
from affine import Affine
import argparse
import json
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rasterio.transform import rowcol
from rasterio.warp import transform
from access import aggregate_masks,shortest_access
from map_io import DIRECTORY,read


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',default='20250716')
    parser.add_argument('--factor',type=int,default=5)
    parser.add_argument('--environment',help='Reviewed environment GeoTIFF; default generated provisional layer')
    parser.add_argument('--evidence',help='Date-matched evidence JSON bound to environmental raster SHA256')
    args=parser.parse_args()
    environment_path = args.environment or (DIRECTORY/f'environment_reviewed_{args.date}.tif' if (DIRECTORY/f'environment_reviewed_{args.date}.tif').exists() else DIRECTORY/f'environment_{args.date}.tif')
    env,p=read(environment_path)
    import rasterio
    with rasterio.open(environment_path) as source:
        if source.tags().get('date') != args.date:
            raise ValueError('Environment date must match the requested scene')
    if not np.isin(env,[0,1,2,3,255]).all():
        raise ValueError('Unexpected environment class codes')
    review,_=read(DIRECTORY/f'review_classes_{args.date}.tif',p)
    if p['crs'].to_epsg()!=32759 or p['transform'].b or p['transform'].d or not np.isclose(p['transform'].a,-p['transform'].e):
        raise ValueError('Expected square north-up EPSG:32759 grid')
    x,y=transform('EPSG:4326',p['crs'],[169.636085],[-73.348581])
    r,c=rowcol(p['transform'],x[0],y[0]);start=(int(r)//args.factor,int(c)//args.factor)
    passable,targets,obstacles=aggregate_masks(env,review,args.factor)
    spacing=p['transform'].a*args.factor
    base_cost=np.where(passable,1.,np.inf)
    baseline=shortest_access(base_cost,targets,start,spacing)
    scenarios=[]
    for buffer_m in [0,80,200]:
        # Apply buffers on the fine grid first, then conservatively aggregate.
        fine=(review==1).astype(np.uint8)
        radius=int(np.ceil(buffer_m/p['transform'].a))
        if radius:
            fine=cv2.dilate(fine,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1)))
        h,w=fine.shape
        blocked=fine.reshape(h//args.factor,args.factor,w//args.factor,args.factor).any(axis=(1,3))
        cost=base_cost.copy();cost[blocked]=np.inf
        result=shortest_access(cost,targets,start,spacing)
        result['candidate_buffer_m']=buffer_m
        if baseline['status']=='model_path_found' and result['status']=='model_path_found':
            result['extra_distance_m']=result['distance_m']-baseline['distance_m']
        scenarios.append(result)
    report={'date':args.date,'environment_file':str(environment_path),
        'grid_spacing_m':spacing,'colony_reference_verified_for_date':False,
        'model':'equal-distance movement on reviewed sea ice/open water; unknown/land/no-data/review zones blocked',
        'baseline':baseline,'candidate_scenarios':scenarios,
        'limitations':['Geometric scenario, not observed GPS or biological cost',
            'Sea-ice traversability is an explicit unvalidated assumption',
            'Candidate obstacles unverified; counterfactual is conditional on fixed reviewed environment',
            'Conservative aggregation can close narrow real passages; no start snapping',
            'Buffers are sensitivity settings, not calibrated position confidence']}
    # Fixed policy for cross-date comparison: first candidate scenario, no buffer.
    selected=scenarios[0]
    coarse_transform=p['transform'] * Affine.scale(args.factor)
    path=selected.get('path',[])
    boundary_contact=touches_unknown(path,env,args.factor)
    evidence_path=args.evidence or DIRECTORY/f'evidence_{args.date}.json'
    from pathlib import Path
    evidence=load_evidence(evidence_path,args.date,environment_path) if Path(evidence_path).exists() else {}
    if args.evidence and not Path(evidence_path).exists():
        raise FileNotFoundError(evidence_path)
    report['temporal_scenario']={
        'date':args.date,'coordinate_crs':str(p['crs']),
        'grid_transform':list(coarse_transform)[:6], 'grid_shape':list(passable.shape),
        'grid_spacing_m':spacing,'movement_model':'8-neighbour equal-distance; no corner cutting',
        'obstacle_policy':'offshore class 1; unknown and review zones blocked',
        'candidate_buffer_m':0,'start_projected':[x[0],y[0]],
        'boundary_contact':boundary_contact,'result':selected,
        # Source text must be supplied with a documented scenario, not inferred from a filename.
        'evidence':evidence,
        'boundary_check':'grid edge or adjacent unknown/no-data coarse cell; conservative',
    }
    (DIRECTORY/f'access_{args.date}.json').write_text(json.dumps(report,indent=2))
    if baseline['status']=='model_path_found':
        fig,ax=plt.subplots(figsize=(8,8),layout='constrained')
        ax.imshow(passable,cmap='gray');ax.contour(obstacles,levels=[.5],colors='orange',linewidths=.6)
        for result,label in [(baseline,'Without candidate barriers')]+[(s,f"Candidates + {s['candidate_buffer_m']} m") for s in scenarios]:
            if result['path']:
                route=np.array(result['path']);ax.plot(route[:,1],route[:,0],label=label)
        ax.scatter(start[1],start[0],marker='*',color='red');ax.legend(fontsize=7)
        ax.set_title('Conditional geometric access — NOT an observed penguin route')
        fig.savefig(DIRECTORY/f'access_{args.date}.png',dpi=140);plt.close(fig)
    else:
        (DIRECTORY/f'access_{args.date}.png').unlink(missing_ok=True)
    print(args.date,baseline['status'])

if __name__=='__main__':main()
