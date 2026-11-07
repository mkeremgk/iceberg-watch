"""Wide-context visual comparison for the user-flagged July22 scenario."""
import hashlib
import json
from html import escape
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_io import DIRECTORY,read
from corridor_scenario import corridor_mask
from fixed_boundary_scenario import fill_candidates
from access import frontier


def main():
    folder=DIRECTORY/'corridor_scenario';study=json.loads((folder/'results.json').read_text())
    source=DIRECTORY/'fixed_boundary_scenario.json'
    if hashlib.sha256(source.read_bytes()).hexdigest()!=study['source_sha256']:raise ValueError('Stale corridor experiment')
    nominal=json.loads(source.read_text());e=next(e for e in nominal['experiments'] if e['spacing_m']==80 and e['policy']=='offshore_only')
    date='20250722';original=next(r for r in e['dates'] if r['date']==date)
    cases=[('Unrestricted',None,original)]
    for width in (500,1000,2000):
        trial=next(x for x in study['experiments'] if x['spacing_m']==80 and x['policy']=='offshore_only' and x['full_width_m']==width)
        cases.append((f'{width} m total corridor',width,next(r for r in trial['dates'] if r['date']==date)))
    surface,p=read(DIRECTORY/'paper_scenario_surface_20250821.tif');im,_=read(DIRECTORY/f'sar_{date}.tif',p)
    review,_=read(DIRECTORY/f'review_classes_{date}.tif',p);common=np.ones(surface.shape,bool)
    for d in ('20250716','20250722','20250728','20250821'):
        a,_=read(DIRECTORY/f'sar_{d}.tif',p);common&=np.isfinite(a)
    h,w=surface.shape;f=2;spacing=80;t=p['transform']
    def blocks(a):return a.reshape(h//f,f,w//f,f)
    allowed=blocks((surface>0)&common).all(axis=(1,3));ribbon=blocks(surface==2).any(axis=(1,3))&allowed
    target=frontier(ribbon,allowed&~ribbon)
    mask=fill_candidates(review,'offshore_only');mask[~common|(surface==0)]=False
    blocked=blocks(mask).any(axis=(1,3))
    points=np.array(e['baseline']['path']+original['path']);center=(points.min(axis=0)+points.max(axis=0))/2
    half=np.maximum((points.max(axis=0)-points.min(axis=0))/2+50,125)
    r0,c0=np.maximum(np.floor(center-half).astype(int)*f,0);r1,c1=np.minimum(np.ceil(center+half).astype(int)*f,[h,w])
    extent=((t.c+c0*40)/1000,(t.c+c1*40)/1000,(t.f-r1*40)/1000,(t.f-r0*40)/1000)
    lo,hi=np.nanpercentile(im,[2,98]);fig,axes=plt.subplots(2,2,figsize=(14,14),layout='constrained')
    for ax,(title,width,result) in zip(axes.flat,cases):
        ax.imshow(im[r0:r1,c0:c1],cmap='gray',vmin=lo,vmax=hi,extent=extent)
        overlay=np.zeros((h,w,4),np.float32)
        if width:
            corridor=corridor_mask(blocked.shape,e['baseline']['path'],spacing,width)
            outside=~np.repeat(np.repeat(corridor,f,0),f,1);overlay[outside]=[.5,.5,.5,.6]
        overlay[np.repeat(np.repeat(blocked,f,0),f,1)]=[1,.35,.05,.65]
        overlay[np.repeat(np.repeat(target,f,0),f,1)]=[0,1,1,.9]
        ax.imshow(overlay[r0:r1,c0:c1],extent=extent)
        for path,color,style,label in [(e['baseline']['path'],'#fff270','--','No-candidate reference'),(result.get('path',[]),'#ff3ca6','-','Selected model route')]:
            if not path:continue
            cells=np.array(path);x=(t.c+(cells[:,1]+.5)*spacing)/1000;y=(t.f-(cells[:,0]+.5)*spacing)/1000
            ax.plot(x,y,c=color,ls=style,lw=2,label=label)
            if style=='-':ax.scatter(x[-1],y[-1],c='cyan',edgecolors='black',s=40,zorder=5)
        label=f"{result['distance_m']/1000:.3f} km" if 'distance_m' in result else 'NO PATH under corridor assumptions'
        ax.set(title=title+'\n'+label,xlabel='Easting (km)',ylabel='Northing (km)',xlim=extent[:2],ylim=extent[2:]);ax.legend(fontsize=8);ax.set_aspect('equal')
    fig.suptitle('22 July / 80 m / offshore candidates — same obstacles and August target\nGrey outside corridor is excluded by assumption, NOT classified water')
    fig.savefig(folder/'comparison_20250722.png',dpi=125);plt.close(fig)
    rows=[]
    for experiment in study['experiments']:
        for r in experiment['dates']:
            distance=f"{r['distance_m']/1000:.3f}" if 'distance_m' in r else 'Unavailable'
            meaning='Route found' if 'distance_m' in r else ('No unblocked target cell inside corridor' if r['status']=='no_reviewed_open_water_target' else 'No connected route under model')
            rows.append(f"<tr><td>{r['date']}</td><td>{experiment['spacing_m']}</td><td>{escape(experiment['policy'])}</td><td>{experiment['full_width_m']}</td><td>{distance}</td><td>{meaning}</td></tr>")
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reference-path corridor experiment</title><style>body{font:16px system-ui;max-width:1300px;margin:30px auto;padding:15px;background:#eff3f6;color:#193047}img{width:100%}td,th{padding:10px;text-align:left;border-bottom:1px solid #ccc}aside{padding:18px;background:#fff0d0}table{border-collapse:collapse}</style><h1>Reference-path corridor experiment</h1><p><a href="../scenario_explorer/index.html">Nominal explorer</a> · <a href="summary.md">Assumptions and results</a></p><aside>Additional counterfactual, not a correction of water classification. Width means total width around the no-candidate reference path. Obstacles remain unchanged. No path does not establish real colony isolation.</aside><img src="comparison_20250722.png" alt="Unrestricted and three corridor widths for July22"><h2>All 48 trials</h2><table><tr><th>Date</th><th>Grid (m)</th><th>Policy</th><th>Width (m)</th><th>Route (km)</th><th>Outcome</th></tr>'''+''.join(rows)+'</table></html>'
    (folder/'index.html').write_text(page)
    print('Corridor comparison page:',folder/'index.html')

if __name__=='__main__':main()
