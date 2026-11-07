import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from corridor_scenario import corridor_mask
from access import shortest_access
from compare_access import compare_path_results
class CorridorScenario(unittest.TestCase):
 def test_total_width_and_nested_corridors(self):
  path=[[4,c] for c in range(9)]
  a=corridor_mask((9,9),path,100,200)
  self.assertTrue(a[3:6].all());self.assertFalse(a[:3].any());self.assertFalse(a[6:].any())
  b=corridor_mask((9,9),path,100,400)
  self.assertTrue(np.all(~a|b))
 def test_barrier_not_removed_and_failure_not_zero(self):
  path=[[4,c] for c in range(9)];corridor=corridor_mask((9,9),path,100,200)
  corridor[:,4]=False;targets=np.zeros((9,9),bool);targets[4,8]=True
  result=shortest_access(np.where(corridor,1.,np.inf),targets,(4,0),100)
  self.assertEqual(result['status'],'no_path_under_model')
  self.assertIsNone(compare_path_results(result,result)['distance_change_m'])
