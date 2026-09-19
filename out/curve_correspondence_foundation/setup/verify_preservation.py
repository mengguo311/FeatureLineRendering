"""Read-only archive/checkpoint hashing; real TEST photograph bytes stay unopened."""
import concurrent.futures,datetime,json,pathlib,sys,time
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];P=R/'out/multiscene_foundation_corrected';sys.path.insert(0,str(O/'code'))
from cc_io import sha,write_json
cfg=json.loads((O/'config.json').read_text());old=json.loads((P/'config.json').read_text());tests=set()
for scene in old['scenes']:
 for i in cfg['splits']['TEST']:
  c=old['scenes'][scene]['cameras'].get(f'train_{i:03d}')
  if c:tests.add(str(pathlib.Path(c['path']).resolve()))
expected={}
for row in json.loads((P/'MANIFEST.json').read_text())['files']:expected[str(P/row['path'])]=row['sha256']
for row in json.loads((P/'PRESERVED_INPUT_VERIFICATION.json').read_text())['records']:expected[row['path']]=row['expected_sha256']
for p,r in json.loads((O/'input_hashes.json').read_text()).items():expected[p]=r['sha256']
skipped=[];jobs=[]
for p,h in expected.items():
 if str(pathlib.Path(p).resolve()) in tests or any(f'/train/r_{i}.png' in p for i in cfg['splits']['TEST']):skipped.append(dict(path=p,reason='TEST remains sealed; no new byte read'))
 else:jobs.append((p,h))
def verify(item):
 p,h=item;observed=sha(p);return dict(path=p,expected_sha256=h,observed_sha256=observed,passed=h==observed)
start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(verify,jobs))
result=dict(passed=all(r['passed'] for r in records),files=len(records),skipped_sealed_TEST=skipped,records=records,elapsed_seconds=time.monotonic()-start,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checkpoint_count=8)
write_json(O/'PRESERVED_INPUT_VERIFICATION.json',result);print('preserved',len(records),'passed',result['passed'],'sealed skips',len(skipped),'seconds',result['elapsed_seconds'],flush=True)
