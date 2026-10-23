import runtime
import json
import unittest
from pathlib import Path
import numpy as np
from geometry import mesh_data,resize_camera
from render import render
from hybrid import compose
from test_gap_completion import fixture
from stroke_tone import stroke_tones,render_tones


class StrokeToneTests(unittest.TestCase):
    def test_arclength_sign_invariance_degenerate_and_shuffle(self):
        # Unequal segment lengths: averaging normalized normals is incorrect.
        m=dict(normals=np.array([[0.,0.,1.],[1.,0.,0.],[0.,0.,0.]]))
        p=dict(points=np.array([[[0,0,0],[2,0,0]],[[2,0,0],[2,1,0]],[[0,0,0],[0,1,0]],
                               [[0,0,0],[1,0,0]]],float),face=np.array([0,1,2,1]),
               stroke_id=np.array([10,10,20,30]),layer_id=np.array([0,0,0,1],np.uint8))
        w,stats=stroke_tones(m,p,light=np.array([0.,0.,1.]))
        self.assertAlmostEqual(w['tone_tau'][0],1-.8*2/3)
        self.assertEqual(w['tone_tau'][1],1.)
        self.assertEqual(stats['degenerate_normal_segments'],1)
        flipped,other=stroke_tones(dict(normals=-m['normals']),p,light=np.array([0.,0.,1.]))
        np.testing.assert_array_equal(w['tone_tau'],flipped['tone_tau'])
        for layer in (0,1):
            ii=w['layer_id']==layer
            np.testing.assert_array_equal(np.sort(w['tone_tau'][ii]),np.sort(w['shuffled_tau'][ii]))
        p['points'][0,1]=p['points'][0,0];p['points'][1,1]=p['points'][1,0]
        zero,stats=stroke_tones(m,p)
        self.assertEqual(zero['tone_tau'][0],1.)
        self.assertEqual(stats['zero_length_strokes'],1)

    def test_legacy_exact_uniform_attenuation_and_real_occluder(self):
        m,p,meta,c=fixture();weights,_=stroke_tones(m,p)
        pair,hi=render_tones(m,p,meta,c,weights)
        np.testing.assert_array_equal(pair['constant'],render(m,{4:p},meta['styles'],c)['hatch'])
        weights['tone_tau'][:]=.4;weights['shuffled_tau'][:]=.4
        scaled,_=render_tones(m,p,meta,c,weights)
        np.testing.assert_allclose(scaled['tone'],pair['constant']*.4,rtol=0,atol=3e-8)
        paper=np.ones((96,96,3),np.float32)*.95
        image,alpha=compose(paper,pair['tone'],np.zeros((96,96),np.float32),True)
        np.testing.assert_array_equal(image,paper);self.assertFalse(alpha.any())
        vertices=np.vstack([m['vertices'],[[-.3,-.4,3.4],[.3,-.4,3.4],[-.3,.4,3.4],[.3,.4,3.4]]])
        faces=np.vstack([m['faces'],[[6,7,8],[8,7,9]]]);occluder=mesh_data(vertices,faces,np.full(len(faces),4))
        blocked,_=render_tones(occluder,p,meta,c,weights)
        for ink in blocked.values():self.assertEqual(float(ink[40:56,42:54].sum()),0.)

    def test_real_asset_identity_and_small_render(self):
        root=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/baseline/portable_demo/examples/lego_bucket_cross')
        with np.load(root/'mesh.npz') as z:m=mesh_data(z['vertices'],z['faces'],z['face_regions'])
        with np.load(root/'region_4.npz') as z:p={k:z[k] for k in z.files}
        before={k:v.copy() for k,v in p.items()};meta=json.loads((root/'asset.json').read_text())
        weights,stats=stroke_tones(m,p)
        self.assertEqual(stats['strokes'],351);self.assertEqual(stats['segments'],1904)
        self.assertTrue(np.all((weights['tone_tau']>=.2)&(weights['tone_tau']<=1)))
        again,_=stroke_tones(m,p)
        for key in weights:np.testing.assert_array_equal(weights[key],again[key])
        scene=json.loads(Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_004/PROTOCOL.json').read_text())['scene']
        c=resize_camera(scene['build_cameras'][0],96)
        pair,_=render_tones(m,p,meta,c,weights)
        np.testing.assert_array_equal(pair['constant'],render(m,{4:p},meta['styles'],c)['hatch'])
        self.assertTrue(np.all(pair['tone']<=pair['constant']))
        for key in p:np.testing.assert_array_equal(p[key],before[key])


if __name__=='__main__':unittest.main(verbosity=2)
