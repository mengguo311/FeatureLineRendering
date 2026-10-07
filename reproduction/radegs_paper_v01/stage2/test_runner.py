"""State-machine tests using simulated GPU samples and fake child processes."""
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import time
from unittest.mock import patch

from safety import atomic_json,sha256,seal_stage
import runner


IDLE=[{'uuid':'GPU-test','memory_mib':0,'util_percent':0,'contexts':[]}]
BUSY=[{'uuid':'GPU-test','memory_mib':400,'util_percent':0,'contexts':[{'pid':99,'type':'G'}]}]


class Child:
    pid=123456
    code=None
    def poll(self):return self.code


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.config={'state_dir':str(self.root/'state'),'log_dir':str(self.root/'logs'),
                     'inputs':{'source':'test'},'poll_seconds':60,'stable_seconds':60,
                     'scene':'scan24','automatic_scene_limit':1,
                     'engineering_ready':True,'immutable_files':{},
                     'stage_commands':{s:['fake',s] for s in runner.STAGES},
                     'cwd':str(self.root),'runtime_env':{},'reports':{},
                     'preflight_report':str(self.root/'preflight.json')}
        atomic_json(self.config['preflight_report'],{'passed':True})
        self.path=self.root/'config.json';atomic_json(self.path,self.config)
        self.spawned=[]
        def spawn(*args,**kwargs):
            child=Child();self.spawned.append((args,kwargs,child));return child
        self.engine=runner.Runner(self.path,spawn=spawn,query=lambda:IDLE,space_check=lambda:True)

    def tearDown(self):
        self.engine.close();self.temp.cleanup()

    def test_busy_failed_query_and_one_idle_sample_never_launch(self):
        for now,sample in [(0,BUSY),(60,None),(120,IDLE),(150,IDLE)]:
            self.engine.tick(sample,now)
        self.assertFalse(self.spawned)
        self.assertEqual(self.engine.state['status'],'WAITING_FOR_IDLE_GPU')

    def test_stable_idle_recheck_launch_uuid_and_lock(self):
        self.engine.tick(IDLE,0);self.engine.tick(IDLE,60)
        self.assertEqual(len(self.spawned),1)
        self.assertEqual(self.engine.state['stage'],'smoke')
        self.assertEqual(self.spawned[0][1]['env']['CUDA_VISIBLE_DEVICES'],'GPU-test')
        self.assertTrue(self.spawned[0][1]['start_new_session'])
        with self.assertRaises(BlockingIOError):
            other=runner.Runner(self.path,spawn=lambda *a,**k:None,query=lambda:IDLE)

    def test_recheck_busy_does_not_launch(self):
        self.engine.query=lambda:BUSY
        self.engine.tick(IDLE,0);self.engine.tick(IDLE,60)
        self.assertFalse(self.spawned)

    def test_foreign_arrival_stops_only_owned_stage(self):
        self.engine.tick(IDLE,0);self.engine.tick(IDLE,60)
        with patch.object(self.engine,'owned_pids',return_value={123456}), \
             patch.object(self.engine,'request_own_stop') as stop:
            self.engine.tick(BUSY,65)
            stop.assert_called_once()
        self.assertEqual(self.engine.state['status'],'PREEMPTING_OWN_STAGE')

    def test_preempted_child_waits_and_failure_blocks(self):
        self.engine.tick(IDLE,0);self.engine.tick(IDLE,60)
        self.engine.child.code=75
        self.engine.tick(IDLE,65)
        self.assertEqual(self.engine.state['status'],'WAITING_FOR_IDLE_GPU')
        self.engine.tick(IDLE,125);self.engine.tick(IDLE,185)
        self.engine.child.code=1
        self.engine.tick(IDLE,190)
        self.assertEqual(self.engine.state['status'],'ENGINEERING_NOT_READY')
        self.engine.tick(IDLE,250)
        self.assertEqual(len(self.spawned),2)

    def test_no_train_before_verified_smoke_outputs(self):
        self.engine.tick(IDLE,0);self.engine.tick(IDLE,60)
        self.engine.child.code=0
        self.engine.tick(IDLE,65)
        self.assertEqual(self.engine.state['status'],'ENGINEERING_NOT_READY')
        self.assertEqual(len(self.spawned),1)

    def test_success_atomic_seal_and_restart_skip_only_verified(self):
        evidence=self.root/'evidence';evidence.write_text('validated')
        rp=self.root/'smoke.json';self.engine.config['reports']['smoke']=str(rp)
        self.engine.tick(IDLE,0);self.engine.tick(IDLE,60)
        atomic_json(rp,{'stage':'smoke','status':'PASS','inputs':self.config['inputs'],
                        'attempt':self.engine.attempt,'outputs':{str(evidence):sha256(evidence)}})
        self.engine.child.code=0;self.engine.tick(IDLE,65)
        self.assertEqual(self.engine.pending_stage(),'train')
        self.engine.close()
        self.engine=runner.Runner(self.path,query=lambda:IDLE,space_check=lambda:True)
        self.assertEqual(self.engine.pending_stage(),'train')
        evidence.write_text('corrupt')
        self.assertEqual(self.engine.pending_stage(),'smoke')

    def test_live_owned_cpu_child_adoption_and_safe_stop(self):
        self.engine.close()
        self.config['stage_commands']['smoke']=[sys.executable,'-c','import time; time.sleep(60)']
        self.config['reports']['smoke']=str(self.root/'report.json')
        atomic_json(self.path,self.config)
        self.engine=runner.Runner(self.path,query=lambda:IDLE,space_check=lambda:True)
        self.engine.tick(IDLE,0);self.engine.tick(IDLE,60)
        original=self.engine.child
        try:
            self.engine.close()
            self.engine=runner.Runner(self.path,query=lambda:IDLE,space_check=lambda:True)
            self.assertEqual(self.engine.state['status'],'ADOPTED_OWN_STAGE')
            self.assertEqual(self.engine.child.pid,original.pid)
            self.engine.tick(BUSY,65)
            original.wait(timeout=5)
            self.engine.tick(IDLE,70)
            self.assertEqual(self.engine.state['status'],'WAITING_FOR_IDLE_GPU')
        finally:
            if original.poll() is None:
                original.terminate();original.wait(timeout=5)


if __name__=='__main__':unittest.main(verbosity=2)
