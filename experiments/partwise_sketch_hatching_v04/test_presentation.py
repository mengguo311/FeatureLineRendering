import runtime
from runtime import OUTPUT_ROOT,sha
import unittest,json,os
from unittest.mock import patch
from pathlib import Path
import numpy as np
from demo import load_asset
from presentation import trajectory,camera_values,export,replay
from geometry import project

class PresentationBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asset=OUTPUT_ROOT/'units/unit_011/portable_demo/assets/ficus'
        cls.mesh,cls.paths,cls.meta=load_asset(cls.asset)
        cls.camera=dict(azimuth=97,elevation=28,distance=5.2)

    def test_whole_real_proxy_fit_and_distinct_motion_cameras(self):
        for kind,count in [('orbit',12),('zoom',6)]:
            values=dict(azimuth=-179,elevation=75,distance=3.8)
            cameras,info=trajectory(self.mesh,values,kind)
            self.assertEqual(len(cameras),count)
            self.assertEqual(len({json.dumps(c) for c in cameras}),count)
            for c in cameras:
                uv,z=project(self.mesh['vertices'],c)
                self.assertTrue((z>.2).all())
                self.assertTrue((uv>=16-1e-6).all() and (uv<=495+1e-6).all())

    def test_current_image_never_auto_fits(self):
        from geometry import orbit_camera
        cameras,_=trajectory(self.mesh,self.camera,'image')
        self.assertEqual(cameras,[orbit_camera(**self.camera)])

    def test_request_bounds_reject_nan_bool_and_unbounded_work(self):
        for key,value in [('distance',float('nan')),('distance',True),('azimuth',361),('elevation',90),('distance',2)]:
            with self.assertRaises(ValueError):camera_values(dict(self.camera,**{key:value}))
        with self.assertRaises(ValueError):trajectory(self.mesh,self.camera,'long')

    def test_missing_encoder_fails_before_output(self):
        output=OUTPUT_ROOT/'units/unit_012/tests'/('missing_encoder_'+str(os.getpid()))
        with patch.dict(os.environ,{'DEMO_FFMPEG':'/nonexistent/presentation/ffmpeg'}),self.assertRaises(ValueError):
            export(self.asset,output,'orbit',self.camera)
        self.assertFalse(output.exists())

    def test_corrupt_replay_is_rejected_before_render(self):
        folder=OUTPUT_ROOT/'units/unit_012/tests'/('corrupt_'+str(os.getpid()));folder.mkdir()
        (folder/'MANIFEST.json').write_text(json.dumps({'files':{'missing.npz':'0'*64}}))
        with self.assertRaises(ValueError):replay(folder,folder/'output')
        self.assertFalse((folder/'output').exists())

if __name__=='__main__':unittest.main(verbosity=2)
