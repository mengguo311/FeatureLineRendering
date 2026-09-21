"""Hash the finished delivery and validate every final command record."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];art=ROOT/'artifacts/adaptive_mass_layered_probe';out=ROOT/'out/adaptive_mass_layered_probe'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
read=lambda p:json.loads(p.read_text())
g0=read(art/'VERIFICATION.json');g1=read(art/'G1_VERIFICATION.json');integrity=read(art/'FINAL_INTEGRITY.json');access=read(art/'FINAL_ACCESS_AUDIT.json');gates=read(art/'GATES.json');assert all(d['passed'] for d in [g0,g1,integrity,access]);assert gates['G1']=='NO_GO'
rs=sorted(map(json.loads,(art/'TDD.jsonl').read_text().splitlines()),key=lambda r:r['sequence']);journal={str(r['sequence']):sha(ROOT/r['output'])==r['output_sha256'] and hashlib.sha256(json.dumps(r['command']).encode()).hexdigest()==r['command_sha256'] for r in rs};assert all(journal.values())
science={}
for run,files in g0['comparison']['hashes'].items():science.update({str(out.relative_to(ROOT)/run/p):h for p,h in files.items()})
for run,files in g1['hashes'].items():science.update({str(out.relative_to(ROOT)/run/p):h for p,h in files.items()})
figures={}
for p in sorted(out.glob('g1_*/figures/*.png'))+sorted(out.glob('g1_*/diagnostics/*.png')):
 b=p.open('rb').read(24);assert b[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',b[16:24]);expected=(3200,6752) if p.parent.name=='diagnostics' else ((3200,844) if p.name.endswith('_RGB.png') else (16000,5064));assert (w,h)==expected;figures[str(p.relative_to(ROOT))]=[w,h]
assert len(figures)==136
proofs={str(p.relative_to(ROOT)):sha(p) for p in sorted(art.rglob('*')) if p.is_file() and p.name!='FINAL_SEAL.json'}
for folder in ['src','scripts','tests']:
 for p in sorted((ROOT/folder).glob('*adaptive*')):
  if p.is_file():proofs[str(p.relative_to(ROOT))]=sha(p)
for p in sorted(out.rglob('*')):
 if p.is_file() and str(p.relative_to(ROOT)) not in science:proofs[str(p.relative_to(ROOT))]=sha(p)
report=Path('/home/u00134/codex_astra_adaptive_mass_layered_probe_report.md');proofs[str(report)]=sha(report)
result=dict(passed=True,scope='Final journal and delivery hashes. Scientific file hashes are taken from successful full independent verification; other output/proof/code/report bytes are hashed here. FINAL_SEAL excludes itself.',journal_entries=len(rs),journal=journal,proof_sha256=proofs,verified_scientific_sha256=science,scientific_files=len(science),g1_png_dimensions=figures,all_scientific_byte_and_array_reruns=True,decoded_official_pngs=g0['comparison']['decoded_pngs']+g1['decoded_pngs'],final_gates={k:gates[k] for k in ['G0','G1','G2','G3','chosen_kmax','execution_audit']})
(art/'FINAL_SEAL.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['proof_sha256','verified_scientific_sha256','g1_png_dimensions','journal']},indent=2))
