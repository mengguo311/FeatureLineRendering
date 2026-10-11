import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from diagnostic_runner import DiagnosticRunner
import shared_runner as shared
import runner
from safety import atomic_json,sha256,seal_stage

GPU=shared.GPU
SAMPLE=[{'uuid':GPU,'memory_mib':9745,'total_mib':49140,'util_percent':0,'contexts':[]}]

class DiagnosticRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.path=self.root/'config.json'
        self.config={'state_dir':str(self.root/'state'),'log_dir':str(self.root/'logs'),
            'inputs':{'diagnostic':'test'},'scene':'scan24','automatic_scene_limit':1,
            'engineering_ready':True,'immutable_files':{},'stable_seconds':60,'poll_seconds':60,
            'preflight_report':str(self.root/'preflight.json'),'cwd':str(self.root),'runtime_env':{},
            'allowed_gpu_uuids':[GPU],'reports':{'checkpoint_diagnostic':str(self.root/'report.json')},
            'stage_commands':{'checkpoint_diagnostic':['fake']}}
        atomic_json(self.root/'preflight.json',{'passed':True});atomic_json(self.path,self.config)
        self.spawned=[]
        def spawn(*a,**kw):
            child=type('Child',(),{'pid':99999999,'poll':lambda self:None})()
            self.spawned.append((a,kw));return child
        self.e=DiagnosticRunner(self.path,spawn=spawn,query=lambda:SAMPLE,space_check=lambda:True)
        self.patch1=patch.object(runner,'is_idle',shared.can_start);self.patch1.start()
        self.patch2=patch('safety.is_idle',shared.can_start);self.patch2.start()
    def tearDown(self):
        self.e.close();self.patch1.stop();self.patch2.stop();self.tmp.cleanup()
    def test_only_diagnostic_pending_never_training(self):
        self.assertEqual(self.e.pending_stage(),'checkpoint_diagnostic')
    def test_failed_query_and_busy_deny_then_stable_60_launch(self):
        busy=[dict(SAMPLE[0],util_percent=11)]
        for now,sample in [(0,None),(60,busy),(120,SAMPLE),(179,SAMPLE)]:self.e.tick(sample,now)
        self.assertFalse(self.spawned)
        self.e.tick(SAMPLE,180)
        self.assertEqual(len(self.spawned),1)
        self.assertEqual(self.e.state['stage'],'checkpoint_diagnostic')
        self.assertEqual(self.spawned[0][1]['env']['CUDA_VISIBLE_DEVICES'],GPU)
    def test_verified_seal_finishes_diagnosis_without_evaluation_claim(self):
        output=self.root/'out';output.write_text('evidence')
        seal_stage(self.root/'state/checkpoint_diagnostic.seal.json','checkpoint_diagnostic',self.config['inputs'],[output])
        self.e.tick(SAMPLE,0)
        self.assertEqual(self.e.state['status'],'DIAGNOSTIC_COMPLETE')
        self.assertFalse(self.e.state.get('pilot_evaluation_verified',False))
        output.write_text('changed')
        self.assertEqual(self.e.pending_stage(),'checkpoint_diagnostic')
    def test_foreign_context_stops_only_own_stage(self):
        self.e.tick(SAMPLE,0);self.e.tick(SAMPLE,60)
        changed=[dict(SAMPLE[0],contexts=[{'pid':123,'type':'C'}])]
        with patch.object(self.e,'request_own_stop') as stop:
            self.e.tick(changed,65);stop.assert_called_once()

if __name__=='__main__':unittest.main(verbosity=2)
