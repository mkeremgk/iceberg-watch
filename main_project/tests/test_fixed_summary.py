import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from summarize_fixed_boundary import summarize
class Summary(unittest.TestCase):
    def records(self,values):
        return [dict(policy=str(i),spacing_m=80,comparisons=[dict(earlier_date='20250716',later_date='20250722',status='distance_comparison_computed' if v is not None else 'comparison_unavailable',distance_change_m=v)]) for i,v in enumerate(values)]
    def test_sign_and_missing(self):
        for values,expected in [([1,2],'increase'),([-1,2],'mixed'),([0,0],'unchanged'),([1,None],'incomplete')]:
            self.assertEqual(summarize(self.records(values))[0]['direction_across_tested_settings'],expected)
