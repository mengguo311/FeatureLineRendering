"""Synthetic CPU wrapper checks; no scene renders or dataset image pixels."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
import run_transport as r

spec=importlib.util.spec_from_file_location('old_fixture',r.OLD/'tests/test_hybrid_raster_evidence.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

class Runner(unittest.TestCase):
    def test_frozen_readout_sealed_payload_and_resume(self):
        with tempfile.TemporaryDirectory(dir=r.OUT/'tests') as d:
            base=Path(d);out=base/'out';(out/'staging').mkdir(parents=True)
            raw=fixture.synthetic_raw();raw.pop('source_id');path=base/'raw.npz';np.savez_compressed(path,**raw)
            lock,_=r.inherited();context={'camera_hash':'synthetic','scientific_parameter_hash':r.PARAMETER_HASH}
            spec={'scene':'synthetic','key':'F_001','split':'F'}
            with patch.object(r,'OUT',out),patch.object(r,'context_for',return_value=context),patch.object(r,'get_raw',return_value=(raw,path,context)):
                first=r.make_frame(spec,{},None,lock,{},{});second=r.make_frame(spec,{},None,lock,{},{});self.assertEqual(first,second)
                dest=out/'frames/synthetic/F_001';self.assertTrue(r.valid_seal(dest,context))
                for name in ['native.npz','typed.npz','responses.npz','provenance.npz','diagnostics.json','line_panel.png','overlay_panel.png','matched_panel.png']:
                    self.assertTrue((dest/name).is_file(),name)
                with np.load(dest/'responses.npz') as v:
                    np.testing.assert_allclose(v['C'],1-(1-v['A'])*(1-v['B']))
                for kind in ['line','overlay','matched']:
                    with Image.open(dest/(kind+'_panel.png')) as im:self.assertEqual(im.size,(100,48))
                with self.assertRaises(ValueError):r.valid_seal(dest,{**context,'camera_hash':'changed'})
                (dest/'diagnostics.json').write_text('{}')
                with self.assertRaises(ValueError):r.make_frame(spec,{},None,lock,{}, {})
    def test_telegram_real_encoder_decode_all_33_h264_yuv420p_faststart(self):
        with tempfile.TemporaryDirectory(dir=r.OUT/'tests') as d:
            path=Path(d)/'fixture.mp4'
            def frames():
                for i in range(33):
                    image=np.full((368,1600,3),255,np.uint8);image[100:250,i*40:i*40+35]=[0,30+i*5,60]
                    yield image
            record=r.encode_telegram(frames(),path)
            self.assertEqual(record['frames'],33);self.assertEqual(record['distinct_frames'],33)
            self.assertEqual(record['size'],[1600,368]);self.assertTrue(record['faststart'])
            self.assertEqual(record['codec'],'h264');self.assertEqual(record['pixel_format'],'yuv420p')
    def test_native_guard_not_replaced_and_build_readonly(self):
        self.assertEqual(Path(r.native.gpu_guard.__code__.co_filename),r.OLD/'src/hybrid_raster_native.py')
        self.assertEqual(r.native.NATIVE,r.OLD/'out/hybrid_raster_evidence_v2/native')
        self.assertEqual(r.native.STAGE,r.OUT)
    def test_failed_calibration_preserves_both_arrays_and_invalid_status(self):
        with tempfile.TemporaryDirectory(dir=r.OUT/'tests') as d:
            base=Path(d);out=base/'out';art=base/'art';raw=fixture.synthetic_raw();bad={k:v.copy() for k,v in raw.items() if isinstance(v,np.ndarray)}
            bad['rgb'][0,0,0]+=.01
            manifest={'scene':'synthetic','checkpoint':{'sha256':'a'*64}}
            spec={'index':1,'key':'F_001','camera':{'synthetic':True}}
            with patch.object(r,'OUT',out),patch.object(r,'ART',art),patch.object(r,'status'),patch.object(r,'frame_specs',return_value=[spec]),patch.object(r,'calibration_context',return_value={'fixture':True}),patch.object(r.native,'render_native',side_effect=[raw,bad]):
                with self.assertRaises(RuntimeError):r.calibrate(manifest,{'mu':np.zeros((100,3))},{})
            failure=json.loads((art/'synthetic/CALIBRATION_FAILURE.json').read_text())
            self.assertEqual(failure['status'],'ENGINEERING_INVALID')
            self.assertEqual(len(failure['frames']),1)
            row=failure['frames'][0]
            self.assertEqual(r.hash_file(row['path']),row['sha256'])
            self.assertEqual(r.hash_file(row['unpatched_path']),row['unpatched_sha256'])
            self.assertFalse((out/'calibration/synthetic/CALIBRATION.json').exists())

if __name__=='__main__':unittest.main(verbosity=2)
