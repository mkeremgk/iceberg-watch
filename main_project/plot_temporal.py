"""Plot comparable model paths in shared projected coordinates, never crop coordinates."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from affine import Affine
from compare_access import compare_scenarios


def projected_path(record):
    path=np.asarray(record['result']['path'],dtype=float)
    if path.ndim!=2 or path.shape[1]!=2 or not len(path) or not np.isfinite(path).all():
        raise ValueError('A nonempty finite row/column path is required')
    h,w=record['grid_shape']
    if np.any(path<0) or np.any(path[:,0]>=h) or np.any(path[:,1]>=w):
        raise ValueError('Path outside declared grid')
    if np.any(path!=np.floor(path)):raise ValueError('Path cells must be integers')
    t=Affine(*record['grid_transform'])
    x,y=t*(path[:,1]+.5,path[:,0]+.5)
    return np.column_stack((x,y))


def plot_pair(a,b,output):
    result=compare_scenarios(a,b)
    if result['status']!='distance_comparison_computed':raise ValueError('Scenarios not comparable')
    fig,ax=plt.subplots(figsize=(8,7),layout='constrained')
    for record,color in ((a,'#087f8c'),(b,'#cf4b18')):
        xy=projected_path(record)/1000
        ax.plot(xy[:,0],xy[:,1],color=color,label=f"{record['date']}: {record['result']['distance_m']/1000:.2f} km")
        ax.scatter(*xy[-1],color=color,marker='s')
    ax.scatter(*(np.asarray(a['start_projected'])/1000),marker='*',s=120,color='black',label='Declared start reference')
    ax.set_aspect('equal');ax.legend();ax.grid(alpha=.2)
    ax.set(xlabel='Easting (km)',ylabel='Northing (km)',title=f"Conditional model paths — not observed penguin routes\nChange: {result['distance_change_m']:.0f} m ({result['relative_change_pct']:.1f}%)")
    fig.savefig(output,dpi=130);plt.close(fig)
