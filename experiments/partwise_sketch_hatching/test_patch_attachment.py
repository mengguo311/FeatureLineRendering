"""Development-only attachment controls; no acceptance configuration is opened."""
import round007_common
import argparse
import unittest
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--backend',choices=['endpoints','new'],default='new');args=p.parse_args()
if args.backend=='new':
 from patch_fixture import validate_attachment
else:
 def validate_attachment(path, segment_faces, faces, shared_edge, eps=1e-9):
  # Deliberately insufficient baseline: endpoints belong to the union;
  # never checks segment identities or face-transition location.
  for q in path:
   ok=False
   for f in faces:
    residual=abs(q[2]-f['z0']-f['sx']*q[0]-f['sy']*q[1])
    xy=np.array(f['xy']);cross=[]
    for a,b in zip(xy,np.roll(xy,-1,axis=0)):
     v=b-a;w=q[:2]-a;cross.append(v[0]*w[1]-v[1]*w[0])
    ok |= residual<=eps and (min(cross)>=-eps or max(cross)<=eps)
   if not ok:raise ValueError('attachment endpoint outside union')
  return {'valid':True}

def fixture():
 faces=[{'z0':3.,'sx':0.,'sy':.2,'xy':[[-1,0],[1,0],[0,-1]]},
        {'z0':3.,'sx':0.,'sy':-.5,'xy':[[-1,0],[1,0],[0,1]]}]
 path=np.array([[0,-.8,2.84],[0,0,3.],[0,.8,2.6]])
 return faces,path,np.array([[-1,0,3],[1,0,3]])

class AttachmentTests(unittest.TestCase):
 def test_genuine_shared_edge_path_valid(self):
  f,x,e=fixture();self.assertTrue(validate_attachment(x,[0,1],f,e)['valid'])
 def test_straight_chord_rejected_for_either_face(self):
  f,x,e=fixture()
  for face in [0,1]:
   with self.assertRaisesRegex(ValueError,'attachment'):validate_attachment(x[[0,2]],[face],f,e)
 def test_wrong_segment_owner_rejected(self):
  f,x,e=fixture()
  with self.assertRaisesRegex(ValueError,'attachment'):validate_attachment(x,[1,0],f,e)
 def test_outside_finite_face_rejected(self):
  f,x,e=fixture();x[0]=[.9,-.8,2.84]
  with self.assertRaisesRegex(ValueError,'attachment'):validate_attachment(x,[0,1],f,e)
 def test_off_plane_rejected(self):
  f,x,e=fixture();x[0,2]+=.01
  with self.assertRaisesRegex(ValueError,'attachment'):validate_attachment(x,[0,1],f,e)
 def test_false_shared_edge_rejected(self):
  f,x,e=fixture();e[:,1]=.1
  with self.assertRaisesRegex(ValueError,'shared edge'):validate_attachment(x,[0,1],f,e)
 def test_single_face_segment_valid(self):
  f,x,e=fixture();self.assertTrue(validate_attachment(x[:2],[0],f,e)['valid'])
 def test_reversed_path_and_face_assignment_valid(self):
  f,x,e=fixture();self.assertTrue(validate_attachment(x[::-1],[1,0],f,e)['valid'])

if __name__=='__main__':unittest.main(argv=['test_patch_attachment'],verbosity=2)
