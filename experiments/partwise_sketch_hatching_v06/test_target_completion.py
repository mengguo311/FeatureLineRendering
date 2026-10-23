"""Targeted unit008 tests: visible authoring, trace relabeling, old path identity."""
import runtime
from pathlib import Path
import json
import unittest
import numpy as np
from geometry import mesh_data
from run_hybrid import read_npz
from target_completion import visible_additions, remap_regions, extend_paths, render_pair

ASSET=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/baseline/portable_demo/examples/lego_bucket_cross')

class TargetTests(unittest.TestCase):
    def test_frontmost_source_faces_only(self):
        faces=np.array([[0,1,2,-1],[0,1,2,-1],[3,3,4,4],[3,3,4,4]])
        labels=np.array([3,4,2,3,3,3])
        got=visible_additions(faces,labels,[[0,0],[1,0],[1,2],[0,2]])
        np.testing.assert_array_equal(got,[0,3])
        self.assertNotIn(5,got) # Hidden face cannot be selected.
    def test_trace_relabels_faces_not_source_ids(self):
        trace=dict(proxy_face=np.array([2,-1,0,1]),proxy_region=np.array([3,0,4,3]),
                   source_index=np.array([97,4,97,201]),weight=np.array([.1,.2,.3,.4]))
        before={k:v.copy() for k,v in trace.items()}
        np.testing.assert_array_equal(remap_regions(trace,np.array([4,3,4])),[4,0,4,3])
        np.testing.assert_array_equal(remap_regions(trace,np.array([4,3,3])),trace['proxy_region'])
        for k in trace:np.testing.assert_array_equal(trace[k],before[k])
    def test_real_empty_and_added_paths(self):
        m=read_npz(ASSET/'mesh.npz');mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
        old=read_npz(ASSET/'region_4.npz');meta=json.loads((ASSET/'asset.json').read_text())
        full,added=extend_paths(mesh,old,np.array([],int),meta['styles']['4'])
        for k in old:np.testing.assert_array_equal(full[k],old[k])
        self.assertEqual(len(added['points']),0)
        c=dict(json.loads((Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_005/PROTOCOL.json')).read_text())['scenes']['lego']['evidence_sources'][3]['camera'])
        from geometry import resize_camera
        c=resize_camera(c,64)
        pair,_=render_pair(mesh,mesh,old,added,meta,c)
        np.testing.assert_array_equal(pair['old'],pair['new'])
        ids=np.flatnonzero(mesh['regions']==3)[:200]
        full,added=extend_paths(mesh,old,ids,meta['styles']['4'])
        for k in old:np.testing.assert_array_equal(full[k][:len(old[k])],old[k])
        self.assertTrue(np.isin(added['face'],ids).all())
        self.assertFalse(np.isin(added['stroke_id'],old['stroke_id']).any())
        np.testing.assert_allclose(np.einsum('nij,njk->nik',added['bary'],mesh['tri'][added['face']]),added['points'],atol=1e-9,rtol=0)

if __name__=='__main__':unittest.main()
