"""Review images for every provisional link; diagnostic shape scores, no auto truth."""
import csv,json
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_io import DIRECTORY,read


def main():
    report=json.loads((DIRECTORY/'association_report.json').read_text())
    scenes={}
    for date in sorted({x[k] for x in report['links'] for k in ('from_date','to_date')}):
        im,p=read(DIRECTORY/f'sar_{date}.tif');proposal,_=read(DIRECTORY/f'proposals_{date}.tif',p)
        land,_=read(DIRECTORY/'land_mask.tif',p)
        n,labels,stats,centers=cv2.connectedComponentsWithStats(((proposal>0)&(land==0)&np.isfinite(im)).astype(np.uint8),connectivity=8)
        scenes[date]=(im,labels,stats,centers)
    diagnostics=[]
    folder=DIRECTORY/'association_review';folder.mkdir(exist_ok=True)
    for i,link in enumerate(report['links']):
        fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained');contours=[]
        sizes=[]
        for key,datekey in [('from_id','from_date'),('to_id','to_date')]:
            stats=scenes[link[datekey]][2][link[key]];sizes.append(max(stats[2],stats[3]))
        # Show surrounding ice and coastline at the same scale in both panels.
        # At 40 m spacing, the minimum full window spans 16 km.
        half=max(200, int(np.ceil(max(sizes)*1.5)))
        for ax,key,datekey in zip(axes,['from_id','to_id'],['from_date','to_date']):
            im,labels,stats,centers=scenes[link[datekey]];identifier=link[key]
            cx,cy=centers[identifier];r0=max(0,int(cy)-half);r1=min(im.shape[0],int(cy)+half)
            c0=max(0,int(cx)-half);c1=min(im.shape[1],int(cx)+half)
            roi=im[r0:r1,c0:c1];mask=(labels[r0:r1,c0:c1]==identifier).astype(np.uint8)
            extracted,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            contours.append(max(extracted,key=cv2.contourArea))
            lo,hi=np.nanpercentile(roi,[2,98]);ax.imshow(roi,cmap='gray',vmin=lo,vmax=hi)
            ax.contour(mask,levels=[.5],colors='orange',linewidths=1)
            ax.set_title(f"{link[datekey]} / region {identifier}");ax.set_axis_off()
        score=float(cv2.matchShapes(contours[0],contours[1],cv2.CONTOURS_MATCH_I1,0))
        small=link['distance_km']<.5
        fig.suptitle(f"Link {i+1}: {link['distance_km']:.3f} km; shape diagnostic {score:.3f}\nUnverified; <500 m displacement needs geolocation caution" if small else f"Link {i+1}: {link['distance_km']:.3f} km; shape diagnostic {score:.3f}\nUnverified association; inspect both shape and context")
        filename=f'link_{i+1:03d}.png';fig.savefig(folder/filename,dpi=110);plt.close(fig)
        diagnostics.append(dict(link_number=i+1,**link,shape_match_i1=score,small_displacement_review=small,
                                review_image=filename,human_decision='unreviewed'))
    (folder/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    template=folder/'human_review.csv'
    if not template.exists():
        with template.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['from_date','from_id','to_date','to_id','decision','reviewer','notes'])
            writer.writeheader()
            for d in diagnostics:writer.writerow({**{k:d[k] for k in ['from_date','from_id','to_date','to_id']},'decision':'unreviewed'})
    html='<html lang="en"><meta charset="utf-8"><title>Association review</title><style>body{font:16px system-ui;max-width:1000px;margin:30px auto}img{max-width:100%}section{border-top:1px solid #ccc;margin-top:20px}</style><h1>Provisional association review</h1><p>Shape scores are diagnostics, not calibrated confidence. A 500 m caution threshold is heuristic, not a measured error bound. Review CSV does not automatically change tracking.</p>'
    for d in diagnostics:html+=f'<section><h2>Link {d["link_number"]}</h2><img src="{d["review_image"]}" alt="Two-date candidate comparison"></section>'
    (folder/'index.html').write_text(html+'</html>')
    print('Review pairs:',len(diagnostics),'small-displacement caution:',sum(d['small_displacement_review'] for d in diagnostics))

if __name__=='__main__':main()
