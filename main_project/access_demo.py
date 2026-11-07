"""Synthetic algorithm demonstration, deliberately separate from Antarctic evidence."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from access import shortest_access
from map_io import DIRECTORY


def main():
    cost=np.ones((60,80));cost[:5]=np.inf;cost[-5:]=np.inf
    target=np.zeros(cost.shape,bool);target[5:55,72]=True
    start=(30,8)
    baseline=shortest_access(cost,target,start,100)
    obstructed=cost.copy();obstructed[14:47,38:45]=np.inf
    detour=shortest_access(obstructed,target,start,100)
    sealed=obstructed.copy();sealed[:,38:45]=np.inf
    closed=shortest_access(sealed,target,start,100)
    fig,axes=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for ax,grid,result,title in zip(axes,[cost,obstructed,sealed],[baseline,detour,closed],['No candidate barrier','Candidate barrier','Closed passage']):
        ax.imshow(np.isfinite(grid),cmap='gray',vmin=0,vmax=1)
        ax.contour(target,levels=[.5],colors='blue',linewidths=1)
        ax.scatter(start[1],start[0],marker='*',c='red')
        if result['path']:
            path=np.array(result['path']);ax.plot(path[:,1],path[:,0],c='orange')
        suffix=f"{result['distance_m']/1000:.2f} km" if 'distance_m' in result else result['status']
        ax.set_title(f'{title}\n{suffix}');ax.set_axis_off()
    fig.suptitle('SYNTHETIC TEST — no real colony, coastline or penguin route')
    fig.savefig(DIRECTORY/'synthetic_access_demo.png',dpi=140);plt.close(fig)
    (DIRECTORY/'synthetic_access_demo.json').write_text(json.dumps({'synthetic':True,'baseline':baseline,'detour':detour,'closed':closed},indent=2))
    print('Synthetic access:',baseline['distance_m'],detour['distance_m'],closed['status'])

if __name__=='__main__':main()
