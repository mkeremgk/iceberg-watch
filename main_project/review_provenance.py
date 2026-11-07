"""Bind review decisions to candidate geometry and source images, not numeric IDs alone."""
import hashlib
import json
from pathlib import Path
import rasterio


def canonical_links(links):
    """Ignore cross-platform floating-point noise, preserving IDs and geometry."""
    def normalize(value):
        if isinstance(value, float):
            return round(value, 12)
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value
    return normalize(links)


def scene_fingerprint(directory):
    directory=Path(directory)
    association=json.loads((directory/'association_report.json').read_text())
    dates=sorted({r[k] for r in association['links'] for k in ('from_date','to_date')})
    result={'association_links':hashlib.sha256(json.dumps(canonical_links(association['links']),sort_keys=True).encode()).hexdigest(),'rasters':{}}
    paths=[directory/'land_mask.tif']
    for date in dates:paths.extend([directory/f'sar_{date}.tif',directory/f'proposals_{date}.tif'])
    for path in paths:
        with rasterio.open(path) as src:
            digest=hashlib.sha256()
            # Fixed row chunks make fingerprints independent of TIFF compression/block layout.
            for row in range(0,src.height,128):
                digest.update(src.read(1,window=((row,min(row+128,src.height)),(0,src.width))).tobytes())
            result['rasters'][path.name]={'pixels':digest.hexdigest(),'crs':str(src.crs),'transform':list(src.transform),'shape':[src.height,src.width]}
    return result


def verify_binding(directory):
    binding=Path(directory)/'association_review/review_binding.json'
    if not binding.exists():return False
    saved=json.loads(binding.read_text())
    if saved['fingerprint']!=scene_fingerprint(directory):
        raise ValueError('Review geometry changed: preserve old decisions and re-review new candidates; IDs alone are insufficient.')
    return True
