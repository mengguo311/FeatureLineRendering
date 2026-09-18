import tempfile,unittest
from pathlib import Path
import numpy as np,cv2
from test_multiscene import CFG

class VisualTests(unittest.TestCase):
    def test_real_glyph_pixels_are_deterministic_sign_invariant_and_empty_is_white(self):
        from src.corrected_visuals import glyph_image,spatial_order,ink_prefix
        camera=dict(K=[[200,0,199.5],[0,200,199.5],[0,0,1]],w2c=np.eye(4).tolist())
        rows=[dict(query=str(i),point=[(i-3)*.12,0,3],axis=[1.,0,0]) for i in range(8)]
        a,stats=glyph_image(rows,camera,.05)
        b,_=glyph_image([dict(r,axis=[-1.,0,0]) for r in rows],camera,.05)
        np.testing.assert_array_equal(a,b);self.assertGreater(np.sum(1-a),0)
        empty,_=glyph_image([],camera,.05);self.assertTrue(np.all(empty==1))
        self.assertEqual(spatial_order(rows,.05),spatial_order(rows[::-1],.05))
        subset,report=ink_prefix(rows,[camera],.05,2.,CFG)
        self.assertLessEqual(len(subset),len(rows));self.assertIn('relative_error',report)

    def test_orbit_and_video_have_exact_frozen_120_frames(self):
        from src.corrected_visuals import orbit_cameras,write_video
        camera=dict(K=[[200,0,199.5],[0,200,199.5],[0,0,1]],native_K=[[400,0,399.5],[0,400,399.5],[0,0,1]],w2c=np.eye(4).tolist())
        orbit=orbit_cameras([0,0,0],4,camera,CFG)
        self.assertEqual(len(orbit),120)
        centers=np.array([np.linalg.inv(c['w2c'])[:3,3] for c in orbit])
        elevation=np.degrees(np.arcsin(centers[:,2]/4))
        self.assertGreaterEqual(elevation.min(),17.-1e-9);self.assertLessEqual(elevation.max(),33.+1e-9)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'diagnostic.mp4'
            write_video(p,[np.full((400,400,3),i/119.) for i in range(120)],CFG)
            cap=cv2.VideoCapture(str(p));count=0
            while cap.read()[0]:count+=1
            cap.release();self.assertEqual(count,120)
