import copy,json,subprocess
from pathlib import Path
import runtime as rt

def freeze():
 p=rt.ART/'PROTOCOL.json'
 if not p.exists():rt.atomic_json(p,json.loads((rt.EXP/'protocol.json').read_text()))
 if json.loads(p.read_text())!=json.loads((rt.EXP/'protocol.json').read_text()):raise RuntimeError('immutable protocol differs')
 prior=rt.ROOT/'artifacts/gaer_view_selection_v01/PREREGISTRATION.json';pre=json.loads(prior.read_text())
 data_path=rt.IMAGE/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json';data=json.loads(data_path.read_text());scenes={}
 protected=dict(pre['protected_before'])
 # Protect all imported and inherited stage evidence byte-for-byte, including mutable parent replay records.
 roots=[rt.ROOT/'experiments/gaer_attribution_capacity_v02',rt.ROOT/'experiments/gaer_view_selection_v01',rt.ROOT/'artifacts/gaer_attribution_capacity_v02',rt.ROOT/'artifacts/gaer_view_selection_v01']
 for root in roots:
  for q in root.rglob('*'):
   if q.is_file():protected[str(q)]=rt.sha(q)
 for old in [rt.ATTR,rt.CAP,Path('/home/u00134/3dgs_line/gaer_rgb_union_voting_v01')]:
  for q in (old/'artifacts').glob('*/results/REPRODUCTION*.json'):protected[str(q)]=rt.sha(q)
 for name,rec in pre['scenes'].items():
  for c in rec['cameras']:
   metadata=json.loads(Path(c['metadata_path']).read_text());matches=[(j,f) for j,f in enumerate(metadata['frames']) if Path(f['file_path']).stem==c['key']]
   if len(matches)!=1 or matches[0][0]!=c['metadata_index']:raise RuntimeError('exact metadata filename/index changed')
  arcs=[]
  for entry in data['scenes'][name]['arc']:
   c=copy.deepcopy(entry['camera']);c['width']=c['native_width'];c['height']=c['native_height']
   import math
   fx=c['width']/(2*math.tan(c['FoVx']/2));fy=c['height']/(2*math.tan(c['FoVy']/2));c['K']=[[fx,0,399.5],[0,fy,399.5],[0,0,1]]
   c.update(key=entry['key'],source_camera_hash=entry['source_camera_hash'],metadata_path=str(data_path),metadata_sha256=rt.sha(data_path),prior_exposure='GS/research seen exploratory visualization')
   c['camera_sha256']=rt.digest(c);arcs.append(c)
   cache=rt.IMAGE/'out/image_space_edge_foundation_v1/raw'/name/'arc'/entry['key']/'native.npz'
   if not cache.exists():raise RuntimeError('prior native camera/cache unavailable')
   protected[str(cache)]=rt.sha(cache)
  if len(arcs)!=33:raise RuntimeError('expected33 prior frames')
  scenes[name]=dict(rec,arc=arcs)
  protected[rec['model']]=rt.sha(rec['model'])
  if rt.sha(rec['model'])!=rec['model_sha256']:raise RuntimeError('model mismatch')
 for q in [data_path,prior,rt.ATTR/'artifacts/gaer_attribution_buffer_v01/instructions/GAER_agent_experiment_prompt.txt']:
  protected[str(q)]=rt.sha(q)
 for name in ['SHAPE','QUERY']:
  q=rt.CAP/'artifacts/gaer_attribution_capacity_v02'/('BUILD_'+name+'.json');b=json.loads(q.read_text());protected[str(q)]=rt.sha(q);protected[b['binary']]=rt.sha(b['binary'])
  if protected[b['binary']]!=b['binary_sha256']:raise RuntimeError('existing isolated binary differs')
 pin={}
 for line in (rt.OUT/'logs/CODEX.stderr.log').read_text().splitlines()[:15]:
  if line.startswith('model:'):pin['model']=line.split(':',1)[1].strip()
  if line.startswith('reasoning effort:'):pin['reasoning_effort']=line.split(':',1)[1].strip()
 if pin!={'model':'gpt-6.1-sol','reasoning_effort':'xhigh'}:raise RuntimeError('actual CLI model pin not proven')
 heads=dict(line.split(' ',1) for line in subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],cwd=rt.ROOT,text=True).splitlines())
 record=dict(protocol_sha256=rt.sha(p),scenes=scenes,protected_before=protected,heads_before=heads,actual_codex=pin,initial_source_hashes=rt.method_hashes(),utc=__import__('time').strftime('%Y-%m-%dT%H:%M:%SZ',__import__('time').gmtime()))
 dst=rt.ART/'INPUT_FREEZE.json'
 if dst.exists():return json.loads(dst.read_text())
 rt.atomic_json(dst,record);print('FROZEN',len(protected),'protected files',flush=True);return record

if __name__=='__main__':freeze()
