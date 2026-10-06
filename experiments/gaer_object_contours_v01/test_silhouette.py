import unittest,json
import numpy as np
import runtime as rt

class SilhouetteTests(unittest.TestCase):
 def test_components_holes_and_outside_gaps(self):
  from silhouette import evidence
  c=json.loads((rt.ART/'PROTOCOL.json').read_text())['silhouette'];a=np.zeros((80,80),np.float32);a[10:45,10:45]=1;a[20:30,20:30]=0;a[55:65,55:65]=.8;a[1,1]=1;a[10:15,26:28]=0
  e=evidence(a,c)
  self.assertTrue(e['holes'][25,25]);self.assertFalse(e['holes'][11,26]);self.assertTrue(e['object_mask'][60,60]);self.assertFalse(e['object_mask'][1,1])
  self.assertEqual(float(e['target'][25,25]),0);self.assertLessEqual(float((e['target']-a).max()),0)
  self.assertGreater(float(e['target'].sum()),50);self.assertEqual(e['components_kept'],2)
  valid=e['boundary'];n=e['normal_yx'];t=e['tangent_yx'];self.assertLess(float(np.abs((n*t).sum(-1))[valid].max()),1e-6)
 def test_no_coverage_cannot_be_black(self):
  from silhouette import evidence
  c=json.loads((rt.ART/'PROTOCOL.json').read_text())['silhouette'];a=np.zeros((80,80),np.float32);a[20:60,20:60]=.6;e=evidence(a,c)
  self.assertLessEqual(float(e['target'].max()),.600001);self.assertFalse(np.any(e['target'][a==0]))

if __name__=='__main__':unittest.main()
