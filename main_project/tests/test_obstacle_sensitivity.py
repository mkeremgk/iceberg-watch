import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from obstacle_sensitivity import perturb,bounds
class BoundarySensitivity(unittest.TestCase):
 def test_nested_masks_and_zero_identity(self):
  mask=np.zeros((15,15),bool);mask[4:11,4:11]=True
  masks=[perturb(mask,n) for n in (-80,-40,0,40,80)]
  self.assertTrue(np.array_equal(masks[2],mask))
  for a,b in zip(masks,masks[1:]):self.assertTrue(np.all(~a|b))
  self.assertFalse(perturb(np.zeros((5,5),bool),80).any())
 def test_independent_offsets_can_reverse_sign(self):
  self.assertEqual(bounds([100,120],[110,130]),[-10,30])
  self.assertIsNone(bounds([],[110]))
