import unittest
from env import *
from diagnostics import apparent_regions
from closure import *
class DiagnosticTests(unittest.TestCase):
 def test_closed_vs_open(self):
  d=np.zeros((40,40));d[10,10:30]=1;d[29,10:30]=1;d[10:30,10]=1;d[10:30,29]=1;rs=apparent_regions(d);self.assertEqual(len(rs),1);d[10,15:20]=0;self.assertEqual(len(apparent_regions(d)),0)
 def test_roi_border_not_region(self):self.assertEqual(len(apparent_regions(np.zeros((40,40)))),0)
 def test_nested_preserve_holes(self):
  d=np.zeros((50,50));d[4,4:46]=1;d[45,4:46]=1;d[4:46,4]=1;d[4:46,45]=1;d[20,20:30]=1;d[29,20:30]=1;d[20:30,20]=1;d[20:30,29]=1;rs=apparent_regions(d);self.assertEqual(len(rs),2);self.assertFalse(any(r[4,4] for r in rs))
 def test_rotation_link(self):
  R=np.array([[0,-1],[1,0]]);a=np.array([0.,0]);b=np.array([2.,0]);ta=np.array([1.,0]);tb=-ta
  self.assertEqual(link_gate(a,b,ta,tb,1,1,.01,True,True)[0],link_gate(R@a,R@b,R@ta,R@tb,1,1,.01,True,True)[0])
if __name__=='__main__':unittest.main()
