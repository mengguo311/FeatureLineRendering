"""Independent CPU recheck; preserve snapshots and never rewrite stage outputs."""
import argparse,json,sys,hashlib,tarfile,shutil,math,importlib.util,datetime
from pathlib import Path
import numpy as np
W=Path('/home/u00134/3dgs_line/gaer_rade_depth_lift_v01');H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');D=H/'depth_only_v01'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import sha256,verify_seal,atomic_json
from depth_checks import compare_cameras,valid_depth

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--audit-dir',required=True);a=ap.parse_args();c=json.loads(Path(a.config).read_text());out=Path(a.audit_dir);out.mkdir(parents=True,exist_ok=False);model=Path(c['model']);delivery=Path(c['delivery_dir']);state=Path(c['state_dir'])
 for p in [Path(a.config),state/'runner_state.json',*state.glob('*.seal.json')]:shutil.copyfile(p,out/p.name)
 shutil.copyfile(W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/MASTER_STATUS.json',out/'MASTER_BEFORE_REVIEW.json')
 seals={}
 for stage in ('smoke','train','export','depth_review'):
  p=state/(stage+'.seal.json');assert verify_seal(p,stage,c['inputs']),stage;seals[stage]=sha256(p);print('verified seal',stage,flush=True)
 for p,digest in c['immutable_files'].items():assert sha256(p)==digest,p
 records=[json.loads(x) for x in (model/'iteration_loss.jsonl').read_text().splitlines()];assert [r['iteration'] for r in records]==list(range(1,30001));assert sum(r['optimizer_updated'] for r in records)==29999
 for r in records:
  active=r['iteration']>=15000;assert r['geometry_active']==active
  assert r['wd']==(100 if active else 0) and r['wn']==(.05 if active else 0)
  assert all(math.isfinite(r[k]) for k in ('photo','distortion','normal','total','alpha_mean'))
 paths={15000:model/'depth_normal_15000',30000:model/'depth_normal'};cams={i:json.loads((p/'cameras_and_conventions.json').read_text()) for i,p in paths.items()};compare_cameras(cams[15000],cams[30000]);assert all(len(v)==49 for v in cams.values())
 spec=importlib.util.spec_from_file_location('colmap_cpu',H/'official_code_fix_v01/source/scene/colmap_loader.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);poses=mod.read_extrinsics_binary(Path(c['data'])/'sparse/0/images.bin');byname={Path(v.name).stem:v for v in poses.values()}
 rows=[];wanted={'median_camera_z':1,'expected_camera_z':1,'alpha':1,'blended_normal_camera':3,'median_depth_normal_camera':3,'rgb':3}
 for iteration,p in paths.items():
  assert len(list(p.glob('*.npz')))==49
  for camera in cams[iteration]:
   view=camera['view'];pose=byname[view];e=np.array(camera['extrinsic']);ref=np.eye(4);ref[:3,:3]=mod.qvec2rotmat(pose.qvec);ref[:3,3]=pose.tvec;assert np.allclose(e,ref,rtol=2e-7,atol=2e-7)
   assert camera['width']==777 and camera['height']==581 and camera['fx']>0 and camera['fy']>0
   with np.load(p/(view+'.npz')) as data:
    assert set(data.files)==set(wanted)
    arrays={k:data[k] for k in data.files}
    for k,v in arrays.items():assert v.dtype==np.float32 and v.shape==(wanted[k],581,777) and np.isfinite(v).all(),(iteration,view,k)
   z=arrays['median_camera_z'];alpha=arrays['alpha'];assert alpha.min()>=0 and alpha.max()<=1
   valid=valid_depth(z,alpha);assert valid.any();vexp=valid_depth(arrays['expected_camera_z'],alpha)
   with np.load(delivery/'masks'/(str(iteration)+'_'+view+'.npz')) as mask:assert np.array_equal(mask['median_valid'],valid) and np.array_equal(mask['expected_valid'],vexp)
   rows.append({'iteration':iteration,'view':view,'finite_all_six_arrays':True,'valid_fraction':float(valid.mean()),'valid_range':[float(z[valid].min()),float(z[valid].max())]})
  print('verified49 raw NPZ',iteration,flush=True)
 receipt=json.loads((delivery/'DELIVERY.json').read_text());manifest=json.loads((delivery/'DEPTH_ONLY_MANIFEST.json').read_text());assert sha256(receipt['archive_path'])==receipt['archive_sha256'];assert sha256(receipt['manifest_path'])==receipt['manifest_sha256']
 expected={name:item['sha256'] for name,item in manifest['files'].items()};expected.update({'DEPTH_ONLY_MANIFEST.json':receipt['manifest_sha256'],'SHA256SUMS':sha256(delivery/'SHA256SUMS')})
 with tarfile.open(receipt['archive_path']) as archive:
  members=archive.getmembers();assert len(members)==len(expected);assert {m.name for m in members}==set(expected)
  for m in members:
   assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
   hash_=hashlib.sha256()
   with archive.extractfile(m) as stream:
    for b in iter(lambda:stream.read(8<<20),b''):hash_.update(b)
   assert hash_.hexdigest()==expected[m.name],m.name
 provenance=json.loads((delivery/'metadata/PROVENANCE.json').read_text());assert provenance['config_sha256']==sha256(a.config);assert provenance['native_sha256']==c['inputs']['native'];assert provenance['source_manifest_sha256']==sha256(provenance['source_manifest_path'])
 native=json.loads(Path(provenance['source_manifest_path']).read_text());assert sha256(native['native'])==native['native_sha256']==c['inputs']['native']
 numeric=json.loads((delivery/'metadata/DEPTH_REVIEW.json').read_text());coverage={str(i):{'min':min(r['valid_fraction'] for r in rows if r['iteration']==i),'mean':float(np.mean([r['valid_fraction'] for r in rows if r['iteration']==i])),'max':max(r['valid_fraction'] for r in rows if r['iteration']==i)} for i in paths}
 result={'scene':c['scene'],'method_variant':c['method_variant'],'numerical_revision':c.get('numerical_revision'),'status':'INDEPENDENT_CPU_REVERIFICATION_PASS','seals':seals,'config_sha256':sha256(a.config),'native_sha256':c['inputs']['native'],'immutable_file_count':len(c['immutable_files']),'unique_training_records':30000,'optimizer_updates':29999,'final_gaussians':records[-1]['points'],'final_opacity_positive_infinities':records[-1]['opacity_logit_posinf'],'raw_npz_count':len(rows),'all_six_arrays_finite':True,'all_cameras_COLMAP_matched':True,'raw_array_rows':rows,'coverage':coverage,'max_joint_valid_15k30k_abs_change':max(r['absolute_delta_scene_units']['range'][1] for r in numeric['fixed_camera_comparisons']),'archive':receipt,'archive_all_members_rehashed':len(expected),'old_fixed_0_4_display_clipped_valid_pixels':numeric['preview_clipped_valid_pixels'],'scientificdone':False,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 atomic_json(out/'REVERIFIED.json',result);print(json.dumps({k:result[k] for k in ['scene','status','coverage','raw_npz_count','final_gaussians','max_joint_valid_15k30k_abs_change','archive_all_members_rehashed']},indent=2),flush=True)
if __name__=='__main__':main()
