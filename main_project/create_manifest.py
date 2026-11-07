"""Inventory current code and output bytes; this is a snapshot, not proof of generation provenance."""
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from map_io import DIRECTORY


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    root=Path(__file__).resolve().parent
    output=DIRECTORY/'snapshot_manifest.json'
    files=sorted(set(root.glob('*.py')) | set(root.glob('*.html')) |
                 set(root.glob('requirements*.txt')) | set(DIRECTORY.rglob('*.json')) |
                 set(DIRECTORY.rglob('*.csv')))
    files=[p for p in files if p != output and 'pipeline_runs' not in p.parts]
    packages={}
    for name in ('numpy','rasterio','matplotlib','opencv-python-headless','opencv-python'):
        try: packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: pass
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
                packages=packages,scope='Code, HTML template, requirements, JSON and CSV only; excludes raw data, raster/image bytes and separately recorded pipeline execution histories.',
                warning='Current snapshot only. Outputs may predate this code. Not evidence that these versions generated the outputs.',
                files=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=sha256(p)) for p in files])
    output.write_text(json.dumps(result,indent=2))
    print('Snapshot files:',len(files))

if __name__=='__main__': main()
