import runtime
import json
import unittest
from pathlib import Path
import numpy as np
from geometry import mesh_data,resize_camera
from hatching import generate_layers
from render import render
from hybrid import compose
from gap_completion import complete_gaps,render_gap_pair


def fixture(mode='plain'):
    vertices=np.array([[-1,-.5,4],[-1,.5,4],[0,-.5,4],[0,.5,4],[1,-.5,4],[1,.5,4]],float)
    faces=np.array([[0,2,1],[1,2,3],[2,4,3],[3,4,5]])
    regions=np.full(4,4)
    if mode=='boundary':regions[2:]=3
    if mode=='hole':faces=faces[[0,3]];regions=regions[[0,3]]
    if mode=='ambiguous':
        vertices=np.vstack([vertices,[.8,.1,4.2]])
        faces=np.vstack([faces,[2,3,6]]);regions=np.r_[regions,4]
    m=mesh_data(vertices,faces,regions)
    style=dict(angle=90.,spacing=.3,length=.12,width=1.,cross_enabled=True,cross_angle=60.,cross_spacing=.3)
    p,_=generate_layers(m,4,style)
    c=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
    return m,p,dict(styles={'4':style}),c


class GapTests(unittest.TestCase):
    def check_geometry(self,m,old,filled,gaps):
        for k in old:np.testing.assert_array_equal(filled[k][:len(old['points'])],old[k])
        np.testing.assert_allclose(np.einsum('nij,njk->nik',gaps['bary'],m['tri'][gaps['face']]),gaps['points'],atol=1e-10,rtol=0)
        self.assertTrue(np.all(m['regions'][gaps['face']]==4))
        for sid in np.unique(gaps['stroke_id']):
            ii=np.flatnonzero(gaps['stroke_id']==sid)
            left=np.flatnonzero(old['stroke_id']==gaps['left_stroke_id'][ii[0]])[-1]
            right=np.flatnonzero(old['stroke_id']==gaps['right_stroke_id'][ii[0]])[0]
            np.testing.assert_allclose(gaps['points'][ii[0],0],old['points'][left,1],rtol=0,atol=1e-9)
            np.testing.assert_allclose(gaps['points'][ii[-1],1],old['points'][right,0],rtol=0,atol=1e-9)
            np.testing.assert_allclose(gaps['points'][ii[:-1],1],gaps['points'][ii[1:],0],rtol=0,atol=1e-9)
            self.assertAlmostEqual(float(np.linalg.norm(gaps['points'][ii,1]-gaps['points'][ii,0],axis=1).sum()),.035,places=8)
            for a,b in zip(gaps['face'][ii[:-1]],gaps['face'][ii[1:]]):
                shared=set(m['faces'][a])&set(m['faces'][b]);self.assertEqual(len(shared),2)
                incident=sum(shared.issubset(set(f)) for f in m['faces'][m['regions']==4]);self.assertEqual(incident,2)

    def test_internal_only_and_topological_stops(self):
        for mode in ('plain','boundary','hole','ambiguous'):
            m,p,meta,c=fixture(mode);before={k:v.copy() for k,v in p.items()}
            filled,gaps,stats=complete_gaps(m,p,meta['styles']['4'])
            self.assertGreater(len(gaps['points']),0);self.check_geometry(m,p,filled,gaps)
            for k in p:np.testing.assert_array_equal(p[k],before[k])
            if mode=='ambiguous':self.assertGreater(stats['ambiguous_nodes'],0)
            disabled,_,_=complete_gaps(m,p,meta['styles']['4'],enabled=False)
            for k in p:np.testing.assert_array_equal(disabled[k],p[k])

    def test_union_matches_legacy_zero_and_same_region_occluder(self):
        m,p,meta,c=fixture();filled,gaps,_=complete_gaps(m,p,meta['styles']['4'])
        pair,hi=render_gap_pair(m,p,gaps,meta,c)
        np.testing.assert_array_equal(pair['old'],render(m,{4:p},meta['styles'],c)['hatch'])
        np.testing.assert_array_equal(pair['filled'],render(m,{4:filled},meta['styles'],c)['hatch'])
        self.assertTrue(np.all(pair['filled']>=pair['old']))
        paper=np.ones((96,96,3),np.float32)*.95
        image,alpha=compose(paper,pair['filled'],np.zeros((96,96)),True)
        np.testing.assert_array_equal(image,paper);self.assertFalse(alpha.any())
        v=np.vstack([m['vertices'],[[-.3,-.4,3.4],[.3,-.4,3.4],[-.3,.4,3.4],[.3,.4,3.4]]])
        f=np.vstack([m['faces'],[[6,7,8],[8,7,9]]]);occluded=mesh_data(v,f,np.full(len(f),4))
        blocked,_=render_gap_pair(occluded,p,gaps,meta,c)
        self.assertEqual(float(blocked['filled'][40:56,42:54].sum()),0.)

    def test_real_asset_regeneration_and_small_render(self):
        root=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/baseline/portable_demo/examples/lego_bucket_cross')
        with np.load(root/'mesh.npz') as z:m=mesh_data(z['vertices'],z['faces'],z['face_regions'])
        with np.load(root/'region_4.npz') as z:p={k:z[k] for k in z.files}
        meta=json.loads((root/'asset.json').read_text())
        filled,gaps,_=complete_gaps(m,p,meta['styles']['4']);self.check_geometry(m,p,filled,gaps)
        self.assertGreater(len(np.unique(gaps['stroke_id'])),20)
        first=gaps['stroke_id'][0];g={k:v[gaps['stroke_id']==first] for k,v in gaps.items()}
        parent_ids=[g['left_stroke_id'][0],g['right_stroke_id'][0]]
        small={k:v[np.isin(p['stroke_id'],parent_ids)] for k,v in p.items()}
        scene=json.loads(Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_004/PROTOCOL.json').read_text())['scene']
        c=resize_camera(scene['build_cameras'][0],96)
        pair,_=render_gap_pair(m,small,g,meta,c)
        np.testing.assert_array_equal(pair['old'],render(m,{4:small},meta['styles'],c)['hatch'])


if __name__=='__main__':unittest.main(verbosity=2)
