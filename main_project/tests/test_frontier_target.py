import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from access import frontier
from access import shortest_access
class Frontier(unittest.TestCase):
    def test_no_interior_target_or_transit(self):
        ribbon=np.zeros((9,9),bool);ribbon[:,5:]=True
        approach=~ribbon;edge=frontier(ribbon,approach)
        self.assertTrue(edge[:,5].all());self.assertFalse(edge[:,6:].any())
        result=shortest_access(np.where(approach|edge,1.,np.inf),edge,(4,1),200)
        self.assertEqual(result['distance_m'],800)
        self.assertEqual(result['end'],(4,5))
    def test_no_contact_no_frontier(self):
        ribbon=np.zeros((9,9),bool);ribbon[:,6:]=True
        approach=np.zeros_like(ribbon);approach[:,:3]=True
        self.assertFalse(frontier(ribbon,approach).any())
