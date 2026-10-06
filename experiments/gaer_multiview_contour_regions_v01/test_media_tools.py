import tempfile,unittest
from pathlib import Path
import numpy as np
import runtime as rt
from media_tools import as_rgb,save_image,make_panel,make_strip,encode_video

class MediaTests(unittest.TestCase):
 def test_complete_video_and_manifest(self):
  with tempfile.TemporaryDirectory(prefix='media_test_',dir=rt.OUT/'tmp') as d:
   d=Path(d);paths=[]
   for i in range(33):
    a=np.full((32,32,3),255,np.uint8);a[:,i%32,:]=0;a[:4,:,0]=i*7;p=save_image(d/f'{i:03d}.png',a);paths.append(p)
   panel=make_panel([[('one',np.ones((3,32,32),np.float32)),('two',np.zeros((32,32),bool))]],tile_size=32,label_height=20)
   self.assertEqual(panel.shape,(52,64,3));self.assertEqual(np.asarray(as_rgb(np.ones((3,32,32),np.float32))).max(),255)
   strip=make_strip(paths,d/'strip.png',columns=3,thumb_width=32);self.assertEqual(strip.shape[0],11*(32+25))
   m=encode_video(paths,d/'smoke.mp4',frame_records=[{'camera_hash':str(i),'geometry_hash':'same'} for i in range(33)])
   self.assertEqual(m['decoded_frames'],33);self.assertEqual(m['distinct_decoded_frames'],33);self.assertTrue(m['faststart']);self.assertTrue(all(x['geometry_hash']=='same' for x in m['frames']))
   with self.assertRaises(ValueError):encode_video(paths[:-1],d/'incomplete.mp4')

if __name__=='__main__':unittest.main()
