"""Register a published schematic to its same-date SAR; produce review-only evidence."""
import hashlib,json
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rasterio.warp import transform
from map_io import DIRECTORY,read

SOURCE='https://www.nature.com/articles/s43247-026-03764-w/figures/5'

def main():
    folder=DIRECTORY.parents[2]/'data/reference/paper'
    path=folder/'figure5_reference_large.png'
    figure=cv2.imread(str(path))
    if figure is None or figure.shape[:2]!=(1699,1200):raise ValueError('Expected reviewed 1200x1699 source figure')
    panel=figure[:1080]
    image,p=read(DIRECTORY/'sar_20250821.tif')
    lo,hi=np.nanpercentile(image,[2,98])
    gray=np.uint8(np.clip((np.nan_to_num(image,nan=lo)-lo)/(hi-lo),0,1)*255)
    sift=cv2.SIFT_create(nfeatures=15000)
    k1,d1=sift.detectAndCompute(cv2.cvtColor(panel,cv2.COLOR_BGR2GRAY),None)
    k2,d2=sift.detectAndCompute(gray,None)
    pairs=cv2.BFMatcher().knnMatch(d1,d2,k=2)
    good=[a for a,b in pairs if a.distance<.7*b.distance]
    src=np.float32([k1[m.queryIdx].pt for m in good]);dst=np.float32([k2[m.trainIdx].pt for m in good])
    # Hold out every fifth tentative correspondence before fitting.
    test=np.arange(len(src))%5==0
    cv2.setRNGSeed(42)
    h,mask=cv2.findHomography(src[~test],dst[~test],cv2.RANSAC,8)
    if h is None or int(mask.sum())<100:raise ValueError('Insufficient registration support')
    predicted=cv2.perspectiveTransform(src[test,None,:],h)[:,0]
    errors=np.linalg.norm(predicted-dst[test],axis=1)
    held_good=errors<8
    if held_good.sum()<25:raise ValueError('Held-out feature support insufficient')
    # Only the blue 2025 line, never the red 2024 line or green inferred route.
    b,g,r=cv2.split(panel)
    blue=(b.astype(int)>r.astype(int)+30)&(b.astype(int)>g.astype(int)+20)&(b>140)
    line=[]
    previous_x=600.0
    for y in range(150,791,5):
        xs=np.flatnonzero(blue[y-2:y+3,450:800].any(axis=0))+450
        if xs.size:
            groups=np.split(xs,np.flatnonzero(np.diff(xs)>2)+1)
            centers=[float(np.median(group)) for group in groups]
            x=min(centers,key=lambda value:abs(value-previous_x))
            if abs(x-previous_x)<=20:
                line.append((x,float(y)))
                previous_x=x
    if len(line)<100:raise ValueError('Blue-line extraction incomplete')
    points=np.float32(line)
    pixel_line=cv2.perspectiveTransform(points[:,None,:],h)[:,0]
    # Visually identified center of the yellow colony marker, not a surveyed coordinate.
    colony_source=np.float32([[[543.,678.]]])
    colony_pixel=cv2.perspectiveTransform(colony_source,h)[0,0]
    def world(points):return [list(p['transform']*(float(x)+.5,float(y)+.5)) for x,y in points]
    colony_xy=world([colony_pixel])[0]
    lon,lat=transform(p['crs'],4326,[colony_xy[0]],[colony_xy[1]])
    old_xy=transform(4326,p['crs'],[169.636085],[-73.348581])
    old_pixel=(~p['transform'])*(old_xy[0][0],old_xy[1][0])
    offset=float(np.hypot(colony_xy[0]-old_xy[0][0],colony_xy[1]-old_xy[1][0]))
    evidence={'type':'FeatureCollection','coordinate_crs':p['crs'].to_string(),'date':'20250821','source':SOURCE,
        'status':'paper_digitisation_draft_not_independently_verified','features':[
        {'type':'Feature','properties':{'role':'2025_fast_ice_edge','method':'blue line extracted from figure; approximate'},'geometry':{'type':'LineString','coordinates':world(pixel_line)}},
        {'type':'Feature','properties':{'role':'paper_colony_reference','source_pixel':[543,678],'surveyed':False},'geometry':{'type':'Point','coordinates':colony_xy}}]}
    (folder/'paper_draft_20250821.geojson').write_text(json.dumps(evidence,indent=2))
    report={'source':SOURCE,'figure_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'homography':h.tolist(),
        'tentative_matches':len(good),'fit_inliers':int(mask.sum()),'heldout_tentative':int(test.sum()),
        'heldout_matches_within_8px':int(held_good.sum()),'heldout_supported_median_error_px':float(np.median(errors[held_good])),
        'heldout_all_median_error_px':float(np.median(errors)),
        'paper_colony_lon_lat':[lon[0],lat[0]],'offset_from_historical_reference_m':offset,
        'limitations':['Feature residuals are conditional registration diagnostics, not surveyed accuracy',
            'Published image is schematic and resampled; manual marker location',
            'Caption says UTM59S but tick values appear consistent with 57S near Coulman; image matching bypasses this discrepancy',
            'Only August21 reference line; no July transfer; inferred green route was not used as a target solution',
            'Line is partial; it does not classify the entire scene']}
    (folder/'registration_report.json').write_text(json.dumps(report,indent=2))
    fig,axes=plt.subplots(1,2,figsize=(14,8),layout='constrained')
    axes[0].imshow(cv2.cvtColor(panel,cv2.COLOR_BGR2RGB));axes[0].plot(points[:,0],points[:,1],c='cyan',lw=1)
    axes[0].set_title('Published Figure 5a; extracted 2025 line');axes[0].axis('off')
    axes[1].imshow(gray,cmap='gray');axes[1].plot(pixel_line[:,0],pixel_line[:,1],c='cyan',lw=2,label='Digitised 2025 fast-ice edge')
    axes[1].scatter(*colony_pixel,c='yellow',s=65,edgecolors='black',label='Paper colony marker (approximate)')
    axes[1].scatter(*old_pixel,c='red',marker='*',s=100,label='Earlier historical reference')
    axes[1].set_xlim(700,1800);axes[1].set_ylim(1900,400);axes[1].legend(fontsize=7)
    axes[1].set_title(f'21 August SAR; reference offset {offset/1000:.2f} km')
    fig.suptitle('SOURCE ALIGNMENT REVIEW — not a measured GPS position or computed route')
    fig.savefig(DIRECTORY/'paper_alignment_review.png',dpi=150);plt.close(fig)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
