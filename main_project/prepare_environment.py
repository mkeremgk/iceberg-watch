"""Batch reference masks and provisional environment; no inferred water labels."""
import json
import numpy as np
from rasterio.features import rasterize
from map_io import DIRECTORY, read, write
from review_candidates import review_regions


def main():
    surfaces=json.loads((DIRECTORY.parents[2]/'data/reference/add/coulman_surfaces.json').read_text())
    summaries={}
    for path in sorted(DIRECTORY.glob('sar_*.tif')):
        date=path.stem[4:]
        image,p=read(path)
        if p['crs'].to_string()!=surfaces['crs']:
            raise ValueError('Reference surfaces CRS mismatch')
        land=rasterize([(f['geometry'],1) for f in surfaces['features'] if f['surface']=='land'],
                       out_shape=image.shape, transform=p['transform'],fill=0,dtype='uint8')
        valid=np.isfinite(image)
        proposals,_=read(DIRECTORY/f'proposals_{date}.tif',p)
        classes,report=review_regions((proposals>0)&(land==0)&valid,land,surfaces['features'],p['transform'],valid,DIRECTORY,date)
        write(DIRECTORY/f'review_classes_{date}.tif',classes,p,None,classes=json.dumps(report['classes']))
        env=np.zeros(image.shape,np.uint8)
        env[land==1]=1
        env[~valid]=255
        write(DIRECTORY/f'environment_{date}.tif',env,p,255,date=date,
              classes='0 unknown; 1 reference land; 2 reviewed open water; 3 reviewed sea ice; 255 no data',
              status='No real water/sea-ice annotations applied')
        write(DIRECTORY/'land_mask.tif',land,p,None,source='SCAR ADD v7.10 (2024)')
        summaries[date]=report['counts']
    (DIRECTORY/'environment_report.json').write_text(json.dumps(summaries,indent=2))
    print('Candidate review counts:',summaries)

if __name__=='__main__': main()
