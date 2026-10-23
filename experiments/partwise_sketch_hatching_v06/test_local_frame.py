import runtime
from pathlib import Path
import json,unittest
import numpy as np
from geometry import mesh_data,resize_camera
from hatching import generate_layers
from local_frame import fit_frame,frame_normals,regenerate_partitions
from target_completion import render_pair
from hybrid import compose
from run_hybrid import read_npz

OLD=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_008')

class FrameTests(unittest.TestCase):
    def test_slanted_plane_frame_and_cross_angle(self):
        u=np.array([1.,0.,1.])/np.sqrt(2);v=np.array([0.,1.,0.])
        vertices=np.array([-2*u-v,2*u-v,2*u+v,-2*u+v])
        mesh=mesh_data(vertices,np.array([[0,1,2],[0,2,3]]),np.array([4,4]))
        frame=fit_frame(mesh,np.array([0,1]));basis=np.array(frame['basis'])
        self.assertAlmostEqual(abs(basis[0]@u),1.,places=10)
        normals=frame_normals(basis,[35.,95.]);n=mesh['normals'][0]
        tangents=np.cross(n,normals);tangents/=np.linalg.norm(tangents,axis=1)[:,None]
        self.assertAlmostEqual(abs(tangents[0]@tangents[1]),.5,places=10)
        style=dict(angle=35.,spacing=.06,length=.12,width=1.,plane='xz',cross_enabled=True,cross_angle=60.,cross_spacing=.075,cutting_basis=basis.tolist())
        paths,_=generate_layers(mesh,4,style)
        np.testing.assert_allclose(paths['points'],np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']]),atol=1e-12)
        # Each stored stroke stays on its selected sheet; a separated island is never bridged.
        vertices=np.vstack([vertices,vertices+np.array([0,4,0])]);faces=np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]])
        mesh=mesh_data(vertices,faces,np.array([4,3,4,4]));paths,_=generate_layers(mesh,4,style)
        self.assertNotIn(1,paths['face'])
        for sid in np.unique(paths['stroke_id']):
            fs=paths['face'][paths['stroke_id']==sid]
            self.assertFalse((fs<2).any() and (fs>=2).any())
        with self.assertRaises(ValueError):fit_frame(mesh,np.array([],int))
        with self.assertRaises(ValueError):generate_layers(mesh,4,dict(style,cutting_basis=[[1,0,0],[1,0,0]]))

    def test_real_legacy_identity_partitions_and_zero_link(self):
        t=read_npz(OLD/'asset/TARGET.npz');oldmesh=mesh_data(t['vertices'],t['faces'],t['old_face_regions'])
        newmesh=mesh_data(t['vertices'],t['faces'],t['face_regions'])
        old=read_npz(OLD/'asset/OLD_PATHS.npz');added=read_npz(OLD/'asset/ADDED_PATHS.npz')
        p=json.loads((OLD/'PROTOCOL.json').read_text());meta=json.loads((Path(p['scene']['asset'])/'asset.json').read_text())
        a,b=regenerate_partitions(oldmesh,newmesh,old,added,meta['styles']['4'],[[1,0,0],[0,0,1]],revision=False)
        for actual,expected in [(a,old),(b,added)]:
            for k in expected:np.testing.assert_array_equal(actual[k],expected[k],err_msg=k)
        c=resize_camera(next(v['camera'] for v in json.loads((OLD/'CAMERAS.json').read_text())['views'] if v['kind']=='build'),64)
        pair,_=render_pair(oldmesh,newmesh,a,b,meta,c);ref,_=render_pair(oldmesh,newmesh,old,added,meta,c)
        np.testing.assert_array_equal(pair['new'],ref['new'])
        paper=np.ones((64,64,3))*.95
        image,alpha=compose(paper,pair['new'],np.zeros((64,64)),True)
        np.testing.assert_array_equal(image,paper);self.assertEqual(float(alpha.sum()),0.)

if __name__=='__main__':unittest.main(verbosity=2)
