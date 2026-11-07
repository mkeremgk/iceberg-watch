"""Human surface interpretation with date/source provenance. Never automatic truth."""
import argparse
import json
from datetime import datetime,timezone
import matplotlib.pyplot as plt
from matplotlib.widgets import PolygonSelector
import numpy as np
from environment import apply_surface_annotation
from map_io import DIRECTORY,read,write


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',default='20250716')
    parser.add_argument('--class-code',type=int,choices=[2,3],required=True)
    parser.add_argument('--source',required=True,help='Actual date-matched evidence used; URL/file and interpretation notes')
    parser.add_argument('--reviewer',required=True)
    args=parser.parse_args()
    if not args.source.strip() or not args.reviewer.strip():raise ValueError('Source and reviewer required')
    image,p=read(DIRECTORY/f'sar_{args.date}.tif')
    output=DIRECTORY/f'environment_reviewed_{args.date}.tif'
    records_path=DIRECTORY/f'surface_annotations_{args.date}.geojson'
    if output.exists()!=records_path.exists():raise ValueError('Reviewed raster and annotation history must exist together')
    labels,_=read(output if output.exists() else DIRECTORY/f'environment_{args.date}.tif',p)
    history=json.loads(records_path.read_text()) if records_path.exists() else {
        'type':'FeatureCollection','coordinate_crs':p['crs'].to_string(),'date':args.date,'features':[]}
    if history['date']!=args.date or history['coordinate_crs']!=p['crs'].to_string():raise ValueError('Annotation history mismatch')
    t=p['transform'];h,w=image.shape
    extent=(t.c,t.c+t.a*w,t.f+t.e*h,t.f)
    lo,hi=np.nanpercentile(image,[2,98])
    fig,ax=plt.subplots(figsize=(10,9),layout='constrained')
    ax.imshow(image,cmap='gray',vmin=lo,vmax=hi,extent=extent)
    overlay=np.zeros((*image.shape,4),np.float32)
    overlay[labels==1]=(.5,.5,.5,.5);overlay[labels==2]=(0,.4,1,.5);overlay[labels==3]=(0,1,.6,.4)
    ax.imshow(overlay,extent=extent)
    ax.set_title(f'{args.date}: HUMAN interpretation, class {args.class_code}\nClick polygon, close it, Enter to save; Q to cancel. Unknown areas remain unknown.')
    ax.set(xlabel='Easting (m), EPSG:32759',ylabel='Northing (m), EPSG:32759')
    vertices=[]
    selector=PolygonSelector(ax,lambda v:vertices.__setitem__(slice(None),v))
    def key(event):
        if event.key in ('q','escape'):plt.close(fig)
        if event.key!='enter' or len(vertices)<3:return
        ring=[list(v) for v in vertices];ring.append(ring[0])
        geometry={'type':'Polygon','coordinates':[ring]}
        updated,count=apply_surface_annotation(labels,geometry,args.class_code,t)
        if not count:
            print('No unknown pixels selected; annotation not saved.');return
        history['features'].append({'type':'Feature','geometry':geometry,'properties':{
            'class_code':args.class_code,'date':args.date,'source':args.source,'reviewer':args.reviewer,
            'created_utc':datetime.now(timezone.utc).isoformat(),'changed_pixels':count,
            'status':'human_interpretation_not_independently_validated'}})
        write(output,updated,p,255,date=args.date,annotation_history=records_path.name,
              status='Human surface interpretation; not biological ground truth')
        records_path.write_text(json.dumps(history,indent=2))
        print('Saved',count,'pixels to',output);plt.close(fig)
    fig.canvas.mpl_connect('key_press_event',key)
    plt.show()

if __name__=='__main__':main()
