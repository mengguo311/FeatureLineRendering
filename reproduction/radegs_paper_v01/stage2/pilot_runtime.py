"""Engineering controls for the single authorized pilot (not a scientific arm)."""
import json
from pathlib import Path
import signal
import time

import torch
from checkpointing import restore_checkpoint, save_checkpoint
from safety import atomic_json


def validate_pilot_arguments(args):
    config = json.loads(Path(args.pilot_config).read_text())
    expected = {'iterations':30000,'resolution':2,'lambda_distortion':100,
                'lambda_depth_normal':5,'regularization_from_iter':15001,
                'use_decoupled_appearance':True,'eval':False,'white_background':False}
    for key,value in expected.items():
        if getattr(args,key) != value:
            raise ValueError('paper-text pilot argument mismatch: '+key)
    if (Path(args.source_path).resolve() != Path(config['data']).resolve()
            or Path(args.model_path).resolve() != Path(config['model']).resolve()
            or args.start_checkpoint is not None):
        raise ValueError('only isolated scan24 data/model and verified resume are allowed')
    if config['scene'] != 'scan24' or config['automatic_scene_limit'] != 1:
        raise ValueError('pilot scope exceeded')


class PilotRuntime:
    def __init__(self, config_path):
        self.config = json.loads(Path(config_path).read_text())
        self.provenance = self.config['inputs']
        self.model_path = Path(self.config['model'])
        self.checkpoint = self.model_path/'restart.json'
        self.stop_requested = False
        signal.signal(signal.SIGTERM,self._request_stop)
        signal.signal(signal.SIGINT,self._request_stop)
        self.log = open(self.model_path/'iteration_loss.jsonl','a',buffering=1)

    def _request_stop(self, signum, frame):
        self.stop_requested = True

    def restore(self, model, options, cameras):
        if not self.checkpoint.exists():
            return 0,None
        iteration,names = restore_checkpoint(self.checkpoint,model,options,self.provenance)
        byname = {camera.image_name:camera for camera in cameras}
        stack = None if names is None else [byname[name] for name in names]
        print('Resuming complete verified checkpoint after iteration',iteration,flush=True)
        return iteration,stack

    def completed_step(self, iteration, model, stack, losses):
        record = {'iteration':iteration,'unix':time.time(),'geometry_active':iteration>15000,
                  'wd':100 if iteration>15000 else 0,'wn':5 if iteration>15000 else 0,
                  'points':len(model._xyz),**{k:float(v.detach()) for k,v in losses.items()}}
        self.log.write(json.dumps(record,allow_nan=False)+'\n')
        if iteration % 500 == 0 or iteration == 30000 or self.stop_requested:
            desc = save_checkpoint(self.checkpoint,model,iteration,
                                   None if stack is None else [c.image_name for c in stack],self.provenance)
            atomic_json(self.model_path/'training_progress.json',{
                'completed_iteration':iteration,'checkpoint':desc,'loss':record,
                'state':'PREEMPTED' if self.stop_requested else 'RUNNING',
                'scientificdone':False})
        if self.stop_requested:
            self.log.close()
            raise SystemExit(75)

    def finished(self, model):
        # Required also when resuming an already completed final checkpoint.
        model.save_ply(str(self.model_path/'point_cloud/iteration_30000/point_cloud.ply'))
        atomic_json(self.model_path/'train_complete.json',{
            'iterations':30000,'photo_iterations':15000,'geometry_iterations':15000,
            'inputs':self.provenance,'scientificdone':False,'unix':time.time()})
        self.log.close()
