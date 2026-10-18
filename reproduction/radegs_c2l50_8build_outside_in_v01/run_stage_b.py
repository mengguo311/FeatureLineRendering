from env import *
from hierarchy import hierarchical,mutual_match
from protocol import containment,visibility
from run_stage_a import grey,overlay
from scipy import ndimage as ndi
CFG=json.loads((ROOT/'CONFIG_FREEZE.json').read_text())['stageB']
ARMS=['rgb_depth','rgb_only','depth_only']

def display(rgb,lab,unknown=None):
 rng=np.random.default_rng(1729);palette=rng.uniform(.12,.95,(int(lab.max())+1,3));x=rgb.copy();m=lab>0;x[m]=.32*x[m]+.68*palette[lab[m]]
 if unknown is not None:x[unknown]=.4*x[unknown]+.6*np.array([1,.5,0])
 return x

def major(lab,mask):
 size=np.bincount(lab.ravel());ids=np.flatnonzero(size>=CFG['minimum_major_area_fraction']*mask.sum());return ids[ids>0],size

def mapping(s,v,tv,lab,tlab):
 ra=npz(rawpath(s,v));rb=npz(rawpath(s,tv));c=cam(s,v);tc=cam(s,tv);z=ra['median_camera_z'].squeeze();a=ra['alpha'].squeeze();tz=rb['median_camera_z'].squeeze();ta=rb['alpha'].squeeze();m=lab>0;tm=tlab>0;groups,size=major(lab,m);targets,tsize=major(tlab,tm);pred={};rows=[]
 for gid in groups:
  yy,xx=np.mgrid[:m.shape[0]:4,:m.shape[1]:4];good=(lab[yy,xx]==gid)&np.isfinite(z[yy,xx])&(z[yy,xx]>.2)&(a[yy,xx]>=.5);uv=np.c_[xx[good],yy[good]];X=unproject(uv,z[uv[:,1],uv[:,0]],c);pv,pz=projection(X,tc);state=visibility(pv,pz,tz,ta,tc);visible=np.flatnonzero(state==1);q=np.rint(pv[visible]).astype(int);labs=tlab[q[:,1],q[:,0]];ct=np.bincount(labs,minlength=int(tlab.max())+1);ct[0]=0
  target=int(ct.argmax()) if len(visible) else 0;frac=float(ct[target]/len(visible)) if len(visible) else 0;comparable=float(len(visible)/max(len(uv),1));eligible=comparable>=.2 and target in targets
  if eligible:pred[int(gid)]=(target,frac)
  rows.append(dict(group=int(gid),target=target,dominant_fraction=frac,source_area=int(size[gid]),target_area=int(tsize[target]) if target else 0,samples=len(uv),visible=len(visible),occluded=int((state==2).sum()),unknown=int((state==0).sum()),outside=int((state==3).sum()),front_inconsistent=int((state==4).sum()),comparable_fraction=comparable,eligible=bool(eligible)))
 return pred,rows

def run():
 gates=json.loads((ROOT/'STAGE_A_GATE.json').read_text())['scenes'];assert gates['ficus']['stageA']=='GO';assert gates['scan24']['stageA']=='NO_GO' and gates['scan65']['stageA']=='NO_GO';s='ficus';views=[DEV[s],AUX[s],*RESERVED[s]];counts=[]
 review('05_B_engineering_GREEN_GO_run','5项B测试已通过，包括真实depth step断言修复、孔洞/薄断组件、嵌套/多对一拒绝。允许仅Ficus执行冻结B三层级及RGB-only/depth-only对照；主解释级为最粗2.0，其他固定层级保留诊断，不事后选最好阈值。C/D仍未许可。',[ROOT/'GREEN_HIERARCHY_V01.log',CODE/'hierarchy.py',ROOT/'B_ENGINEERING_FIX.json'])
 state('STAGE_B_FICUS',children=[os.getpid()])
 for v in views:
  guard();p=ROOT/'stageB'/s/v;p.mkdir(parents=True,exist_ok=True);raw=npz(rawpath(s,v));sa=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');ref=npz(ROOT/'stageA'/s/v/'REFERENCE.npz');mask=sa['candidate'];c=cam(s,v);imgs=[];stats=[]
  for arm in ARMS:
   r=hierarchical(raw['rgb'],raw['median_camera_z'].squeeze(),raw['alpha'].squeeze(),mask,c,arm);assert containment(r['levels'][0],r['levels'][1]) and containment(r['levels'][1],r['levels'][2]);np.savez_compressed(p/(arm+'.npz'),**r)
   armrows=[]
   for i,t in enumerate(CFG['merge_levels']):
    ids,size=major(r['levels'][i],mask);armrows.append(dict(level=t,all_region_count=int(r['levels'][i].max()),major_count=len(ids),major_ids=ids.tolist(),major_area_pixels=size[ids].tolist(),major_fraction=float(size[ids].sum()/mask.sum()),allowed_major_budget=bool(2<=len(ids)<=CFG['max_major_regions'])))
   stats.append(dict(scene=s,view=v,arm=arm,markers=int(r['markers'].max()),unknown_depth_pixels=int(r['unknown_depth'].sum()),levels=armrows));imgs.append((arm+' | coarse level 2.0',display(raw['rgb'],r['levels'][-1],r['unknown_depth']|sa['unknown'])))
   panel(p/(arm+'_LEVELS.jpg'),[('Source-only frozen RGB',raw['rgb'])]+[(arm+' | level '+str(t),display(raw['rgb'],r['levels'][i],r['unknown_depth']|sa['unknown'])) for i,t in enumerate(CFG['merge_levels'])],s+' / '+v+' | Nested image-region hypotheses','Orange: unknown. Colors are image regions, not semantic parts / 3D surfaces. No line construction input.',2)
  panel(p/'COMPARISON_FULL.jpg',[('Source-only frozen RGB',raw['rgb']),('Original C8 ink / XRAY (context only)',ref['line_rgb']),('Qualified Stage A subject proxy',overlay(raw['rgb'],mask)),*imgs],s+' / '+v+' | Stage B: coarse-to-fine region hierarchy','All subject pixels retained in regions or unknown. No source GS labels or geometry changes.',3)
  js(p/'COUNTS.json',dict(rows=stats));seal(p);counts+=stats;print('B_VIEW',v,stats[0]['levels'],flush=True)
 matches=[]
 for arm in ARMS:
  for tv in [AUX[s],*RESERVED[s]]:
   for level in range(3):
    lab=npz(ROOT/'stageB'/s/DEV[s]/(arm+'.npz'))['levels'][level];tlab=npz(ROOT/'stageB'/s/tv/(arm+'.npz'))['levels'][level];ab,rr=mapping(s,DEV[s],tv,lab,tlab);ba,tt=mapping(s,tv,DEV[s],tlab,lab);pairs=mutual_match(ab,ba,.75);matches.append(dict(arm=arm,level=CFG['merge_levels'][level],from_view=DEV[s],to_view=tv,mutual_pairs=pairs,forward=rr,reverse=tt));print('B_TRANSFER',arm,CFG['merge_levels'][level],tv,len(pairs),flush=True)
 js(ROOT/'B_COUNTS.json',dict(rows=counts,matches=matches,formal_source_labels=0,physical_primitives=0));state('STAGE_B_COMPLETE',children=[],stageB_ficus='AWAITING_REVIEW')
if __name__=='__main__':run()
