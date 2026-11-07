import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluate_reviews import summarize

class ReviewEvaluation(unittest.TestCase):
    def test_empty_is_not_zero_accuracy(self):
        self.assertIsNone(summarize([])['acceptance_fraction_all'])
    def test_uncertain_is_not_discarded_from_denominator(self):
        result=summarize([{'decision':x} for x in ('accepted','rejected','uncertain','unreviewed')])
        self.assertEqual(result['acceptance_fraction_all'],.25)
        self.assertEqual(result['unresolved_fraction'],.5)

if __name__=='__main__':unittest.main()
