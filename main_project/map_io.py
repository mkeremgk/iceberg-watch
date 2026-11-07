"""Shared grid checks and small raster outputs."""
from pathlib import Path
import rasterio

DIRECTORY = Path(__file__).resolve().parent / 'outputs/common_grid'

def read(path, reference=None):
    with rasterio.open(path) as src:
        profile = src.profile.copy()
        if reference and any(profile[k] != reference[k] for k in ('crs','transform','width','height')):
            raise ValueError(f'Grid mismatch: {path}')
        return src.read(1), profile

def write(path, array, profile, nodata, **tags):
    profile = profile.copy()
    profile.update(driver='GTiff', dtype=str(array.dtype), count=1, nodata=nodata, compress='deflate')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(array, 1)
        dst.update_tags(**tags)
