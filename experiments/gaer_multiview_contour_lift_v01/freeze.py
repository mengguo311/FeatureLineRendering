import runtime as rt
from pathlib import Path
import json,subprocess,numpy as np,time
OLD=Path('/home/u00134/3dgs_line/gaer_multiview_contour_regions_v01')
def main():
 if (rt.ART/'INPUT_FREEZE.json').exists():return
 op=OLD/'artifacts/gaer_multiview_contour_regions_v01/INPUT_FREEZE.json';old=json.loads(op.read_text());protected={str(op):rt.sha(op)}
 for s,r in old['scenes'].items():
  assert rt.sha(r['model'])==r['model_sha256'];protected[r['model']]=r['model_sha256']
  for c in r['cameras'].values():
   x=dict(c);ch=x.pop('camera_sha256');assert ch==rt.digest(x)
   mp=Path(c['metadata_path']);assert rt.sha(mp)==c['metadata_sha256'];protected[str(mp)]=rt.sha(mp)
   meta=json.loads(mp.read_text());byfile={f['file_path']:(j,f) for j,f in enumerate(meta['frames'])};assert len(byfile)==86
   j,f=byfile[c['frame_file']];assert j==c['metadata_index']
   C=np.array(f['transform_matrix']);C[:3,1:3]*=-1;assert np.max(np.abs(np.linalg.inv(C)-c['w2c']))<1e-9
 for p in old['protected_before']:
  assert Path(p).is_file();protected[p]=rt.sha(p)
 for stage in ('gaer_multiview_contour_regions_v01','gaer_fixed_contour_asset_v01'):
  root=OLD.parent/stage
  for base in ('experiments','artifacts'):
   for p in (root/base/stage).rglob('*'):
    if p.is_file() and p.suffix in ('.py','.cpp','.md','.json','.so'):protected[str(p)]=rt.sha(p)
 protected[str(rt.ROOT/'.codex/config.toml')]=rt.sha(rt.ROOT/'.codex/config.toml')
 heads=dict(x.split(' ',1) for x in subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],text=True).splitlines())
 rt.atomic_json(rt.ART/'INPUT_FREEZE.json',dict(source=str(op),source_sha256=rt.sha(op),scenes=old['scenes'],protected_before=protected,heads_before=heads,model_config=dict(model='gpt-6-astra',reasoning_effort='ultra'),prior_exposure='all metadata GS/research seen; reserved construction holdout only',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
 P=dict(alpha=.5,sample_arc_px=2,min_perimeter_px=16,proxy='all accepted alphaT conditional weighted median original kernel center camera-z; NOT surface depth',source_max_edge_wpp=6,source_max_edge_diagonal=.025,matching=dict(world_distance_wpp=2.5,abs_tangent_dot=.92,shared_normalized_mass=.1,epipolar_px=1.,source_reproject_px=2.,min_ray_angle_deg=3.,max_displacement_wpp=2.5,local_track_min=3,local_track_index_window=4,distinct_camera_per_cluster=True,all_sources_rechecked=True),fused_min_endpoint_views=2,radius_wpp_candidates=[.75,1.,1.25],dev_rule='min absolute median analytic projected diameter - 2px; p95<=6; lower radius tie',visibility='fixed actual tube self-zbuffer, xray relative to GS; no external occluder',internal_rgb='NOT_IMPLEMENTED',resources=dict(cpu_threads=2,root_min_GiB=4,shared_git_min_GiB=1.5,stage_max_GiB=4,production_single_allocation_max_GiB=1),method_design_sha256=rt.sha(rt.ART/'METHOD_DESIGN_ZH.md'),input_freeze_sha256=rt.sha(rt.ART/'INPUT_FREEZE.json'),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 rt.atomic_json(rt.ART/'PROTOCOL.json',P);rt.atomic_json(rt.ART/'FUSION_FREEZE.json',dict(protocol=P,code=rt.method_hashes(),before_real_source_extraction=True));rt.guard('freeze');print('FREEZE PASS',len(protected),flush=True)
if __name__=='__main__':main()
