import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from temporal_comparison import compare_records

class Temporal(unittest.TestCase):
    def test_missing_evidence_never_becomes_zero(self):
        rows=compare_records([{'date':'20250716','result':{}},{'date':'20250722','result':{}}])
        self.assertIsNone(rows[0]['distance_change_m'])
        self.assertEqual(rows[0]['status'],'incomparable_scenarios')
    def test_duplicate_dates_rejected(self):
        with self.assertRaises(ValueError):compare_records([{'date':'20250716'}]*2)
    def test_all_ordered_pairs(self):
        rows=compare_records([{'date':d} for d in ('20250821','20250716','20250722','20250728')])
        self.assertEqual(len(rows),6)
        self.assertTrue(all(r['earlier_date']<r['later_date'] for r in rows))
if __name__=='__main__':unittest.main()
