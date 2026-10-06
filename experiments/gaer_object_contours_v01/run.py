"""Resumable exactly-two-view development slice before frozen evaluation."""
import json,sys
import runtime as rt
from adapter import scene_io
from pipeline import run_view

def main():
 config=json.loads((rt.ART/'PROTOCOL.json').read_text());f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());p=rt.ART/'DEV_RUN_FREEZE.json'
 if not p.exists():rt.atomic_json(p,dict(protocol_sha256=rt.sha(rt.ART/'PROTOCOL.json'),input_freeze_sha256=rt.sha(rt.ART/'INPUT_FREEZE.json'),source_hashes=rt.method_hashes(),role='DEV r_7/r_33 only, both scenes'))
 freeze=json.loads(p.read_text())
 for q,h in freeze['source_hashes'].items():
  if rt.sha(rt.ROOT/q)!=h:raise RuntimeError('DEV source changed '+q)
 digest=rt.digest(freeze)
 for name in config['scenes']:
  rt.guard(name+'_load');record=f['scenes'][name];model=scene_io.load_model(record)
  for key in config['roles']['dev']:
   c=next(c for c in record['cameras'] if c['key']==key);run_view(name,c,record,config,digest,model)
  del model

if __name__=='__main__':main()
