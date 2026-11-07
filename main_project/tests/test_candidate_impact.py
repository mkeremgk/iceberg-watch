import sys
import unittest
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from candidate_impact import interventions, component_cells, outcome_change


class ImpactTests(unittest.TestCase):
    def setUp(self):
        self.domain=np.ones((7,9),bool)
        self.target=np.zeros_like(self.domain);self.target[3,8]=True
        self.start=(3,0)

    def test_off_route_object_has_no_effect(self):
        records,_=interventions(self.domain,self.target,self.start,1,[np.array([0])])
        self.assertFalse(records[0]['single_candidate']['chosen_path_changed'])
        self.assertFalse(records[0]['removed_from_all']['distance_changed'])

    def test_barrier_increases_distance_and_removal_restores_it(self):
        records,_=interventions(self.domain,self.target,self.start,1,[np.array([3*9+4])])
        self.assertGreater(records[0]['single_candidate']['distance_change_m'],0)
        self.assertLess(records[0]['removed_from_all']['distance_change_m'],0)

    def test_shared_cell_is_not_removed_with_one_owner(self):
        records,_=interventions(self.domain,self.target,self.start,1,[np.array([31]),np.array([31])])
        self.assertTrue(all(r['single_candidate']['distance_changed'] for r in records))
        self.assertTrue(all(not r['removed_from_all']['chosen_path_changed'] for r in records))
        self.assertEqual(records[0]['unique_domain_cells'],0)

    def test_joint_closure_is_not_equal_to_sum_of_single_effects(self):
        a=np.array([r*9+4 for r in range(4)])
        b=np.array([r*9+4 for r in range(4,7)])
        records,full=interventions(self.domain,self.target,self.start,1,[a,b])
        self.assertEqual(full['status'],'no_path_under_model')
        self.assertTrue(all(r['single_status']=='model_path_found' for r in records))
        self.assertTrue(all(r['removed_from_all']['status_changed'] for r in records))
        self.assertIsNone(records[0]['removed_from_all']['distance_change_m'])

    def test_single_pixel_survives_aggregation_and_hole_is_filled(self):
        mask=np.zeros((10,10),np.uint8);mask[2:7,2:7]=1;mask[3:6,3:6]=0
        _,labels,stats,_=cv2.connectedComponentsWithStats(mask,connectivity=8)
        indices,count=component_cells(labels,stats,1,5,np.ones(mask.shape,bool))
        self.assertEqual(count,25);self.assertEqual(len(indices),4)
        mask[:]=0;mask[9,9]=1
        _,labels,stats,_=cv2.connectedComponentsWithStats(mask,connectivity=8)
        indices,count=component_cells(labels,stats,1,5,np.ones(mask.shape,bool))
        self.assertEqual(count,1);self.assertEqual(indices.tolist(),[3])

    def test_equal_length_geometry_is_not_distance_effect(self):
        a=dict(status='model_path_found',path=[[0,0],[0,1],[1,1]],distance_m=2)
        b=dict(status='model_path_found',path=[[0,0],[1,0],[1,1]],distance_m=2)
        change=outcome_change(a,b,1)
        self.assertTrue(change['equal_length_path_change']);self.assertFalse(change['distance_changed'])

if __name__=='__main__':unittest.main()
