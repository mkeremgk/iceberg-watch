"""Date-matched AMSR2 context only, never a fine-scale route mask."""
import hashlib
import json
import urllib.request
import ssl
import certifi
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from map_io import DIRECTORY,read,write


def main():
    cache=DIRECTORY.parents[2]/'data/reference/sea_ice'
    cache.mkdir(parents=True,exist_ok=True)
    paths=sorted(DIRECTORY.glob('sar_*.tif'))
    fig,axes=plt.subplots(1,len(paths),figsize=(15,5),squeeze=False,layout='constrained')
    reports={}
    for path,ax in zip(paths,axes[0]):
        date=path.stem[4:]
        name=f'asi-AMSR2-s6250-{date}-v5.4.nc'
        url=f'https://data.seaice.uni-bremen.de/amsr2/asi_daygrid_swath/s6250/netcdf/{date[:4]}/{name}'
        target=cache/name
        if not target.exists():
            with urllib.request.urlopen(url,timeout=45,context=ssl.create_default_context(cafile=certifi.where())) as response:
                payload=response.read()
            temporary=target.with_suffix('.part')
            temporary.write_bytes(payload)
            temporary.replace(target)
        image,p=read(path)
        destination=np.full(image.shape,np.nan,np.float32)
        with rasterio.open(target) as src:
            raw=src.read(1)
            finite=raw[np.isfinite(raw)]
            if finite.size==0 or finite.min()<0 or finite.max()>100:
                raise ValueError('Unexpected NetCDF concentration encoding')
            reproject(raw,destination,src_transform=src.transform,src_crs=src.crs,
                      src_nodata=np.nan,dst_transform=p['transform'],dst_crs=p['crs'],
                      dst_nodata=np.nan,resampling=Resampling.nearest)
        write(DIRECTORY/f'sic_context_{date}.tif',destination,p,np.nan,
              source=url,native_spacing_m=6250,units='percent',role='regional context only; not reviewed open water')
        land,_=read(DIRECTORY/'land_mask.tif',p)
        ocean=(land==0)&np.isfinite(image)&np.isfinite(destination)
        values=destination[ocean]
        reports[date]={'source':url,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'native_spacing_m':6250,'resampling':'nearest; no added resolution',
            'ocean_context_percentiles':np.percentile(values,[0,25,50,75,100]).tolist() if values.size else [],
            'low_concentration_below_15_percent_grid_pixels':int(np.count_nonzero(ocean&(destination<15))),
            'warning':'Low concentration is NOT verified open water; coastal contamination possible; no labels assigned'}
        ax.imshow(np.ma.masked_where(~ocean,destination),vmin=0,vmax=100,cmap='Blues_r')
        ax.contour(land,levels=[.5],colors='black',linewidths=.5)
        ax.set_title(date);ax.set_axis_off()
    fig.suptitle('AMSR2 daily ice concentration (%) — 6.25 km native grid\nRegional context only; not a route or narrow-lead map')
    fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0,100),cmap='Blues_r'),ax=axes.ravel().tolist(),label='Sea-ice concentration (%)')
    fig.savefig(DIRECTORY/'sea_ice_context.png',dpi=140);plt.close(fig)
    (DIRECTORY/'sea_ice_context_report.json').write_text(json.dumps(reports,indent=2))
    print('AMSR2 context prepared for',list(reports))

if __name__=='__main__':main()
