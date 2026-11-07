"""Verify a code-only installation without any Antarctic data or credentials."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root/'main_project'))
    import cv2
    from map_io import DIRECTORY
    from access_demo import main as synthetic_demo
    if cv2.__version__.split('.')[0] != '5':
        raise RuntimeError('The competition build requires OpenCV 5')
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s',
                    str(root/'main_project/tests'), '-q'], cwd=root, check=True)
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    synthetic_demo()
    result = json.loads((DIRECTORY/'synthetic_access_demo.json').read_text())
    if not (result['detour']['distance_m'] > result['baseline']['distance_m']
            and result['closed']['status'] == 'no_path_under_model'):
        raise RuntimeError('Synthetic routing contract failed')
    print('Installation verified: tests and synthetic detour/closed-passage demo passed.')
    print('This check does not reproduce the Antarctic analysis. See DATA_SETUP.md.')


if __name__ == '__main__':
    main()
