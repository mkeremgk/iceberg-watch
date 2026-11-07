import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_associations import validate_reviews


class Reviews(unittest.TestCase):
    def setUp(self):
        self.link = dict(from_date='20250716', from_id=12, to_date='20250722', to_id=10)
        self.row = dict(self.link, decision='accepted', reviewer='tester', notes='shape inspected')

    def test_missing_stays_unreviewed(self):
        result = validate_reviews([self.link], [])
        self.assertEqual(result['counts'], {'unreviewed': 1})
        self.assertEqual(result['missing_review_rows'], 1)

    def test_human_decision_preserved_separately(self):
        result = validate_reviews([self.link], [self.row])
        self.assertEqual(result['counts'], {'accepted': 1})
        self.assertNotIn('decision', self.link)

    def test_rejects_unsafe_review_input(self):
        cases = [[self.row, self.row], [dict(self.row, from_id=99)],
                 [dict(self.row, reviewer='')], [dict(self.row, decision='true')]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_reviews([self.link], rows)

if __name__ == '__main__':
    unittest.main()
