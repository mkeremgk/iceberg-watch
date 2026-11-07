import sys,json,tempfile,unittest
from pathlib import Path
from copy import deepcopy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scenario_evidence import load_evidence,file_hash,touches_unknown
from access import shortest_access
from temporal_comparison import compare_records
from plot_temporal import plot_pair,projected_path

class Workflow(unittest.TestCase):
    def test_evidence_bound_to_date_and_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            raster=Path(folder)/'environment';raster.write_bytes(b'fixture')
            record=dict(date='20250716',environment_sha256=file_hash(raster),status='human_reviewed_scenario',**{k:'synthetic' for k in ('boundary_source','surface_source','interpretation','reviewer','limitations')})
            source=Path(folder)/'evidence.json';source.write_text(json.dumps(record))
            self.assertEqual(load_evidence(source,'20250716',raster)['reviewer'],'synthetic')
            with self.assertRaises(ValueError):load_evidence(source,'20250722',raster)
            raster.write_bytes(b'changed')
            with self.assertRaises(ValueError):load_evidence(source,'20250716',raster)
    def test_internal_unknown_and_edge(self):
        env=np.full((10,10),3,dtype=np.uint8)
        self.assertFalse(touches_unknown([[5,5]],env,1))
        env[5,6]=0
        self.assertTrue(touches_unknown([[5,5]],env,1))
        self.assertTrue(touches_unknown([[0,5]],env,1))
        self.assertIsNone(touches_unknown([],env,1))
    def test_solver_to_comparison_and_plot(self):
        cost=np.ones((15,15));target=np.zeros_like(cost,dtype=bool);target[7,12]=True
        a=dict(date='20250716',coordinate_crs='EPSG:32759',grid_transform=[40,0,1000,0,-40,2000],grid_shape=[15,15],grid_spacing_m=40,movement_model='equal_distance',obstacle_policy='synthetic',candidate_buffer_m=0,start_projected=[1100,1700],evidence=dict(boundary_source='synthetic',surface_source='synthetic',interpretation='synthetic'),boundary_contact=False,result=shortest_access(cost,target,(7,2),40))
        b=deepcopy(a);b['date']='20250722';cost[4:11,7]=np.inf;b['result']=shortest_access(cost,target,(7,2),40)
        result=compare_records([a,b])[0]
        self.assertGreater(result['distance_change_m'],0)
        np.testing.assert_allclose(projected_path(a)[0],[1100,1700])
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'pair.png';plot_pair(a,b,output);self.assertGreater(output.stat().st_size,1000)
