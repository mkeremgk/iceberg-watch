import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from route_geometry_audit import geometry


class RouteGeometry(unittest.TestCase):
    def test_equal_lengths_can_have_different_paths(self):
        a = [[0, 0], [0, 1], [1, 1]]
        b = [[0, 0], [1, 0], [1, 1]]
        result = geometry(a, b, 80)
        self.assertFalse(result['identical_ordered_cells'])
        self.assertEqual(result['shared_edge_length_m'], 0)
        self.assertEqual(result['earlier_only_edge_length_m'], 160)
        self.assertEqual(result['later_only_edge_length_m'], 160)
        self.assertEqual(result['endpoint_shift_m'], 0)
        self.assertEqual(result['max_nearest_vertex_distance_m'], 80)

    def test_same_path_and_missing_path(self):
        a = [[1, 1], [1, 2], [1, 3]]
        result = geometry(a, a, 200)
        self.assertTrue(result['identical_ordered_cells'])
        self.assertEqual(result['shared_edge_length_m'], 400)
        self.assertEqual(result['max_nearest_vertex_distance_m'], 0)
        self.assertEqual(geometry([], a, 200)['status'], 'unavailable_path')
