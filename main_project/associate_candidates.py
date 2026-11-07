"""Conservative, unvalidated centroid/area association; not biological tracking."""
import csv
import json
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_io import DIRECTORY,read


def associate(a,b,days,max_km_per_day=5.,max_area_ratio=2.,margin=.15):
    if days<=0:raise ValueError("Dates must increase")
    if days>12:return []
    scores=np.full((len(a),len(b)),np.inf)
    distances=np.zeros_like(scores)
    for i,left in enumerate(a):
        for j,right in enumerate(b):
            distance=np.hypot(left['easting_m']-right['easting_m'],left['northing_m']-right['northing_m'])/1000
            ratio=max(left['area_km2'],right['area_km2'])/min(left['area_km2'],right['area_km2'])
            distances[i,j]=distance
            if distance<=days*max_km_per_day and ratio<=max_area_ratio:
                scores[i,j]=distance/(days*max_km_per_day)+abs(np.log(ratio))
    links=[]
    for i in range(len(a)):
        possible=np.flatnonzero(np.isfinite(scores[i]))
        if not len(possible):continue
        j=int(possible[np.argmin(scores[i,possible])])
        if np.argmin(scores[:,j])!=i:continue
        row=np.sort(scores[i,np.isfinite(scores[i])]);col=np.sort(scores[np.isfinite(scores[:,j]),j])
        gap=min(row[1]-row[0] if len(row)>1 else np.inf,col[1]-col[0] if len(col)>1 else np.inf)
        if gap<margin:continue
        links.append({'from_id':a[i]['component_id'],'to_id':b[j]['component_id'],
                      'distance_km':float(distances[i,j]),'speed_km_per_day':float(distances[i,j]/days),
                      'score':float(scores[i,j]),'status':'provisional_mutual_best_not_validated'})
    return links


def main():
    scenes={}
    for path in sorted(DIRECTORY.glob('review_candidates_*.csv')):
        date=path.stem.split('_')[-1]
        with path.open() as f:
            rows=list(csv.DictReader(f))
        scenes[date]=[{k:(int(v) if k=='component_id' else float(v)) for k,v in r.items()
                     if k in ('component_id','area_km2','easting_m','northing_m')}
                    for r in rows if r['class_code']=='1']
    dates=sorted(scenes);links=[];track_rows=[];next_track=1;assignments={}
    for index,date in enumerate(dates):
        current=scenes[date]
        if index:
            previous=dates[index-1]
            days=(datetime.strptime(date,'%Y%m%d')-datetime.strptime(previous,'%Y%m%d')).days
            pairs=associate(scenes[previous],current,days) if days <= 12 else []
            for pair in pairs:
                pair.update(from_date=previous,to_date=date)
                assignments[(date,pair['to_id'])]=assignments[(previous,pair['from_id'])]
            links.extend(pairs)
        for row in current:
            key=(date,row['component_id'])
            if key not in assignments:
                assignments[key]=next_track;next_track+=1
            track_rows.append(dict(date=date,provisional_track_id=assignments[key],**row))
    with (DIRECTORY/'provisional_tracks.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['date','provisional_track_id','component_id','area_km2','easting_m','northing_m'])
        writer.writeheader();writer.writerows(track_rows)
    report={'method':'mutual best centroid-distance + log-area score; alternative margin >= 0.15',
        'heuristics':{'max_km_per_day':5,'max_area_ratio':2,'max_gap_days':12},'links':links,
        'unmatched_meaning':'unmatched or ambiguous; not evidence of birth/disappearance',
        'limitations':['No labelled association validation','No split/merge handling','Gaps longer than 12 days start new provisional IDs','Only offshore class 1 included',
                       'Provisional IDs can be incorrect; motion direction is distinct from shape orientation']}
    (DIRECTORY/'association_report.json').write_text(json.dumps(report,indent=2))
    image,p=read(DIRECTORY/f'sar_{dates[0]}.tif');lo,hi=np.nanpercentile(image,[2,98])
    fig,ax=plt.subplots(figsize=(8,8),layout='constrained')
    ax.imshow(image,cmap='gray',vmin=lo,vmax=hi,extent=(p['transform'].c/1000,(p['transform'].c+p['width']*40)/1000,
              (p['transform'].f-p['height']*40)/1000,p['transform'].f/1000))
    for date in dates:
        ax.scatter([r['easting_m']/1000 for r in scenes[date]],[r['northing_m']/1000 for r in scenes[date]],s=14,label=date)
    for link in links:
        a=next(r for r in scenes[link['from_date']] if r['component_id']==link['from_id'])
        b=next(r for r in scenes[link['to_date']] if r['component_id']==link['to_id'])
        ax.plot([a['easting_m']/1000,b['easting_m']/1000],[a['northing_m']/1000,b['northing_m']/1000],color='cyan',alpha=.5,lw=.7)
    ax.legend();ax.set(xlabel='Easting (km)',ylabel='Northing (km)',title='Provisional centroid associations — NOT verified tracks')
    fig.savefig(DIRECTORY/'provisional_tracks.png',dpi=140);plt.close(fig)
    print('Provisional associations:',len(links))

if __name__=='__main__':main()
