from pathlib import Path
import subprocess,json,hashlib,os
R=Path('/home/u00134/3dgs_line/research_progress_summary_v1')
URL='git@github.com:mengguo311/FeatureLineRendering.git'
stages=[
('object_neighborhood_edge_control_v1','object-neighborhood-edge-control-v1','10e4aabaab2ffdc1d1d99e786e4b78eca8f45445'),
('object_neighborhood_edge_control_v2','object-neighborhood-edge-control-v2','abe73412cb828ad8c3b1fe83cf6f1d238a32d506'),
('edge_control_lego_chair_v1','edge-control-lego-chair-v1','cd4dc554bc406a2cc392a3d004e8d28338a33b4b'),
('edge_responsibility_lego_chair_v2','edge-responsibility-lego-chair-v2','f76fd00f03dc96a099a5ea1ff7935cb8ddb04f0e'),
('image_space_edge_foundation_v1','image-space-edge-foundation-v1','b2d562753de6759b1bb2d3ac2034b35dc080d025'),
('gaer_attribution_buffer_v01','gaer-attribution-buffer-v01','ee28fdce75b07a2cee5406e60f4be8014aa77336'),
('gaer_view_selection_v01','gaer-view-selection-v01','e682614a7fedcb529102f67efcf78f7905d3d519'),
('gaer_rgb_union_voting_v01','gaer-rgb-union-voting-v01','bea1bfc10ec1d2e58f7ffd8ac857a55ade95d8b3'),
('gaer_attribution_capacity_v02','gaer-attribution-capacity-v02','10bf025e3791cea8f4f2e30780ad3cec0681e323')]
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
assert git('status','--porcelain').decode().strip() in ['', '?? artifacts/research_progress_summary_v1/import_research_update.py']
heads=git('ls-remote',URL,'refs/heads/*').decode()
(R/'artifacts/research_progress_summary_v1/REMOTE_HEADS_BEFORE_UPDATE.txt').write_text(heads)
existing=git('sparse-checkout','list').decode().splitlines()
paths=[f'{kind}/{stage}' for stage,branch,sha in stages for kind in ['artifacts','experiments']]
subprocess.run(['git','-C',str(R),'sparse-checkout','set',*existing,*paths],check=True)
records=[]
for stage,branch,sha in stages:
 git('cat-file','-e',sha+'^{commit}')
 chosen=[p for p in [f'artifacts/{stage}',f'experiments/{stage}'] if git('ls-tree',sha,'--',p).strip()]
 subprocess.run(['git','-C',str(R),'restore','--source='+sha,'--staged','--worktree','--',*chosen],check=True)
 files=[]
 for line in git('ls-tree','-rl',sha,'--',*chosen).decode().splitlines():
  meta,path=line.split('\t');mode,kind,blob,size=meta.split();data=(R/path).read_bytes()
  assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob,path
  files.append({'path':path,'source_blob':blob,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 records.append({'stage':stage,'branch':branch,'source_commit':sha,'artifact_and_code_snapshot':True,'files':files,'count':len(files)})
 print(stage,len(files),sum(f['bytes'] for f in files),flush=True)
p=R/'artifacts/research_progress_summary_v1/IMPORTED_20261006_SNAPSHOTS.json'
p.write_text(json.dumps({'schema':'exact-git-blob-snapshot-v1','summary_base':'8deeb1d6f12ef813c4ff20cbd4992410311d92ba','mode':'separate experiment snapshots, not algorithm merge or rerun','stages':records,'stage_count':len(records),'file_count':sum(x['count'] for x in records)},ensure_ascii=False,indent=2)+'\n')
print('IMPORTED',len(records),'stages',sum(x['count'] for x in records),'files')
