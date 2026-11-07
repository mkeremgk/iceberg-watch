"""Bind declared evidence to exact environmental raster bytes; no scientific auto-approval."""
import hashlib
import json
from pathlib import Path


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def load_evidence(path,date,environment_path):
    record=json.loads(Path(path).read_text())
    if record.get('date')!=date:raise ValueError('Evidence date differs from scene date')
    if record.get('environment_sha256')!=file_hash(environment_path):
        raise ValueError('Evidence references different environmental raster bytes')
    for field in ('boundary_source','surface_source','interpretation','reviewer','limitations'):
        if not isinstance(record.get(field),str) or not record[field].strip():
            raise ValueError('Missing evidence field: '+field)
    if record.get('status')!='human_reviewed_scenario':
        raise ValueError('Evidence must explicitly declare human_reviewed_scenario')
    return record


def touches_unknown(path,environment,factor):
    """Conservative check: route cell or adjacent coarse cell contains unknown/no-data."""
    import numpy as np
    h,w=environment.shape
    unknown=np.isin(environment,[0,255]).reshape(h//factor,factor,w//factor,factor).any(axis=(1,3))
    for r,c in path:
        if r in (0,unknown.shape[0]-1) or c in (0,unknown.shape[1]-1):return True
        if unknown[r-1:r+2,c-1:c+2].any():return True
    return False if path else None
