import unittest
import cv2
import numpy as np
from src.stroke_relations import _arrangements,view_evidence,projected_metrics
CFG={'sigmas':[1.5,2.5],'canny':[50,120],'min_arm_px':12,'junction_px':4,'repeat_px':4,'match_px':3,'match_cos':.85,'cell_px':32,'relations_per_cell':2,'max_matches_per_arm':3}

class RelationTests(unittest.TestCase):
    def test_distant_infinite_line_intersection_rejected(self):
        lines=np.array([[[10,10],[30,10]],[[60,40],[60,70]]],float)
        self.assertEqual(_arrangements(lines,CFG),[])
    def test_t_is_image_relation_and_requires_finite_arms(self):
        lines=np.array([[[20,50],[100,50]],[[60,50],[60,100]]],float)
        out=_arrangements(lines,CFG)
        self.assertEqual(len(out),1);self.assertEqual(len(out[0]['arms']),3)
    def test_two_scale_corner_has_complementary_bundles(self):
        gray=np.full((160,160),255,np.uint8)
        # Candidates follow the boundaries of a filled region, not the center
        # of a thick stroke whose two blurred edges lie several pixels away.
        cv2.rectangle(gray,(35,35),(125,125),0,-1)
        paths=[[np.column_stack([np.linspace(35,125,100),np.full(100,35)])],
               [np.column_stack([np.full(100,35),np.linspace(35,125,100)])]]
        u,l,e,o,s=view_evidence(gray,paths,CFG,0)
        self.assertGreater(s['relations'],0)
        self.assertTrue(any(b['ids']==[0,1] for r in e for b in r['bundles']))
        self.assertTrue(all(len(b['ids'])>=2 for r in e for b in r['bundles']))
        metrics=projected_metrics(paths,np.ones(2,bool),gray.shape)
        self.assertAlmostEqual(metrics['visible_length_px'],180)

if __name__=='__main__':unittest.main()
