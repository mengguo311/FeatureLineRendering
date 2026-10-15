from common import *
from format import *
from renderer import render
def errors(a,b):
 return dict(means_max_abs=float(abs(a['means']-b['means']).max(initial=0)),covariance_max_relative_frobenius=float((np.linalg.norm(a['covariance']-b['covariance'],axis=(1,2))/np.maximum(np.linalg.norm(a['covariance'],axis=(1,2)),1e-30)).max(initial=0)),opacity_max_abs=float(abs(a['opacity']-b['opacity']).max(initial=0)))
def export(scene):
 guard();start=time.monotonic();out=ROOT/'scenes'/scene/'model';out.mkdir(parents=True,exist_ok=True)
 if (out/'SEAL.json').exists():
  seal=json.loads((out/'SEAL.json').read_text())
  for name,h in seal['files'].items():assert sha(out/name)==h
  return json.loads((out/'AUDIT.json').read_text())
 reg=registry()[scene];s=read_ply(reg['model']);l=read_ply(line_dir(scene)/'gaussians.ply');n=len(s);nl=len(l)
 with np.load(line_dir(scene)/'gaussians.npz') as z:line={k:z[k].copy() for k in z.files}
 assert nl==len(line['means']);mp=mapping(n,line);m=merge_native(s,l);extra=[(k,'u1' if k=='group_id' else '<i4') for k in ['group_id','source_index','line_index','internal_piece_id'] if k not in m.dtype.names];outm=np.zeros(len(m),list(m.dtype.descr)+extra)
 for k in m.dtype.names:outm[k]=m[k]
 for k in ['group_id','source_index','line_index','internal_piece_id']:outm[k]=mp[k]
 outm['primitive_id'][:n]=-1;outm['arc_t'][:n]=-1
 write_ply(out/'merged_native.ply',outm);p,ps=portable(outm);write_ply(out/'merged_portable.ply',p);np.savez_compressed(out/'GROUP_MAPPING.npz',**mp)
 del m,outm,p
 m=read_ply(out/'merged_native.ply');p=read_ply(out/'merged_portable.ply')
 for k in s.dtype.names:assert m[k][:n].tobytes()==s[k].tobytes(),k
 for k in l.dtype.names:assert m[k][n:].tobytes()==l[k].tobytes(),k
 for k in [k for k in s.dtype.names if k.startswith(('f_dc_','f_rest_'))]:assert p[k][:n].tobytes()==s[k].tobytes(),k
 act=activate(m);eff=activate(p);pe=errors(act,eff);assert pe['means_max_abs']==0 and pe['covariance_max_relative_frobenius']<3e-6 and pe['opacity_max_abs']<2e-7
 la={k:a[n:] for k,a in act.items()};le=errors(la,line);lc=np.maximum(0,la['SH'][:,:,0]*.28209479177387814+.5);le['black_color_max_abs']=float(abs(lc-line['colors']).max());assert le['means_max_abs']<2e-6 and le['covariance_max_relative_frobenius']<3e-6 and le['opacity_max_abs']<1e-7 and le['black_color_max_abs']<1e-7,le
 assert np.linalg.eigvalsh(act['covariance']).min()>0;assert ((act['opacity']>=0)&(act['opacity']<=1)).all();assert not any(np.isnan(m[k]).any() for k in s.dtype.names)
 for f in ['LENGTH_AND_PARENT.npz','parents.json','ASSOCIATIONS.json','OBSERVATION_TO_PARENT.npz','SHARED_CONTROL_AND_SAMPLING.npz']:shutil.copyfile(line_dir(scene)/f,out/f)
 ranges=dict(source=dict(start=0,stop=n,group_id=0),ink=dict(start=n,stop=n+nl,group_id=1),source_index='Original source vertex order; -1 for ink',line_index='Original arms/C vertex order; -1 for source',primitive_id='Original C parent ID, never a source GS ID; -1 for source',original_units=reg.get('units','Original scene units, not meters'),original_observations=str(line_dir(scene)/'OBSERVATIONS.npz'),original_observations_sha256=sha(line_dir(scene)/'OBSERVATIONS.npz'))
 js(out/'RANGES.json',ranges)
 audit=dict(scene=scene,source_count=n,ink_count=nl,merged_count=n+nl,source_raw_opacity_positive_inf=int(np.isposinf(s['opacity']).sum()),source_fields_exact=True,source_full_SH_exact=True,line_original_PLY_fields_exact=True,line_filter_zero=True,source_filter_preserved='filter_3D' in s.dtype.names,line_PLY_vs_canonical_NPZ=le,portable=ps,portable_effective_vs_native=pe,minimum_effective_cov_eigenvalue=float(np.linalg.eigvalsh(act['covariance']).min()),seconds=time.monotonic()-start,source_sha256=sha(reg['model']),line_ply_sha256=sha(line_dir(scene)/'gaussians.ply'),line_npz_sha256=sha(line_dir(scene)/'gaussians.npz'),no_geometry_fit=True)
 js(out/'AUDIT.json',audit);js(out/'SEAL.json',dict(complete=True,files={p.name:sha(p) for p in out.iterdir() if p.is_file()}));guard();print('EXPORT',json.dumps(audit),flush=True);return audit
def load_model(scene):
 reg=registry()[scene];p=ROOT/'scenes'/scene/'model';r=json.loads((p/'RANGES.json').read_text());m=read_ply(p/'merged_native.ply');a=activate(m);n=r['source']['stop'];s={k:v[:n] for k,v in a.items()};l={k:v[n:] for k,v in a.items()};floor=np.full(len(m),.12**2);floor[:n]=.3 if scene=='ficus' else .12**2;return a,s,l,floor
def render_view(scene,view,loaded=None):
 guard();out=ROOT/'scenes'/scene/'views'/view;out.mkdir(parents=True,exist_ok=True)
 if (out/'SEAL.json').exists():
  for f,h in json.loads((out/'SEAL.json').read_text())['files'].items():assert sha(out/f)==h
  return json.loads((out/'AUDIT.json').read_text())
 a,s,l,floor=loaded if loaded is not None else load_model(scene);c=next(c for c in registry()[scene]['cameras'] if c['view']==view);bg=[1,1,1] if scene=='ficus' else [0,0,0];n=len(s['means']);start=time.monotonic();src=render(s,c,bg,floor[:n]);t1=time.monotonic();ink=render(l,c,[1,1,1],floor[n:]);t2=time.monotonic();joint=render(a,c,bg,floor);t3=time.monotonic()
 with np.load(BASE/'scenes'/scene/'inputs'/f'{view}.npz') as f:ref={k:f[k] for k in ['rgb','alpha','median_camera_z']}
 np.savez_compressed(out/'RENDER_ARRAYS.npz',source=src['rgb'],line=ink['rgb'],joint=joint['rgb'],source_alpha=src['alpha'],joint_alpha=joint['alpha'],source_center_z=src['median_center_z'])
 for name,im in [('SOURCE_CPU',src['rgb']),('LINE_ONLY',ink['rgb']),('JOINT',joint['rgb']),('REFERENCE',ref['rgb'])]:save(out/(name+'.png'),im)
 ref_label='Frozen official native RaDe RGB' if scene!='ficus' else 'Frozen vanilla-GS CPU RGB reference'
 panel(out/'COMPARISON.jpg',[(ref_label,ref['rgb']),('Same-renderer original source (full SH)',src['rgb']),('C2L50 8BUILD C ink only / white',ink['rgb']),('TRUE joint source + ink (one depth sort)',joint['rgb'])],f'{scene} / {view} | Frozen source + C2L50 8BUILD','CPU EWA approximation; source/ink geometry and opacity unchanged; no 2D overlay')
 ok=(ref['alpha']>=.5)&(src['alpha']>=.5)&np.isfinite(ref['median_camera_z'])&(ref['median_camera_z']>.2)&(src['median_center_z']>.2);dz=abs(src['median_center_z'][ok]-ref['median_camera_z'][ok])/ref['median_camera_z'][ok]
 audit=dict(scene=scene,view=view,source_seconds=t1-start,line_seconds=t2-t1,joint_seconds=t3-t2,RGB_MAE_vs_frozen=float(abs(src['rgb']-ref['rgb']).mean()),alpha_MAE_vs_frozen=float(abs(src['alpha']-ref['alpha']).mean()),center_depth_vs_surface_relative_median=float(np.median(dz)) if len(dz) else None,center_depth_vs_surface_relative_p95=float(np.quantile(dz,.95)) if len(dz) else None,depth_is_not_native_affine_equivalence=True,joint_vs_source_RGB_MAE=float(abs(joint['rgb']-src['rgb']).mean()),joint_vs_RGB_times_ink_max=float(abs(joint['rgb']-src['rgb']*ink['rgb']).max()),same_model_from_reloaded_native_ply=True,native=[c['width'],c['height']],gain=1,background=bg,line_only_background=[1,1,1])
 js(out/'AUDIT.json',audit);js(out/'SEAL.json',dict(files={p.name:sha(p) for p in out.iterdir() if p.is_file()},model_sha256=sha(ROOT/'scenes'/scene/'model/merged_native.ply'),reference_sha256=sha(BASE/'scenes'/scene/'inputs'/f'{view}.npz')));print('VIEW',json.dumps(audit),flush=True);return audit
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--scene',required=True,choices=SCENES);p.add_argument('--view');a=p.parse_args();export(a.scene)
 if a.view:render_view(a.scene,a.view)
