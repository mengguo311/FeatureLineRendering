import runtime as rt
import json,re
from pathlib import Path
import numpy as np
from core import geometry_hash

def main():
 files=[p for base in (rt.EXP,rt.ART) for p in base.rglob('*') if p.is_file() and p.name not in ('DELIVERY_INVENTORY.json',)]
 assert all(p.stat().st_size<95*2**20 for p in files),'single file near GitHub100MiB limit'
 code={str(p.relative_to(rt.ROOT)):rt.sha(p) for p in rt.EXP.rglob('*') if p.is_file()}
 for n in ('lego','chair'):
  asset=json.loads((rt.ART/'results'/(n+'_asset.json')).read_text());frozen=json.loads((rt.ART/'INPUT_FREEZE.json').read_text())['scenes'][n]
  for arm,record in asset['arms'].items():
   g=dict(np.load(rt.ART/'assets'/n/arm/'centerlines.npz'));assert geometry_hash(g['xyz'],g['edges'],float(g['radius']))==record['geometry_sha256']
  m=json.loads((rt.ART/'media'/n/'arc/three_arms_33.manifest.json').read_text());assert m['decoded_frames']==33 and m['expected_frames']==33 and m['full_decode'] and m['faststart'] and m['codec']=='h264' and m['pixel_format']=='yuv420p';assert rt.sha(m['path'])==m['sha256']
  for i,r in enumerate(m['frames']):
   assert r['camera_sha256']==frozen['arc'][i]['camera_sha256'];assert r['geometry_sha256']=={k:v['geometry_sha256'] for k,v in asset['arms'].items()};assert rt.sha(r['source_png'])==r['source_png_sha256']
  for key in frozen['roles']['reserved']:
   r=json.loads((rt.ART/'results'/f'{n}_reserved_{key}.json').read_text());assert r['camera_sha256']==frozen['cameras'][key]['camera_sha256'];assert r['geometry_sha256']=={k:v['geometry_sha256'] for k,v in asset['arms'].items()}
 # Local document links in human entrypoints; wildcards in code snippets are not URLs.
 checked=0
 for p in [rt.ART/'REPORT_ZH.md',rt.ART/'INDEX.html',rt.ART/'REPRODUCE.md']:
  text=p.read_text();links=re.findall(r'\]\(([^)]+)\)',text) if p.suffix=='.md' else re.findall(r'(?:href|src)="([^"]+)"',text)
  for link in links:
   if '://' in link or link.startswith('#'):continue
   assert (p.parent/link.split('#')[0]).exists(),str(p)+' -> '+link;checked+=1
 audit=json.loads((rt.ART/'PROTECTION_AUDIT.json').read_text());assert audit['status']=='PASS'
 test=(rt.ART/'tdd/EXTENDED_02.log').read_text();assert 'Ran 10 tests' in test and '\nOK\n' in test;assert 'Ran 8 tests' in (rt.ART/'tdd/GREEN_01.log').read_text()
 resource=rt.guard('final_inventory')
 rt.atomic_json(rt.ART/'DELIVERY_INVENTORY.json',dict(status='PASS',verdict='PARTIAL_THIN_FIXED_CURVES / NO_GO_COMPLETE_CONTOUR',core_producer_hashes=rt.method_hashes(),all_current_code_hashes=code,diagnostic_binding_note='Current supplemental/report/test code bound at delivery; only FUSION_FREEZE is a pre-extraction core-method freeze. Expanded tests retain their actual later timestamps.',files={str(p.relative_to(rt.ROOT)):dict(sha256=rt.sha(p),bytes=p.stat().st_size) for p in files},local_links_checked=checked,media_camera_geometry_hashes_verified=True,full_decode_per_scene=33,asset_geometry_unchanged=True,resource=resource))
 print('INVENTORY_PASS',len(files),'files',checked,'links',max(p.stat().st_size for p in files),'max bytes',flush=True)
if __name__=='__main__':main()
