from env import *
from evidence import acquire,ARMS
from responsibility import ProjectedSource
from validation import ordering_diagnostic,evaluate_models,alln_roi
from collections import Counter

def parallax(s,case,view):
 X=np.mean(npz(linepath(s)/'gaussians.npz')['means'][case['child_ids']],axis=0);d=[]
 for v in [DEV[s],AUX[s],view]:
  E=np.asarray(cam(s,v)['extrinsic']);O=-E[:3,:3].T@E[:3,3];r=X-O;d.append(r/np.linalg.norm(r))
 return dict(dev_to_reserved_deg=float(np.degrees(np.arccos(np.clip(d[0]@d[2],-1,1)))),aux_to_reserved_deg=float(np.degrees(np.arccos(np.clip(d[1]@d[2],-1,1)))),dev_aux_deg=float(np.degrees(np.arccos(np.clip(d[0]@d[1],-1,1)))))

def run():
 rd=ROOT/'round3';js(rd/'CODE_CONFIG_FREEZE.json',dict(code={p.name:sha(p) for p in CODE.glob('*.py')},protocol=sha(ROOT/'PROTOCOL_FREEZE.json')));records=[];failed=[]
 for s in SCENES:
  try:
   state('ROUND3_RESERVED_FALSIFICATION',round=3,completed_rounds=2,scene=s,status='RUNNING',children=[os.getpid()]);acquire(s,RESERVED[s],rd/'evidence');a=activate(read_ply(registry()[s]['model']))
   for v in RESERVED[s]:
    c=cam(s,v);proj=ProjectedSource.from_asset(a,c,s)
    for ca in cases(s):
     if not ca['selection_valid']:continue
     for arm in ARMS:
      inp=rd/'evidence'/s/v/ca['case']/arm;out=rd/'validation'/s/v/ca['case']/arm;out.mkdir(parents=True,exist_ok=True)
      if (out/'SEAL.json').exists():checkseal(out);records.append(json.loads((out/'RESULT.json').read_text()));continue
      e=npz(inp/'EVIDENCE.npz');base=json.loads((inp/'CENTER_BASELINE.json').read_text());arrays,r=ordering_diagnostic(e,a,proj,base['info']['pixel_world_proxy']);r.update(scene=s,view=v,case=ca['case'],arm=arm,parent=ca['parent_id'],all_N_roi=alln_roi(proj,e),frozen_patch_validation=evaluate_models(s,ca['case'],arm,v,e,base),parallax=parallax(s,ca,v),input_sha256=sha(inp/'EVIDENCE.npz'));np.savez_compressed(out/'ORDERING_COUNTERFACTUAL.npz',**arrays,original_source_index=e['source_index'],csr_offsets=e['csr_offsets'],query_uv=e['query_uv']);js(out/'RESULT.json',r);seal(out);records.append(r);print(s,v,ca['case'],arm,'L1',r['mean_responsibility_L1'],'depth',r['old_conditional_native_error_p'],'->',r['reordered_conditional_native_error_p'],r['source_visibility_counts'],flush=True)
   del a
  except Exception as ex:
   import traceback;traceback.print_exc();js(rd/f'INVALID_{s}.json',dict(error=repr(ex)));failed.append(s)
 counts=dict(round=3,measurements=len(records),frozen_patch_states_by_arm={arm:dict(Counter(z['state'] for r in records if r['arm']==arm for z in r['frozen_patch_validation'])) for arm in ARMS},visibility_line_by_scene={s:dict(sum((Counter(r['source_visibility_counts']) for r in records if r['scene']==s and r['arm']=='line'),Counter())) for s in SCENES},all_N_ROI_pixels=sum(r['all_N_roi']['count'] for r in records),physical_primitives=0,failed_scenes=failed)
 js(rd/'COUNTS.json',counts);state('ROUND3_MEASURED',round=3,status='INVALID' if failed else 'READY_FOR_PLOTS',children=[],round_counts=counts)
 if failed:raise SystemExit(1)
if __name__=='__main__':run()
