"""Pre-output bookkeeping only: pin allowed inputs and pose-only camera domain."""
import json,hashlib,subprocess
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from src.foundation import freeze_json
P=Path('artifacts/direct_curve_global_fit_probe');F=[1,14,27,41,53,67,79,93];C=[7,21,33,47,59,73,86,99]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=json.loads(Path('artifacts/adaptive_mass_layered_probe/INPUTS.json').read_text());b=json.loads(Path('out/curve_correspondence_foundation/config.json').read_text())
inputs=dict(F=F,C=C,scenes={})
for s,v in a['scenes'].items():
 box=np.array(b['scenes'][s]['eligibility']['box']);center=box.mean(0);cams={}
 for i in F+C:
  cam=dict(v['cameras'][str(i)]);old=b['scenes'][s]['cameras'][f'train_{i:03d}'];path=old['path'];h=sha(path);assert h==old['sha256'];cam.update(path=path,sha256=h);cams[str(i)]=cam
 assert sha(v['checkpoint']['path'])==v['checkpoint']['sha256']
 ids=sorted(F+C);poses=np.array([np.linalg.inv(cams[str(i)]['w2c']) for i in ids]);loc=poses[:,:3,3]-center;r=np.linalg.norm(loc,axis=1);u=loc/r[:,None];ang=np.degrees(np.arccos(np.clip(u@u.T,-1,1)));np.fill_diagonal(ang,np.inf)
 pairs=set()
 for j in range(16):
  k=int(np.argmin(ang[j]));
  if ang[j,k]<=20:pairs.add(tuple(sorted([j,k])))
 chosen=sorted(pairs,key=lambda jk:(ang[jk],ids[jk[0]],ids[jk[1]]))[:2];arcs=[]
 for j,k in chosen:
  ts=np.linspace(0,1,33);theta=np.radians(ang[j,k]);dirs=(np.sin((1-ts)*theta)[:,None]*u[j]+np.sin(ts*theta)[:,None]*u[k])/np.sin(theta)
  radius=(1-ts)*r[j]+ts*r[k];rotation=Slerp([0,1],Rotation.from_matrix(poses[[j,k],:3,:3]))(ts).as_matrix();frames=[]
  for n,t in enumerate(ts):
   pose=np.eye(4);pose[:3,:3]=rotation[n];pose[:3,3]=center+dirs[n]*radius[n];frames.append(dict(w2c=np.linalg.inv(pose).tolist(),native_K=cams[str(ids[j])]['native_K'],native_height=800,native_width=800,t=float(t)))
  arcs.append(dict(endpoints=[ids[j],ids[k]],angle=float(ang[j,k]),frames=frames))
 inputs['scenes'][s]=dict(checkpoint=v['checkpoint'],box=box.tolist(),center=center.tolist(),cameras=cams,arcs=arcs,distance_range=[float(r.min()),float(r.max())],eligible_neighbor_pairs=[[ids[j],ids[k],float(ang[j,k])] for j,k in sorted(pairs)])
freeze_json(P/'INPUTS.json',inputs)
# Opaque preservation inventory: omit TEST-named historical outputs explicitly.
files=subprocess.check_output(['git','ls-files','-z']).decode().split('\0');records={};excluded=[]
for f in files:
 if not f or f=='.gitignore':continue
 if 'test' in f.lower() and not f.startswith('tests/') and not f.endswith('.py'):excluded.append(f);continue
 if Path(f).is_file():records[f]=sha(f)
freeze_json(P/'PRESERVATION.json',dict(files=records,excluded_test_named=excluded))
refs=['/home/u00134/astra_next_direction_round1.txt','/home/u00134/astra_next_direction_round2.txt','/home/u00134/codex_astra_curve_correspondence_foundation_report.md','/home/u00134/codex_astra_multiscene_foundation_corrected_report.md','/home/u00134/codex_astra_adaptive_mass_layered_probe_report.md']+[f'artifacts/adaptive_mass_layered_probe/{n}' for n in ['GATES.json','G1_VISUAL_REVIEW.json','G1_CONTROL_SUMMARY.json','FIGURES.md']]
freeze_json(P/'FREEZE.json',dict(protocol_sha256=sha(P/'PROTOCOL.md'),inputs_sha256=sha(P/'INPUTS.json'),references={f:sha(f) for f in refs},base_head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()))
(P/'PROTOCOL.sha256').write_text(sha(P/'PROTOCOL.md')+'\n')
print('FROZEN',sha(P/'PROTOCOL.md'));print({s:[a['endpoints'] for a in d['arcs']] for s,d in inputs['scenes'].items()})
