"""Single-scene durable supervisor. Standard library only; never imports CUDA.

The advisory flock excludes this user's duplicate runners, not other users.
Foreign contexts and failed queries trigger termination of our own group only.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from safety import (STAGES, IdleGate, archive_failure, atomic_json, is_idle,
                    next_stage, query_gpus, seal_stage, sha256, stage_conflict, verify_seal)


def process_identity(pid):
    try:
        path=Path('/proc')/str(pid)
        fields=(path/'stat').read_text().rsplit(')',1)[1].split()
        if fields[0]=='Z':return None
        return {'uid':path.stat().st_uid,'start_ticks':fields[19],'pgid':int(fields[2])}
    except (OSError,ValueError,IndexError):return None


class AdoptedChild:
    def __init__(self,pid,identity,report):
        self.pid,self.identity,self.report=pid,identity,Path(report)
    def poll(self):
        if process_identity(self.pid)==self.identity:return None
        # A successful stage writes its report atomically after checking outputs.
        return 0 if self.report.exists() else 75


class Runner:
    def __init__(self,config_path,spawn=subprocess.Popen,query=query_gpus,space_check=None):
        self.config_path=Path(config_path).resolve()
        self.config=json.loads(self.config_path.read_text())
        self.config_hash=sha256(self.config_path)
        c=self.config
        if c['scene']!='scan24' or c['automatic_scene_limit']!=1 or not c['engineering_ready']:
            raise ValueError('unauthorized scope or engineering not ready')
        self.directory=Path(c['state_dir']);self.directory.mkdir(parents=True,exist_ok=True)
        self.logdir=Path(c['log_dir']);self.logdir.mkdir(parents=True,exist_ok=True)
        self.lock=open(self.directory/'runner.lock','a')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close();raise
        self.spawn,self.query=spawn,query
        self.space_check=space_check or (lambda:shutil.disk_usage('/').free>=10*1024**3
                                         and shutil.disk_usage(self.directory).free>=30*1024**3)
        self.gate=IdleGate(c['stable_seconds'])
        self.child=None;self.gpu_lock=None;self.child_log=None;self.identity=None
        self.stop_time=None;self.selected=None;self.attempt=None;self.known_owned={}
        self.shutdown=False
        self.path=self.directory/'runner_state.json'
        previous=json.loads(self.path.read_text()) if self.path.exists() else None
        self.state={'status':'STARTING','stage':None,'scientificdone':False,
                    'runner_pid':os.getpid(),'config':str(self.config_path),'config_sha256':self.config_hash,
                    'selected_gpu_uuid':None,'child_pid':None}
        self.verify_preflight()
        if previous and previous.get('status')=='ENGINEERING_NOT_READY':
            self.state.update(status='ENGINEERING_NOT_READY',reason='previous failure requires review')
        elif previous and previous.get('child_pid'):
            pid=previous['child_pid'];ident=previous.get('child_identity')
            if ident and process_identity(pid)==ident and ident['uid']==os.getuid() and ident['pgid']==pid:
                if previous['config_sha256']!=self.config_hash:
                    raise ValueError('live previous child has different config')
                self.child=AdoptedChild(pid,ident,c['reports'][previous['stage']])
                self.identity=ident;self.selected=previous['selected_gpu_uuid']
                self.state.update(previous,runner_pid=os.getpid(),status='ADOPTED_OWN_STAGE')
                self.gpu_lock=open(self.directory/(self.selected+'.lock'),'a')
                fcntl.flock(self.gpu_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                self.attempt=previous.get('attempt')
        self.persist()

    def verify_preflight(self):
        if not json.loads(Path(self.config['preflight_report']).read_text())['passed']:
            raise ValueError('preflight not passed')
        if sha256(self.config_path)!=self.config_hash:
            raise ValueError('config changed')
        for path,digest in self.config['immutable_files'].items():
            if sha256(path)!=digest:raise ValueError('immutable file changed: '+path)
        if not self.space_check():raise ValueError('disk reserve not satisfied')

    def persist(self,**updates):
        self.state.update(updates,updated_unix=time.time())
        atomic_json(self.path,self.state)

    def pending_stage(self):
        verified={s:verify_seal(self.directory/(s+'.seal.json'),s,self.config['inputs']) for s in STAGES}
        return next_stage(verified)

    def owned_pids(self,sample):
        owned=set()
        if self.child is None:return owned
        candidates={self.child.pid}
        for gpu in sample or []:
            candidates.update(c['pid'] for c in gpu['contexts'])
        for pid in candidates:
            ident=process_identity(pid)
            if ident and ident['uid']==os.getuid() and ident['pgid']==self.child.pid:
                if pid==self.child.pid and self.identity and ident!=self.identity:continue
                owned.add(pid);self.known_owned[pid]=ident
        return owned

    def request_own_stop(self):
        if self.child is None:return
        # Never signal a reused PID/group. At least one known owned member must
        # still have its recorded UID, group and kernel start time.
        ident=process_identity(self.child.pid)
        safe=(ident is not None and ident==self.identity)
        safe=safe or any(process_identity(pid)==old for pid,old in self.known_owned.items())
        if safe:
            try:os.killpg(self.child.pid,signal.SIGTERM)
            except ProcessLookupError:pass

    def finish_child(self,code):
        stage=self.state['stage']
        if self.child_log:self.child_log.close();self.child_log=None
        if self.gpu_lock:self.gpu_lock.close();self.gpu_lock=None
        self.child=None;self.identity=None;self.known_owned={}
        if code==0 and self.stop_time is None:
            try:
                report_path=Path(self.config['reports'][stage])
                report=json.loads(report_path.read_text())
                if (report['status']!='PASS' or report['inputs']!=self.config['inputs']
                        or report['stage']!=stage or report.get('attempt')!=self.attempt):
                    raise ValueError('stage report mismatch')
                outputs=report['outputs']
                if not outputs or not all(sha256(p)==h for p,h in outputs.items()):
                    raise ValueError('stage output missing or changed')
                seal_stage(self.directory/(stage+'.seal.json'),stage,self.config['inputs'],[report_path,*outputs])
                self.persist(status='STAGE_SEALED',child_pid=None,returncode=code)
            except (OSError,KeyError,ValueError,TypeError) as exc:
                self.persist(status='ENGINEERING_NOT_READY',reason=str(exc),child_pid=None,returncode=code)
                archive_failure(self.path,self.directory/'failed_stages')
        elif code==75 or self.stop_time is not None:
            self.persist(status='WAITING_FOR_IDLE_GPU',reason='own stage stopped; resume verified checkpoint',
                         child_pid=None,returncode=code)
            archive_failure(self.path,self.directory/'preempted_stages')
        else:
            self.persist(status='ENGINEERING_NOT_READY',reason='stage exited unsuccessfully',
                         child_pid=None,returncode=code)
            archive_failure(self.path,self.directory/'failed_stages')
        self.stop_time=None;self.selected=None;self.gate=IdleGate(self.config['stable_seconds'])

    def tick(self,samples,now=None):
        now=time.monotonic() if now is None else now
        if self.state['status']=='ENGINEERING_NOT_READY':return
        if self.child:
            code=self.child.poll()
            if code is not None:
                self.finish_child(code);return
            if stage_conflict(samples,self.selected,self.owned_pids(samples)) or self.shutdown:
                if self.stop_time is None:
                    self.stop_time=now
                    self.request_own_stop()
                self.persist(status='PREEMPTING_OWN_STAGE',reason='foreign context, failed query or shutdown',gpu_snapshot=samples)
                if now-self.stop_time>180:
                    # Keep waiting rather than force-killing during checkpoint IO.
                    self.persist(reason='waiting for own safe exit; last durable checkpoint retained')
            else:
                self.persist(status='RUNNING',gpu_snapshot=samples)
            return
        stage=self.pending_stage()
        if stage is None:
            self.persist(status='PILOT_CHAIN_COMPLETE',stage=None,child_pid=None,
                         pilot_evaluation_verified=True,full_suite_completed=False)
            return
        if self.shutdown:return
        self.persist(status='WAITING_FOR_IDLE_GPU',stage=stage,child_pid=None,
                     selected_gpu_uuid=None,gpu_snapshot=samples)
        ready=self.gate.observe(samples,now)
        if not ready:return
        self.verify_preflight()
        for gpu in ready:
            if gpu not in self.config.get('allowed_gpu_uuids',ready):continue
            lock=open(self.directory/(gpu+'.lock'),'a')
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:lock.close();continue
            fresh=self.query()
            if not fresh or not any(g['uuid']==gpu and is_idle(g) for g in fresh):
                lock.close();self.gate=IdleGate(self.config['stable_seconds']);return
            self.gpu_lock=lock;self.selected=gpu
            env=os.environ.copy();env.update(self.config['runtime_env'])
            env['CUDA_VISIBLE_DEVICES']=gpu;env['PYTHONUNBUFFERED']='1'
            self.attempt=str(time.time_ns())
            env['RADEGS_ATTEMPT']=self.attempt
            logfile=self.logdir/(stage+'-'+self.attempt+'.log')
            self.child_log=open(logfile,'a')
            self.child=self.spawn(self.config['stage_commands'][stage],cwd=self.config['cwd'],env=env,
                                  stdout=self.child_log,stderr=subprocess.STDOUT,start_new_session=True)
            self.identity=process_identity(self.child.pid)
            self.persist(status='RUNNING',stage=stage,selected_gpu_uuid=gpu,child_pid=self.child.pid,
                         child_identity=self.identity,attempt=self.attempt,stage_log=str(logfile))
            return

    def close(self):
        if self.child_log:self.child_log.close()
        if self.gpu_lock:self.gpu_lock.close()
        self.lock.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    args=parser.parse_args();engine=Runner(args.config)
    def stop(signum,frame):engine.shutdown=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        while True:
            try:engine.tick(engine.query())
            except Exception as exc:
                if engine.child:
                    engine.shutdown=True;engine.request_own_stop()
                engine.persist(status='ENGINEERING_NOT_READY',reason=type(exc).__name__+': '+str(exc))
                archive_failure(engine.path,engine.directory/'failed_stages')
                raise
            if engine.state['status'] in ('PILOT_CHAIN_COMPLETE','ENGINEERING_NOT_READY'):break
            if engine.shutdown and engine.child is None:break
            time.sleep(5 if engine.child else engine.config['poll_seconds'])
    finally:engine.close()


if __name__=='__main__':main()
