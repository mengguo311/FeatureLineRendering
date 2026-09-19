import unittest,tempfile,pathlib
import numpy as np
import cv2
from test_matching import camera
class Visuals(unittest.TestCase):
 def test_actual_projection_png_and_stable_colors(self):
  import cc_visual
  c=camera([0,0,0],[[100,0,50],[0,100,50],[0,0,1.]])
  r=[dict(id='persistent',xyz=np.array([[-.2,0,1],[.2,0,1]]))]
  a=cc_visual.curve_image(r,c,size=100,color=True);b=cc_visual.curve_image(r,c,size=100,color=True)
  np.testing.assert_array_equal(a,b);self.assertLess(a[50,50].mean(),250);self.assertGreater(a[0,0].mean(),250)
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'x.png';cc_visual.write_png(p,a);image=cv2.imread(str(p));self.assertEqual(image.shape,(100,100,3))
   with self.assertRaises(FileExistsError):cc_visual.write_png(p,a)
 def test_empty_and_matched_ink_never_add_geometry(self):
  import cc_visual
  c=camera([0,0,0],[[100,0,50],[0,100,50],[0,0,1.]])
  a=[dict(id=str(i),xyz=np.array([[-.2,i*.05,1],[.2,i*.05,1]])) for i in range(10)]
  sel=cc_visual.ink_prefix(a,[c],80,size=100);self.assertLessEqual(len(sel['ids']),len(a));self.assertGreater(sel['ink'],0)
  image=cc_visual.curve_image([],c,size=100);self.assertTrue(np.all(image==255))
 def test_blinding_key_is_separate_and_bytes_unchanged(self):
  import cc_visual
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);a=root/'a.png';b=root/'b.png';cc_visual.write_png(a,np.zeros((20,20,3),'u1'));cc_visual.write_png(b,np.full((20,20,3),255,'u1'))
   package=root/'blind';key=cc_visual.blind_package([('one',a),('two',b)],package,123)
   self.assertEqual(len(key),2);self.assertFalse((package/'identity_key.json').exists())
   self.assertEqual(sorted(p.read_bytes() for p in package.glob('*.png')),sorted([a.read_bytes(),b.read_bytes()]))
 def test_video_real_120_frames_and_contact_sheet(self):
  import cc_visual,imageio_ffmpeg
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'x.mp4';frames=[np.full((32,32,3),i%255,'u1') for i in range(120)]
   cc_visual.write_video(p,frames,24);count,_=imageio_ffmpeg.count_frames_and_secs(str(p));self.assertEqual(count,120)
   sheet=cc_visual.contact_sheet(frames[:4],['0','1','2','3'],2);self.assertEqual(sheet.shape[1],64)
if __name__=='__main__':unittest.main()

class ReferenceLayout(unittest.TestCase):
 def test_noncontiguous_reference_storage_is_drawable_and_rgb8_contiguous(self):
  import cc_visual
  image=np.full((60,60,3),255,'u1').transpose(1,0,2)
  self.assertFalse(image.flags.c_contiguous)
  cc_visual.draw_polyline(image,[[5,5],[50,50]])
  self.assertLess(image[20,20].mean(),250)
  converted=cc_visual.rgb8(image.astype(float)/255)
  self.assertTrue(converted.flags.c_contiguous)
