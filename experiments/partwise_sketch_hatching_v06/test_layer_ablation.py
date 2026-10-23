import runtime
import json
import unittest
from pathlib import Path
import numpy as np
from layer_ablation import combine_coverage, render_pair, match_scales
from hybrid import compose
from geometry import mesh_data, resize_camera
from render import render

OLD = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_001')

class LayerTests(unittest.TestCase):
    def test_union_before_downsample(self):
        a=np.array([[True,False],[False,False]])
        b=np.array([[False,True],[False,False]])
        pair=combine_coverage({0:a,1:b},.8,2)
        self.assertAlmostEqual(float(pair['cross'][0,0]),.4)
        self.assertAlmostEqual(float(pair['base'][0,0]),.2)
        self.assertGreater(pair['cross'][0,0],max(pair['base'][0,0],pair['second'][0,0]))

    def test_real_anchored_paths_and_legacy_equivalence(self):
        p=json.loads((OLD/'PROTOCOL.json').read_text())['scenes']['lego']
        asset=Path(p['asset'])
        with np.load(asset/'mesh.npz') as z: m=mesh_data(z['vertices'],z['faces'],z['face_regions'])
        with np.load(asset/'region_4.npz') as z: paths={k:z[k] for k in z.files}
        selected=np.concatenate([np.flatnonzero(paths['layer_id']==k)[:24] for k in (0,1)])
        small={k:v[selected].copy() for k,v in paths.items()}
        saved={k:v.copy() for k,v in small.items()}
        meta=json.loads((asset/'asset.json').read_text())
        camera=resize_camera(p['build_cameras'][0],96)
        old=render(m,{4:small},meta['styles'],camera,2,meta.get('display'))
        pair,aux=render_pair(m,small,meta,camera)
        np.testing.assert_array_equal(pair['cross'],old['layers'][4])
        np.testing.assert_array_equal(pair['base'],old['style_layers']['4_0'])
        np.testing.assert_allclose(np.einsum('nij,njk->nik',small['bary'],m['tri'][small['face']]),small['points'],atol=1e-9,rtol=0)
        for k in small: np.testing.assert_array_equal(small[k],saved[k])

    def test_visible_budget_and_zero_link(self):
        paper=np.ones((2,2,3),np.float32)*.9
        support=np.array([[.2,.5],[0.,1.]],np.float32)
        target=np.array([[True,True],[False,True]])
        inks={'cross':np.ones((2,2),np.float32)*.8,'base':np.ones((2,2),np.float32)*.4}
        masses={k:float(np.abs(compose(paper,h,support,True)[0]-paper)[target].sum()) for k,h in inks.items()}
        scales,budget=match_scales(masses)
        for k,h in inks.items():
            image,alpha=compose(paper,h,support,True,scales[k])
            self.assertAlmostEqual(float(np.abs(image-paper)[target].sum()),budget,places=5)
            null,na=compose(paper,h,np.zeros_like(support),True,scales[k])
            np.testing.assert_array_equal(null,paper)
            self.assertEqual(float(na.sum()),0.)

if __name__=='__main__': unittest.main(verbosity=2)
