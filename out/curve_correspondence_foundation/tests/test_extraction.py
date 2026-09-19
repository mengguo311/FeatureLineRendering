import unittest
import numpy as np
import cc

class Extraction(unittest.TestCase):
 def test_ordered_graph_junction_and_determinism(self):
  e=np.zeros((25,25),bool);e[12,2:23]=1;e[3:13,12]=1
  a=cc.trace_edges(e);b=cc.trace_edges(e)
  self.assertEqual(a,b);self.assertEqual(len(a['paths']),3)
  self.assertEqual(a['junctions'],[[12,12]])
  covered=set()
  for p in a['paths']:
   x=np.array(p); self.assertTrue(np.all(np.linalg.norm(np.diff(x,axis=0),axis=1)<=np.sqrt(2)))
   covered.update(map(tuple,p))
  self.assertEqual(covered,set(map(tuple,np.argwhere(e)[:,::-1])))
 def test_loop_topology_and_diagonal_staircase(self):
  e=np.zeros((15,15),bool)
  for p in [(5,1),(6,2),(7,3),(6,4),(5,5),(4,4),(3,3),(4,2)]:e[p[1],p[0]]=1
  a=cc.trace_edges(e);self.assertEqual(len(a['paths']),1);self.assertEqual(a['paths'][0][0],a['paths'][0][-1])
  self.assertEqual(a['junctions'],[])
 def test_corner_split_arclength_and_no_pixel_cloud(self):
  p=np.vstack([np.c_[np.arange(21),np.zeros(21)],np.c_[np.full(20,20),np.arange(1,21)]])
  a=cc.split_path(p,min_length=12,max_length=96,corner_window=4,corner_degrees=45,corner_suppression=6)
  self.assertEqual(len(a),2);self.assertAlmostEqual(sum(x['length'] for x in a),40)
  for x in a:self.assertTrue(x['eligible']);self.assertGreater(len(x['pixels']),10)
  self.assertTrue(np.allclose(a[0]['pixels'][-1],a[1]['pixels'][0]))
 def test_resample_descriptor_reversal(self):
  p=np.array([[4.,5.],[14.,5.]])
  q,s=cc.resample(p,2);self.assertEqual(len(q),6);np.testing.assert_allclose(s,[0,2,4,6,8,10])
  rgb=np.zeros((20,20,3));rgb[:5,:,0]=1;rgb[6:,:,1]=1
  d=cc.describe(rgb,q,1.2,[2,4]);r=cc.describe(rgb,q[::-1],1.2,[2,4])
  np.testing.assert_allclose(d,r[::-1,::-1],atol=1e-10)
 def test_axial_and_directed_angles(self):
  self.assertAlmostEqual(float(cc.axial_angle([1,0],[-1,0])),0)
  self.assertAlmostEqual(float(cc.axial_angle([1,0],[0,1])),90)
  self.assertTrue(np.isnan(cc.axial_angle([0,0],[1,0])))

if __name__=='__main__':unittest.main()

class Detector(unittest.TestCase):
 def test_frozen_detector_extraction_keeps_topology(self):
  import json,pathlib
  from src.multiscene_probe import edge_field
  cfg=json.loads((pathlib.Path(__file__).parents[1]/'config.json').read_text())
  rgb=np.ones((80,80,3));rgb[20:60,20:60]=0
  a=cc.extract(rgb,7,cfg)
  np.testing.assert_array_equal(a['edge'],edge_field(rgb,cfg)['edge'])
  self.assertGreater(len(a['curves']),0)
  for c in a['curves']:
   self.assertEqual(c['view'],7);self.assertIn('parent',c);self.assertIn('arc',c)
   self.assertTrue(np.all(np.diff(c['arc'])>0))
