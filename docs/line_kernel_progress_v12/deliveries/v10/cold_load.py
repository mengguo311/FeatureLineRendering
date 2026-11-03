"""Read v10 delivered ZIP bytes only. No fitting, rendering, pickle or server dependency.
Usage: python cold_load.py [scan24|scan65]
Requires existing NumPy. Extract all 8 ZIP parts together OR keep ZIPs beside this file.
Returned original_gaussians preserve the seven arrays; auxiliary model knots are world coordinates.
Auxiliary models explain grouping and MUST NOT be drawn as supported gap bridges.
"""
from pathlib import Path
import io,json,zipfile,sys
import numpy as np
ROOT='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103'
LATEST={'scan24':'units/unit_003/scenes/scan24/stages/R2_R4_R6_OFF_TRANSPORT_FINAL','scan65':'units/unit_011/scenes/scan65/stages/BASE_J_FINAL'}
class Package:
 def __init__(self,directory):
  self.files={};self.directory=Path(directory)
  for p in sorted(self.directory.glob('v10_assets_part*.zip')):
   with zipfile.ZipFile(p) as z:
    for n in z.namelist():
     if not n.startswith('PART_'):
      if n in self.files:raise ValueError('duplicate member '+n)
      self.files[n]=p
 def member(self,path):
  path=str(path)
  if path.startswith(ROOT+'/'):return 'v10/'+path[len(ROOT)+1:]
  return 'dependencies/'+path.lstrip('/') if path.startswith('/') else path
 def read(self,path):
  n=self.member(path)
  if n in self.files:
   with zipfile.ZipFile(self.files[n]) as z:return z.read(n)
  return (self.directory/n).read_bytes()
 def exists(self,path):return self.member(path) in self.files or (self.directory/self.member(path)).exists()
 def js(self,path):return json.loads(self.read(path))
 def npz(self,path):
  with np.load(io.BytesIO(self.read(path)),allow_pickle=False) as z:return {k:z[k] for k in z.files}
 def asset(self,scene):
  final=ROOT+'/'+LATEST[scene];unit='/'.join(final.split('/')[:final.split('/').index('scenes')]);c=self.js(unit+'/CONFIG.json');p=c['p'];g=self.npz(c['gaussians']);m=self.npz(final+'/MEMBERSHIP.npz');models={};visited=[]
  base=self.npz(c['carriers'])
  for j,gid in enumerate(base['carrier_id']):models[int(gid)]={'version':int(base['version'][j]),'knots_world':base['knots'][base['knot_offsets'][j]:base['knot_offsets'][j+1]],'rows':base['rows'][base['row_offsets'][j]:base['row_offsets'][j+1]],'source':c['carriers']}
  def restore(stage):
   if stage in visited:return
   visited.append(stage)
   if self.exists(stage+'/GROUPS.json'):
    gg=self.js(stage+'/GROUPS.json');parent=gg.get('unchanged_background')
    if parent:restore(parent)
   if self.exists(stage+'/MODELS.npz'):
    z=self.npz(stage+'/MODELS.npz')
    for j,gid in enumerate(z['group_id']):models[int(gid)]={'version':int(z['version'][j]),'knots_world':z['knots_p'][z['knot_offsets'][j]:z['knot_offsets'][j+1]]*p,'rows':z['rows'][z['row_offsets'][j]:z['row_offsets'][j+1]],'source':stage+'/MODELS.npz'}
   elif self.exists(stage+'/GROWTH_STATE.json'):
    st=self.js(stage+'/GROWTH_STATE.json')
    for gid,q in st.get('curves',{}).items():
     key=int(gid)
     if key in models:models[key].update(knots_world=np.asarray(q)*p,version=st.get('versions',{}).get(gid,models[key]['version']),source=stage+'/GROWTH_STATE.json')
  restore(final)
  ids=np.unique(m['edge_id'][m['edge_id']>=0]);missing=[int(i) for i in ids if int(i) not in models];assert not missing,missing
  np.testing.assert_array_equal(m['line_kernel_id'],np.arange(len(g['means'])));np.testing.assert_array_equal(m['primitive_id'],g['primitive_id'])
  order=np.argsort(m['edge_id'],kind='stable');labels=m['edge_id'][order];unique,starts=np.unique(labels,return_index=True);stops=np.r_[starts[1:],len(order)];member_rows={int(i):np.sort(order[a:b]) for i,a,b in zip(unique,starts,stops) if i>=0}
  row_errors=[int(gid) for gid in ids if not np.array_equal(np.sort(models[int(gid)]['rows']),member_rows[int(gid)])]
  # Old background row lists can retain absorbed members; final membership is authority.
  for gid in ids:models[int(gid)]['rows']=member_rows[int(gid)]
  return {'original_gaussians':g,'membership':m,'models':{int(i):models[int(i)] for i in ids},'background_model_row_refresh_ids':row_errors,'restored_stage_chain':visited,'p_world_per_normalized_unit':p}
if __name__=='__main__':
 scenes=sys.argv[1:] or ['scan24','scan65'];pkg=Package(Path(__file__).parent);receipt=[]
 for scene in scenes:
  a=pkg.asset(scene);m=a['membership'];receipt.append({'scene':scene,'original_rows':len(m['edge_id']),'assigned':int(np.sum(m['edge_id']>=0)),'unknown':int(np.sum(m['edge_id']<0)),'all_assigned_auxiliary_models':len(a['models']),'missing_auxiliary_models':0,'background_model_row_refresh_ids':a['background_model_row_refresh_ids'],'restored_stage_chain':a['restored_stage_chain'],'geometry_arrays':list(a['original_gaussians']),'knots_output_units':'world','read_only':True,'zip_member_bytes':True})
 print(json.dumps(receipt,ensure_ascii=False,indent=2))
