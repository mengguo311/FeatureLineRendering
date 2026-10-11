from pathlib import Path
import hashlib,json,tarfile,shutil,time
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/spatial_rgb_gaussian_demo_v01')
W=Path('/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/spatial_rgb_gaussian_demo_v01')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def js(p,a):p.write_text(json.dumps(a,indent=2,ensure_ascii=False))
# Final copy includes packaging code; never modify original production scripts.
for p in W.iterdir():
 if p.is_file():shutil.copy2(p,T/'code'/p.name)
roots=['code','TEST_LOGS','results_v1','results_v2','build']
owned=[p for d in roots for p in (T/d).rglob('*') if p.is_file()]
owned += [T/n for n in ['ASTRA_PLAN_ZH.md','BUILD_ONLY_REVIEW_AND_V2_ZH.md','REPORT_ZH.md','ASSET_FORMAT_ZH.md','ASTRA_FINAL.md','STATUS.json','STATUS_BEFORE_COMPLETION.json','SOURCE_FREEZE.json','ASSET_FREEZE.json','BALANCED_ASSET_FREEZE.json','BUILD_RESULTS.json','FIXED_PARAMETERS.json','VISUAL_REVIEW.json','ENVIRONMENT_NATIVE_PROVENANCE.json','INDEX.html','BUILD_RUN.log','BALANCED_BUILD_RUN.log','EVALUATION_RUN.log','BALANCED_EVALUATION_RUN.log']]
owned=sorted(set(owned));inputs=json.loads((T/'SOURCE_FREEZE.json').read_text())['files']
package_files=[p for p in owned if 'arc_frames' not in p.parts and p.name!='source_samples.npz' and not p.name.endswith('_source_maps.npz')]
package_files += [Path(r['path']) for r in inputs if not Path(r['path']).name.endswith('.npz')]
packed=set(package_files)
manifest={'status':'HONEST_NEGATIVE','output_count':len(owned),'source_files':inputs,'outputs':[{'path':str(p),'relative_path':str(p.relative_to(T)),'sha256':sha(p),'bytes':p.stat().st_size,'in_compact_package':p in packed} for p in owned],'main_previews':[str(T/'results_v2'/s/(v+'_comparison.jpg')) for s,v in [('scan24','0012'),('scan65','0012'),('scan63','0048'),('scan65','0036')]],'videos':[str(p) for p in sorted((T/'results_v2').glob('*/*.mp4'))],'package':{'path':str(T/'DELIVERABLE.tar.gz'),'sha256_sidecar':str(T/'DELIVERABLE.sha256'),'self_reference_policy':'manifest excludes itself/archive/hash-sidecars to avoid hash recursion; archive has independently verified member hashes','validation':str(T/'PACKAGE_VALIDATION.json')},'full_fields_remote':['source_samples.npz','*_source_maps.npz','arc_frames/*.png'],'scientific_claim':'actual Gaussian demo completed; visual stability/completeness target not achieved'}
js(T/'RESULTS_MANIFEST.json',manifest);package_files.append(T/'RESULTS_MANIFEST.json')
# A member listing whose own hash is deliberately outside its scope.
listing=''.join(sha(p)+'  '+str(p.relative_to(T))+'\n' for p in sorted(package_files));(T/'PACKAGE_CONTENTS.sha256').write_text(listing);package_files.append(T/'PACKAGE_CONTENTS.sha256')
with tarfile.open(T/'DELIVERABLE.tar.gz','w:gz',compresslevel=6) as tar:
 for p in sorted(package_files):tar.add(p,arcname=str(p.relative_to(T)),recursive=False)
archive=T/'DELIVERABLE.tar.gz';digest=sha(archive);(T/'DELIVERABLE.sha256').write_text(digest+'  DELIVERABLE.tar.gz\n')
expected={str(p.relative_to(T)):sha(p) for p in package_files};count=0
with tarfile.open(archive,'r:gz') as tar:
 for member in tar:
  assert member.isfile();assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
  h=hashlib.sha256(tar.extractfile(member).read()).hexdigest();assert h==expected[member.name],member.name;count+=1
assert count==len(package_files);assert not any(p.name.endswith('.npz') and p.parent.name=='evidence' for p in package_files)
result={'archive':str(archive),'sha256':digest,'bytes':archive.stat().st_size,'members':count,'all_member_hashes_verified':True,'unsafe_paths':0,'input_NPZ_included':0,'package_source_fields':'delivery_source_provenance + model means/covariance; full tangent/normal/source maps stay remote','status':'PASS','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())};js(T/'PACKAGE_VALIDATION.json',result);print(json.dumps(result,indent=2))
assert sum(p.stat().st_size for p in T.rglob('*') if p.is_file())<15*1024**3
assert shutil.disk_usage(T).free>=10*1024**3 and shutil.disk_usage('/').free>=1024**3
