"""Isolation/seed/worker contracts tested before new production behavior."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GS = ROOT / 'out/multiscene_foundation/vendor/gaussian-splatting'


class TrainingTests(unittest.TestCase):
    def test_seed_patch_changes_all_streams_and_only_seed_semantics(self):
        from src.multiscene_training import seed_sources
        original = {p: subprocess.check_output(['git', 'show', 'HEAD:' + p], cwd=GS).decode()
                    for p in ['train.py', 'utils/general_utils.py']}
        changed = seed_sources(original)
        expected = original['utils/general_utils.py'].replace('def safe_state(silent):', 'def safe_state(silent, seed=0):')
        for name in ['random.seed', 'np.random.seed', 'torch.manual_seed']:
            expected = expected.replace(name + '(0)', name + '(seed)')
        self.assertEqual(changed['utils/general_utils.py'], expected)
        # Removing the one seed declaration and changing the call back must recover
        # byte-identical training code, including every optimizer/loss argument.
        recovered = changed['train.py'].replace('    parser.add_argument("--seed", type=int, default=0)\n', '')
        recovered = recovered.replace('safe_state(args.quiet, args.seed)', 'safe_state(args.quiet)')
        self.assertEqual(recovered, original['train.py'])
        source = changed['utils/general_utils.py']
        program = '''
import sys,random,numpy as np,torch
ns={}; exec(sys.stdin.read(),ns)
def sample(seed):
 old=sys.stdout; ns['safe_state'](False,seed); sys.stdout=old
 return [random.random(),float(np.random.random()),float(torch.rand(())),float(torch.rand((),device='cuda'))]
a=sample(1729); b=sample(2718); c=sample(1729)
assert a==c, (a,c)
assert all(x!=y for x,y in zip(a,b)), (a,b)
'''
        p = subprocess.run([sys.executable, '-c', program], input=source, text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_staged_data_is_identical_but_has_independent_initialization(self):
        from src.multiscene_training import stage_training_data, training_command
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); source = tmp / 'source'; source.mkdir()
            for name in ['train', 'val']:
                (source / name).mkdir()
                for i in range(4): (source / name / f'r_{i}.png').write_bytes(bytes([i]))
                (source / f'transforms_{name}.json').write_text(json.dumps(dict(camera_angle_x=.7,
                    frames=[dict(file_path=f'./{name}/r_{i}', transform_matrix=[[i]]) for i in range(4)])))
            (source / 'points3d.ply').write_text('FORBIDDEN SHARED INITIALIZER')
            cfg = dict(training=dict(optimization_indices=[0,2],validation_indices=[1,3],
                seeds=[1729,2718],iterations=30000,test_iterations=[7000,30000],save_iterations=[7000,30000]))
            manifests = [stage_training_data(source, tmp / str(seed), cfg) for seed in [1729,2718]]
            self.assertEqual(manifests[0]['data_digest'], manifests[1]['data_digest'])
            for seed in [1729,2718]:
                d = tmp / str(seed)
                self.assertFalse((d / 'points3d.ply').exists())
                self.assertEqual(len(list(d.rglob('*.png'))), 4)
                self.assertEqual(len(json.loads((d/'transforms_train.json').read_text())['frames']), 2)
            (tmp/'1729/points3d.ply').write_text('seed1729 generated')
            self.assertFalse((tmp/'2718/points3d.ply').exists())
            command = training_command('/python', '/clean', tmp/'1729', tmp/'output', 1729, 6009, cfg)
            self.assertEqual(command[command.index('--iterations')+1], '30000')
            self.assertEqual(command[command.index('--seed')+1], '1729')
            self.assertIn('--eval', command); self.assertIn('--white_background', command)
            self.assertNotIn('--start_checkpoint', command)
            with self.assertRaises(FileExistsError): stage_training_data(source,tmp/'1729',cfg)

    def test_worker_resource_wait_and_failure_are_durable(self):
        from src.multiscene_training import run_job
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp); samples = iter([100,20000]); sleeps=[]
            rc = run_job([sys.executable,'-c','print("started"); raise SystemExit(7)'],tmp,
                {},0,dict(min_free_mib=16384,min_disk_gib=0,resource_poll_seconds=60,
                resource_wait_seconds=120,timeout_seconds=10),
                memory_query=lambda gpu:next(samples),sleep=sleeps.append)
            self.assertEqual(sleeps,[60]); self.assertEqual(rc,7)
            status=json.loads((tmp/'exit_status.json').read_text())
            self.assertEqual(status['exit_code'],7); self.assertIn('started',(tmp/'train.log').read_text())
            self.assertEqual(len((tmp/'resources.jsonl').read_text().splitlines()),2)
            with self.assertRaises(FileExistsError):
                run_job([],tmp,{},0,{},memory_query=lambda gpu:20000,sleep=sleeps.append)

    def test_training_entry_preserves_arguments_and_blocks_unstaged_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); clean=tmp/'clean'; clean.mkdir(); data=tmp/'data'; data.mkdir()
            output=tmp/'output'; output.mkdir(); forbidden=tmp/'DEV.png'; forbidden.write_text('sealed')
            (clean/'train.py').write_text('''
import sys,json
from pathlib import Path
assert sys.argv[1:]==['--seed','1729']
try:
 Path(%r).read_bytes()
except PermissionError: pass
else: raise RuntimeError('unrestricted DEV read')
Path(%r).write_text('ok')
''' % (str(forbidden), str(output/'result')))
            spec=tmp/'entry.json'; spec.write_text(json.dumps(dict(source=str(clean),data=str(data),
                output=str(output),site=[],arguments=['--seed','1729'])))
            p=subprocess.run([sys.executable,str(ROOT/'scripts/multiscene_train_entry.py'),'--spec',str(spec)],
                capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual((output/'result').read_text(),'ok')

    def test_job_manifests_enumerate_eight_fixed_runs_without_recipe_drift(self):
        from src.multiscene_training import job_manifests
        cfg=json.loads((ROOT/'out/multiscene_foundation/config.json').read_text())
        jobs=job_manifests(cfg,Path('/isolated'),'/python')
        self.assertEqual(len(jobs),8)
        self.assertEqual({(j['scene'],j['seed']) for j in jobs},
                         {(s,k) for s in ['lego','chair','drums','ficus'] for k in [1729,2718]})
        for j in jobs:
            self.assertEqual(j['expected_iteration'],30000)
            self.assertEqual(j['command'][1],'/isolated/vendor/gaussian-splatting/train.py')
            self.assertEqual(j['source_commit'],'472689c0dc70417448fb451bf529ae532d32c095')
            self.assertIn('/isolated/inputs/',j['data'])
            self.assertEqual(j['gpu'],0 if j['seed']==1729 else 1)
        self.assertEqual(len({j['data'] for j in jobs}),8)


if __name__ == '__main__': unittest.main()
