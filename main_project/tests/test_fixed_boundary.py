import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fixed_boundary_scenario import fill_candidates
from access import shortest_access
class FixedBoundary(unittest.TestCase):
    def test_unknown_policy_rejected(self):
        with self.assertRaises(ValueError):
            fill_candidates(np.zeros((3,3),np.uint8),'offshore_typo')

    def test_policy_and_holes(self):
        a=np.zeros((12,12),np.uint8);a[2:7,2:7]=1;a[3:6,3:6]=0;a[9,9]=2
        offshore=fill_candidates(a,'offshore_only');all_regions=fill_candidates(a,'all_retained')
        self.assertTrue(offshore[4,4]);self.assertFalse(offshore[9,9]);self.assertTrue(all_regions[9,9])
    def test_blocked_fixed_target_does_not_move(self):
        target=np.zeros((7,7),bool);target[3,5]=True
        cost=np.ones((7,7));cost[3,5]=np.inf
        result=shortest_access(cost,target,(3,1),40)
        self.assertNotEqual(result['status'],'model_path_found')
        self.assertEqual(int(target.sum()),1)
