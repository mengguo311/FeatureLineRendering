from env import *
import urllib.request

def main():
 state('RESEARCH_PREFLIGHT')
 review('00_scope_GO','GO：仅研究、只读来源审计、原图查看及主体候选的预注册。尚未运行新分割结果。原线仅A原C8，不读核心线标签。完整主体资格优先；任何失败场景停止正式下层。', [ROOT/'PROMPT.txt'])
 js(ROOT/'ROLLBACK_BEFORE.json',rollback())
 literature=ROOT/'literature';literature.mkdir(exist_ok=True)
 urls={'arbelaez2011':'https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/papers/amfm_pami2010.pdf','gaussian_grouping2024':'https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/04195.pdf','ownership2000':'https://www.jneurosci.org/content/jneuro/20/17/6594.full.pdf'}
 access=[]
 for name,url in urls.items():
  p=literature/(name+'.pdf')
  try:
   request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(request,timeout=40) as r:
    b=r.read(25*2**20);assert b.startswith(b'%PDF');p.write_bytes(b)
   subprocess.run(['pdftotext','-layout',str(p),str(p.with_suffix('.txt'))],check=True)
   access.append(dict(name=name,url=url,status='FULL_PDF',sha256=sha(p),text_sha256=sha(p.with_suffix('.txt'))))
  except Exception as e:access.append(dict(name=name,url=url,status='BLOCKED',error=str(e)))
 js(literature/'ACCESS.json',access)
 paths=[BASE/'REGISTRY.json'];rows={}
 for s in SCENES:
  reg=registry()[s];p=Path(reg['model']);assert sha(p)==reg['model_sha256'];paths.append(p)
  line=npz(linepath(s)/'gaussians.npz');n=len(line['means']);assert n=={'scan24':458490,'scan65':279616,'ficus':285956}[s]
  for name in ['gaussians.npz','gaussians.ply','parents.json','SHARED_CONTROL_AND_SAMPLING.npz','LENGTH_AND_PARENT.npz']:paths.append(linepath(s)/name)
  rows[s]=dict(model=str(p),model_sha256=sha(p),line_count=n,views={})
  for v in [DEV[s],AUX[s],*RESERVED[s]]:
   raw=rawpath(s,v);paths.append(raw);d=npz(raw);c=cam(s,v);rgb=d['rgb'];z=d['median_camera_z'].squeeze();alpha=d['alpha'].squeeze();assert rgb.shape==(c['height'],c['width'],3) and rgb.dtype==np.float32
   good=np.isfinite(z)&(z>.2)&(alpha>.5)
   rows[s]['views'][v]=dict(shape=list(rgb.shape),rgb_dtype=str(rgb.dtype),fx=c['fx'],fy=c['fy'],cx=c['cx'],cy=c['cy'],alpha_quantiles=np.quantile(alpha,[0,.1,.5,.9,1]).tolist(),depth_quantiles_diagnostic_only=np.quantile(z[good],[0,.1,.5,.9,1]).tolist(),depth_valid=int(good.sum()),keys=list(d))
  save(ROOT/'inputs'/(s+'_DEV_RGB.png'),npz(rawpath(s,DEV[s]))['rgb'])
 for d in [JC,GC]:paths.extend(sorted(d.glob('*.py')))
 for name in ['c2l50_8build_region_closure_v01','c2l50_8build_surface_partition_v01']:
  paths.append(ROOT.parent/name/'REPORT_ZH.md')
 js(ROOT/'INPUT_AUDIT.json',rows);js(ROOT/'SOURCE_MANIFEST.json',dict(files={str(p):sha(p) for p in sorted(set(paths))}))
 js(ROOT/'RESOURCE_START.json',guard());state('PREFLIGHT_COMPLETE')
if __name__=='__main__':main()
