"""Bounded plain runner. Existing global F seal is verified and never rewritten."""
import argparse,subprocess,sys,json
from io_utils import *

def ready(kind):
 if kind=='evidence':
  folders=[OUT/s/'F'/f['key'] for s in CFG['scenes'] for f in frames(s,'F')]
 elif kind=='contributions':
  if not (OUT/'COMPLETENESS.json').exists():return False
  k=json.loads((OUT/'COMPLETENESS.json').read_text())['available_K'];folders=[OUT/s/'contributions'/('K'+str(k))/f['key'] for s in CFG['scenes'] for f in frames(s,'F')]
 elif kind=='selection':folders=[OUT/'F_SELECTION_SEAL']+[OUT/s/'assets' for s in CFG['scenes']]
 elif kind=='evaluation':folders=[OUT/s/'evaluation'/f['key'] for s in CFG['scenes'] for f in INPUTS['scenes'][s]['frames']]
 else:raise ValueError(kind)
 if not all((d/'SEAL.json').exists() for d in folders):return False
 for d in folders:verify(d)
 if kind=='selection':
  b=json.loads((OUT/'F_SELECTION_SEAL/bindings.json').read_text())
  assert b['normalization_sha256']==sha(OUT/'NORMALIZATION.json')
  for s in CFG['scenes']:assert b['scenes'][s]==sha(OUT/s/'assets/SEAL.json')
 return True

def stage(check=False):
 verify_s0();guard();prior=sha(OUT/'F_SELECTION_SEAL/SEAL.json') if (OUT/'F_SELECTION_SEAL/SEAL.json').exists() else None
 states={k:ready(k) for k in ['evidence','contributions','selection','evaluation']}
 if check:
  atomic(OUT/'RESUME_CHECK.json',dict(utc=utc(),ready=states,F_seal_sha256=prior,check_only=True,no_science_or_seal_mutation=True));print(json.dumps(states));return
 for kind,cmd in [('evidence',['run.py','evidence']),('contributions',['run.py','contributions']),('selection',['selection.py']),('evaluation',['evaluate.py'])]:
  if states[kind]:event('RESUME_VERIFIED_SKIP',completed_stage=kind);continue
  if kind=='evaluation' and not (OUT/'INDEPENDENT_CPU_AUDIT.json').exists():subprocess.run([sys.executable,'-B',str(ART/'code/audit.py')],check=True)
  subprocess.run([sys.executable,'-B',str(ART/'code'/cmd[0])]+cmd[1:],check=True)
  if prior and sha(OUT/'F_SELECTION_SEAL/SEAL.json')!=prior:raise RuntimeError('Existing F global seal changed')
 stage(check=True)
 for script in ['projection_audit.py','finalize.py','interpret.py','supplement.py','ledger.py']:
  subprocess.run([sys.executable,'-B',str(ART/'code'/script)],check=True)
 if prior:assert sha(OUT/'F_SELECTION_SEAL/SEAL.json')==prior
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');a=p.parse_args();stage(a.check_only)
