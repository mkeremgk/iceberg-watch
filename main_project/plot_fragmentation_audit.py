"""Wide-context screening figure; proximity does not establish common identity."""
import json
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from map_io import DIRECTORY, read


def main():
    folder=DIRECTORY/'fragmentation_audit';report=json.loads((folder/'results.json').read_text())
    items=[(s['date'],pair) for s in report['scenes'] for pair in s['trials'][-1]['pairs']]
    fig,axes=plt.subplots((len(items)+1)//2,2,figsize=(13,6*((len(items)+1)//2)),squeeze=False,layout='constrained')
    land,p=read(DIRECTORY/'land_mask.tif');cache={}
    for ax,(date,pair) in zip(axes.flat,items):
        if date not in cache:
            im,_=read(DIRECTORY/f'sar_{date}.tif',p);proposals,_=read(DIRECTORY/f'proposals_{date}.tif',p)
            _,labels=cv2.connectedComponents(((proposals>0)&(land==0)&np.isfinite(im)).astype('uint8'),connectivity=8)
            cache[date]=(im,labels)
        im,labels=cache[date];rows,cols=np.where(np.isin(labels,pair))
        rmid=(rows.min()+rows.max())//2;cmid=(cols.min()+cols.max())//2
        half=max(250,int(max(np.ptp(rows),np.ptp(cols))*.75))
        r0=max(0,rmid-half);r1=min(im.shape[0],rmid+half);c0=max(0,cmid-half);c1=min(im.shape[1],cmid+half)
        crop=im[r0:r1,c0:c1];lo,hi=np.nanpercentile(im,[2,98])
        ax.imshow(crop,cmap='gray',vmin=lo,vmax=hi,extent=(c0*40/1000,c1*40/1000,r1*40/1000,r0*40/1000))
        for label,color in zip(pair,('cyan','orange')):
            contours,_=cv2.findContours((labels[r0:r1,c0:c1]==label).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                pts=contour[:,0,:];ax.plot((pts[:,0]+c0+.5)*.04,(pts[:,1]+r0+.5)*.04,color=color,lw=1)
            ax.plot([],[],color=color,label=f'Candidate {label}')
        ax.legend(fontsize=8);ax.set(title=f'{date}: nearby regions, NOT a merge decision',xlabel='Grid column distance (km)',ylabel='Grid row distance (km)')
    for ax in list(axes.flat)[len(items):]:ax.set_visible(False)
    fig.suptitle('Fragmentation review: wide context, minimum 20 km window\nClose regions may be separate icebergs; no labels or masks changed')
    fig.savefig(folder/'wide_context.png',dpi=130);plt.close(fig)
    print('Context pairs:',len(items))

if __name__=='__main__':main()
