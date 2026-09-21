import hashlib
import tempfile
import unittest
from pathlib import Path
import numpy as np
import cv2


class LayoutTests(unittest.TestCase):
    def test_layout_confinement_audits_startup_directory_metadata(self):
        import json,subprocess,sys,shutil
        from src.corrected_audit import audit_policy,bootstrap_reads_before_policy
        if not shutil.which('strace'):self.skipTest('strace unavailable')
        tracer=next(line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('TracerPid:'))
        if tracer!='0':self.skipTest('nested ptrace is unavailable; run this self-traced integration test without an outer tracer')
        repo=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'run';run.mkdir()
            for folder in ['raw','native','final']:(run/folder).mkdir()
            for name in ['GATES.json','NORMALIZATION.json']:(run/name).write_text('{}')
            z=np.zeros((2,2));raw={'diagnostics.'+k:z.copy() for k in ['A','z_front','z_mean','z_50','z_var','H_id','D_id','D_zdist','ordering_consistency','stable_split','layer_count_transition','front_mass_transition']}
            raw.update({'layers.'+k:z.copy() for k in ['tail_alpha','overflow_mass','local_scale','layer_count']})
            raw.update({'layers.retained_mass':np.full((2,2,4),.1),'layers.retained_depth':np.ones((2,2,4))*4,'events.offsets':np.zeros(5,'i8'),'events.ids':np.array([],'i8')})
            for scene in ['lego','chair','drums','ficus']:
                for view in [1,27,53,79]:
                    np.savez(run/'raw'/f'{scene}_{view}_full.npz',**raw)
                    np.savez(run/'native'/f'{scene}_{view}.npz',native_alpha=np.ones((2,2))*.8)
            trace=Path(tmp)/'layout.strace'
            p=subprocess.run(['strace','-f','-yy','-e','trace=open,openat,openat2,creat','-o',str(trace),sys.executable,'-X',f'pycache_prefix={tmp}/unused',str(repo/'scripts/render_adaptive_g1_diagnostics.py'),'--run',str(run)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            policy=json.loads((run/'diagnostics/allowlist.json').read_text());exceptions=[str(repo),str(repo/'scripts'),str(repo/'src'),str(repo/'tests')]+policy['bootstrap_files']
            audit=audit_policy(trace.read_text(),policy,run/'diagnostics',exceptions)
            self.assertTrue(audit['passed'],audit)
            self.assertTrue(bootstrap_reads_before_policy(trace.read_text(),run/'diagnostics/allowlist.json',exceptions))

    def test_layout_cli_requires_existing_run(self):
        import subprocess,sys
        script=Path(__file__).resolve().parents[1]/'scripts/render_adaptive_g1_diagnostics.py'
        p=subprocess.run([sys.executable,str(script),'--help'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('--run',p.stdout)

    def test_diagnostic_sheet_keeps_all_pixels_and_source_bytes(self):
        from scripts.render_adaptive_g1_diagnostics import diagnostic_sheet
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'raw.npz'
            np.savez(source,field=np.arange(48).reshape(6,8))
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            maps=[('native alpha',np.ones((6,8))),('residual',np.zeros((6,8)))]
            diagnostic_sheet(root/'sheet.png',[maps,maps])
            im=cv2.imread(str(root/'sheet.png'))
            self.assertEqual(im.shape[:2],(2*(6+44),16))
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
            self.assertTrue(np.all(im[44:50,:8]==255))
            self.assertTrue(np.all(im[94:100,:8]==0))

    def test_mechanism_maps_include_residuals_and_all_four_layers(self):
        from scripts.render_adaptive_g1_diagnostics import mechanism_maps
        z=np.zeros((2,2));raw={'diagnostics.'+k:z.copy() for k in ['A','z_front','z_mean','z_50','z_var','H_id','D_id','D_zdist','ordering_consistency','stable_split','layer_count_transition','front_mass_transition']}
        raw.update({'layers.'+k:z.copy() for k in ['tail_alpha','overflow_mass','local_scale','layer_count']})
        raw.update({'layers.retained_mass':np.full((2,2,4),.1),'layers.retained_depth':np.ones((2,2,4))*4,'events.offsets':np.zeros(5,'i8'),'events.ids':np.array([],'i8')})
        raw['diagnostics.A'][:]=.4
        native={'native_alpha':np.ones((2,2))*.8}
        maps=dict(mechanism_maps(raw,native))
        self.assertEqual(len(maps),32)
        np.testing.assert_array_equal(maps['missing native alpha'],.4*np.ones((2,2)))
        np.testing.assert_array_equal(maps['retained/native alpha'],.5*np.ones((2,2)))
        for i in range(4):
            np.testing.assert_array_equal(maps[f'layer {i+1} mass'],.1*np.ones((2,2)))
            np.testing.assert_array_equal(maps[f'layer {i+1} depth /8'],.5*np.ones((2,2)))
