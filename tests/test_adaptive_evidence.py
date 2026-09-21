import unittest,tempfile,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def library(td):
    p=Path(td)/'evidence.so'
    subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC','-fopenmp',str(ROOT/'src/adaptive_evidence_native.cpp'),'-o',str(p)],check=True)
    return p


class EvidenceTests(unittest.TestCase):
    def test_exact_weighted_depth_transport_and_ID_overlap(self):
        from src.adaptive_evidence import pair_fields
        from src.adaptive_layers import compress_layers
        e=dict(offsets=np.array([0,2,4]),ids=np.array([1,2,2,3]),z=np.array([2.,4,3,5]),
               w=np.array([.2,.6,.4,.4]),rgb=np.zeros((4,3)),tail_alpha=np.zeros((1,2)),tail_rgb=np.zeros((1,2,3)))
        layers=compress_layers(e,np.ones((1,2))*.8)
        with tempfile.TemporaryDirectory() as td:
            lib=library(td);f=pair_fields(e,layers,lib)
            self.assertAlmostEqual(f['BC'][0,0,4],np.sqrt(.75*.5),places=6)
            self.assertAlmostEqual(f['W1'][0,0,4],1.,places=6)
            renamed=dict(e,ids=e['ids']+100)
            g=pair_fields(renamed,layers,lib)
            np.testing.assert_array_equal(f['BC'],g['BC'])
            np.testing.assert_array_equal(f['W1'],g['W1'])

    def test_matched_layer_hessian_never_averages_front_and_back(self):
        from src.adaptive_evidence import matched_hessian
        shape=(21,21);depth=np.zeros((*shape,4));mass=np.zeros_like(depth)
        depth[...,0]=2;depth[...,1]=5;mass[...,:2]=.4
        l=dict(retained_depth=depth,retained_mass=mass,local_scale=np.full(shape,.01),
               retained_index=np.arange(np.prod(shape)*4).reshape(*shape,4),layer_seedable=np.tile([True,True,False,False],np.prod(shape)))
        with tempfile.TemporaryDirectory() as td:
            lib=library(td);h=matched_hessian(l,1.5,lib)
            np.testing.assert_allclose(h[...,:3],0,atol=1e-10)
            x=np.arange(21)-10;l['retained_depth'][...,0]=2+.001*x*x
            curved=matched_hessian(l,1.5,lib)
            self.assertGreater(curved[10,10,0,0],.1)
            np.testing.assert_allclose(curved[...,1,:3],0,atol=1e-10)

    def test_ID_turnover_alone_cannot_activate_any_line_channel(self):
        from src.adaptive_evidence import build_evidence
        shape=(15,15);n=np.prod(shape)
        e=dict(offsets=np.arange(n+1),ids=np.arange(n),z=np.ones(n)*2,w=np.ones(n)*.9,
               rgb=np.zeros((n,3)),tail_alpha=np.zeros(shape),tail_rgb=np.zeros((*shape,3)))
        with tempfile.TemporaryDirectory() as td:
            lib=library(td);result=build_evidence(e,np.ones(shape)*.9,lib)
            for field in result['channels'].values():self.assertEqual(float(field['response'].max()),0)
            changed=dict(e,z=np.where(np.indices(shape)[1].ravel()<7,2.,3.))
            edge=build_evidence(changed,np.ones(shape)*.9,lib)
            self.assertGreater(edge['channels']['E_occ']['response'].max(),.5)
            self.assertEqual(edge['channels']['E_shape_ridge']['response'].max(),0)

    def test_controls_preserve_mass_and_shuffle_slots_not_global_labels(self):
        from src.adaptive_evidence import prefix_control,transform_control
        e=dict(offsets=np.array([0,3,6]),ids=np.array([1,2,3,1,2,3]),z=np.array([1.,2,3,1,2,3]),
               w=np.array([.2,.3,.4,.1,.4,.4]),rgb=np.ones((6,3)),tail_alpha=np.zeros((1,2)),tail_rgb=np.zeros((1,2,3)))
        p=prefix_control(e,np.ones((1,2))*.9,None,2)
        np.testing.assert_array_equal(p['offsets'],[0,2,4]);np.testing.assert_allclose(p['tail_alpha'],.4)
        u=transform_control(e,'uniform',7)
        np.testing.assert_allclose(u['w'],.3)
        s=transform_control(e,'shuffled_ids',7);t=transform_control(e,'shuffled_ids',7)
        np.testing.assert_array_equal(s['ids'],t['ids']);np.testing.assert_array_equal(np.sort(s['ids']),np.sort(e['ids']))
        self.assertFalse(np.array_equal(s['ids'][:3],s['ids'][3:]))
        z=transform_control(e,'shuffled_depths',1007)
        for lo,hi in zip(z['offsets'][:-1],z['offsets'][1:]):self.assertTrue(np.all(np.diff(z['z'][lo:hi])>=0))
        np.testing.assert_array_equal(np.sort(z['w']),np.sort(e['w']))

    def test_oriented_hysteresis_recovers_weak_span_and_rejects_wrong_class(self):
        from src.adaptive_evidence import hysteresis_bands
        shape=(9,15);response=np.zeros(shape);response[3:6,2:13]=.4;response[4,2:13]=.5;response[4,2]=1
        f=dict(response=response,orientation=np.zeros(shape),sigma=np.ones(shape)*2,depth=np.ones(shape)*2,layer=np.zeros(shape,'i2'))
        bc=np.ones((*shape,8));d=np.ones(shape)*.01
        with tempfile.TemporaryDirectory() as td:
            lib=library(td);b=hysteresis_bands(f,bc,d,lib,high=.8,low=.3)
            self.assertTrue(b['center'][4,12]);self.assertTrue(b['band'][3,8]);self.assertFalse(b['band'][2,8])
            f['depth'][4,7]=4;blocked=hysteresis_bands(f,bc,d,lib,high=.8,low=.3)
            self.assertFalse(blocked['band'][4,7])
            f['depth'][:]=2;f['orientation'][:,7:]=np.pi/2
            turn=hysteresis_bands(f,bc,d,lib,high=.8,low=.3)
            self.assertFalse(turn['center'][4,12])

    def test_frozen_percentiles_keep_soft_response_and_raw_band_grids(self):
        from src.adaptive_evidence import finalize_channel
        response=np.linspace(.01,1,100).reshape(1,100)
        f=dict(response=response,orientation=np.zeros_like(response),sigma=np.ones_like(response)*1.5,depth=np.ones_like(response)*2,layer=np.zeros_like(response,'i2'))
        with tempfile.TemporaryDirectory() as td:
            r=finalize_channel(f,np.ones((1,100,8)),np.ones_like(response)*.01,2.,library(td))
            np.testing.assert_allclose(r['normalized_soft'],response/2)
            self.assertAlmostEqual(r['thresholds'][0,0],np.percentile(response,95))
            self.assertTrue(np.all(r['band_95_70']<=r['band_90_60']))
            self.assertGreater(r['band_95_70'].sum(),r['anchors_95_70'].sum())

    def test_equal_distance_neighbor_layer_match_keeps_frontmost_tie(self):
        from src.adaptive_evidence import pair_fields
        from src.adaptive_layers import compress_layers
        shape=(5,5);counts=np.ones(25,'i8');counts[13]=2;off=np.r_[0,np.cumsum(counts)]
        z=np.ones(26)*2;z[off[12]]=3;z[off[13]+1]=4
        ids=np.ones(26,'i8');ids[off[13]+1]=2;weights=np.ones(26)*.5;weights[off[13]:off[14]]=.25
        e=dict(offsets=off,ids=ids,z=z,w=weights,rgb=np.zeros((26,3)),tail_alpha=np.zeros(shape),tail_rgb=np.zeros((*shape,3)))
        layers=compress_layers(e,np.ones(shape)*.8)
        with tempfile.TemporaryDirectory() as td:
            f=pair_fields(e,layers,library(td))
            self.assertAlmostEqual(f['layer_BC'][2,2,4,0],1.)

    def test_batched_scales_preserve_separate_native_hessians_bitwise(self):
        from src.adaptive_evidence import matched_hessian,matched_hessians
        shape=(19,23);y,x=np.indices(shape);depth=np.broadcast_to(np.array([2.,3,4,5]),(*shape,4)).copy();depth[...,0]+=.0007*(x-11)**2+.0003*(y-9)**2
        l=dict(retained_depth=depth,retained_mass=np.ones_like(depth)*.2,local_scale=np.full(shape,.03),
               retained_index=np.arange(np.prod(shape)*4).reshape(*shape,4),layer_seedable=np.ones(np.prod(shape)*4,bool))
        with tempfile.TemporaryDirectory() as td:
            lib=library(td);batched=matched_hessians(l,lib)
            for i,s in enumerate([1.5,2.5,4.]):np.testing.assert_array_equal(batched[i],matched_hessian(l,s,lib))
