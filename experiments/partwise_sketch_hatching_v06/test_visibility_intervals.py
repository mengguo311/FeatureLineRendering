import runtime
import json
import unittest
from pathlib import Path
import numpy as np
from geometry import mesh_data, resize_camera
from hybrid import compose
from render import _coverage
from visibility_intervals import compare_visibility


def fixture(block=False, gap=False):
    # Two genuinely shared-edge triangles, folded but continuously visible.
    vertices=np.array([[-1,-.6,4.4],[-1,.6,4.4],[0,-.6,4],[0,.6,4],
                       [1,-.6,4.4],[1,.6,4.4]],float)
    faces=[[0,2,1],[1,2,3],[2,4,3],[3,4,5]]
    if block:
        # Disconnected foreground surface with the SAME region label.
        vertices=np.vstack([vertices,[[-.18,-.3,3.4],[.18,-.3,3.4],[-.18,.3,3.4],[.18,.3,3.4]]])
        faces += [[6,7,8],[8,7,9]]
    mesh=mesh_data(vertices,np.array(faces),np.full(len(faces),4))
    # Intersections with y=0, split at every actual triangle edge.
    points=np.array([[[-.8,0,4.32],[-.5,0,4.2]],[[-.5,0,4.2],[0,0,4]],
                     [[0,0,4],[.5,0,4.2]],[[.5,0,4.2],[.8,0,4.32]]])
    if gap:
        points=points[[0,3]];owners=np.array([0,3]);ids=np.array([10,11])
    else: owners=np.arange(4);ids=np.full(4,10)
    paths=dict(points=points,face=owners,stroke_id=ids,layer_id=np.zeros(len(ids),np.uint8))
    camera=dict(extrinsic=np.eye(4).tolist(),width=96,height=96,fx=120.,fy=120.,cx=47.5,cy=47.5)
    styles={'4':dict(angle=35.,spacing=.06,length=.12,width=1.,cross_enabled=True,ink_strength=.8)}
    return mesh,paths,styles,camera


class VisibilityTests(unittest.TestCase):
    def test_shared_edge_and_legacy_exact(self):
        m,p,s,c=fixture();r=compare_visibility(m,p,s,c)
        old=_coverage(m,{4:p},s,c,2)['coverage'][4][0]
        np.testing.assert_array_equal(r['coverage']['legacy'][0],old)
        q=r['samples'];self.assertTrue(np.all(q['status']==0))
        self.assertGreater(np.mean(q['interval_alpha']>.05),.98)
        self.assertEqual(len(np.unique(q['stroke_id'])),1)

    def test_same_region_foreground_and_planned_gap(self):
        m,p,s,c=fixture(block=True);r=compare_visibility(m,p,s,c)
        q=r['samples'];hidden=np.abs(q['uv'][:,0]-47.5)<4
        self.assertTrue(np.all(q['status'][hidden]==3))
        self.assertTrue(np.all(q['interval_alpha'][hidden]==0))
        self.assertEqual(float(r['ink']['interval'][46:50,44:51].sum()),0.)
        m,p,s,c=fixture(gap=True);r=compare_visibility(m,p,s,c)
        self.assertEqual(float(r['ink']['interval'][:,40:56].sum()),0.)
        paper=np.ones((96,96,3),np.float32)*.95
        output,alpha=compose(paper,r['ink']['interval'],np.zeros((96,96)),True)
        np.testing.assert_array_equal(output,paper);self.assertEqual(float(alpha.sum()),0.)

    def test_real_shared_edge_paths_and_identity(self):
        old=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_001')
        scene=json.loads((old/'PROTOCOL.json').read_text())['scenes']['lego'];a=Path(scene['asset'])
        with np.load(a/'mesh.npz') as z:m=mesh_data(z['vertices'],z['faces'],z['face_regions'])
        with np.load(a/'region_4.npz') as z:p={k:z[k] for k in z.files}
        ids=[]
        for sid in np.unique(p['stroke_id']):
            ix=np.flatnonzero(p['stroke_id']==sid)
            if len(ix)>=3 and np.max(np.abs(p['points'][ix[:-1],1]-p['points'][ix[1:],0]))<1e-8:
                ids.extend(ix.tolist())
            if len(ids)>=40:break
        self.assertGreater(len(ids),10)
        small={k:v[ids].copy() for k,v in p.items()};before={k:v.copy() for k,v in small.items()}
        meta=json.loads((a/'asset.json').read_text());c=resize_camera(scene['build_cameras'][0],96)
        r=compare_visibility(m,small,meta['styles'],c)
        oldcov=_coverage(m,{4:small},meta['styles'],c,2)['coverage'][4]
        for layer in oldcov:np.testing.assert_array_equal(r['coverage']['legacy'][layer],oldcov[layer])
        for k in small:np.testing.assert_array_equal(small[k],before[k])
        np.testing.assert_allclose(np.einsum('nij,njk->nik',small['bary'],m['tri'][small['face']]),small['points'],atol=1e-9,rtol=0)


if __name__=='__main__':unittest.main(verbosity=2)
