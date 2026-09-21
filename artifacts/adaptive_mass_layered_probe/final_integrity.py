"""Final bookkeeping audit: immutable inputs, preserved history and exact command logs."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];art=ROOT/'artifacts/adaptive_mass_layered_probe';out=ROOT/'out/adaptive_mass_layered_probe'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
checks={};protocol=(art/'PROTOCOL.md').read_text();checks['protocol']=sha(art/'PROTOCOL.md')==(art/'PROTOCOL.sha256').read_text().strip()
checks['g1_freeze']=sha(art/'G1_IMPLEMENTATION.md')==(art/'G1_IMPLEMENTATION.sha256').read_text().split()[0]
for name,h in re.findall(r'([A-Z_]+\.(?:json|md)) SHA256: `([a-f0-9]{64})`',protocol):checks['frozen:'+name]=sha(art/name)==h
base=json.loads((art/'BASE_TRACKED.json').read_text());checks['base_tracked']=all(sha(ROOT/p)==h for p,h in base.items());print('base tracked',len(base),checks['base_tracked'],flush=True)
preserved=json.loads((art/'PRESERVED_FIXED_K.json').read_text());checks['fixed_k']=all(sha(p)==h for p,h in preserved.items())
attempt=json.loads((art/'ATTEMPT_01.json').read_text())['files'];checks['archived_attempt']=all(sha(out/'attempt_01_layer_tie'/p)==h for p,h in attempt.items())
cfg=json.loads((art/'INPUTS.json').read_text());checks['checkpoints']=all(sha(d['checkpoint']['path'])==d['checkpoint']['sha256'] for d in cfg['scenes'].values());checks['source_config']=sha(cfg['source_config'])==cfg['source_config_sha256']
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
checks['HEAD']=head=='062d7ce73a740e1a817c82e57e516b395e45f417';checks['branch']=branch=='adaptive-mass-layered-line-probe';checks['tracked_diff_empty']=not subprocess.check_output(['git','diff','HEAD','--name-only'],cwd=ROOT,text=True).strip()
journal=sorted(map(json.loads,(art/'TDD.jsonl').read_text().splitlines()),key=lambda x:x['sequence']);logs={r['output']:sha(ROOT/r['output'])==r['output_sha256'] and hashlib.sha256(json.dumps(r['command']).encode()).hexdigest()==r['command_sha256'] for r in journal};checks['journal_integrity']=all(logs.values());checks['journal_protocol']=all(r['protocol_sha256']==sha(art/'PROTOCOL.md') for r in journal);checks['unique_sequences']=len({r['sequence'] for r in journal})==len(journal)
pairs={}
for r in journal:
 if r['phase'] in ['RED','GREEN']:pairs.setdefault(r['label'],[]).append(r)
tdd={}
for label,rs in pairs.items():
 red=next(r for r in reversed(rs) if r['phase']=='RED' and all(t not in (ROOT/r['output']).read_text() for t in ['SyntaxError','IndentationError']));green=rs[-1]
 tdd[label]=dict(red_sequence=red['sequence'],green_sequence=green['sequence'],passed=red['exit_code']!=0 and green['phase']=='GREEN' and green['exit_code']==0 and red['finished_utc']<=green['started_utc'])
checks['vertical_tdd']=all(x['passed'] for x in tdd.values())
visuals={}
for stage in ['G0','G1']:
 review=json.loads((art/(stage+'_VISUAL_REVIEW.json')).read_text());visuals[stage]=review
checks['g1_all_figures_inspected']=all(x['status'].startswith('INSPECTED') and sha(out/'g1_run'/p)==x['sha256'] for p,x in visuals['G1']['figures'].items())
checks['g1_stop']=visuals['G1']['decision']=='NO_GO' and visuals['G1']['scene_go_count']==0 and not any((out/p).exists() for p in ['g2_run','g3_run'])
sources={str(p.relative_to(ROOT)):sha(p) for folder in ['src','scripts','tests'] for p in (ROOT/folder).glob('*adaptive*') if p.is_file()}
binaries={str(p.relative_to(ROOT)):sha(p) for p in (out/'setup').glob('*.so')}
result=dict(passed=all(checks.values()),checks=checks,head=head,branch=branch,preserved_fixed_k_files=len(preserved),preexisting_tracked_files=len(base),archived_attempt_files=len(attempt),journal_entries=len(journal),journal=logs,tdd=tdd,sources=sources,binaries=binaries,bookkeeping_scope='Opaque byte hashes include historical TEST-named tracked artifacts disclosed in BOOKKEEPING_SCOPE.json. No semantic decoding or scientific use.',scope='Final integrity of frozen inputs/history/code/journal; full scientific array and native-access checks are in VERIFICATION.json and G1_VERIFICATION.json.')
(art/'FINAL_INTEGRITY.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['sources','binaries','journal','tdd']},indent=2));raise SystemExit(0 if result['passed'] else 1)
