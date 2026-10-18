"""Read-only integrity and deterministic scientific replay. No outputs rewritten."""
from env import *
from graph import fragments,find_regions,no_line_regions,transfer_region
from responsibility import ProjectedSource
import argparse

def main(replay=False):
 for filename in ['SOURCE_MANIFEST.json','DEPENDENCY_MANIFEST.json']:
  for p,h in json.loads((ROOT/filename).read_text())['files'].items():assert sha(p)==h,(filename,p)
 for p,h in json.loads((ROOT/'EXECUTION_CODE_FREEZE.json').read_text())['files'].items():assert sha(p)==h,('execution code modified',p)
 units=list((ROOT/'dev').glob('*/*/SEAL.json'))+list((ROOT/'reserved').glob('*/*/SEAL.json'));assert len(units)==12
 for p in units:checkseal(p.parent)
 counts=json.loads((ROOT/'evaluation/ALL_COUNTS.json').read_text());assert len(counts)==132;assert sum(x['arm']=='original' for x in counts)==44
 reports=[]
 for s in SCENES:
  l=npz(linepath(s)/'gaussians.npz');layout=npz(linepath(s)/'SHARED_CONTROL_AND_SAMPLING.npz');m=(layout['control'][layout['control_index']]*layout['basis'][:,:,None]).sum(1);np.testing.assert_array_equal(l['means'],m)
  source=read_ply(registry()[s]['model']);a=activate(source);assert all(np.isfinite(a[k]).all() for k in ['means','covariance','opacity','SH']);assert (np.linalg.eigvalsh(a['covariance'])>0).all();assert a['SH'].shape[1:]==(3,16)
  unknown=npz(ROOT/'evaluation'/s/'SOURCE_IDS_REGION_UNKNOWN.npz');np.testing.assert_array_equal(unknown['source_index'],np.arange(len(source)));assert unknown['unknown'].all() and (unknown['region_id']==-1).all()
  stat=dict(scene=s,source_count=len(source),line_count=len(l['means']),raw_positive_infinite_opacity=int(np.isposinf(source['opacity']).sum()),filter_3D='filter_3D' in source.dtype.names,full_SH_channels=a['SH'].shape[2],replay=[])
  for v in [DEV[s]]+RESERVED[s]:
   phase='dev' if v==DEV[s] else 'reserved';vp=ROOT/phase/s/v;c=cam(s,v);raw=npz(rawpath(s,v));proj=ProjectedSource.from_asset(a,c,s);cal=json.loads((vp/'CALIBRATION.json').read_text());assert cal['engineering_go']
   if replay:
    got=render(a,c,[1]*3 if s=='ficus' else [0]*3,.3 if s=='ficus' else .0144);old=npz(vp/'REFERENCE.npz')
    for k in got:np.testing.assert_array_equal(got[k],old[k])
    ink=render(l,c,[1]*3,.0144)['rgb'];np.testing.assert_array_equal(ink,npz(vp/'INK_REFERENCE.npz')['rgb'])
    for check in cal['all_N'][:3]:
     q=proj.query(check['uv']);r=proj.query(check['uv'],all_N=True);np.testing.assert_array_equal(q['ids'],r['ids']);np.testing.assert_array_equal(q['weight'],r['weight'])
    case=next(x for x in cases(s) if x.get('selection_valid',True));cp=vp/case['case'];pr=json.loads((cp/'original/PROVENANCE.json').read_text());parents=json.loads((linepath(s)/'parents.json').read_text());fs,vl=fragments(parents,c,raw,np.array(pr['center_uv']));rs,ledger=find_regions(fs,raw,c);saved=json.loads((cp/'original/REGIONS.json').read_text());assert [{k:v for k,v in r.items() if k!='mask'} for r in rs]==saved
    masks=npz(cp/'original/REGION_MASKS.npz')['masks'];assert len(rs)==len(masks)
    for r,m in zip(rs,masks):np.testing.assert_array_equal(r['mask'],m)
    nr=no_line_regions(raw,c,np.array(pr['center_uv']));saved=json.loads((cp/'no_line/REGIONS.json').read_text());assert [{k:v for k,v in r.items() if k!='mask'} for r in nr]==saved
    stat['replay'].append(dict(view=v,source_and_ink_bitexact=True,graph_and_no_line_bitexact=True,all_N=3))
  reports.append(stat)
 # Verify cross-view transfer computations for at least one original/strong null per scene, no source ID equality assumption.
 if replay:
  rows=json.loads((ROOT/'evaluation/TRANSFERS.json').read_text())
  for s in SCENES:
   for arm in ['original','no_line']:
    candidates=[r for r in rows if r['scene']==s and r['arm']==arm]
    if not candidates:continue
    r=candidates[0];p=ROOT/'dev'/s/DEV[s]/r['case']/arm;q=ROOT/'reserved'/s/r['target_view']/r['case']/arm;ma=npz(p/'REGION_MASKS.npz')['masks'][r['dev_region']];r2=json.loads((q/'REGIONS.json').read_text());mb=npz(q/'REGION_MASKS.npz')['masks'];good=[m for x,m in zip(r2,mb) if x['qualified']];new=transfer_region(ma,npz(rawpath(s,DEV[s])),cam(s,DEV[s]),npz(rawpath(s,r['target_view'])),cam(s,r['target_view']),good)
    for key,val in new.items():assert r[key]==val,(s,arm,key)
 protection=rollback();print(json.dumps(dict(ok=True,readonly=True,replay=replay,units=len(units),case_view_arms=len(counts),sources=reports,old_protection=protection,resources=guard()),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--readonly',action='store_true',required=True);p.add_argument('--replay',action='store_true');a=p.parse_args();main(a.replay)
