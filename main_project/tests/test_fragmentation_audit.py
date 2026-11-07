import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fragmentation_audit import nearby_pairs
class FragmentScreen(unittest.TestCase):
 def test_radius_and_allowed_ids(self):
  labels=np.zeros((8,8),np.int32);labels[0,0]=1;labels[0,3]=2;labels[5,5]=3
  self.assertEqual(nearby_pairs(labels,[1,2,3],2),[])
  self.assertEqual(nearby_pairs(labels,[1,2,3],3),[(1,2)])
  self.assertEqual(nearby_pairs(labels,[1,3],3),[])
