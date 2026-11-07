import sys,json,tempfile,unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_provenance import scene_fingerprint,verify_binding,canonical_links

class ReviewBinding(unittest.TestCase):
    def test_roundoff_tolerated_but_different_pair_rejected(self):
        a = [dict(from_id=1, to_id=2, distance_km=0.050620494527257434)]
        b = [dict(from_id=1, to_id=2, distance_km=0.05062049452725743)]
        self.assertEqual(canonical_links(a), canonical_links(b))
        b[0]['to_id'] = 3
        self.assertNotEqual(canonical_links(a), canonical_links(b))

    def test_geometry_changes_rejected_even_when_ids_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'association_review').mkdir()
            (root/'association_report.json').write_text(json.dumps({'links':[dict(from_date='20250716',to_date='20250722',from_id=1,to_id=1)]}))
            paths=['land_mask.tif']+[f'{kind}_{date}.tif' for kind in ('sar','proposals') for date in ('20250716','20250722')]
            def write(name,value,compress):
                with rasterio.open(root/name,'w',driver='GTiff',width=4,height=4,count=1,dtype='uint8',crs='EPSG:32759',transform=from_origin(100,200,40,40),compress=compress) as dst:dst.write(np.full((4,4),value,np.uint8),1)
            for name in paths:write(name,1,'lzw')
            (root/'association_review/review_binding.json').write_text(json.dumps({'fingerprint':scene_fingerprint(root)}))
            self.assertTrue(verify_binding(root))
            write('proposals_20250716.tif',1,'deflate')
            self.assertTrue(verify_binding(root))
            write('proposals_20250716.tif',2,'deflate')
            with self.assertRaises(ValueError):verify_binding(root)
