from env import *
from partition import make_partition,pair_models
from evidence import acquire,ARMS
from collections import Counter

def save_partition(d,out,result,graph,e,source):
 out.mkdir(parents=True,exist_ok=True);js(out/'RESULT.json',result);np.savez_compressed(out/'CONDITIONAL_GRAPH.npz',**{k:v for k,v in graph.items() if isinstance(v,np.ndarray)})
 ids=np.unique(e['source_index']);total=np.zeros(len(ids));np.add.at(total,np.searchsorted(ids,e['source_index']),e['weight']);mass=np.zeros((len(ids),len(result['patches'])));ii=np.searchsorted(ids,graph['source_index'])
 for j in range(mass.shape[1]):np.add.at(mass[:,j],ii,graph['weight']*(graph['patch_membership'][:,j]>0))
 soft=np.divide(mass,total[:,None],out=np.zeros_like(mass),where=total[:,None]>0);assert (soft.sum(1)<=1+1e-12).all();unknown=1-soft.sum(1);np.savez_compressed(out/'SOURCE_ROLES.npz',source_index=ids,original_xyz=source['means'][ids],soft_patch=soft,unknown=unknown,total_visible_mass=total,all_scene_source_count=np.array(len(source['means'])),unlisted_role=np.array('UNKNOWN'))
 # Bipartite graph retains ALL original EWA source/pixel responsibility, including rejected candidates.
 np.savez_compressed(out/'SOURCE_PIXEL_GRAPH.npz',source_index=e['source_index'],query_row=e['conditional_row'],weight=e['weight'],conditional_valid=e['conditional_valid'],conditional_z=e['conditional_z'],conditional_sigma=e['conditional_sigma'],query_uv=e['query_uv'],side=e['side_offset'],qualified_csr_index=graph['csr_index'])
 with open(out/'SOURCE_ROLES.csv','w') as f:
  f.write('source_index,local_patch,soft_mass,unknown\n')
  for i,s in enumerate(ids):
   if soft.shape[1]:
    for j in range(soft.shape[1]):f.write(f'{s},{j},{soft[i,j]:.12g},{unknown[i]:.12g}\n')
   else:f.write(f'{s},-1,0,1\n')
 color=np.tile([140,140,140],(len(ids),1)).astype(float)
 for j in range(soft.shape[1]):color+=soft[:,j,None]*(np.array([240,60,40] if j==0 else [30,90,240])-140)
 with open(out/'SOURCE_ID_DIAGNOSTIC_POINTS.ply','w') as f:
  f.write('ply\nformat ascii 1.0\ncomment ORIGINAL SOURCE CENTERS diagnostic points NOT fitted surface or Gaussian replacement\nelement vertex '+str(len(ids))+'\nproperty float x\nproperty float y\nproperty float z\nproperty int source_index\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n')
  for i,s in enumerate(ids):f.write(' '.join([*(format(float(x),'.17g') for x in source['means'][s]),str(s),*(str(int(x)) for x in color[i])])+'\n')
 js(out/'PROVENANCE.json',dict(input_evidence=str(d),sha256=sha(d/'EVIDENCE.npz'),source=str(registry()[result['scene']]['model']),source_index_original=True,unlisted_all_scene_UNKNOWN=True,soft_not_probability_calibration=True,diagnostic_PLY_is_original_centers_not_surface=True));seal(out)

def execute():
 rd=ROOT/'round2';js(rd/'CODE_CONFIG_FREEZE.json',dict(code={p.name:sha(p) for p in CODE.glob('*.py')},protocol=sha(ROOT/'PROTOCOL_FREEZE.json')));allresults=[];cross=[];fail=[]
 for s in SCENES:
  try:
   state('ROUND2',round=2,completed_rounds=1,scene=s,status='RUNNING',children=[os.getpid()]);acquire(s,[AUX[s]],rd/'evidence');source=activate(read_ply(registry()[s]['model']))
   for ca in cases(s):
    if not ca['selection_valid']:continue
    for arm in ARMS:
     models=[]
     for v in [DEV[s],AUX[s]]:
      inp=(ROOT/'round1/scenes' if v==DEV[s] else rd/'evidence')/s/v/ca['case']/arm;out=rd/'models'/s/v/ca['case']/arm
      if (out/'SEAL.json').exists():checkseal(out);r=json.loads((out/'RESULT.json').read_text())
      else:
       e=npz(inp/'EVIDENCE.npz');base=json.loads((inp/'CENTER_BASELINE.json').read_text());r,g=make_partition(e,base,cam(s,v));r.update(scene=s,view=v,case=ca['case'],arm=arm,parent_id=ca['parent_id']);save_partition(inp,out,r,g,e,source)
      models.append(r);allresults.append(r);print(s,v,ca['case'],arm,r['model'],r['counts'],flush=True)
     pair=pair_models(*models);pair.update(scene=s,case=ca['case'],arm=arm,views=[DEV[s],AUX[s]]);cross.append(pair)
   del source
  except Exception as ex:
   import traceback;traceback.print_exc();js(rd/f'INVALID_{s}.json',dict(error=repr(ex)));fail.append(s)
 js(rd/'CROSS_VIEW.json',dict(pairs=cross));counts=dict(round=2,model_comparisons=len(allresults),local_by_arm={a:dict(Counter(r['model'] for r in allresults if r['arm']==a)) for a in ARMS},eligible_crossview_by_arm={a:sum(x['eligible'] for x in cross if x['arm']==a) for a in ARMS},cases=len(cross)//4,physical_primitives=0,failed_scenes=fail);js(rd/'COUNTS.json',counts);state('ROUND2_MODELS_MEASURED',round=2,status='INVALID' if fail else 'READY_FOR_PLOTS',children=[],round_counts=counts)
 if fail:raise SystemExit(1)
if __name__=='__main__':execute()
