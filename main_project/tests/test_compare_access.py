import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compare_access import compare_distances, compare_path_results


class ComparisonTests(unittest.TestCase):
    def test_lengthening_shortening_and_equal(self):
        self.assertEqual(compare_distances(10000, 12000),
                         {'distance_change_m': 2000, 'relative_change_pct': 20})
        self.assertEqual(compare_distances(10000, 8000)['relative_change_pct'], -20)
        self.assertEqual(compare_distances(10000, 10000)['distance_change_m'], 0)

    def test_invalid_distances(self):
        for value in (None, True, '100', -1, float('nan'), float('inf')):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): compare_distances(value, 100)
                with self.assertRaises(ValueError): compare_distances(100, value)
        with self.assertRaises(ValueError): compare_distances(0, 100)
        self.assertEqual(compare_distances(100, 0)['relative_change_pct'], -100)

    def test_unavailable_results_do_not_become_zero(self):
        for status in ('no_reviewed_open_water_target', 'no_path_under_model'):
            result = compare_path_results(
                {'status': 'model_path_found', 'distance_m': 1000},
                {'status': status})
            self.assertEqual(result['status'], 'comparison_unavailable')
            self.assertEqual(result['later_status'], status)
            self.assertIsNone(result['distance_change_m'])

    def test_success_and_missing_distance(self):
        earlier = {'status': 'model_path_found', 'distance_m': 10000}
        later = {'status': 'model_path_found', 'distance_m': 12000}
        self.assertEqual(compare_path_results(earlier, later)['relative_change_pct'], 20)
        with self.assertRaises(ValueError):
            compare_path_results(earlier, {'status': 'model_path_found'})


class ScenarioComparisonTests(unittest.TestCase):
    def records(self):
        from copy import deepcopy
        first = dict(date='20250716', coordinate_crs='EPSG:32759',
                     grid_transform=[40, 0, 0, 0, -40, 100000],
                     grid_shape=[2500, 2500], grid_spacing_m=80,
                     movement_model='equal_distance', obstacle_policy='all_candidates',
                     candidate_buffer_m=0, start_projected=[1000, 2000],
                     evidence=dict(boundary_source='synthetic fixture',
                                   surface_source='synthetic fixture', interpretation='synthetic'),
                     boundary_contact=False,
                     result=dict(status='model_path_found', distance_m=10000))
        later = deepcopy(first)
        later['date'] = '20250821'
        later['result']['distance_m'] = 12000
        return first, later

    def test_comparable_synthetic_records(self):
        from compare_access import compare_scenarios
        self.assertEqual(compare_scenarios(*self.records())['relative_change_pct'], 20)

    def test_different_start_grid_policy_or_date_rejected(self):
        from compare_access import compare_scenarios
        for field, value in [('start_projected', [1000, 5000]),
                             ('grid_spacing_m', 200), ('obstacle_policy', 'offshore'),
                             ('date', '20250716'), ('boundary_contact', True)]:
            first, later = self.records()
            later[field] = value
            with self.subTest(field=field):
                self.assertEqual(compare_scenarios(first, later)['status'], 'incomparable_scenarios')

    def test_missing_evidence_rejected(self):
        from compare_access import compare_scenarios
        first, later = self.records()
        later['evidence']['boundary_source'] = ''
        self.assertIsNone(compare_scenarios(first, later)['distance_change_m'])


if __name__ == '__main__':
    unittest.main()
