import json,struct,hashlib,time
from pathlib import Path
import numpy as np
import demo,core
T=core.TASK
checks=[]
def check(name,condition,detail=None):
 assert condition,(name,detail);checks.append({'name':name,'pass':True,'detail':detail})
for row in json.loads((T/'SOURCE_FREEZE.json').read_text())['files']:check('unchanged_source:'+Path(row['path']).name,demo.sha(row['path'])==row['sha256'])
for f in ['ASSET_FREEZE.json','BALANCED_ASSET_FREEZE.json']:
 for row in json.loads((T/f).read_text())['files']:check('frozen_asset:'+Path(row['path']).name,demo.sha(row['path'])==row['sha256'])
scene_rows=[]
for scene in demo.SCENES:
 d=demo.OUT/scene;s=dict(np.load(d/'source_samples.npz'));raw=dict(np.load(d/'raw_gaussians.npz'));fused=dict(np.load(d/'fused_gaussians.npz'));balanced=dict(np.load(T/'results_v2'/scene/'balanced_gaussians.npz'));bpro=dict(np.load(T/'results_v2'/scene/'balanced_provenance.npz'))
 check(scene+':source_views_exact_build',set(s['source_view'].tolist())=={0,1,2});check(scene+':all_valid_marked_created',len(s['means'])==sum(int(np.load(d/(v+'_source_maps.npz'))['marked'].sum()-np.load(d/(v+'_source_maps.npz'))['invalid_depth_rejected'].sum()) for v in demo.BUILD));check(scene+':raw_means_exact_sample',np.array_equal(raw['means'],s['means']));check(scene+':balanced_no_sample_deleted',len(bpro['source_to_balanced_id'])==len(s['means']) and np.all(bpro['source_to_balanced_id']>=0))
 groupids=s['fused_id'];valid=np.flatnonzero(groupids>=0);order=valid[np.argsort(groupids[valid],kind='stable')];splits=np.split(order,np.flatnonzero(np.diff(groupids[order]))+1);maxdist=0.
 for members in splits:
  checkok=len(np.unique(s['source_view'][members]))==len(members)
  assert checkok
  for i in members:
   for j in members:
    dist=np.linalg.norm(s['means'][i]-s['means'][j])/min(s['pixel'][i],s['pixel'][j]);maxdist=max(maxdist,dist);assert dist<=2+1e-10
 check(scene+':groups_distinct_view_bounded',True,{'max_pair_distance_in_pixel_units':maxdist,'groups':len(splits)})
 cams=demo.cameras(scene)
 for vid,v in enumerate(demo.BUILD):
  ids=np.flatnonzero(s['source_view']==vid);im=np.ones((cams[v]['height'],cams[v]['width'],3),np.float32);uv=s['uv'][ids];sup=s['supported'][ids];counter=(s['votes'][ids]<0).any(1);colors=np.tile([.15,.4,.9],(len(ids),1));colors[counter]=[.85,.2,.2];colors[sup]=[.05,.55,.15];im[uv[:,1],uv[:,0]]=colors;demo.saveimage(d/(v+'_source_evidence_categories.png'),im)
 for name,a in [('raw',raw),('fused',fused),('balanced',balanced)]:
  check(scene+':'+name+':finite_spd',np.isfinite(a['means']).all() and np.isfinite(a['covariance']).all() and np.all(np.linalg.eigvalsh(a['covariance'])>0));check(scene+':'+name+':opacity_range',np.all((a['opacity']>0)&(a['opacity']<=.95+1e-7)))
  dd=d if name!='balanced' else T/'results_v2'/scene;f=dd/(name+'_gaussians.ply')
  with f.open('rb') as stream:
   lines=[]
   while True:
    line=stream.readline().decode('ascii');lines.append(line)
    if line=='end_header\n':break
   body=stream.read()
  number=int(next(x for x in lines if x.startswith('element vertex')).split()[-1]);check(scene+':'+name+':ply_count',number==len(a['means']));check(scene+':'+name+':ply_payload_size',len(body)==number*50)
  # verify no cropping of 3sigma projected footprints in the exact chosen novel arc
  arc=json.loads((d/'ARC_CAMERAS.json').read_text())['cameras'];minimum=1e9
  for c in arc:
   uv,z,S=core.project_cov(a['means'],a['covariance'],c);radius=3*np.sqrt(np.diagonal(S,axis1=1,axis2=2));minimum=min(minimum,float(np.min(uv-radius)),float(np.min(np.array([c['width']-1,c['height']-1])-uv-radius)));assert np.all(z>0)
  check(scene+':'+name+':arc_full_gaussian_framing',minimum>=0,{'minimum_footprint_margin_px':minimum})
 scene_rows.append({'scene':scene,'raw':len(raw['means']),'strict_fused':len(fused['means']),'balanced':len(balanced['means']),'source_samples':len(s['means']),'supported_samples':int(s['supported'].sum()),'source_missing_depth':sum(json.loads((d/'BUILD_SUMMARY.json').read_text())[v]['invalid_depth_rejected'] for v in demo.BUILD)})
demo.writejson(T/'TEST_LOGS/INTEGRATION_VALIDATION.json',{'checks_passed':len(checks),'checks':checks,'scene_counts':scene_rows});print(json.dumps({'passed':len(checks),'scenes':scene_rows},indent=2))
