"""Full-region locators for review pairs; coordinates refer to the common grid."""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_io import DIRECTORY, read


def main():
    folder=DIRECTORY/'association_review'
    records=json.loads((folder/'diagnostics.json').read_text())
    scenes={}
    for date in sorted({r[k] for r in records for k in ('from_date','to_date')}):
        image,profile=read(DIRECTORY/f'sar_{date}.tif')
        with (DIRECTORY/f'review_candidates_{date}.csv').open() as handle:
            rows={int(r['component_id']):r for r in csv.DictReader(handle)}
        lo,hi=np.nanpercentile(image,[2,98])
        scenes[date]=(image,profile,rows,lo,hi)
    for r in records:
        fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
        for ax,datekey,idkey in zip(axes,('from_date','to_date'),('from_id','to_id')):
            date=r[datekey];im,p,rows,lo,hi=scenes[date];row=rows[r[idkey]]
            x,y=float(row['easting_m']),float(row['northing_m'])
            col,line=(~p['transform'])*(x,y)
            ax.imshow(im[::4,::4],extent=(0,p['width'],p['height'],0),cmap='gray',vmin=lo,vmax=hi)
            ax.scatter([col],[line],s=180,facecolors='none',edgecolors='red',linewidths=2)
            ax.annotate(str(r[idkey]),(col,line),xytext=(10,10),textcoords='offset points',color='red',weight='bold')
            ax.set(title=date,xlabel='Common grid column (px)',ylabel='Common grid row (px)')
        fig.suptitle('Full-region location — red circle is the candidate centroid')
        fig.savefig(folder/f"context_{r['link_number']:03d}.png",dpi=100);plt.close(fig)
    print('Context maps:',len(records))

if __name__=='__main__':main()
