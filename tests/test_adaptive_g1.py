import unittest,tempfile,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


class G1Tests(unittest.TestCase):
    def test_native_view_saves_every_control_layers_and_separate_soft_channels(self):
        from scripts.render_adaptive_g1 import construct_view,finalize_run,CONTROLS,CHANNELS
        asset=dict(mu=np.array([[.1,.2,2],[.1,.2,3]],'f4'),scale=np.tile([.12,.08,.02],(2,1)).astype('f4'),
                   quat=np.tile([1,0,0,0],(2,1)).astype('f4'),opacity=np.array([[.8],[.5]],'f4'),sh=np.zeros((2,16,3),'f4'))
        camera=dict(native_K=[[60.,0,17],[0,50.,13],[0,0,1]],w2c=np.eye(4).tolist(),native_height=32,native_width=40)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);csr=out/'csr.so';evidence=out/'evidence.so'
            for source,lib in [('adaptive_mass_native.cpp',csr),('adaptive_evidence_native.cpp',evidence)]:
                subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC','-fopenmp',str(ROOT/'src'/source),'-o',str(lib)],check=True)
            construct_view(out,'synthetic',1,asset,camera,csr,evidence)
            finalize_run(out,[('synthetic',1)],evidence)
            self.assertEqual(len(CONTROLS),18)
            for name in CONTROLS:
                with np.load(out/'raw'/f'synthetic_1_{name}.npz') as f:
                    for channel in CHANNELS:self.assertIn(channel+'.response',f.files)
                    self.assertIn('layers.assignment',f.files);self.assertIn('layers.overflow_mass',f.files)
                with np.load(out/'final'/f'synthetic_1_{name}.npz') as f:
                    for channel in CHANNELS:
                        for suffix in ['normalized_soft','band_95_70','band_90_60','matched_full','matched_control']:self.assertIn(channel+'.'+suffix,f.files)

    def test_fixed_k_sensitivity_cannot_stop_at_a_native_mass_target(self):
        from scripts.render_adaptive_g1 import fixed_prefix
        s=dict(means2D=np.zeros((3,2),'f4'),conic=np.array([[1,0,1,.1]]*3,'f4'),depths=np.array([1,2,3],'f4'),
               rgb=np.ones((3,3),'f4'),point_list=np.arange(3,dtype='u4'),ranges=np.array([[0,3]],'u4'),final_T=np.array([[.95]],'f4'))
        with tempfile.TemporaryDirectory() as td:
            lib=Path(td)/'csr.so';subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC','-fopenmp',str(ROOT/'src/adaptive_mass_native.cpp'),'-o',str(lib)],check=True)
            e=fixed_prefix(s,1,1,16,lib)
            np.testing.assert_array_equal(e['ids'],[0,1,2])
            np.testing.assert_array_equal(e['native_final_T'],s['final_T'])

    def test_complete_sheets_decode_without_changing_scientific_arrays(self):
        from scripts.render_adaptive_g1 import make_sheets,CONTROLS,CHANNELS
        import cv2,hashlib
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);(out/'native').mkdir();(out/'final').mkdir()
            np.savez_compressed(out/'native'/'synthetic_1.npz',stock_white=np.ones((4,6,3)))
            for control in CONTROLS:
                data={ch+'.'+key:np.zeros((4,6)) for ch in CHANNELS for key in ['normalized_soft','band_95_70','band_90_60','matched_full','matched_control']}
                np.savez_compressed(out/'final'/f'synthetic_1_{control}.npz',**data)
            before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*.npz')}
            make_sheets(out,[('synthetic',1)])
            self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*.npz')})
            figures=list((out/'figures').glob('*.png'));self.assertEqual(len(figures),13)
            for path in figures:self.assertIsNotNone(cv2.imread(str(path)))

    def test_g1_cli_requires_new_output_and_exposes_gate_input(self):
        import sys
        result=subprocess.run([sys.executable,str(ROOT/'scripts/render_adaptive_g1.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--g0',result.stdout);self.assertIn('--output',result.stdout)
