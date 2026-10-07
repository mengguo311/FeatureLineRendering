"""CPU-only safety and persistence contracts; no CUDA imports."""
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

import safety


def xml(mem=0, util=0, processes="", uuid="GPU-test"):
    return f'''<nvidia_smi_log><gpu><uuid>{uuid}</uuid>
    <fb_memory_usage><used>{mem} MiB</used></fb_memory_usage>
    <utilization><gpu_util>{util} %</gpu_util></utilization>
    <processes>{processes}</processes></gpu></nvidia_smi_log>'''


class IdleTests(unittest.TestCase):
    def test_idle_requires_two_spaced_samples_same_uuid(self):
        gate = safety.IdleGate(stable_seconds=60)
        self.assertEqual(gate.observe(safety.parse_gpu_xml(xml()), 0), [])
        self.assertEqual(gate.observe(safety.parse_gpu_xml(xml()), 59), [])
        self.assertEqual(gate.observe(safety.parse_gpu_xml(xml()), 60), ["GPU-test"])

    def test_compute_graphics_context_memory_util_and_failure_block(self):
        for sample in [xml(processes='<process_info><pid>123</pid><type>C</type></process_info>'),
                       xml(processes='<process_info><pid>124</pid><type>G</type></process_info>'),
                       xml(mem=256), xml(util=1), '<bad>',
                       xml().replace('<processes></processes>', '<processes>N/A</processes>'),
                       xml().replace('<gpu_util>0 %</gpu_util>', ''),
                       xml().replace('<processes></processes>', '')]:
            gate = safety.IdleGate(stable_seconds=60)
            gate.observe(safety.parse_gpu_xml(xml()), 0)
            self.assertEqual(gate.observe(safety.parse_gpu_xml(sample), 60), [])
            self.assertEqual(gate.observe(safety.parse_gpu_xml(xml()), 120), [])

    def test_foreign_context_is_not_excused_by_free_memory(self):
        sample = safety.parse_gpu_xml(xml(mem=10, processes='<process_info><pid>12</pid><type>C</type></process_info>'))
        self.assertFalse(safety.is_idle(sample[0]))
        self.assertTrue(safety.stage_conflict(sample, "GPU-test", {13}))
        self.assertFalse(safety.stage_conflict(sample, "GPU-test", {12}))
        self.assertTrue(safety.stage_conflict(None, "GPU-test", {12}))


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seal_skip_only_after_verified_inputs_and_outputs(self):
        output = self.root / 'result'
        output.write_text('complete')
        seal = self.root / 'seal.json'
        safety.seal_stage(seal, 'smoke', {'source': 'abc'}, [output])
        self.assertTrue(safety.verify_seal(seal, 'smoke', {'source': 'abc'}))
        self.assertFalse(safety.verify_seal(seal, 'smoke', {'source': 'changed'}))
        output.write_text('truncated')
        self.assertFalse(safety.verify_seal(seal, 'smoke', {'source': 'abc'}))

    def test_unsealed_and_interrupted_atomic_write_do_not_skip(self):
        path = self.root / 'state.json'
        safety.atomic_json(path, {'state': 'WAITING_FOR_IDLE_GPU'})
        with self.assertRaises(TypeError):
            safety.atomic_json(path, {'bad': object()})
        self.assertEqual(json.loads(path.read_text())['state'], 'WAITING_FOR_IDLE_GPU')
        self.assertFalse(safety.verify_seal(self.root / 'missing', 'train', {}))

    def test_stage_order_and_fail_closed(self):
        self.assertEqual(safety.next_stage({}), 'smoke')
        self.assertEqual(safety.next_stage({'smoke': True}), 'train')
        with self.assertRaises(ValueError):
            safety.next_stage({'train': True})
        self.assertIsNone(safety.next_stage(dict.fromkeys(safety.STAGES, True)))

    def test_failed_stage_retains_history(self):
        state = self.root / 'current.json'
        safety.atomic_json(state, {'stage': 'train', 'returncode': 1})
        saved = safety.archive_failure(state, self.root / 'failures')
        self.assertEqual(json.loads(saved.read_text())['returncode'], 1)
        self.assertTrue(state.exists())


class ArchiveTests(unittest.TestCase):
    def test_tar_rejects_traversal_links_absolute_and_duplicates_before_writes(self):
        for name, kind in [('../escape', 'file'), ('/abs', 'file'), ('scan/link', 'link'),
                           ('scan/hard', 'hard'), ('scan/f', 'duplicate')]:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = root / 'bad.tar'
                with tarfile.open(archive, 'w') as t:
                    info = tarfile.TarInfo(name)
                    if kind in ('link', 'hard'):
                        info.type = tarfile.SYMTYPE if kind == 'link' else tarfile.LNKTYPE
                        info.linkname = '../../escape'
                    t.addfile(info, io.BytesIO())
                    if kind == 'duplicate':
                        t.addfile(info, io.BytesIO())
                with self.assertRaises(ValueError):
                    safety.safe_extract_tar(archive, root / 'out')
                self.assertFalse((root / 'out').exists())

    def test_normal_archive_is_extracted_and_counted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'good.tar'
            with tarfile.open(archive, 'w') as t:
                info = tarfile.TarInfo('dtu/scan24/images/a.png')
                info.size = 3
                t.addfile(info, io.BytesIO(b'abc'))
            result = safety.safe_extract_tar(archive, root / 'out')
            self.assertEqual(result['files'], 1)
            self.assertEqual((root / 'out/dtu/scan24/images/a.png').read_bytes(), b'abc')


if __name__ == '__main__':
    unittest.main(verbosity=2)
