"""Real CPU Open3D cached-depth chain with a known plane; no renderer or GT."""
import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.append(str(Path(__file__).resolve().parents[2]/'stage2'))
from safety import atomic_json,seal_stage,sha256
import postprocess as gpu_stages

class CachedTSDFPipeline(unittest.TestCase):
 def test_four_identity_cameras_preserve_camera_z_plane_and_all_views(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);model=root/'model';state=root/'state';data=root/'data'
   for p in [model/'depth_normal',state,data/'images']:p.mkdir(parents=True)
   cams=[];files=[]
   for i in range(4):
    name=f'{i:04d}';p=model/'depth_normal'/(name+'.npz')
    np.savez_compressed(p,median_camera_z=np.full((1,32,32),2.,np.float32),alpha=np.ones((1,32,32),np.float32));files.append(p)
    Image.fromarray(np.full((32,32,4),255,np.uint8),'RGBA').save(data/'images'/(name+'.png'))
    cams.append({'view':name,'width':32,'height':32,'fx':400.,'fy':400.,'extrinsic':np.eye(4).tolist()})
   cp=model/'depth_normal/cameras_and_conventions.json';atomic_json(cp,cams);files.append(cp)
   inputs={'test':'known-camera-z-plane'}
   for s in ['train','export']:seal_stage(state/(s+'.seal.json'),s,inputs,files)
   hashes={str(p):sha256(p) for p in files}
   c={'state_dir':str(state),'model':str(model),'data':str(data),'inputs':inputs,'expected_scene':{'views':4},'reports':{'tsdf':str(state/'tsdf.report.json')}}
   with patch.dict(os.environ,{'RADEGS_ATTEMPT':'cpu_known_plane'}):gpu_stages.tsdf(c)
   r=json.loads((state/'tsdf.report.json').read_text());self.assertEqual(len(r['details']['view_records']),4)
   self.assertTrue(all(v['integrated'] and v['mode']=='C24_NATIVE_STRIDE4' for v in r['details']['view_records']))
   import open3d as o3d
   mesh=o3d.io.read_triangle_mesh(str(model/'recon.ply'));vertices=np.asarray(mesh.vertices)
   self.assertGreater(len(mesh.triangles),0);np.testing.assert_allclose(vertices[:,2],2.,atol=.002)
   self.assertEqual(hashes,{str(p):sha256(p) for p in files})
if __name__=='__main__':unittest.main(verbosity=2)
