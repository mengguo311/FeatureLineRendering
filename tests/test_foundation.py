"""Prerequisite-first foundation experiment: deterministic synthetic fixtures."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np

class FoundationTests(unittest.TestCase):
    def test_01_freeze_json_is_canonical_and_exclusive(self):
        from src.foundation import freeze_json
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'
            digest=freeze_json(p,{'z':[1,2],'a':0.5})
            self.assertEqual(p.read_bytes(),b'{"a":0.5,"z":[1,2]}\n')
            self.assertEqual(digest,hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(Path(str(p)+'.sha256').read_text().strip(),digest)
            with self.assertRaises(FileExistsError): freeze_json(p,{'a':1})
            with self.assertRaises(ValueError): freeze_json(Path(d)/'bad.json',{'x':float('nan')})

    def test_02_verified_read_detects_tampering(self):
        from src.foundation import freeze_json, verified_json
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'; h=freeze_json(p,{'F':[1,14],'C':[7,21]})
            self.assertEqual(verified_json(p,h),{'F':[1,14],'C':[7,21]})
            p.write_text('{"F":[7,21],"C":[1,14]}\n')
            with self.assertRaisesRegex(ValueError,'hash'): verified_json(p,h)

    def test_03_landlock_denies_native_forbidden_reads_and_writes(self):
        from src.foundation import restrict_filesystem
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            for name in ['F','C','DEV','TEST','mesh']: (d/name).write_text(name)
            (d/'output').mkdir()
            code='''
import ctypes,os,sys
from src.foundation import restrict_filesystem
base=sys.argv[1]; lib=ctypes.CDLL(None,use_errno=True)
restrict_filesystem([base+'/F'],[base+'/output'])
fd=lib.open((base+'/F').encode(),os.O_RDONLY); assert fd>=0; lib.close(fd)
for name in ['C','DEV','TEST','mesh']:
    assert lib.open((base+'/'+name).encode(),os.O_RDONLY)==-1
    assert ctypes.get_errno()==13
assert lib.open((base+'/F').encode(),os.O_WRONLY)==-1
fd=lib.open((base+'/output/log').encode(),os.O_CREAT|os.O_WRONLY,0o600)
assert fd>=0; lib.close(fd)
'''
            p=subprocess.run([os.sys.executable,'-c',code,str(d)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)

    def test_04_full_K_projection_and_analytic_jacobian(self):
        from src.foundation import project_jacobian
        K=np.array([[80.,3,19],[0,60,11],[0,0,1]])
        w=np.eye(4); w[:3,3]=[.1,-.2,.3]
        p=np.array([[.2,.4,2.],[.3,-.5,3.]])
        uv,z,J=project_jacobian(p,K,w)
        q=p+w[:3,3]; h=q@K.T
        np.testing.assert_allclose(uv,h[:,:2]/h[:,2:])
        for axis in range(3):
            e=np.eye(3)[axis]*1e-6
            diff=(project_jacobian(p+e,K,w)[0]-project_jacobian(p-e,K,w)[0])/2e-6
            np.testing.assert_allclose(J[:,:,axis],diff,rtol=1e-7,atol=1e-7)
        self.assertTrue(np.isnan(project_jacobian(np.array([[0,0,-1.]]),K,np.eye(4))[0]).all())

    def test_05_native_anisotropic_full_K_stock_buffers(self):
        from src.foundation import native_render
        asset={'mu':np.array([[.1,.2,2]],np.float32),'scale':np.array([[.12,.03,.02]],np.float32),
               'quat':np.array([[1,0,0,0]],np.float32),'opacity':np.array([[.8]],np.float32),
               'sh':np.ones((1,16,3),np.float32)*0}
        K=np.array([[100.,0,21],[0,70.,13],[0,0,1]])
        state=native_render(asset,K,np.eye(4),40,48,1.)
        np.testing.assert_allclose(state['means2D'][0],[26,20],atol=1e-5)
        # Official projected covariance includes +0.3 low-pass variance.
        np.testing.assert_allclose(state['conic'][0,[0,2]],[1/(36+.0025+.3),1/(1.1025+.0049+.3)],rtol=1e-4)
        self.assertGreater(state['stock_rgb'].std(),.01)
        self.assertEqual(state['ranges'].shape,(9,2))
        np.testing.assert_allclose(state['stock_rgb'],state['wrapper_rgb'],atol=1e-7)
        self.assertEqual(float(state['depths'][0]),2.)

    def test_06_native_replay_weights_layers_cutoff_and_termination(self):
        from src.foundation import replay_native
        root=Path(__file__).resolve().parents[1]
        subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC','-fopenmp',str(root/'src/foundation_composite.cpp'),'-o',str(root/'out/point_feature_foundation/setup/composite.so')],check=True)
        state={'means2D':np.zeros((3,2),np.float32),'conic':np.array([[1,0,1,.5],[1,0,1,.5],[1,0,1,.001]],np.float32),
               'rgb':np.eye(3,dtype=np.float32),'depths':np.array([2,5,8],np.float32),
               'point_list':np.array([0,1,2],np.uint32),'ranges':np.array([[0,3]],np.uint32)}
        out=replay_native(state,1,1,np.array([1,0,0],np.uint8),np.array([0,1,0],np.uint8),0.)
        np.testing.assert_allclose(out['rgb'][0,0],[.5,.25,0])
        np.testing.assert_allclose(out['alpha'],.75)
        np.testing.assert_allclose(out['selected'],.5)
        np.testing.assert_allclose(out['outside'],.25)
        np.testing.assert_allclose(out['depth_quantiles'][0,0],[2,2,5])
        state['conic'][:,3]=1.
        out=replay_native(state,1,1,np.ones(3,np.uint8),np.zeros(3,np.uint8),1.)
        np.testing.assert_allclose(out['rgb'][0,0],[1,.01,.01],atol=2e-7)
        np.testing.assert_allclose(out['alpha'],.99,atol=1e-7)
        np.testing.assert_allclose(out['depth_quantiles'][0,0],[2,2,2])

    def test_07_calibration_detects_rgb_and_alpha_errors(self):
        from src.foundation import calibration_metrics
        white=np.full((3,3,3),.7,np.float32); black=np.full_like(white,.3)
        state={'stock_rgb':white,'wrapper_rgb':white.copy(),'final_T':np.full((3,3),.4,np.float32)}
        replay={'rgb':white.copy(),'alpha':np.full((3,3),.6,np.float32)}
        good=calibration_metrics(state,black,replay)
        self.assertTrue(good['passed'])
        replay['rgb'][1,1,0]+=.005
        self.assertFalse(calibration_metrics(state,black,replay)['passed'])
        replay['rgb']=white.copy(); replay['alpha'][0,0]+=.005
        self.assertFalse(calibration_metrics(state,black,replay)['passed'])

    def test_08_load_full_SH_asset_without_filtering(self):
        from src.foundation import load_asset
        from plyfile import PlyData,PlyElement
        names=['x','y','z','opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(45)]
        rows=np.zeros(2,dtype=[(k,'f4') for k in names]); rows['z']=[2,3]; rows['rot_0']=1
        rows['opacity']=[-10,0]
        for i in range(45): rows[f'f_rest_{i}']=i
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'asset.ply'; PlyData([PlyElement.describe(rows,'vertex')]).write(p)
            a=load_asset(p)
        self.assertEqual(len(a['mu']),2) # low opacity must survive
        np.testing.assert_allclose(a['scale'],1.)
        self.assertLess(a['opacity'][0,0],.001)
        np.testing.assert_array_equal(a['sh'][0,1,:],[0,15,30])
        np.testing.assert_array_equal(a['sh'][0,15,:],[14,29,44])

    def test_09_clone_split_deterministic_parent_mass_and_moments(self):
        from src.foundation import perturb_asset
        n=6; a={'mu':np.arange(18,dtype=np.float32).reshape(6,3),'scale':np.tile([.1,.3,.2],(n,1)).astype('f4'),
            'quat':np.tile([1.,0,0,0],(n,1)).astype('f4'),'opacity':np.full((n,1),.64,np.float32),
            'sh':np.arange(n*48,dtype=np.float32).reshape(n,16,3)}
        frozen={k:v.copy() for k,v in a.items()}
        for mode in ['clone','split']:
            child,parent,selected=perturb_asset(a,mode)
            self.assertEqual(len(child['mu']),9); self.assertEqual(selected.sum(),3)
            for key in a: np.testing.assert_array_equal(a[key],frozen[key])
            again,par,sel=perturb_asset(a,mode)
            for key in a: np.testing.assert_array_equal(child[key],again[key])
            for i in np.flatnonzero(selected):
                idx=np.flatnonzero(parent==i); self.assertEqual(len(idx),2)
                np.testing.assert_allclose(child['mu'][idx].mean(0),a['mu'][i],atol=1e-6)
                np.testing.assert_allclose(1-np.prod(1-child['opacity'][idx]),.64,atol=1e-6)
                np.testing.assert_array_equal(child['sh'][idx],np.tile(a['sh'][i],(2,1,1)))
                offsets=child['mu'][idx]-a['mu'][i]
                np.testing.assert_allclose(np.diag(child['scale'][idx[0]]**2)+offsets.T@offsets/2,np.diag(a['scale'][i]**2),atol=2e-7)
                self.assertAlmostEqual(float(np.linalg.norm(offsets[0])),0 if mode=='clone' else .06,places=5)
        with self.assertRaises(ValueError): perturb_asset(a,'tuned')

    def test_10_qualification_uses_frozen_roi_and_all_thresholds(self):
        from src.foundation import qualification_metrics
        base=np.full((32,32,3),.5,np.float32); roi=np.zeros((32,32),bool); roi[8:24,8:24]=True
        same=qualification_metrics(base,base.copy(),roi)
        self.assertTrue(same['passed']); self.assertEqual(same['ssim'],1.)
        changed=base.copy(); changed[roi]+=.04
        fail=qualification_metrics(base,changed,roi)
        self.assertFalse(fail['passed']); self.assertLess(fail['psnr_db'],40)
        self.assertGreater(fail['p99_max_channel_abs'],8/255)
        changed=base.copy(); changed[0:2]=0
        self.assertEqual(qualification_metrics(base,changed,roi)['psnr_db'],None)
        self.assertFalse(qualification_metrics(base,base,np.zeros_like(roi))['valid'])

    def test_11_prerequisite_gate_never_calls_invalid_a_scientific_failure(self):
        from src.foundation import prerequisite_verdict
        q={'clone':[{'passed':False}],'split':[{'passed':False}]}
        r=prerequisite_verdict([{'passed':True}],q,[.5],[0.],0,True)
        self.assertEqual(r['verdict'],'UNDETERMINED'); self.assertEqual(r['gates']['G0']['state'],'INVALID')
        self.assertEqual(r['gates']['G5']['state'],'UNCERTIFIED')
        r=prerequisite_verdict([{'passed':False}],q,[.5],[0.],0,True)
        self.assertEqual(r['verdict'],'ENGINEERING_NOT_READY')
        q['clone']=[{'passed':True}]
        r=prerequisite_verdict([{'passed':True}],q,[.19],[0.],0,True)
        self.assertEqual(r['verdict'],'UNDETERMINED')
        r=prerequisite_verdict([{'passed':True}],q,[.5],[0.],0,True)
        self.assertEqual(r['verdict'],'UNDETERMINED'); self.assertTrue(r['may_run_local_probe'])
        self.assertNotEqual(r['gates']['G0']['state'],'PASS') # search/view gates not yet measured
        self.assertFalse(prerequisite_verdict([{'passed':True}],q,[.5],[.011],0,True)['may_run_local_probe'])
        self.assertFalse(prerequisite_verdict([{'passed':True}],q,[.5],[0.],1,True)['may_run_local_probe'])
        self.assertFalse(prerequisite_verdict([{'passed':True}],q,[.5],[0.],0,False)['may_run_local_probe'])

    def test_12_native_open_audit_separates_denials_and_violations(self):
        from src.foundation import audit_opens
        trace='''100 openat(AT_FDCWD, "/allowed/F.png", O_RDONLY) = 3</allowed/F.png>
100 openat(AT_FDCWD, "/hidden/DEV.png", O_RDONLY) = -1 EACCES (Permission denied)
100 openat(AT_FDCWD, "/hidden/mesh.ply", O_RDONLY) = 4</hidden/mesh.ply>
100 openat(AT_FDCWD, "/run/log.json", O_WRONLY|O_CREAT, 0666) = 5</run/log.json>
100 openat(AT_FDCWD, "/lib/libc.so", O_RDONLY|O_CLOEXEC) = 6</lib/libc.so>
'''
        a=audit_opens(trace,['/allowed/F.png'],['/lib'],'/run')
        self.assertEqual(a['forbidden_successes'],['/hidden/mesh.ply'])
        self.assertEqual(a['denied'],['/hidden/DEV.png'])
        self.assertEqual(a['approved_data_reads'],['/allowed/F.png'])
        self.assertEqual(a['unparsed_open_lines'],[])

    def test_13_deterministic_png_contact_sheet(self):
        from src.foundation import save_sheet
        import cv2
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); panels=[('dark',np.zeros((20,30,3))),('light',np.ones((20,30,3)))]
            h1=save_sheet(d/'a.png',panels); h2=save_sheet(d/'b.png',panels)
            self.assertEqual(h1,h2)
            im=cv2.imread(str(d/'a.png')); self.assertEqual(im.shape,(48,60,3))
            self.assertTrue((im[28:,:30]==0).all()); self.assertTrue((im[28:,30:]==255).all())
            with self.assertRaises(FileExistsError):save_sheet(d/'a.png',panels)
