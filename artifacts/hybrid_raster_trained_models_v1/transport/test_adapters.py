import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('transport_adapters', HERE/'adapters.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

class Adapters(unittest.TestCase):
    def test_camera_scene_fov_and_native_principal(self):
        meta = {'camera_angle_x': .6194058656692505, 'frames':[{'transform_matrix':np.eye(4).tolist()} for _ in range(100)]}
        camera = a.camera_from_train(meta, 7, 800, 800)
        self.assertEqual(camera['native_K'][0][2],399.5)
        self.assertAlmostEqual(camera['native_K'][0][0],400/np.tan(meta['camera_angle_x']/2))
        np.testing.assert_array_equal(camera['w2c'],np.diag([1,-1,-1,1]))
        with self.assertRaises(ValueError): a.camera_from_train(meta,7,400,800)
    def test_arc_33_distinct_endpoints_exact_algorithm(self):
        cams={}
        for i,theta in [(7,0),(33,.2)]:
            pose=np.eye(4);pose[:3,3]=[4*np.sin(theta),0,4*np.cos(theta)]
            cams[str(i)]={'w2c':np.linalg.inv(pose).tolist(),'native_K':[[1000,0,399.5],[0,1000,399.5],[0,0,1]],'native_width':800,'native_height':800}
        arc=a.arc_from_center(cams,np.array([.1,.2,.3]))
        self.assertEqual(len(arc['frames']),33)
        self.assertEqual(len({a.canonical_hash(c['w2c']) for c in arc['frames']}),33)
        for j,i in [(0,7),(-1,33)]: np.testing.assert_allclose(arc['frames'][j]['w2c'],cams[str(i)]['w2c'],atol=1e-14)
        from scipy.spatial.transform import Rotation,Slerp
        center=np.array([.1,.2,.3]); poses=np.array([np.linalg.inv(cams[str(i)]['w2c']) for i in [7,33]])
        loc=poses[:,:3,3]-center;r=np.linalg.norm(loc,axis=1);u=loc/r[:,None]
        angle=np.degrees(np.arccos(np.clip(u@u.T,-1,1)))[0,1];theta=np.radians(angle);ts=np.linspace(0,1,33)
        dirs=(np.sin((1-ts)*theta)[:,None]*u[0]+np.sin(ts*theta)[:,None]*u[1])/np.sin(theta)
        radius=(1-ts)*r[0]+ts*r[1];rot=Slerp([0,1],Rotation.from_matrix(poses[:,:3,:3]))(ts).as_matrix()
        for n,c in enumerate(arc['frames']):
            pose=np.eye(4);pose[:3,:3]=rot[n];pose[:3,3]=center+dirs[n]*radius[n]
            np.testing.assert_array_equal(c['w2c'],np.linalg.inv(pose))
    def test_frame_spec_counts_and_no_source_pixels(self):
        cams={str(i):{'w2c':np.eye(4).tolist()} for i in a.F+a.C}
        manifest={'scene':'hotdog','cameras':cams,'arcs':[{'frames':[{'t':i/32} for i in range(33)]}]}
        specs=a.frame_specs(manifest)
        self.assertEqual(len(specs),49);self.assertEqual(len({x['key'] for x in specs}),49)
        self.assertEqual([x['index'] for x in specs if x['split']=='F'],a.F)
    def test_frozen_json_rejects_mismatch(self):
        with tempfile.TemporaryDirectory(dir=a.OUT/'tests') as d:
            path=Path(d)/'x.json';a.frozen_json(path,{'x':1});a.frozen_json(path,{'x':1})
            with self.assertRaises(RuntimeError):a.frozen_json(path,{'x':2})
    def test_inherited_source_parameter_equality(self):
        lock,record=a.inherited()
        self.assertEqual(lock['parameter_hash'],'6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9')
        self.assertEqual(record['lock_sha256'],'d5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926')
        self.assertEqual(record['sources'],lock['config']['sources'])
    def test_training_lock_rejects_incomplete_or_wrong_checkpoint(self):
        lock={'schema':1,'state':'COMPLETE','scene':'hotdog','seed':1729,'iterations':30000,
              'checkpoints':{'7000':{},'30000':{'iteration':30000,'path':str(a.OUT/'synthetic.ply'),'sha256':'a'*64}}}
        self.assertTrue(a.validate_training_lock('hotdog',a.OUT/'synthetic.ply','a'*64,lock))
        for changed in [dict(lock,state='FAILED'),dict(lock,seed=0),dict(lock,iterations=7000)]:
            with self.assertRaises(RuntimeError):a.validate_training_lock('hotdog',a.OUT/'synthetic.ply','a'*64,changed)
        with self.assertRaises(RuntimeError):a.validate_training_lock('hotdog',a.OUT/'synthetic.ply','b'*64,lock)

if __name__=='__main__': unittest.main(verbosity=2)
