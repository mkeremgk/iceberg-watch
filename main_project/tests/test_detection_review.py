import copy
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_detection_review import choose_tiles, validate_annotations

class DetectionReview(unittest.TestCase):
    def test_selection_repeatable_and_excludes_invalid_tiles(self):
        valid=np.ones((40,40),bool);land=np.zeros((40,40),bool)
        land[:,0:2]=True;valid[30:40,30:40]=False
        a,pools=choose_tiles(valid,land,10)
        self.assertEqual(a,choose_tiles(valid,land,10)[0])
        self.assertEqual(sum(t['stratum']=='coastal' for t in a),2)
        self.assertEqual(sum(t['stratum']=='offshore' for t in a),2)
        self.assertTrue(all(valid[t['row']:t['row']+10,t['col']:t['col']+10].all() for t in a))
    def test_no_silent_completion_or_wrong_pack(self):
        pack={'pack_id':'a','tiles':[{'id':'one','size':250}]}
        data={'pack_id':'a','reviewer':'tester','tiles':[{'id':'one','reviewed':True,'points':[]}]}
        self.assertEqual(validate_annotations(data,pack),1)
        bad=copy.deepcopy(data);bad['tiles'][0]['reviewed']=False
        with self.assertRaises(ValueError):validate_annotations(bad,pack)
        bad=copy.deepcopy(data);bad['pack_id']='b'
        with self.assertRaises(ValueError):validate_annotations(bad,pack)
        bad=copy.deepcopy(data);bad['tiles'][0]['points']=[{'x':250,'y':0,'class':'uncertain'}]
        with self.assertRaises(ValueError):validate_annotations(bad,pack)
        bad=copy.deepcopy(data);bad['tiles']*=2
        with self.assertRaises(ValueError):validate_annotations(bad,pack)
