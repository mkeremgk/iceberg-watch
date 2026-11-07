"""Offline date/policy explorer of existing nominal paths; does not recompute routes."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_io import DIRECTORY,read
from fixed_boundary_scenario import fill_candidates
from access import frontier


def main():
    source=DIRECTORY/'fixed_boundary_scenario.json';report=json.loads(source.read_text())
    folder=DIRECTORY/'scenario_explorer';folder.mkdir(exist_ok=True)
    surface,p=read(DIRECTORY/'paper_scenario_surface_20250821.tif');h,w=surface.shape;t=p['transform']
    images={};reviews={};contrast={};common=np.ones(surface.shape,bool)
    dates=[r['date'] for r in report['experiments'][0]['dates']]
    for date in dates:
        images[date],_=read(DIRECTORY/f'sar_{date}.tif',p);common&=np.isfinite(images[date])
        contrast[date]=np.nanpercentile(images[date],[2,98])
        reviews[date],_=read(DIRECTORY/f'review_classes_{date}.tif',p)
    points=[]
    for e in report['experiments']:
        for result in e['dates']:
            for r,c in result.get('path',[]):points.append(((c+.5)*e['spacing_m']/40,(r+.5)*e['spacing_m']/40))
    if not points:raise ValueError('No paths to display')
    points=np.asarray(points);center=(points.min(axis=0)+points.max(axis=0))/2
    half=np.maximum((points.max(axis=0)-points.min(axis=0))/2+100,250)
    c0,r0=np.maximum(np.floor(center-half).astype(int),0);c1,r1=np.minimum(np.ceil(center+half).astype(int),[w,h])
    extent=((t.c+c0*40)/1000,(t.c+c1*40)/1000,(t.f-r1*40)/1000,(t.f-r0*40)/1000)
    records=[]
    for e in report['experiments']:
        spacing=e['spacing_m'];f=spacing//40
        def blocks(a):return a.reshape(h//f,f,w//f,f)
        allowed=blocks((surface>0)&common).all(axis=(1,3));ribbon=blocks(surface==2).any(axis=(1,3))&allowed
        target=frontier(ribbon,allowed&~ribbon)
        for result in e['dates']:
            date=result['date'];image=images[date];mask=fill_candidates(reviews[date],e['policy'])
            mask[~common|(surface==0)]=False
            # Show the actual conservative coarse barriers, not just fine proposals.
            blocked=blocks(mask).any(axis=(1,3));display_blocked=np.repeat(np.repeat(blocked,f,0),f,1)
            display_target=np.repeat(np.repeat(target,f,0),f,1)
            fig,ax=plt.subplots(figsize=(9,9),layout='constrained');lo,hi=contrast[date]
            ax.imshow(image[r0:r1,c0:c1],cmap='gray',vmin=lo,vmax=hi,extent=extent)
            overlay=np.zeros((r1-r0,c1-c0,4));overlay[display_blocked[r0:r1,c0:c1]]=[1,.35,.05,.4]
            overlay[display_target[r0:r1,c0:c1]]=[0,1,1,.8]
            ax.imshow(overlay,extent=extent)
            for path,color,style,label in [(e['baseline']['path'],'#f8ec77','--','No candidate barriers'),(result.get('path',[]),'#ff3ca6','-','Selected model route')]:
                if path:
                    cells=np.asarray(path);x=(t.c+(cells[:,1]+.5)*spacing)/1000;y=(t.f-(cells[:,0]+.5)*spacing)/1000
                    ax.plot(x,y,color=color,ls=style,lw=2,label=label)
                    if style=='-':ax.scatter([x[0],x[-1]],[y[0],y[-1]],c=[color,'cyan'],edgecolors='black',s=45,zorder=5)
            ax.set(xlim=extent[:2],ylim=extent[2:],xlabel='Easting (km)',ylabel='Northing (km)',title=f'{date} / {spacing} m / {e["policy"]}\nOrange: candidate barriers; cyan: fixed August target set')
            ax.legend(fontsize=8);ax.set_aspect('equal')
            name=f'{date}_{spacing}_{e["policy"]}.png';fig.savefig(folder/name,dpi=115);plt.close(fig)
            records.append(dict(date=date,spacing_m=spacing,policy=e['policy'],image=name,status=result['status'],distance_m=result.get('distance_m'),extra_m=result.get('extra_distance_vs_fixed_baseline_m')))
    data=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),records=records)
    template=Path(__file__).with_name('scenario_explorer.html').read_text()
    (folder/'index.html').write_text(template.replace('EXPLORER_DATA',json.dumps(data)))
    (folder/'manifest.json').write_text(json.dumps(data,indent=2))
    print('Scenario explorer:',len(records),'views')

if __name__=='__main__':main()
