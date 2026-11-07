"""Candidate-independent, blinded review tiles. No detection accuracy is inferred."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from map_io import DIRECTORY, read


def choose_tiles(valid, land, tile_size=250, seed=20261020):
    pools = {'coastal': [], 'offshore': []}
    h, w = valid.shape
    for r in range(0, h-tile_size+1, tile_size):
        for c in range(0, w-tile_size+1, tile_size):
            v = valid[r:r+tile_size, c:c+tile_size]
            l = land[r:r+tile_size, c:c+tile_size] > 0
            fraction = float(l.mean())
            if v.mean() < .95 or fraction >= .5:
                continue
            kind = 'coastal' if fraction > 0 else 'offshore'
            pools[kind].append(dict(row=r, col=c, size=tile_size, stratum=kind))
    rng = np.random.default_rng(seed)
    selected = []
    for kind, pool in pools.items():
        if len(pool) < 2:
            raise ValueError(f'Insufficient eligible {kind} tiles')
        selected.extend(pool[i] for i in rng.choice(len(pool), 2, replace=False))
    return selected, {k: len(v) for k, v in pools.items()}


def validate_annotations(data, pack):
    if data.get('pack_id') != pack['pack_id']:
        raise ValueError('Wrong source pack')
    if not str(data.get('reviewer', '')).strip():
        raise ValueError('Reviewer required')
    tiles = {t['id']: t for t in pack['tiles']}
    records = data.get('tiles', [])
    if len(records) != len(tiles) or {r['id'] for r in records} != set(tiles):
        raise ValueError('Missing or duplicate tiles')
    for record in records:
        if record.get('reviewed') is not True:
            raise ValueError('Every tile needs explicit review, including empty tiles')
        size = tiles[record['id']]['size']
        for point in record.get('points', []):
            if point.get('class') not in ('iceberg_candidate', 'uncertain'):
                raise ValueError('Unknown annotation class')
            if not (0 <= point['x'] < size and 0 <= point['y'] < size):
                raise ValueError('Point outside tile')
    return len(records)


def main():
    land, profile = read(DIRECTORY/'land_mask.tif')
    files = sorted(DIRECTORY.glob('sar_????????.tif'))
    images = {}; common = np.ones(land.shape, bool); hashes = {}
    for path in [DIRECTORY/'land_mask.tif', *files]:
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in files:
        im, _ = read(path, profile); images[path.stem[4:]] = im
        common &= np.isfinite(im)
    selected, pools = choose_tiles(common, land)
    spec = dict(seed=20261020, source_sha256=hashes, selected=selected, eligible_pools=pools,
                selection='2 coastal + 2 offshore spatial tiles, repeated across dates; independent of proposals',
                limitations=['Pilot review, not representative regional accuracy.',
                             'Repeated dates at the same spatial tiles are correlated.',
                             'Same-source visual annotations are not independent physical ground truth.',
                             'Point marks do not establish object area or segmentation IoU.',
                             'No precision/recall until annotations and an explicit matching protocol are reviewed.'])
    pack_id = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]
    folder = DIRECTORY/'detection_review'/pack_id
    folder.mkdir(parents=True, exist_ok=True)
    tiles = []
    for date, im in images.items():
        lo, hi = np.nanpercentile(im, [2, 98])
        for n, tile in enumerate(selected):
            r, c, size = tile['row'], tile['col'], tile['size']
            crop = im[r:r+size, c:c+size]
            gray = np.uint8(np.clip((np.nan_to_num(crop,nan=lo)-lo)/(hi-lo), 0, 1)*255)
            name = f'{date}_{n+1}'
            if not cv2.imwrite(str(folder/(name+'.png')), gray):
                raise OSError('Could not write review image')
            r0, c0 = max(0, r-size), max(0, c-size)
            r1, c1 = min(im.shape[0], r+2*size), min(im.shape[1], c+2*size)
            context = im[r0:r1, c0:c1]
            context_gray = np.uint8(np.clip((np.nan_to_num(context,nan=lo)-lo)/(hi-lo), 0, 1)*255)
            context_rgb = cv2.cvtColor(context_gray, cv2.COLOR_GRAY2BGR)
            context_rgb[~np.isfinite(context)] = (120, 60, 120)
            if not cv2.imwrite(str(folder/(name+'_context.png')), context_rgb):
                raise OSError('Could not write context image')
            tiles.append(dict(id=name, date=date, image=name+'.png',
                              context_image=name+'_context.png', context_x=c-c0,
                              context_y=r-r0, context_width=c1-c0, context_height=r1-r0, **tile))
    pack = dict(pack_id=pack_id, tiles=tiles, **spec)
    (folder/'pack.json').write_text(json.dumps(pack, indent=2))
    template = Path(__file__).with_name('detection_review.html').read_text()
    (folder/'index.html').write_text(template.replace('PACK_DATA', json.dumps(pack)))
    print('Blinded detection review:', folder/'index.html')


if __name__ == '__main__':
    main()
