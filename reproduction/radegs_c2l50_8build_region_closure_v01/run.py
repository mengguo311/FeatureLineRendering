from env import *
from graph import *
from responsibility import ProjectedSource,mass
import argparse,traceback

def calibration(s,c,raw,a,proj,out):
 ref=render(a,c,[1]*3 if s=='ficus' else [0]*3,.3 if s=='ficus' else .0144);z=raw['median_camera_z'].squeeze();al=raw['alpha'].squeeze();ok=np.isfinite(z)&(z>.2)&(al>=.5)&(ref['median_center_z']>.2)
 err=dict(rgb_mae=float(abs(ref['rgb']-raw['rgb']).mean()),alpha_mae=float(abs(ref['alpha']-al).mean()),center_surface_p95=float(np.percentile(abs(ref['median_center_z'][ok]-z[ok])/z[ok],95)))
 err['engineering_go']=err['rgb_mae']<=.02 and err['alpha_mae']<=.02 and err['center_surface_p95']<=.15;assert err['engineering_go'],err
 yy,xx=np.nonzero(ok);checks=[]
 for i in np.linspace(0,len(xx)-1,12,dtype=int):
  uv=[int(xx[i]),int(yy[i])];r=proj.query(uv);q=proj.query(uv,all_N=True);np.testing.assert_array_equal(r['ids'],q['ids']);np.testing.assert_allclose(r['weight'],q['weight'],rtol=0,atol=2e-12);rc=r['rgb']+r['trans']*(1 if s=='ficus' else 0);er=float(max(abs(rc-ref['rgb'][uv[1],uv[0]]).max(),abs(r['alpha']-ref['alpha'][uv[1],uv[0]])));assert er<=5e-7;checks.append(dict(uv=uv,sources=len(r['ids']),render_max_error=er))
 err['all_N']=checks;np.savez_compressed(out/'REFERENCE.npz',**ref);js(out/'CALIBRATION.json',err);save(out/'SOURCE_CPU.jpg',ref['rgb']);return ref

def col(i):return [(0.05,.7,.9),(.9,.2,.6),(.3,.85,.25),(1.,.6,.05),(.5,.35,.95)][i%5]
def annotate(raw,regionlist,center,title=None):
 arr=raw.copy();im=Image.fromarray(np.uint8(np.clip(arr,0,1)*255));d=ImageDraw.Draw(im)
 for i,r in enumerate(regionlist):
  p=r['uv'];color=tuple(int(x*255) for x in col(i)) if r['qualified'] else (150,150,150);d.line([tuple(x) for x in p],fill=color,width=2)
 x,y=center;d.rectangle((x-48,y-48,x+48,y+48),outline=(255,190,0),width=1)
 if title:d.text((max(0,x-47),max(0,y-46)),title,fill=(255,50,30))
 return np.asarray(im)/255

def region_colors(rgb,rs):
 im=rgb.copy()
 for i,r in enumerate(rs):
  if r['qualified']:im[r['mask']]=.5*im[r['mask']]+.5*np.array(col(i))
 return im

def save_regions(out,rs,fs,ledger,center,case):
 masks=np.asarray([r['mask'] for r in rs],bool) if rs else np.empty((0,0,0),bool);np.savez_compressed(out/'REGION_MASKS.npz',masks=masks)
 js(out/'REGIONS.json',[{k:v for k,v in r.items() if k!='mask'} for r in rs]);js(out/'LINK_LEDGER.json',jsonsafe(ledger))
 js(out/'FRAGMENTS.json',[dict(parent=f['parent'],uv=f['uv'].tolist(),z=f['z'].tolist(),original_piece_local=f['indices'].tolist(),end_ok=f['end_ok'],closed=f['closed'],source_views=f.get('source_views',[])) for f in fs]);js(out/'PROVENANCE.json',dict(scene=case['scene'],case=case['case'],original_anchor_parent=case['parent_id'],original_anchor_child_ids=case['child_ids'],center_uv=list(map(float,center)),source_index_is_not_line_index=True,source_assignment='UNKNOWN_until_reserved_checks',new_ink=0))

def query_region(out,rs,proj,s,c,limit=64):
 good=[(i,r) for i,r in enumerate(rs) if r['qualified']];ids=[];weights=[];uvs=[];rids=[];offsets=[0];checks=[]
 # One frozen rank-0 qualified candidate per case/arm, <=64 distinct pixels. Scope is a bounded attribution audit.
 for rid,r in good[:1]:
  yy,xx=np.nonzero(r['mask']);idx=np.linspace(0,len(xx)-1,min(limit,len(xx)),dtype=int)
  for j,i in enumerate(idx):
   uv=[int(xx[i]),int(yy[i])];q=proj.query(uv)
   if j==0:
    z=proj.query(uv,all_N=True);np.testing.assert_array_equal(q['ids'],z['ids']);np.testing.assert_allclose(q['weight'],z['weight'],rtol=0,atol=2e-12);checks.append(dict(uv=uv,count=len(q['ids'])))
   ids.extend(q['ids']);weights.extend(q['weight']);offsets.append(len(ids));uvs.append(uv);rids.append(rid)
 np.savez_compressed(out/'SOURCE_RESPONSIBILITY.npz',source_index=np.asarray(ids,np.int64),weight=np.asarray(weights),query_uv=np.asarray(uvs).reshape(-1,2),region_id=np.asarray(rids,np.int32),csr_offsets=np.asarray(offsets),unknown=np.ones(len(ids),bool));js(out/'SOURCE_ATTRIBUTION_STATUS.json',dict(queried_pixels=len(uvs),membership_assigned=False,all_N_checks=checks,reason='finite alpha*T participation only; no cross-view qualified region yet',source_only=True,center_depth_order=True))

def run_scene(s,phase):
 ps=json.loads((linepath(s)/'parents.json').read_text());g=npz(linepath(s)/'gaussians.npz');a=activate(read_ply(registry()[s]['model']));cs=cases(s);views=[DEV[s]] if phase=='dev' else [AUX[s]]+RESERVED[s]
 for v in views:
  out=ROOT/phase/s/v
  if (out/'SEAL.json').exists():checkseal(out);continue
  out.mkdir(parents=True,exist_ok=True);c=cam(s,v);raw=npz(rawpath(s,v));proj=ProjectedSource.from_asset(a,c,s);ref=calibration(s,c,raw,a,proj,out);ink=render(g,c,[1]*3,.0144)['rgb'];np.savez_compressed(out/'INK_REFERENCE.npz',rgb=ink);save(out/'C8_INK.jpg',ink)
  overview={arm:raw['rgb'].copy() for arm in ['original','shifted','no_line']};regoverview=raw['rgb'].copy();count=[]
  for case in cs:
   if not case.get('selection_valid',True):
    js(out/(case['case']+'_UNAVAILABLE.json'),dict(case=case['case'],reason='inherited source selection unavailable; no replacement'));continue
   X=np.median(g['means'][case['child_ids']],axis=0)[None];center,zz=projection(X,c);center=center[0]
   caseout=out/case['case'];caseout.mkdir(exist_ok=True);allrs={}
   for arm in ['original','shifted','no_line']:
    ad=caseout/arm;ad.mkdir(exist_ok=True)
    if arm=='no_line':fs=[];ledger=[];rs=no_line_regions(raw,c,center)
    else:
     fs,visledger=fragments(ps,c,raw,center,shift=12. if arm=='shifted' else 0.);rs,links=find_regions(fs,raw,c);ledger=[dict(stage='visibility',**x) for x in visledger]+[dict(stage='endpoint_graph',**x) for x in links]
    save_regions(ad,rs,fs,ledger,center,case);query_region(ad,rs,proj,s,c);allrs[arm]=rs;overview[arm]=annotate(overview[arm],rs,center,case['case']);count.append(dict(scene=s,view=v,case=case['case'],arm=arm,fragments=len(fs),candidates=len(rs),qualified=sum(r['qualified'] for r in rs),open_expected=case['case'] in json.loads((ROOT/'CONFIG_FREEZE.json').read_text())['open_cases'],physical_primitive=False))
   regoverview=region_colors(regoverview,allrs['original']);reg=region_colors(raw['rgb'],allrs['original']);pro=annotate(raw['rgb'],allrs['original'],center)
   items=[('Original frozen source RGB',raw['rgb']),('Original C8 Gaussian ink | XRAY',ink),('Line-region hypotheses; gray = UNKNOWN',pro),('Local 2D regions only; overlap is ambiguous',reg),('Shift +12px null; identical budget',annotate(raw['rgb'],allrs['shifted'],center)),('No-line RGB/alpha level-set baseline',annotate(raw['rgb'],allrs['no_line'],center))]
   panel(caseout/'FULL_FRAME.jpg',items,f'{s} {v} | {case["case"]}', 'No new ink / no physical plane claim / independent raw-image evidence',cols=3)
   # Zooms are supplementary; full native frame remains available above.
   x,y=np.rint(center).astype(int);W,H=c['width'],c['height'];box=(max(0,x-48),max(0,y-48),min(W,x+49),min(H,y+49));zoom=[]
   if box[2]>box[0] and box[3]>box[1]:
    for lab,arr in items:
     im=Image.fromarray(np.uint8(np.clip(arr,0,1)*255)).crop(box).resize((388,388),Image.Resampling.NEAREST);zoom.append((lab,np.asarray(im)/255))
    panel(caseout/'DETAIL.jpg',zoom,f'{s} {v} {case["case"]} | 4x diagnostic',cols=3)
   print(s,v,case['case'],[(k,len(r),sum(x['qualified'] for x in r)) for k,r in allrs.items()],flush=True)
  panel(out/'OVERVIEW.jpg',[('Frozen source RGB',raw['rgb']),('Original C8 ink | XRAY',ink),('Original line proposals / UNKNOWN gray',overview['original']),('2D candidate region display; NOT source-GS labels',regoverview),('Shifted-line null',overview['shifted']),('No-line RGB / alpha baseline',overview['no_line'])],f'{s} {v} | bounded region-closure pilot','Same native frame / no added 3D line / temporary graph links only',cols=3);js(out/'COUNTS.json',count);seal(out);guard()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['dev','reserved'],required=True);p.add_argument('--scene',choices=SCENES);args=p.parse_args();failed=[]
 for s in ([args.scene] if args.scene else SCENES):
  state('RUN_'+args.phase.upper(),scene=s,children=[os.getpid()])
  try:run_scene(s,args.phase)
  except Exception as e:
   traceback.print_exc();js(ROOT/f'FAILURE_{args.phase}_{s}.json',dict(error=repr(e),time=now()));failed.append(s)
 state(args.phase.upper()+'_COMPLETE' if not failed else 'ENGINEERING_INVALID',children=[],failed_scenes=failed)
 if failed:raise SystemExit(1)
