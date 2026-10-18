from env import *
def main():
 assert not (R/'ITERATION_STATUS.json').exists();status('INPUT_AUDIT',children=[])
 review('00_INPUT_GO','GO仅允许检查v02冻结方法/全图/实际源码及原相机；新科学结果前冻结r01。新机制候选为相机一致竖直框架与可见截面瓶颈，非调K或旧阈值。', [V2/'HYPOTHESIS_FREEZE_ZH.md',V2/'REPORT_ZH.md',V2/'STAGE_A_GATE.json',V2/'STAGE_B_GATE.json'])
 js(R/'ROLLBACK_BEFORE.json',rollback());files={}
 for f in ['SOURCE_MANIFEST.json','REPLAY_DEPENDENCIES.json']:
  files.update(json.loads((V2/f).read_text())['files'])
 for p,h in files.items():assert sha(p)==h,p
 for p in [BASE/'CAM_SELECTION.json',*V2.glob('*.md'),V2/'CONFIG_FREEZE.json',V2/'STAGE_A_GATE.json',V2/'STAGE_B_GATE.json',V2/'RESULTS_MANIFEST.json',*Path('/home/u00134/3dgs_line/gaer_c2l50_8build_outside_in_v02/reproduction/radegs_c2l50_8build_outside_in_v02').glob('*.py')]:files[str(p)]=sha(p)
 for top in ['stageA','stageB','delivery']:
  for p in (V2/top).rglob('*'):
   if p.is_file():files[str(p)]=sha(p)
 js(R/'SOURCE_MANIFEST.json',dict(files=files));audit={}
 for s,r in reg().items():
  cameras=[c for c in r['cameras'] if c['view'] in r['build_views']];rr=np.asarray([c['extrinsic'] for c in cameras])[:,:3,:3];ev,Q=np.linalg.eigh(rr[:,0].T@rr[:,0]/len(rr));up=Q[:,0];up*=np.sign(up@(-rr[:,1].mean(0)));audit[s]=dict(up_proposal=up.tolist(),right_axis_eigenvalues=ev.tolist(),rms_degrees=float(np.degrees(np.arcsin(np.sqrt(max(ev[0],0))))),build_camera_ids=r['build_views'],uses_camera_poses_only=True,not_gravity_truth=True)
 js(R/'POSE_INPUT_AUDIT.json',audit)
 import urllib.request
 p=R/'literature';p.mkdir(exist_ok=True);url='https://sites.socsci.uci.edu/~ddhoff/1989-22-PartsExpTest.pdf'
 try:
  with urllib.request.urlopen(url,timeout=25) as f:b=f.read(8*2**20)
  assert b.startswith(b'%PDF');q=p/'PartsExpTest1989.pdf';q.write_bytes(b);subprocess.run(['pdftotext','-layout',str(q),str(q.with_suffix('.txt'))],check=True);access=dict(url=url,status='FULL_TEXT',sha256=sha(q))
 except Exception as e:access=dict(url=url,status='BLOCKED',reason=str(e))
 js(R/'SOURCES_ACCESS.json',dict(primary=access,original1984=dict(url='https://dspace.mit.edu/entities/publication/8be13635-4c2e-41bc-95f0-f267280ba370',status='abstract read; full PDF web429',not_claimed_full_read=True)))
 status('INPUT_AUDIT_COMPLETE',children=[],source_files=len(files));print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
