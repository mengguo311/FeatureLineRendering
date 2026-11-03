from pathlib import Path
import json,zipfile,hashlib,io,os
os.environ['OPENBLAS_NUM_THREADS']='2'
import numpy as np
from PIL import Image
B=Path('/Users/menakuniay/.hermes/research-deliveries/line_kernel_relaxed_guards_v10_20261103');D=json.loads(Path('/Users/menakuniay/.hermes/cache/scratch/v10_delivery_status.json').read_text());Z=json.loads((B/'ZIP_VERIFICATION.json').read_text());lookup={};seen={};bad=[];count=0
for p in Z['parts']:
 zpath=B/Path(p['path']).name
 assert hashlib.sha256(zpath.read_bytes()).hexdigest()==p['sha256']
 with zipfile.ZipFile(zpath) as z:
  assert z.testzip() is None
  manifest=json.loads(z.read(next(n for n in z.namelist() if n.startswith('PART_'))))
  for e in manifest:
   raw=z.read(e['member']);assert hashlib.sha256(raw).hexdigest()==e['sha256'];assert len(raw)==e['bytes'];assert e['member'].casefold() not in seen;seen[e['member'].casefold()]=e['member'];lookup[e['member']]=str(zpath);count+=1
assert count==Z['payload_members']
print('ZIP_ALL',count,'bytes',sum(p['bytes'] for p in Z['parts']))
def read(name):
 with zipfile.ZipFile(lookup[name]) as z:return z.read(name)
for name in lookup:
 if name.endswith('CARRIERS.npz'):
  with np.load(io.BytesIO(read(name)),allow_pickle=False) as a:print('CARRIER',name,[(k,list(a[k].shape)) for k in a.files])
T=json.loads((B/'TRANSACTION_SOURCE_AUDIT.json').read_text());print('TRANSACTIONS',T['total_transactions'],'issues',T['issues']);print('FREEZE',[(x['unit'],x['snapshot_files'],x['errors']) for x in T['freeze_checks']]);print('ARMS',[(x['unit'],x['arm'],x['events'],x['exact_unions'],x['complete_minimum_with_tie_break'],x['witnesses'],x['errors']) for x in T['arms']]);print('OWNPIDS',T['owned_pid_comm_readback'])
A=json.loads((B/'AUDIT.json').read_text());print('MAPPINGCOUNT',sum(x['mapping_count'] for x in A['units']));print('RANKCOUNT',sum(x['rank_checks'] for x in A['units']));print('LIBRARYCOUNT',sum(x['libraries'] for x in A['units']))
images=[]
for p in (B/'evidence').rglob('*.png'):
 with Image.open(p) as im:im.load();images.append({'path':str(p.relative_to(B)),'size':list(im.size),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
receipt={'local_archive_sha_crc_member_sha_all_pass':True,'payload_members':count,'zip_members_including_manifests':count+len(Z['parts']),'parts':len(Z['parts']),'compressed_bytes':sum(p['bytes'] for p in Z['parts']),'casefold_collisions':[],'decoded_original_pngs':len(images),'images':images,'remote_zip_coldload':Z['cold_load'],'all_intermediate_evidence_included':False,'transactions':T['total_transactions'],'transaction_errors':T['issues'],'checkpoint_maps':sum(x['mapping_count'] for x in A['units']),'protection_correction':'INHERITED_SOURCE_CORRECTED.json'}
(B/'LOCAL_VERIFICATION.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));(B/'MEMBER_LOCATION_INDEX.json').write_text(json.dumps(lookup,indent=2));print('DONE PNGS',len(images))
