"""Parent-owned scan24 entry; unchanged v09 numerical loop and complete competition."""
from runtime_io import *
import whole_runner as engine
import scan24_loader
import scan24_delivery
import argparse

original_grow=engine.grow
def load(c,guard):
 d=scan24_loader.load(c,guard);root=Path(c['unit_root'])/'scenes'/c['scene']
 js(root/'SEED_SELECTION_LEDGER.json',d['seed_ledger']);js(root/'CAMERA_READINESS.json',d['camera_receipt'])
 return d
def grow(d,c,*args,**kwargs):
 active=[s for s in c['seed_ids'] if d['seed_status'][s]=='READY'];cfg=dict(c,seed_ids=active)
 objects,events,version,status,contexts=original_grow(d,cfg,*args,**kwargs)
 failed={s:v for s,v in d['seed_status'].items() if v!='READY'}
 if failed:status=dict(status,status='PARTIAL',seed_not_run=failed)
 return objects,events,version,status,contexts
def run(c,path):
 engine.load=load;engine.grow=grow;engine.diagnostics=scan24_delivery.diagnostics
 return engine.run(c,path)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args();run(json.loads(Path(args.config).read_text()),args.config)
