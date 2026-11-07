"""Verify all manifest-listed package files; requires only the Python standard library."""
import hashlib
import json
from pathlib import Path


def verify(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
    for name, expected in manifest.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f'Missing or invalid package path: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Package file changed: {name}')
    return len(manifest)


if __name__=='__main__':
    print('Verified packaged files:',verify(Path(__file__).resolve().parents[2]))
