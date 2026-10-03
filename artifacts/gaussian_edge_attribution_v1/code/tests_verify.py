"""Independent reference and output integrity TDD; no source data accessed."""
import hashlib
import json
import pathlib
import tempfile
import unittest
import numpy as np
from verify import reference_projection, reference_id_statistics, verify_seal, validate_camera, audit_workspace
from media import mask_image, write_panel
from audit_access import trace_summary

TEMP_ROOT=pathlib.Path(__file__).resolve().parents[3]/'out/gaussian_edge_attribution_v1/validation/tmp'
TEMP_ROOT.mkdir(parents=True,exist_ok=True)

class VerificationTests(unittest.TestCase):
    def test_projection_preserves_full_transmittance_and_empty(self):
        ids=np.array([[[0,1,-1,-1],[1,2,0,-1]]])
        w=np.array([[[.4,.12,0,0],[.3,.2,.1,0]]])
        score=np.array([1.,.5,0.])
        np.testing.assert_allclose(reference_projection(ids,w,score),[[.46,.25]])
        np.testing.assert_allclose(reference_projection(ids,w,np.array([0.,1.,0.])),[[.12,.3]])
        self.assertEqual(float(reference_projection(ids[:,:0],w[:,:0],score).sum()),0)

    def test_projection_more_than_four_and_original_id_permutation(self):
        ids=np.array([[[5,4,3,2,1,0]]]); w=np.array([[[.3,.2,.1,.08,.04,.02]]]); s=np.array([0,.2,.4,.6,.8,1.])
        np.testing.assert_allclose(reference_projection(ids,w,s),[[.56]])
        p=np.array([3,4,1,5,0,2]); inverse=np.argsort(p)
        np.testing.assert_allclose(reference_projection(inverse[ids],w,s[p]),reference_projection(ids,w,s))
        self.assertGreater(float(reference_projection(ids,w,s).sum()),float(reference_projection(ids[...,:4],w[...,:4],s).sum()))

    def test_visible_nonevidence_not_unknown_and_area_normalization(self):
        ids=np.array([[[0,1],[0,-1],[2,-1]]]); w=np.array([[[.2,.3],[.8,0],[.5,0]]]); e=np.array([[1.,0.,0.]])
        r=reference_id_statistics(ids,w,e,[0,1,2,3])
        np.testing.assert_allclose(r['numerator'],[.2,.3,0,0]); np.testing.assert_allclose(r['denominator'],[1.,.3,.5,0])
        np.testing.assert_allclose(r['negative'],[.8,0,.5,0]); self.assertTrue(r['unknown'][-1]); self.assertEqual(r['score'][2],0)
        self.assertAlmostEqual(r['score'][0],.2); self.assertAlmostEqual(r['score'][1],1.)

    def test_repeated_id_accumulates_raw_weights(self):
        r=reference_id_statistics(np.array([[[1,1]]]),np.array([[[.2,.3]]]),np.array([[.4]]),[1])
        self.assertAlmostEqual(r['numerator'][0],.2); self.assertAlmostEqual(r['denominator'][0],.5)

    def test_corruption_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as td:
            root=pathlib.Path(td); (root/'a.bin').write_bytes(b'first')
            seal={'files':{'a.bin':hashlib.sha256(b'first').hexdigest()}}
            (root/'SEAL.json').write_text(json.dumps(seal)); self.assertTrue(verify_seal(root/'SEAL.json')['ok'])
            (root/'a.bin').write_bytes(b'changed')
            with self.assertRaises(ValueError): verify_seal(root/'SEAL.json')
            seal['files']={'../outside':'0'*64}; (root/'SEAL.json').write_text(json.dumps(seal))
            with self.assertRaises(ValueError): verify_seal(root/'SEAL.json')

    def test_camera_shape_and_finite(self):
        c={'native_width':800,'native_height':800,'w2c':np.eye(4).tolist(),'native_K':np.eye(3).tolist()}
        self.assertTrue(validate_camera(c))
        c['w2c'][3][3]=0
        with self.assertRaises(ValueError): validate_camera(c)

    def test_trace_reassembles_resumed_and_reports_external_write(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as td:
            p=pathlib.Path(td)/'trace.log'
            p.write_text('42 openat(AT_FDCWD, "/readonly/model.ply", O_RDONLY <unfinished ...>\n42 <... openat resumed>) = 3\n43 openat(AT_FDCWD, "/outside/artifact.bin", O_WRONLY|O_CREAT, 0666) = 4\n')
            r=trace_summary(p)
            self.assertEqual(r['unfinished_open_records_not_reconstructed'],0)
            self.assertEqual(r['successful_open_records'],2)
            self.assertEqual(r['external_regular_or_unresolved_file_write_opens'],['/outside/artifact.bin'])
            self.assertFalse(r['ok'])

    def test_trace_thread_name_pseudofile_is_explicit(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as td:
            p=pathlib.Path(td)/'trace.log'
            p.write_text('42 openat(AT_FDCWD, "/proc/self/task/43/comm", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 4\n42 openat(AT_FDCWD, "/dev/null", O_WRONLY) = 5</dev/null<char 1:3>>\n')
            r=trace_summary(p)
            self.assertTrue(r['ok'])
            self.assertEqual(r['thread_name_pseudofile_write_opens'],['/proc/42/task/43/comm'])
            self.assertEqual(r['device_write_open_paths'],['/dev/null'])

    def test_white_mask_and_full_uncropped_panel(self):
        self.assertEqual(np.asarray(mask_image(np.zeros((2,2))))[0,0,0],255)
        self.assertEqual(np.asarray(mask_image(np.ones((2,2))))[0,0,0],0)
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as td:
            p=pathlib.Path(td)/'panel.png'; rgb=np.zeros((8,8,3)); z=np.zeros((8,8))
            from PIL import Image
            result=write_panel(p,rgb,z,z,z,z,title='test',display_gain=2.)
            with Image.open(p) as image: self.assertEqual(image.width,40)
            self.assertEqual(result['tile_size'],[8,8]); self.assertFalse(result['cropped'])

if __name__=='__main__': unittest.main()
