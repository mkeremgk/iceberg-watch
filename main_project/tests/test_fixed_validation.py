import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from validate_fixed_boundary import check_path
class Checks(unittest.TestCase):
    def test_tampered_length_and_corner(self):
        allowed=np.ones((3,3),bool);target=np.zeros((3,3),bool);target[1,1]=True
        r=dict(status='model_path_found',path=[[0,0],[1,1]],distance_m=2**.5*40)
        self.assertTrue(check_path(r,allowed,target,(0,0),40))
        allowed[0,1]=False
        with self.assertRaises(ValueError):check_path(r,allowed,target,(0,0),40)
        allowed[0,1]=True;r['distance_m']=1
        with self.assertRaises(ValueError):check_path(r,allowed,target,(0,0),40)
