from env import *
if __name__=='__main__':
 review('00_scope_GO','GO仅用于输入核验与同相机校准。只用原arms/C和source；禁用core标签。两侧原GS责任不是表面认证，源最短轴不是法线。先三scene DEV原图/真实CPU源渲染/原C8线图，核raw字段及坐标，之后看图固定病例。若源RGB MAE>.02、alpha MAE>.02、有效depth相对p95>.15则对应视角贡献解释NO_GO；这些是CPU与封存render的一致性容差，不是几何准确率。没有强制拟合/分组后续许可。',[ROOT/'ROLLBACK_RECEIPT.json',BASE/'REGISTRY.json',JC/'renderer.py',JC/'format.py'])
 state('STAGE0_AUDIT',status='RUNNING',children=[os.getpid()]);js(ROOT/'ROLLBACK_BEFORE.json',rollback());reg=registry();sources={str(BASE/'REGISTRY.json'):sha(BASE/'REGISTRY.json')};rows={}
 for s in SCENES:
  guard();r=reg[s];p=Path(r['model']);assert sha(p)==r['model_sha256'];src=read_ply(p);a=activate(src);line=npz(linepath(s)/'gaussians.npz');mp=npz(JOINT/'scenes'/s/'model/GROUP_MAPPING.npz');merged=read_ply(JOINT/'scenes'/s/'model/merged_native.ply')
  assert len(src)=={'scan24':596467,'scan65':317817,'ficus':284835}[s];assert len(line['means'])=={'scan24':458490,'scan65':279616,'ficus':285956}[s]
  for k in src.dtype.names:assert np.array_equal(src[k],merged[k][:len(src)],equal_nan=True)
  assert np.array_equal(mp['source_index'][:len(src)],np.arange(len(src))) and np.all(mp['primitive_id'][:len(src)]==-1)
  paths=[p,JOINT/'scenes'/s/'model/GROUP_MAPPING.npz',JOINT/'scenes'/s/'model/merged_native.ply']+[linepath(s)/n for n in ['gaussians.npz','gaussians.ply','parents.json','SHARED_CONTROL_AND_SAMPLING.npz','LENGTH_AND_PARENT.npz','OBSERVATIONS.npz']]
  paths += [rawpath(s,v) for v in VIEWS[s]]
  for f in paths:assert f.exists(),f;sources[str(f)]=sha(f)
  out=ROOT/'scenes'/s/'stage0';out.mkdir(parents=True,exist_ok=True);v=DEV[s];c=cam(s,v);raw=npz(rawpath(s,v));assert raw['rgb'].dtype==np.float32 and raw['rgb'].shape==(c['height'],c['width'],3)
  result=render(a,c,[1]*3 if s=='ficus' else [0]*3,.3 if s=='ficus' else .0144);ink=activate(read_ply(linepath(s)/'gaussians.ply'));li=render(ink,c)['rgb']
  z=raw['median_camera_z'].squeeze();al=raw['alpha'].squeeze();valid=(z>.2)&np.isfinite(z)&(al>=.5)&(result['median_center_z']>.2)
  metrics=dict(rgb_mae=float(abs(result['rgb']-raw['rgb']).mean()),alpha_mae=float(abs(result['alpha']-al).mean()),center_vs_surface_relative_p95=float(np.percentile(abs(result['median_center_z'][valid]-z[valid])/z[valid],95)),native_valid_fraction=float(valid.mean()))
  metrics['engineering_calibration_go']=metrics['rgb_mae']<=.02 and metrics['alpha_mae']<=.02 and metrics['center_vs_surface_relative_p95']<=.15
  np.savez_compressed(out/'REFERENCE.npz',original_rgb=raw['rgb'],original_alpha=al,original_depth=z,source_rgb=result['rgb'],source_alpha=result['alpha'],source_median_center_z=result['median_center_z'],source_expected_center_z=result['expected_center_z'],C8_line=li)
  save(out/'original_rgb.png',raw['rgb']);save(out/'C8_line.png',li);panel(out/'REFERENCE.jpg',[('Frozen original RGB',raw['rgb']),('CPU source full SH',result['rgb']),('Original C8 line / X-RAY',li),('Source alpha',np.repeat(result['alpha'][...,None],3,2))],f'{s} {v} | ORIGINAL arms/C and source only','No core-selection inputs. CPU EWA is approximate; center depth is not native surface depth.',2)
  lm=npz(linepath(s)/'LENGTH_AND_PARENT.npz');obs=npz(linepath(s)/'OBSERVATIONS.npz');sh=npz(linepath(s)/'SHARED_CONTROL_AND_SAMPLING.npz');parents=json.loads((linepath(s)/'parents.json').read_text())
  rows[s]=dict(source_count=len(src),ink_count=len(line['means']),source_fields=list(src.dtype.names),filter_present='filter_3D' in src.dtype.names,raw_positive_inf=int(np.isposinf(src['opacity']).sum()),line_schema={k:list(x.shape) for k,x in line.items()},length_schema={k:list(x.shape) for k,x in lm.items()},observation_schema={k:list(x.shape) for k,x in obs.items()},shared_schema={k:list(x.shape) for k,x in sh.items()},parent_example=parents[:1] if isinstance(parents,list) else {k:str(v)[:200] for k,v in parents.items()},calibration=metrics,camera=c,source_type=r.get('source_type'),depth_condition=r.get('depth',r.get('depth_condition')),raw_fields={k:list(x.shape) for k,x in raw.items()},effective_scale_quantiles=np.quantile(np.sqrt(np.linalg.eigvalsh(a['covariance'])),[0,.5,.95,1],axis=0).tolist())
  js(out/'AUDIT.json',rows[s]);seal(out);print(s,metrics,flush=True)
 for f in list(JC.glob('*.py'))+[JC/'ewa.cpp',JOINT/'build/libjoint.so',ROOT.parent/'official_code_fix_v01/source/utils/sh_utils.py']:sources[str(f)]=sha(f)
 js(ROOT/'SOURCE_MANIFEST.json',dict(files=sources,allowed_assets='original A arms/C and raw source GS only; joint prefix for identity and renderer; no v02/mv01 labels'))
 js(ROOT/'INPUT_AUDIT.json',rows);state('STAGE0_COMPLETE',status='READY_FOR_REVIEW',children=[])
