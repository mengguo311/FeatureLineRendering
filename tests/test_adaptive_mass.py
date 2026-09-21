"""Behavior slices for the isolated adaptive native CSR probe."""
import subprocess
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def fixture():
    return dict(means2D=np.array([[0,0]]*4,'f4'),
                conic=np.array([[1,0,1,.5],[1,0,1,.25],[1,0,1,.1],[1,0,1,.001]],'f4'),
                depths=np.array([2,2,1,4],'f4'),rgb=np.eye(4,3,dtype='f4'),
                point_list=np.array([2,1,0,3],'u4'),ranges=np.array([[0,4]],'u4'),
                final_T=np.array([[.3375,1]],'f4'))

class AdaptiveTests(unittest.TestCase):
    def test_csr_shortest_native_mass_prefix_ties_and_residual(self):
        from src.adaptive_mass import native_csr
        with tempfile.TemporaryDirectory() as td:
            lib=Path(td)/'csr.so'
            subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC','-fopenmp',str(ROOT/'src/adaptive_mass_native.cpp'),'-o',str(lib)],check=True)
            s=fixture()
            e=native_csr(s,1,2,.45,128,lib)
            np.testing.assert_array_equal(e['offsets'],[0,2,2])
            np.testing.assert_array_equal(e['ids'],[2,1])
            np.testing.assert_array_equal(e['stream_position'],[0,1])
            np.testing.assert_allclose(e['T'],[1,.9])
            np.testing.assert_allclose(e['w'],[.1,.225])
            np.testing.assert_allclose(e['tail_alpha'][0,0],.3375)
            np.testing.assert_allclose(e['tail_rgb'][0,0],[.3375,0,0])
            np.testing.assert_allclose(e['final_T'][0,0],.3375)
            high=native_csr(s,1,2,.90,128,lib)
            np.testing.assert_array_equal(high['ids'],[2,1,0])
            np.testing.assert_array_equal(high['z'],[1,2,2])
            cap=native_csr(s,1,2,.90,2,lib)
            np.testing.assert_array_equal(cap['ids'],[2,1])
            self.assertEqual(cap['count'][0,0],3)
            self.assertEqual(high['rgb'].shape,(3,3))

    def test_reject_bad_target_and_native_transmittance_before_ffi(self):
        from src.adaptive_mass import native_csr
        for tau in [0,1.1,np.nan]:
            with self.assertRaises(ValueError):native_csr(fixture(),1,2,tau,32,'/no/library')
        for value in [np.zeros(2),np.array([[0,np.nan]]),np.array([[0,1.1]])]:
            with self.assertRaises(ValueError):native_csr(dict(fixture(),final_T=value),1,2,.9,32,'/no/library')

    def test_csr_metrics_gate_and_semantics_detect_corruption(self):
        from src.adaptive_mass import csr_metrics
        e=dict(offsets=np.array([0,2,2]),ids=np.array([1,0]),stream_position=np.array([0,1]),
               z=np.array([2,2]),alpha=np.array([.5,.5]),T=np.array([1,.5]),w=np.array([.5,.25]),
               rgb=np.ones((2,3))*.2,tail_rgb=np.zeros((1,2,3)),tail_alpha=np.zeros((1,2)),
               final_T=np.array([[.25,1]]),native_final_T=np.array([[.25,1]]),count=np.array([[2,0]]))
        s=dict(depths=np.array([2,2]),point_list=np.array([1,0]),ranges=np.array([[0,2]]),
               stock_rgb=np.array([[[.4]*3,[1]*3]]),wrapper_rgb=np.array([[[.4]*3,[1]*3]]))
        black=np.array([[[.15]*3,[0]*3]])
        m,d=csr_metrics(e,s,black,.9,32)
        self.assertTrue(m['passed'],m)
        self.assertEqual(m['coverage']['mass_capture'],1)
        self.assertEqual(m['coverage']['K_roi']['p99'],2)
        self.assertEqual(m['memory']['stored_events'],2)
        np.testing.assert_allclose(d['A'],[[.75,0]])
        np.testing.assert_allclose(d['z_50'],[[2,0]])
        for key,index,value in [('ids',1,1),('w',0,.4),('T',1,.7),('stream_position',1,0)]:
            bad={k:v.copy() for k,v in e.items()};bad[key][index]=value
            self.assertFalse(csr_metrics(bad,s,black,.9,32)[0]['passed'],key)
        self.assertFalse(csr_metrics(e,s,black,.6,32)[0]['checks']['shortest_prefix'])

    def test_gpu_calibration_full_K_ties_and_native_prefix(self):
        from scripts.render_adaptive_mass_probe import calibrate
        asset=dict(mu=np.array([[.1,.2,2],[.1,.2,2],[.1,.2,3],[.1,.2,4]],'f4'),
                   scale=np.tile([.12,.03,.02],(4,1)).astype('f4'),quat=np.tile([1,0,0,0],(4,1)).astype('f4'),
                   opacity=np.array([[.8],[.5],[.3],[.001]],'f4'),sh=np.zeros((4,16,3),'f4'))
        camera=dict(native_K=[[100.,0,21],[0,70.,13],[0,0,1]],w2c=np.eye(4).tolist(),native_height=40,native_width=48)
        with tempfile.TemporaryDirectory() as td:
            lib=Path(td)/'csr.so'
            subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC','-fopenmp',str(ROOT/'src/adaptive_mass_native.cpp'),'-o',str(lib)],check=True)
            e,s,b,m,d=calibrate(asset,camera,.9,32,lib)
            self.assertTrue(m['passed'],m)
            np.testing.assert_allclose(s['means2D'][0],[26,20],atol=1e-4)
            p=20*48+26;lo,hi=e['offsets'][p:p+2]
            np.testing.assert_array_equal(e['ids'][lo:hi],[0,1])
            self.assertFalse(np.any(e['ids']==3))
            self.assertTrue(m['checks']['existing_native_prefix'])

    def test_smallest_common_cap_and_fail_closed_gate(self):
        from scripts.render_adaptive_mass_probe import gate_summary
        rows={s:{f'{t}_{k}':dict(passed=(k>=64),checks={'coverage':k>=64}) for t in ['90','95'] for k in [32,64,128]} for s in ['lego','chair','drums','ficus']}
        g=gate_summary(rows);self.assertEqual(g['chosen_kmax'],64);self.assertEqual(g['G0'],'PASS')
        rows['ficus']['90_64']['passed']=False
        self.assertEqual(gate_summary(rows)['chosen_kmax'],128)
        rows['ficus']['90_128']['passed']=False
        g=gate_summary(rows);self.assertEqual(g['verdict'],'ENGINEERING_NOT_READY')
        self.assertEqual(g['G1'],'NOT_RUN');self.assertEqual(g['G2'],'NOT_RUN')
        self.assertIsNone(g['chosen_kmax'])
        self.assertEqual(gate_summary({})['G0'],'INVALID')

    def test_complete_artifacts_retain_csr_and_decode_deterministically(self):
        from scripts.render_adaptive_mass_probe import save_config,save_sheets
        import cv2,hashlib,json
        shape=(4,6);e=dict(offsets=np.arange(25),ids=np.zeros(24,'i8'),w=np.full(24,.8),rgb=np.zeros((24,3)))
        d={k:np.ones(shape)*.8 for k in ['A','z_front','z_mean','z_50','z_var','H_id','missing','K','reached']}
        s=dict(stock_rgb=np.ones((*shape,3)),final_T=np.ones(shape)*.2,depths=np.array([2]),point_list=np.array([0]),ranges=np.array([[0,1]]))
        camera=dict(native_K=np.eye(3).tolist(),w2c=np.eye(4).tolist())
        with tempfile.TemporaryDirectory() as td:
            for name in ['a','b']:
                out=Path(td)/name;out.mkdir();panels=[]
                for t in [90,95]:
                    for k in [32,64,128]:panels.append(save_config(out,'fixture',t,k,e,s,np.zeros((*shape,3)),camera,{'passed':True},d))
                save_sheets(out,'fixture',panels,s,d,e)
                with np.load(out/'fixture_90_32.npz') as f:
                    self.assertEqual(f['ids'].ndim,1)
                    for key in ['offsets','native_alpha','missing','stock_white','stock_black','camera_K','w2c','truncated_rgb']:self.assertIn(key,f.files)
                for p in out.glob('*.png'):
                    im=cv2.imread(str(p));self.assertIsNotNone(im);self.assertGreaterEqual(im.shape[1],3200)
            for p in (Path(td)/'a').iterdir():self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),hashlib.sha256((Path(td)/'b'/p.name).read_bytes()).hexdigest())

    def test_cli_requires_explicit_fresh_output(self):
        import sys
        script=ROOT/'scripts/render_adaptive_mass_probe.py'
        result=subprocess.run([sys.executable,str(script),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--output',result.stdout)
        result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
