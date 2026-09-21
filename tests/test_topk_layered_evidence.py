"""Exact native-state prefix calibration; no scene inputs in unit fixtures."""
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

class NativePrefixTests(unittest.TestCase):
    def test_first_contributors_original_ids_weights_and_tail(self):
        from src.topk_layered_evidence import native_prefix
        with tempfile.TemporaryDirectory() as td:
            lib=Path(td)/'prefix.so'
            subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC','-fopenmp',str(ROOT/'src/topk_native.cpp'),'-o',str(lib)],check=True)
            state=dict(means2D=np.zeros((4,2),'f4'),conic=np.array([[1,0,1,.5],[1,0,1,.25],[1,0,1,.1],[1,0,1,.001]],'f4'),depths=np.array([3,2,1,4],'f4'),rgb=np.array([[1,0,0],[0,1,0],[0,0,1],[1,1,1]],'f4'),point_list=np.array([2,1,0,3],'u4'),ranges=np.array([[0,4]],'u4'))
            result=native_prefix(state,1,1,2,lib)
            np.testing.assert_array_equal(result['ids'][0,0],[2,1])
            np.testing.assert_allclose(result['z'][0,0],[1,2])
            np.testing.assert_allclose(result['alpha'][0,0],[.1,.25])
            np.testing.assert_allclose(result['T'][0,0],[1,.9])
            np.testing.assert_allclose(result['w'][0,0],[.1,.225])
            np.testing.assert_allclose(result['tail_rgb'][0,0],[.3375,0,0])
            np.testing.assert_allclose(result['tail_alpha'],.3375)
            np.testing.assert_allclose(result['final_T'],.3375)
            self.assertEqual(result['count'][0,0],3)

    def test_reject_invalid_native_buffers_before_ffi(self):
        from src.topk_layered_evidence import validate_native_state
        s=dict(means2D=np.zeros((2,2)),conic=np.ones((2,4)),depths=np.ones(2),rgb=np.ones((2,3)),point_list=np.array([0,1]),ranges=np.array([[0,2]]))
        validate_native_state(s,1,1,8)
        for key,value in [('point_list',np.array([0,2])),('point_list',np.array([-1,1])),('ranges',np.array([[0,3]])),('means2D',np.zeros((2,3))),('depths',np.array([1,np.nan]))]:
            with self.subTest(key=key),self.assertRaises(ValueError):validate_native_state(dict(s,**{key:value}),1,1,8)
        for h,w,k in [(0,1,8),(1,0,8),(1,1,0),(1,1,1.5)]:
            with self.assertRaises(ValueError):validate_native_state(s,h,w,k)

    def test_g0_validation_replay_semantics_and_frozen_tail_gate(self):
        from src.topk_layered_evidence import prefix_calibration
        ids=np.full((1,1,16),-1,'i8');ids[0,0,:2]=[0,1]
        z=np.zeros((1,1,16),'f4');z[0,0,:2]=[2,3]
        a=np.zeros_like(z);a[0,0,:2]=.5
        T=np.zeros_like(z);T[0,0,:2]=[1,.5]
        w=T*a;rgb=np.ones((1,1,16,3),'f4')*.2;rgb[:,:,2:]=0
        e=dict(ids=ids,z=z,alpha=a,T=T,w=w,rgb=rgb,tail_rgb=np.zeros((1,1,3),'f4'),tail_alpha=np.zeros((1,1),'f4'),final_T=np.full((1,1),.25,'f4'),count=np.full((1,1),2))
        state=dict(stock_rgb=np.full((1,1,3),.4,'f4'),wrapper_rgb=np.full((1,1,3),.4,'f4'),final_T=e['final_T'],depths=np.array([2,3],'f4'))
        black=np.full((1,1,3),.15,'f4')
        good=prefix_calibration(e,state,black)
        self.assertTrue(good['passed'],good)
        for key,index,value in [('ids',(0,0,1),0),('z',(0,0,1),1),('w',(0,0,0),.3),('T',(0,0,1),.7),('alpha',(0,0,3),.2)]:
            bad={k:v.copy() for k,v in e.items()};bad[key][index]=value
            self.assertFalse(prefix_calibration(bad,state,black)['passed'],key)
        tail={k:v.copy() for k,v in e.items()};tail['w'][:]*=.5
        tail['alpha'][0,0,:2]=[.25,1/6];tail['T'][0,0,:2]=[1,.75]
        tail['tail_alpha'][:]=.375;tail['tail_rgb'][:]=.075
        result=prefix_calibration(tail,state,black)
        self.assertFalse(result['checks']['coverage_k8']);self.assertFalse(result['passed'])
        empty={k:np.zeros_like(v) for k,v in e.items()};empty['ids'][:]=-1;empty['final_T'][:]=1
        empty_state=dict(state,stock_rgb=np.ones((1,1,3)),wrapper_rgb=np.ones((1,1,3)),final_T=np.ones((1,1)))
        self.assertFalse(prefix_calibration(empty,empty_state,np.zeros((1,1,3)))['passed'])

    def test_calibration_diagnostics_keep_absolute_mass_and_empty_support(self):
        from src.topk_layered_evidence import prefix_diagnostics
        e=dict(w=np.array([[[.25,.25],[0,0]]]),z=np.array([[[2.,4],[0,0]]]),ids=np.array([[[4,7],[-1,-1]]]))
        d=prefix_diagnostics(e,2)
        np.testing.assert_allclose(d['A'],[[.5,0]])
        np.testing.assert_allclose(d['z_mean'],[[3,0]])
        np.testing.assert_allclose(d['z_front'],[[2,0]])
        np.testing.assert_allclose(d['z_50'],[[2,0]])
        np.testing.assert_allclose(d['z_var'],[[1,0]])
        np.testing.assert_allclose(d['H_id'],[[np.log(2),0]])
        np.testing.assert_array_equal(d['valid'],[[True,False]])

    def test_write_complete_g0_artifacts_deterministically(self):
        from scripts.render_topk_layered_probe import save_calibration
        import cv2,json,hashlib
        shape=(4,6);ids=np.full((*shape,16),-1,'i8');ids[...,0]=0
        z=np.zeros_like(ids,dtype='f4');z[...,0]=2
        a=np.zeros_like(z);a[...,0]=.8;T=np.zeros_like(z);T[...,0]=1
        e=dict(ids=ids,z=z,alpha=a,T=T,w=a,rgb=np.zeros((*shape,16,3),'f4'),tail_rgb=np.zeros((*shape,3),'f4'),tail_alpha=np.zeros(shape,'f4'),final_T=np.full(shape,.2,'f4'),count=np.ones(shape,'i8'))
        state=dict(stock_rgb=np.full((*shape,3),.2,'f4'),final_T=e['final_T'])
        camera=dict(native_K=np.eye(3).tolist(),w2c=np.eye(4).tolist())
        with tempfile.TemporaryDirectory() as td:
            for name in ['a','b']:
                out=Path(td)/name;out.mkdir();save_calibration(out,'synthetic',e,state,np.zeros((*shape,3)),camera,{'passed':True})
                self.assertIsNotNone(cv2.imread(str(out/'synthetic_g0.png')))
                with np.load(out/'synthetic_g0.npz') as f:
                    for key in ['ids','alpha','T','w','rgb','stock_white','stock_black','native_alpha','A4','A8','A16','missing8','z_mean','z_50','z_front','z_var','H_id','K','w2c']:self.assertIn(key,f.files)
                    np.testing.assert_allclose(f['A8'],.8)
                self.assertTrue(json.loads((out/'synthetic_g0.json').read_text())['passed'])
            for p in (Path(td)/'a').iterdir():
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),hashlib.sha256((Path(td)/'b'/p.name).read_bytes()).hexdigest())

    def test_native_gpu_full_intrinsics_ties_cutoff_and_existing_prefix(self):
        from scripts.render_topk_layered_probe import calibrate
        asset=dict(mu=np.array([[.1,.2,2],[.1,.2,2],[.1,.2,3],[.1,.2,4]],'f4'),scale=np.tile([.12,.03,.02],(4,1)).astype('f4'),quat=np.tile([1,0,0,0],(4,1)).astype('f4'),opacity=np.array([[.8],[.5],[.3],[.001]],'f4'),sh=np.zeros((4,16,3),'f4'))
        camera=dict(native_K=[[100.,0,21],[0,70.,13],[0,0,1]],w2c=np.eye(4).tolist(),native_height=40,native_width=48)
        with tempfile.TemporaryDirectory() as td:
            lib=Path(td)/'prefix.so';subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC','-fopenmp',str(ROOT/'src/topk_native.cpp'),'-o',str(lib)],check=True)
            e,state,black,metrics=calibrate(asset,camera,lib)
            self.assertTrue(metrics['passed'],metrics)
            np.testing.assert_allclose(state['means2D'][0],[26,20],atol=1e-4)
            np.testing.assert_array_equal(e['ids'][20,26,:2],[0,1])
            self.assertFalse(np.any(e['ids']==3))
            self.assertTrue(metrics['checks']['existing_native_prefix'])
            self.assertTrue(metrics['checks']['full_intrinsics'])

    def test_gate_summary_stops_on_incomplete_or_failed_g0(self):
        from scripts.render_topk_layered_probe import gate_summary
        scenes=['lego','chair','drums','ficus']
        rows={s:dict(passed=True,failed=[]) for s in scenes}
        self.assertEqual(gate_summary(rows)['G0'],'PASS')
        rows['ficus']=dict(passed=False,failed=['coverage_k8'])
        result=gate_summary(rows)
        self.assertEqual(result['verdict'],'ENGINEERING_NOT_READY')
        self.assertEqual(result['G1'],'NOT_RUN');self.assertEqual(result['G2'],'NOT_RUN');self.assertEqual(result['G3'],'NOT_RUN')
        self.assertFalse(result['scientific_failure'])
        self.assertEqual(gate_summary({})['G0'],'INVALID')

    def test_frozen_protocol_and_inputs_fail_closed_on_tampering(self):
        from scripts.render_topk_layered_probe import frozen_inputs
        import hashlib,json
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);data=b'{"scenes": {}}\n';(p/'INPUTS.json').write_bytes(data)
            protocol='INPUTS.json SHA256: `'+hashlib.sha256(data).hexdigest()+'`\n'
            (p/'PROTOCOL.md').write_text(protocol);(p/'PROTOCOL.sha256').write_text(hashlib.sha256(protocol.encode()).hexdigest()+'\n')
            self.assertEqual(frozen_inputs(p),{'scenes':{}})
            (p/'INPUTS.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'input'):frozen_inputs(p)
            (p/'PROTOCOL.md').write_text(protocol+'changed')
            with self.assertRaisesRegex(ValueError,'protocol'):frozen_inputs(p)

    def test_cli_requires_explicit_new_output_directory(self):
        import sys
        r=subprocess.run([sys.executable,str(ROOT/'scripts/render_topk_layered_probe.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--output',r.stdout)
        r=subprocess.run([sys.executable,str(ROOT/'scripts/render_topk_layered_probe.py')],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0)
