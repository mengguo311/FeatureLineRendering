import json
import tempfile
import unittest
from pathlib import Path

from src.hybrid_raster_stage import frame_specs, require_evaluation_lock, read_inputs


class StageContractTest(unittest.TestCase):
    def test_exact_predeclared_domain_and_camera(self):
        inputs = read_inputs()
        for scene in ('lego', 'chair', 'drums', 'ficus'):
            f = frame_specs(inputs, scene, 'F')
            c = frame_specs(inputs, scene, 'C')
            arc = frame_specs(inputs, scene, 'arc0')
            self.assertEqual([x['index'] for x in f], [1,14,27,41,53,67,79,93])
            self.assertEqual([x['index'] for x in c], [7,21,33,47,59,73,86,99])
            self.assertEqual(len(arc), 33)
            self.assertEqual(arc[16]['camera'], inputs['scenes'][scene]['arcs'][0]['frames'][16])
            self.assertEqual(f[0]['camera']['native_K'][0][2], 399.5)
            self.assertEqual(f[0]['camera']['native_width'], 800)
        with self.assertRaises(ValueError):
            frame_specs(inputs, 'lego', 'TEST')

    def test_c_gate_requires_all_primary_f_seals_and_matching_lock(self):
        with tempfile.TemporaryDirectory(dir=Path('out/hybrid_raster_evidence_v2/tmp')) as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError):
                require_evaluation_lock(root)

    def test_complete_f_lock_releases_gate_then_detects_tamper(self):
        from src.hybrid_raster_io import canonical_hash, hash_file, seal_frame, atomic_json
        with tempfile.TemporaryDirectory(dir=Path('out/hybrid_raster_evidence_v2/tmp')) as tmp:
            root=Path(tmp); records=[]
            config={'sources':{'fixture':'synthetic'}}; normalization={'fixed':'synthetic'}
            parameter_hash=canonical_hash({'config':config,'normalization':normalization})
            for scene in ('lego','chair'):
                for index in (1,14,27,41,53,67,79,93):
                    key=f'F_{index:03d}'; staging=root/f'{scene}_{key}'
                    staging.mkdir(); (staging/'response.txt').write_text('synthetic response')
                    final=root/'frames'/scene/key; context={'scene':scene,'key':key,'parameter_hash':parameter_hash,'source_hashes':config['sources']}
                    seal_frame(staging,final,context)
                    records.append({'scene':scene,'key':key,'context':context,'seal_sha256':hash_file(final/'SEAL.json')})
            lock={'primary_F':records,'normalization':normalization,'config':config,'parameter_hash':parameter_hash}
            lock['lock_hash']=canonical_hash(lock); atomic_json(root/'LOCK.json',lock)
            self.assertEqual(require_evaluation_lock(root),lock)
            (root/'frames/lego/F_001/response.txt').write_text('corrupted')
            with self.assertRaises(ValueError):
                require_evaluation_lock(root)
            (root/'LOCK.json').write_text(json.dumps({'normalization': {}, 'primary_F': []}))
            with self.assertRaises(RuntimeError):
                require_evaluation_lock(root)


if __name__ == '__main__':
    unittest.main()
