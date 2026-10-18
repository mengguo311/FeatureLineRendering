from env import *
import urllib.request
def main():
 state('PREFLIGHT');review('00_scope_GO','GO：只读审计v01、原C8/source/native缓存及文献；无新分割结果。先分清主体归属错误与独立切块后配对错误。拟采用共同3D可见深度样本，不能用GS中心/核ID作为物理部件。', [V1/'OUTLINE_ZH.md',V1/'REPORT_ZH.md',V1/'STAGE_A_GATE.json',V1/'STAGE_B_GATE.json'])
 js(ROOT/'ROLLBACK_BEFORE.json',rollback());paths=[]
 for d in [V1CODE,JC]:paths+=sorted(d.glob('*.py'))
 for f in ['OUTLINE_ZH.md','REPORT_ZH.md','STAGE_A_GATE.json','STAGE_B_GATE.json','CONFIG_FREEZE.json','SOURCE_MANIFEST.json','RENDERER_AUDIT.json','VERIFY_REPLAY.json']:paths.append(V1/f)
 paths.append(BASE/'REGISTRY.json');audit={}
 for s in SCENES:
  reg=registry()[s];p=Path(reg['model']);assert sha(p)==reg['model_sha256'];paths.append(p);ln=BASE/'arms/C/scenes'/s/'full';line=npz(ln/'gaussians.npz');assert len(line['means'])=={'scan24':458490,'scan65':279616,'ficus':285956}[s]
  paths += [ln/f for f in ['gaussians.npz','gaussians.ply','parents.json','SHARED_CONTROL_AND_SAMPLING.npz','LENGTH_AND_PARENT.npz']]
  rows=[]
  for v in views(s):
   p=rawpath(s,v);paths.append(p);rgb,z,a=raw(s,v);c=cam(s,v);assert rgb.dtype==np.float32 and rgb.shape==(c['height'],c['width'],3)
   for f in ['REFERENCE.npz','SUBJECT.npz','CALIBRATION.json','SEAL.json']:paths.append(V1/'stageA'/s/v/f)
   if s=='ficus':
    for f in ['rgb_only.npz','rgb_depth.npz','COUNTS.json','SEAL.json']:paths.append(V1/'stageB'/s/v/f)
   uv=np.array([[c['cx'],c['cy']],[.25*c['width'],.33*c['height']]]);zz=np.ones(2)*3;u2,z2=projection(unproject(uv,zz,c),c);assert np.allclose(u2,uv,atol=1e-9) and np.allclose(z2,zz,atol=1e-9)
   good=np.isfinite(z)&(z>.2)&(a>=.5);rows.append(dict(view=v,shape=list(rgb.shape),fx=c['fx'],fy=c['fy'],cx=c['cx'],cy=c['cy'],valid=int(good.sum()),alpha_fraction=float((a>.5).mean()),condition='native RaDe camera-z' if s!='ficus' else 'vanilla GS CPU plane camera-z proxy'))
  audit[s]=dict(source=str(p),model=reg['model'],model_sha256=reg['model_sha256'],line_count=len(line['means']),views=rows)
 js(ROOT/'INPUT_AUDIT.json',audit);js(ROOT/'SOURCE_MANIFEST.json',dict(files={str(p):sha(p) for p in sorted(set(paths))}))
 lit=ROOT/'literature';lit.mkdir(exist_ok=True);access=[]
 for name,url in [('vccs2013','https://openaccess.thecvf.com/content_cvpr_2013/papers/Papon_Voxel_Cloud_Connectivity_2013_CVPR_paper.pdf'),('graphseg2004','https://www.cs.cornell.edu/~dph/papers/seg-ijcv.pdf')]:
  p=lit/(name+'.pdf')
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=40) as r:b=r.read(16*2**20)
   assert b.startswith(b'%PDF');p.write_bytes(b);subprocess.run(['pdftotext','-layout',str(p),str(p.with_suffix('.txt'))],check=True);access.append(dict(name=name,url=url,status='FULL_TEXT',sha256=sha(p)))
  except Exception as e:access.append(dict(name=name,url=url,status='BLOCKED',reason=str(e)))
 js(ROOT/'SOURCES_ACCESS.json',access);state('PREFLIGHT_COMPLETE',children=[])
if __name__=='__main__':main()
