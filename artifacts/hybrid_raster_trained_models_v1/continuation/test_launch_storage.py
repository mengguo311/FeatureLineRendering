"""Storage continuation launcher contracts; fixtures and traces stay external."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import launch_storage as launch


class LaunchStorageTests(unittest.TestCase):
    def fixture(self):
        path = launch.EXTERNAL_ROOT / 'tests' / ('launch_' + uuid.uuid4().hex)
        path.mkdir(parents=True)
        return path

    def test_command_is_exact_producer_and_strace(self):
        command = launch.producer_command('materials', 'render')
        self.assertEqual(command[-4:], ['--phase', 'render', '--scene', 'materials'])
        self.assertEqual(Path(command[1]), launch.CONT / 'run_storage_transport.py')
        path = launch.EXTERNAL_ROOT / 'launchlogs' / 'fixture' / 'production.strace'
        trace = launch.trace_command(command, path)
        self.assertEqual(trace[:8], ['strace', '-f', '-q', '-yy', '-s', '4096', '-e', 'trace=open,openat,openat2,creat'])
        self.assertEqual(trace[8:11], ['-o', str(path), '--'])
        with self.assertRaises(ValueError):
            launch.producer_command('hotdog', 'render')
        with self.assertRaises(ValueError):
            launch.producer_command('ship', 'training')

    def test_same_uid_does_not_establish_gpu_ownership(self):
        with self.assertRaises(RuntimeError):
            launch.require_idle_gpu([{'pid': os.getpid(), 'uid': os.getuid()}])
        self.assertEqual(launch.require_idle_gpu([]), [])

    def test_owned_stop_requires_exact_pid_starttime_and_group(self):
        identity = {'pid': 71234, 'ppid': os.getpid(), 'starttime': 321, 'pgid': 71234, 'uid': os.getuid()}
        with patch.object(launch, 'process_identity', return_value={**identity, 'starttime': 322}), patch.object(launch.os, 'killpg') as kill:
            with self.assertRaises(RuntimeError):
                launch.stop_owned(identity, signal.SIGTERM)
            kill.assert_not_called()
        with patch.object(launch, 'process_identity', return_value={**identity, 'pgid': 7}), patch.object(launch.os, 'killpg') as kill:
            with self.assertRaises(RuntimeError):
                launch.stop_owned(identity, signal.SIGTERM)
            kill.assert_not_called()
        with patch.object(launch, 'process_identity', return_value=identity), patch.object(launch.os, 'killpg') as kill:
            self.assertTrue(launch.stop_owned(identity, signal.SIGTERM))
            kill.assert_called_once_with(71234, signal.SIGTERM)

    def test_trace_requires_normal_zero_exit_and_no_pending_call(self):
        normal = '10 openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY) = 3</etc/ld.so.cache>\n10 +++ exited with 0 +++\n'
        self.assertTrue(launch.trace_finished(normal, 0))
        self.assertFalse(launch.trace_finished(normal, 143))
        self.assertFalse(launch.trace_finished('11 openat(AT_FDCWD, "/x", O_RDONLY) = 3</x>\n' + normal, 0))
        self.assertFalse(launch.trace_finished(normal.splitlines()[0] + '\n', 0))
        self.assertFalse(launch.trace_finished(normal.replace('exited with 0', 'killed by SIGTERM'), 0))
        self.assertFalse(launch.trace_finished('10 openat(AT_FDCWD, "/x", O_RDONLY <unfinished ...>\n' + normal, 0))

    def test_budget_includes_failed_render_but_not_media(self):
        rows = [{'phase': 'render', 'elapsed_seconds': 11, 'state': 'FAILED'},
                {'phase': 'render', 'elapsed_seconds': 7, 'state': 'COMPLETE'},
                {'phase': 'media', 'elapsed_seconds': 90, 'state': 'COMPLETE'}]
        result = launch.budget_remaining({'started_epoch': 100, 'wall_limit_seconds': 200, 'gpu_limit_seconds': 50}, rows, now=130)
        self.assertEqual(result['gpu_remaining_seconds'], 32)
        self.assertEqual(result['wall_remaining_seconds'], 170)
        with self.assertRaises(RuntimeError):
            launch.budget_remaining({'started_epoch': 100, 'wall_limit_seconds': 20, 'gpu_limit_seconds': 50}, rows, now=130)

    def test_process_environment_routes_every_cache_and_temp_external(self):
        environment = launch.child_environment()
        self.assertEqual(environment['PYTHONDONTWRITEBYTECODE'], '1')
        for name in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'TORCH_HOME', 'TORCH_EXTENSIONS_DIR', 'CUDA_CACHE_PATH', 'MPLCONFIGDIR'):
            self.assertTrue(Path(environment[name]).is_relative_to(launch.EXTERNAL_ROOT), name)
        self.assertEqual(environment['GIT_OPTIONAL_LOCKS'], '0')

    def test_storage_guard_rechecks_both_roots(self):
        fake = {'roots': [{'path': str(launch.ROOT), 'free_bytes': 2**30},
                          {'path': str(launch.EXTERNAL_ROOT), 'free_bytes': 2**30}]}
        with patch.object(launch, 'assert_roots', return_value=fake) as check:
            self.assertEqual(launch.storage_guard(), fake)
            check.assert_called_once_with()

    def test_cpu_real_strace_has_normal_exit_receipt_and_untouched_start(self):
        attempt = self.fixture()
        start = {'scene': 'fixture', 'phase': 'media', 'producer': 'synthetic CPU fixture'}
        launch.write_once_json(attempt / 'START.json', start)
        before = launch.hash_file(attempt / 'START.json')
        output = attempt / 'fixture.txt'
        command = [sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("sealed CPU fixture\\n")', str(output)]
        receipt = launch.run_traced(command, attempt, phase='media', scene='fixture', remaining_seconds=30, guard=lambda: {'test': 'CPU fixture'})
        self.assertEqual(receipt['exit_code'], 0)
        self.assertTrue(receipt['completed'])
        self.assertTrue(receipt['normal_exit'])
        self.assertEqual(receipt['trace_sha256'], launch.hash_file(attempt / 'production.strace'))
        self.assertEqual(before, launch.hash_file(attempt / 'START.json'))
        self.assertEqual(json.loads((attempt / 'EXIT.json').read_text())['state'], 'COMPLETE')
        self.assertEqual(output.read_text(), 'sealed CPU fixture\n')
        self.assertTrue((attempt / 'LAUNCH.json').is_file())
        self.assertTrue((attempt / 'resources.jsonl').is_file())

    def test_detached_launch_uses_private_session_and_external_handles(self):
        from types import SimpleNamespace
        with patch.object(sys, 'argv', ['launch_storage.py', '--scene', 'ship', '--phase', 'media']), \
                patch.object(launch, 'storage_guard', return_value={'test': 'CPU fixture'}), \
                patch.object(launch, 'LAUNCH_ROOT', self.fixture()), \
                patch.object(launch.subprocess, 'Popen', return_value=SimpleNamespace(pid=os.getpid())) as popen:
            self.assertEqual(launch.main(), 0)
        call = popen.call_args
        self.assertTrue(call.kwargs['start_new_session'])
        self.assertEqual(call.kwargs['stdin'], subprocess.DEVNULL)
        self.assertTrue(Path(call.kwargs['stdout'].name).is_relative_to(launch.EXTERNAL_ROOT))
        self.assertIn('--supervise', call.args[0])

    def test_nonzero_cpu_process_is_retained_as_failure(self):
        attempt = self.fixture()
        launch.write_once_json(attempt / 'START.json', {'fixture': True})
        receipt = launch.run_traced([sys.executable, '-c', 'raise SystemExit(9)'], attempt,
                                   phase='media', scene='fixture', remaining_seconds=30,
                                   guard=lambda: {'test': 'CPU fixture'})
        self.assertEqual(receipt['exit_code'], 9)
        self.assertFalse(receipt['completed'])
        self.assertFalse(receipt['normal_exit'])
        self.assertEqual(receipt['state'], 'FAILED')
        self.assertTrue((attempt / 'production.strace').is_file())


if __name__ == '__main__':
    unittest.main(verbosity=2)
