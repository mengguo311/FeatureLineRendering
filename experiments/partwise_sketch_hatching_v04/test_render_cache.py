"""Real Chair cache behavior, independent frozen renderer and invalidation."""
import runtime
from pathlib import Path
import copy,importlib.util,tempfile,unittest
from unittest.mock import patch
import numpy as np
from unit024_run import U,ASSET
from demo import load_asset
from geometry import orbit_camera,mesh_data
import render as raster
from viewer import Editor

def equal(test,a,b):
    test.assertEqual(set(a),set(b))
    for k in a:
        if isinstance(a[k],dict):equal(test,a[k],b[k])
        elif isinstance(a[k],np.ndarray):test.assertTrue(np.array_equal(a[k],b[k]),k)
        else:test.assertEqual(a[k],b[k],k)

class RenderCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('frozen_unit023_renderer',U/'source_before/render.py')
        cls.legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.legacy)

    def test_zero_ink_display_and_returned_arrays_do_not_corrupt_cache(self):
        m,s,meta=load_asset(ASSET);style=copy.deepcopy(meta['styles']);c=orbit_camera(43,28,4.9,96)
        cache=raster.RenderCache()
        for ink,display in [(0,None),(.35,{'contour_strength':.35,'contours_visible':True}),
                            (1,{'contours_visible':False,'contour_strength':1}),(.8,None)]:
            style['4']['ink_strength']=ink
            a=raster.render(m,s,style,c,display=display,cache=cache)
            b=self.legacy.render(m,s,style,c,display=display);equal(self,a,b)
            a['proxy'][:]=0;a['region_rgb'][:]=0;a['depth'][:]=0;a['regions'][:]=0
        self.assertEqual(cache.builds,1);self.assertEqual(cache.hits,3)

    def test_content_changes_invalidate_including_in_place_arrays(self):
        m,s,meta=load_asset(ASSET);style=copy.deepcopy(meta['styles']);c=orbit_camera(43,28,4.9,96)
        cache=raster.RenderCache()
        def check():
            builds=cache.builds
            equal(self,raster.render(m,s,style,c,cache=cache),self.legacy.render(m,s,style,c))
            self.assertEqual(cache.builds,builds+1)
        check()
        c=orbit_camera(73,28,4.9,96);check()
        style['4']['width']=1.5;check()
        # These are low-level renderer dependency probes, not valid edited assets.
        s[4]['points'][0,0,0]+=.001;check()
        s[4]['visibility_mask'][0]^=np.uint64(1 << 2);check()
        m['regions'][0]=2 if m['regions'][0]!=2 else 3;check()
        vertices=m['vertices'].copy();vertices[0,0]+=.001
        m=mesh_data(vertices,m['faces'],m['regions']);check()
        # Same content in freshly loaded/copy arrays must be reusable.
        equal(self,raster.render(copy.deepcopy(m),copy.deepcopy(s),style,c,cache=cache),self.legacy.render(m,s,style,c))
        self.assertTrue(cache.last_hit)
        equal(self,raster.render(m,s,style,c,supersample=1,cache=cache),self.legacy.render(m,s,style,c,supersample=1))
        self.assertFalse(cache.last_hit)

    def test_cross_layer_toggle_and_cache_size_cap(self):
        path=U.parent/'unit_023/portable_demo/examples/lego_bucket_cross'
        m,s,meta=load_asset(path);style=copy.deepcopy(meta['styles']);c=orbit_camera(43,28,4.9,96)
        cache=raster.RenderCache()
        region=next(k for k,v in style.items() if v.get('cross_enabled'))
        for enabled in (True,False,True):
            style[region]['cross_enabled']=enabled
            equal(self,raster.render(m,s,style,c,cache=cache),self.legacy.render(m,s,style,c))
            self.assertFalse(cache.last_hit)
        tiny=raster.RenderCache(max_bytes=1)
        equal(self,raster.render(m,s,style,c,cache=tiny),self.legacy.render(m,s,style,c))
        self.assertIsNone(tiny.value);self.assertEqual(tiny.bytes,0)

    def test_real_editor_ink_reuses_coverage(self):
        with tempfile.TemporaryDirectory(dir=U,prefix='test_editor_') as tmp:
            with patch.object(raster,'ray_surface',wraps=raster.ray_surface) as cast:
                e=Editor(ASSET,Path(tmp)/'session')
                before=e.record;before_asset=e.asset
                values=dict(before['styles']['4'],**before['camera'],region=4,ink_strength=.35,
                            cross_enabled=False,cross_angle=60.,cross_spacing=.06)
                after=e.apply(values)
                self.assertEqual(cast.call_count,1,'ink-only edit repeated real surface/coverage work')
                self.assertEqual(after['styles']['5'],before['styles']['5'])
                for f in before_asset.iterdir():
                    if f.is_file() and f.name!='asset.json':self.assertEqual(f.read_bytes(),(e.asset/f.name).read_bytes())
                a=np.load(e.output/'view_0000/frame_000_arrays.npz');b=np.load(e.output/'view_0001/frame_000_arrays.npz')
                self.assertGreater(float(np.abs(a['image']-b['image']).sum()),0)
                for k in ('contour','depth','regions','layer_1','layer_2','layer_3','layer_5'):
                    self.assertTrue(np.array_equal(a[k],b[k]),k)

if __name__=='__main__':unittest.main()
