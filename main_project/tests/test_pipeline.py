import sys
from pathlib import Path
import unittest
import numpy as np
from rasterio.transform import from_origin
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from access import shortest_access,aggregate_masks
from environment import apply_surface_annotation
from associate_candidates import associate

class AccessTests(unittest.TestCase):
    def test_nonfinite_spacing_rejected(self):
        for spacing in (float('nan'), float('inf'), 0, -1):
            with self.assertRaises(ValueError):
                shortest_access(np.ones((2,2)),np.ones((2,2),bool),(0,0),spacing)

    def test_weighted_cost_can_prefer_longer_route(self):
        cost=np.ones((3,5));cost[1,1:4]=100
        targets=np.zeros((3,5),bool);targets[1,4]=True
        result=shortest_access(cost,targets,(1,0),1)
        self.assertAlmostEqual(result['cost'],2+2*np.sqrt(2))
        self.assertTrue(all(cost[p]==1 for p in result['path']))

    def test_detour_and_closed_passage(self):
        cost=np.ones((7,9));target=np.zeros_like(cost,dtype=bool);target[3,8]=True
        baseline=shortest_access(cost,target,(3,0),100)
        self.assertEqual(baseline['distance_m'],800)
        cost[1:6,4]=np.inf
        detour=shortest_access(cost,target,(3,0),100)
        self.assertGreater(detour['distance_m'],800)
        self.assertTrue(all(np.isfinite(cost[p]) for p in detour['path']))
        cost[:,4]=np.inf
        self.assertEqual(shortest_access(cost,target,(3,0),100)['status'],'no_path_under_model')
    def test_no_corner_cut(self):
        cost=np.array([[1,np.inf],[np.inf,1]])
        targets=np.array([[False,False],[False,True]])
        self.assertEqual(shortest_access(cost,targets,(0,0),40)['status'],'no_path_under_model')
    def test_missing_target_and_start(self):
        cost=np.ones((2,2));targets=np.zeros((2,2),bool)
        self.assertEqual(shortest_access(cost,targets,(0,0),40)['status'],'no_reviewed_open_water_target')
        targets[1,1]=True;cost[0,0]=np.inf
        self.assertEqual(shortest_access(cost,targets,(0,0),40)['status'],'start_not_on_reviewed_passable_surface')
    def test_conservative_aggregation(self):
        env=np.full((4,4),3,np.uint8);env[0,0]=0;env[3,3]=2
        review=np.zeros_like(env);review[0,3]=2;review[3,0]=1
        allowed,target,barrier=aggregate_masks(env,review,2)
        self.assertEqual(allowed.tolist(),[[False,False],[True,True]])
        self.assertTrue(target[1,1]);self.assertTrue(barrier[1,0])
    def test_annotation_preserves_existing(self):
        labels=np.array([[0,1],[255,3]],np.uint8)
        g={'type':'Polygon','coordinates':[[(0,0),(2,0),(2,2),(0,2),(0,0)]]}
        out,n=apply_surface_annotation(labels,g,2,from_origin(0,2,1,1))
        self.assertEqual(out.tolist(),[[2,1],[255,3]]);self.assertEqual(n,1)
        self.assertEqual(labels[0,0],0)
        with self.assertRaises(ValueError):apply_surface_annotation(labels,g,5,from_origin(0,2,1,1))
    def test_ambiguous_association_rejected(self):
        def row(i,x):return dict(component_id=i,easting_m=x,northing_m=0,area_km2=1)
        self.assertEqual(associate([row(1,0)],[row(2,-100),row(3,100)],6),[])
        links=associate([row(1,0)],[row(2,100)],6)
        self.assertEqual(len(links),1)
        self.assertEqual(associate([row(1,0)],[row(2,100)],24),[])
        with self.assertRaises(ValueError):associate([row(1,0)],[row(2,100)],0)
        self.assertEqual(associate([row(1,0)],[row(2,100000)],6),[])

if __name__=='__main__':unittest.main()
