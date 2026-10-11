from pathlib import Path
import json,hashlib,shutil,time
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/fusion_redesign_v03');B=T.parent/'balanced_multiview_v02';O=T.parent/'spatial_rgb_gaussian_demo_v01';W=Path('/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction');rows=[]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def check(p,expected=None,kind='evidence'):
 s=sha(p)
 if expected:assert s==expected,str(p)
 rows.append({'path':str(p),'sha256':s,'bytes':p.stat().st_size,'verified_against_prior':bool(expected),'kind':kind});return s
assert shutil.disk_usage('/').free>2**30 and shutil.disk_usage(T).free>10*2**30
for base,key in [('parent_detection_vs_gaussians','files'),('parent_strict_retry_v01','outputs')]:
 d=B/base;a=json.loads((d/'MANIFEST.json').read_text());check(d/'MANIFEST.json')
 for n,s in a[key].items():check(d/n,s,'parent evidence')
for n in ['RECIPE_FREEZE.json','SOURCE_MANIFEST.json','STATUS.json']:check(B/n)
recipe=json.loads((B/'RECIPE_FREEZE.json').read_text())
for r in recipe['files']:check(Path(r['path']),r['sha256'],'frozen source')
for d in [B/'models/scan24'/f'views_{n:02d}' for n in (3,12,24,47)]+[B/'cache/scan24'/v for v in ('0000','0024','0048')]+[B/'pair_cache/scan24'/v for v in ('0000','0024','0048')]:
 a=json.loads((d/'SEAL.json').read_text());check(d/'SEAL.json');assert a['recipe_sha256']==sha(B/'RECIPE_FREEZE.json')
 for r in a['files']:check(d/r['name'],r['sha256'],'sealed cache/model')
archive=json.loads((B/'SOURCE_MANIFEST.json').read_text())['archives'][0]
for r in archive['files']:
 p=Path(r['path'])
 if p.name in [f'scan24_{v}.npz' for v in ('0000','0024','0048')] or not p.name.endswith('.npz'):check(p,r['sha256'],'original build-only input')
images=[B/'parent_detection_vs_gaussians'/f'{v}_detector_vs_gaussians.jpg' for v in ('0012','0036')]+[B/'parent_strict_retry_v01/0012_detector_balanced_strict.jpg',B/'parent_strict_retry_v01/0036_strict_3_12_24_47.jpg']+[O/'results_v2/scan65'/f'{v}_comparison.jpg' for v in ('0012','0036')]+[O/'results_v2/scan63/0048_comparison.jpg']
for i,p in enumerate(images):
 check(p,kind='actually viewed');shutil.copyfile(p,T/'evidence'/f'{i:02d}_{p.parent.name}_{p.name}')
for n in ['REPORT_ZH.md','ASTRA_PLAN_ZH.md']:check(O/n)
for p in sorted((W/'spatial_rgb_gaussian_demo_v01').glob('*.py')):check(p,kind='old code')
(T/'EVIDENCE_MANIFEST.json').write_text(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':rows,'copied_visuals':[str(T/'evidence'/f'{i:02d}_{p.parent.name}_{p.name}') for i,p in enumerate(images)],'old_builder_live':False,'v02_sealed_units_observed':[str(p.parent) for p in sorted((B/'models').glob('*/views_*/SEAL.json'))],'archive_provenance':{k:v for k,v in archive.items() if k!='files'}},indent=2))
print('VERIFIED',len(rows),'file hash records; old sealed model units',len(list((B/'models').glob('*/views_*/SEAL.json'))))
