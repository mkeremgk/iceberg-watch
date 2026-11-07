"""User-approved, paper-derived August scenario, separate from reviewed surface truth."""
import json
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rasterio.features import rasterize
from access import shortest_access
from map_io import DIRECTORY,read,write


def main():
    folder=DIRECTORY.parents[2]/'data/reference/paper'
    evidence=json.loads((folder/'paper_draft_20250821.geojson').read_text())
    if evidence['date']!='20250821':raise ValueError('Paper reference date mismatch')
    image,p=read(DIRECTORY/'sar_20250821.tif');land,_=read(DIRECTORY/'land_mask.tif',p)
    review,_=read(DIRECTORY/'review_classes_20250821.tif',p)
    if evidence['coordinate_crs']!=p['crs'].to_string():raise ValueError('Paper/grid CRS mismatch')
    inverse=~p['transform']
    edge=np.array([inverse*tuple(xy) for xy in evidence['features'][0]['geometry']['coordinates']])
    start_xy=evidence['features'][1]['geometry']['coordinates'];start_pixel=inverse*tuple(start_xy)
    if not np.all(np.diff(edge[:,1])>0):raise ValueError('Edge must be monotonic in image rows')
    h,w=image.shape;rows,cols=np.indices((h,w))
    edge_x=np.interp(np.arange(h)+.5,edge[:,1],edge[:,0])[:,None]
    # Finite local domain supported by the published edge; no extrapolation to rest of ROI.
    span=(rows+.5>=edge[0,1])&(rows+.5<=edge[-1,1])
    domain=span&(cols+.5>=edge_x-25000/40)&(cols+.5<=edge_x+1000/40)
    surfaces=json.loads((DIRECTORY.parents[2]/'data/reference/add/coulman_surfaces.json').read_text())
    fixed_ice=rasterize([(f['geometry'],1) for f in surfaces['features'] if f['surface']!='land'],
                       out_shape=image.shape,transform=p['transform'],fill=0,dtype='uint8')>0
    fixed=(land>0)|fixed_ice|~np.isfinite(image)|~domain
    # Scenario obstacle hypothesis: all retained bright proposals, including coastal review.
    # Fill internal holes, never assume dark fissures through a bright region are a corridor.
    candidate=(review>0).astype(np.uint8)
    contours,_=cv2.findContours(candidate,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    filled=np.zeros_like(candidate);cv2.drawContours(filled,contours,-1,1,cv2.FILLED)
    filled[fixed]=0
    surface=np.zeros_like(candidate);surface[domain]=3
    surface[domain&(cols+.5>=edge_x)]=2;surface[fixed]=0
    write(DIRECTORY/'paper_scenario_surface_20250821.tif',surface,p,0,date='20250821',
        status='ASSUMED scenario surface; not independently reviewed labels',source=evidence['source'],
        method='west of digitised edge assumed traversable fast ice; 1km eastern ribbon target domain')
    write(DIRECTORY/'paper_scenario_barriers_20250821.tif',filled,p,None,
          status='All retained bright-region footprints filled; unverified iceberg hypothesis')
    results=[];routes=[]
    for factor in (2,5):
        def blocks(a):return a.reshape(h//factor,factor,w//factor,factor)
        allowed=blocks(~fixed).all(axis=(1,3));target=blocks((surface==2)).any(axis=(1,3))&allowed
        start=(int(start_pixel[1])//factor,int(start_pixel[0])//factor)
        baseline=shortest_access(np.where(allowed,1.,np.inf),target,start,40*factor)
        baseline.update(grid_spacing_m=40*factor,scenario='no_candidate_barriers',buffer_m=0)
        results.append(baseline)
        for buffer_m in (0,80,200):
            radius=int(np.ceil(buffer_m/40));obstacle=filled.copy()
            if radius:obstacle=cv2.dilate(obstacle,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1)))
            allowed_obstacles=allowed&~blocks(obstacle>0).any(axis=(1,3))
            result=shortest_access(np.where(allowed_obstacles,1.,np.inf),target,start,40*factor)
            result.update(grid_spacing_m=40*factor,scenario='all_candidate_barriers',buffer_m=buffer_m)
            if result['status']=='model_path_found' and baseline['status']=='model_path_found':
                result['extra_distance_m']=result['distance_m']-baseline['distance_m']
            results.append(result)
    # Isolate how much of the effect depends on suspect coastal detections.
    offshore=np.zeros_like(candidate)
    offshore_contours,_=cv2.findContours((review==1).astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(offshore,offshore_contours,-1,1,cv2.FILLED)
    offshore[fixed]=0
    factor=2
    def blocks(a):return a.reshape(h//factor,factor,w//factor,factor)
    allowed=blocks(~fixed).all(axis=(1,3));target=blocks(surface==2).any(axis=(1,3))&allowed
    blocked=blocks(offshore>0).any(axis=(1,3))
    start=(int(start_pixel[1])//factor,int(start_pixel[0])//factor)
    offshore_result=shortest_access(np.where(allowed&~blocked,1.,np.inf),target,start,80)
    offshore_result.update(grid_spacing_m=80,scenario='offshore_candidates_only',buffer_m=0)
    if offshore_result['path']:
        offshore_result['extra_distance_m']=offshore_result['distance_m']-results[0]['distance_m']
    results.append(offshore_result)
    sensitivity=[]
    factor=2
    def blocks(a):return a.reshape(h//factor,factor,w//factor,factor)
    allowed=blocks(~fixed).all(axis=(1,3))
    blocked=blocks(filled>0).any(axis=(1,3))
    for dx,dy,edge_shift in [(0,0,0),(250,0,0),(-250,0,0),(0,250,0),(0,-250,0),(0,0,200),(0,0,-200)]:
        start=(int(start_pixel[1]-dy/40)//factor,int(start_pixel[0]+dx/40)//factor)
        target=blocks(domain&(cols+.5>=edge_x+edge_shift/40)&~fixed).any(axis=(1,3))&allowed
        no_barriers=shortest_access(np.where(allowed,1.,np.inf),target,start,80)
        with_barriers=shortest_access(np.where(allowed&~blocked,1.,np.inf),target,start,80)
        row={'start_shift_east_m':dx,'start_shift_north_m':dy,'edge_shift_east_m':edge_shift,
             'baseline_status':no_barriers['status'],'barrier_status':with_barriers['status']}
        if no_barriers['path'] and with_barriers['path']:
            row.update(baseline_distance_m=no_barriers['distance_m'],barrier_distance_m=with_barriers['distance_m'],
                       extra_distance_m=with_barriers['distance_m']-no_barriers['distance_m'])
        sensitivity.append(row)
    fig,ax=plt.subplots(figsize=(10,10),layout='constrained');lo,hi=np.nanpercentile(image,[2,98])
    ax.imshow(image,cmap='gray',vmin=lo,vmax=hi)
    ax.contour(fixed_ice,levels=[.5],colors='gray',linewidths=.5)
    ax.contour(filled,levels=[.5],colors='orange',linewidths=.5)
    ax.plot(edge[:,0],edge[:,1],c='cyan',label='Paper-derived fast-ice edge')
    ax.scatter(*start_pixel,c='yellow',edgecolors='black',s=70,label='Paper-derived colony reference')
    for result in results:
        factor=result['grid_spacing_m']//40
        if result['path']:
            pixels=np.array(result['path'])[:,::-1]*factor+factor/2
            coords=[list(p['transform']*tuple(pt)) for pt in pixels]
            # Flag contact with artificial domain sides; avoid pretending domain-limited route is global.
            rr=np.clip(pixels[:,1].astype(int),0,h-1);cc=np.clip(pixels[:,0].astype(int),0,w-1)
            boundary=cv2.erode(domain.astype(np.uint8),np.ones((2*factor+1,2*factor+1),np.uint8))==0
            result['touches_artificial_domain_boundary']=bool(boundary[rr,cc].any())
            routes.append({'type':'Feature','geometry':{'type':'LineString','coordinates':coords},
                'properties':{k:v for k,v in result.items() if k not in ('path','end')}})
            if result['grid_spacing_m']==80 and result['buffer_m']==0:
                ax.plot(pixels[:,0],pixels[:,1],lw=2,label=f"{result['scenario']}: {result['distance_m']/1000:.2f} km")
    ax.set_xlim(850,1750);ax.set_ylim(1600,800);ax.legend(fontsize=8)
    ax.set_title('21 August — PAPER-DERIVED CONDITIONAL SCENARIO\nAll bright footprints are hypothetical barriers; not observed penguin paths')
    ax.set_xlabel('Common-grid column (40 m samples)');ax.set_ylabel('Common-grid row')
    fig.savefig(DIRECTORY/'paper_access_scenario.png',dpi=150);plt.close(fig)
    report={'date':'20250821','status':'user_approved_paper_based_approximate_scenario','approval_date':'2026-10-16',
        'source':evidence['source'],'start_projected':start_xy,'coordinate_crs':p['crs'].to_string(),
        'domain':'Digitised line row span, up to 25 km west and 1 km east; no extrapolation beyond line ends',
        'results':results,'position_sensitivity':sensitivity,'sensitivity_interpretation':'Illustrative shifts, not calibrated confidence intervals','assumptions':['West of edge is an assumed traversable fast-ice platform except fixed land/ice tongues',
            'Eastern ribbon is a paper-supported access target, not a complete water classification',
            'Reference 2024 land and ice tongues/shelves fixed in both scenarios',
            'All retained bright components including coastal classes treated as hypothetical barriers; holes filled',
            'Candidate-buffer sensitivity 0/80/200m; not calibrated uncertainty',
            'Coarse grid accepts a target cell containing some water; endpoint quantisation remains',
            'No observed GPS, biological energy model or causal mortality estimate',
            'Paper inferred green route NOT used to fit or force our calculated solution']}
    (DIRECTORY/'paper_access_scenario.json').write_text(json.dumps(report,indent=2))
    (DIRECTORY/'paper_access_routes.geojson').write_text(json.dumps({'type':'FeatureCollection','coordinate_crs':p['crs'].to_string(),'features':routes},indent=2))
    print([(r['grid_spacing_m'],r['scenario'],r['buffer_m'],r['status'],round(r.get('distance_m',0))) for r in results])

if __name__=='__main__':main()
