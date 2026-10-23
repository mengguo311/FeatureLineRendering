"""Append only bounded internal OFF intervals of the unchanged legacy generator.

Traversal and arithmetic below follow the frozen hatching.generate_region.
The legacy module is unchanged. Old on-segments are regenerated only to prove
the correspondence; output retains the actual saved arrays verbatim as prefix.
No nearest-endpoint joining, terminal extension, or new surface is introduced.
"""
import runtime
import numpy as np
from hatching import cutting_normal,validate_style,cross_style,layer_ids,visibility_masks
from render import _coverage
from geometry import project
from visibility_intervals import cast_points,sample_support

CORE=('points','bary','face','stroke_id')


def reconstruct_layer(mesh,region,style,layer):
    validate_style(style)
    ids=np.flatnonzero(mesh['regions']==region)
    normal=cutting_normal(region,style['angle'],style.get('plane'))
    q=mesh['vertices']@normal;qt=q[mesh['faces'][ids]]
    spacing=style['spacing'];max_length=style['length'];gap=.035
    first=int(np.floor(qt.min()/spacing));last=int(np.ceil(qt.max()/spacing))
    on=[];off=[];stroke=region*10**9+layer*500_000_000;chain=layer*10**6
    ambiguous=0;terminal_off=0
    for k in range(first,last+1):
        level=(k+.1732050807568877)*spacing
        hits=ids[(qt.min(1)<level)&(qt.max(1)>level)]
        records=[];nodes={}
        for face in hits:
            f=mesh['faces'][face];v=q[f]-level;ends=[];keys=[]
            for j,l in ((0,1),(1,2),(2,0)):
                if v[j]*v[l]<0:
                    t=-v[j]/(v[l]-v[j]);b=np.zeros(3);b[j]=1-t;b[l]=t
                    ends.append(b);keys.append(tuple(sorted((int(f[j]),int(f[l])))))
            if len(ends)!=2:continue
            index=len(records);records.append((int(face),np.asarray(ends),keys))
            for end,key in enumerate(keys):nodes.setdefault(key,[]).append((index,end))
        ambiguous+=sum(len(v)>2 for v in nodes.values())
        used=set()
        starts=sorted((key,items[0][0],items[0][1]) for key,items in nodes.items() if len(items)!=2)
        starts += [(rec[2][0],i,0) for i,rec in enumerate(records)]
        for _,i,entry in starts:
            if i in used:continue
            chain+=1;arc=0.;piece=-1;path_id=None;pieces={};pending=[]
            while i not in used:
                used.add(i);face,b,keys=records[i]
                if entry==1:b=b[::-1]
                xyz=b@mesh['tri'][face];length=float(np.linalg.norm(xyz[1]-xyz[0]));s=0.
                while s<length-1e-12:
                    absolute=arc+s;period=max_length+gap
                    current=int(np.floor((absolute+1e-10)/period));within=absolute-current*period
                    active=within<max_length-1e-10
                    end=min(length,s+max(1e-10,(max_length if active else period)-within))
                    if end-s>1e-10:
                        t0,t1=s/length,end/length
                        bb=np.stack([(1-t0)*b[0]+t0*b[1],(1-t1)*b[0]+t1*b[1]])
                        if active:
                            if current!=piece:stroke+=1;path_id=stroke;piece=current
                            pieces[current]=path_id
                            on.append((bb@mesh['tri'][face],bb,face,path_id))
                        else:
                            pending.append((bb@mesh['tri'][face],bb,face,current,arc+s,arc+end))
                    s=end
                arc+=length;candidates=nodes[keys[1-entry]]
                if len(candidates)!=2:break
                nxt=[x for x in candidates if x[0]!=i]
                if not nxt:break
                i,entry=nxt[0]
            for xyz,bb,face,period_idx,start,end in pending:
                if period_idx not in pieces or period_idx+1 not in pieces:
                    terminal_off+=1;continue
                off.append((xyz,bb,face,chain,k,period_idx,start,end,pieces[period_idx],pieces[period_idx+1],layer))
    return on,off,dict(ambiguous_nodes=ambiguous,terminal_off_segments_excluded=terminal_off,chains=chain-layer*10**6)


def complete_gaps(mesh,old,style,enabled=True):
    if not style.get('cross_enabled',False):raise ValueError('frozen two-layer style required')
    ons=[];offs=[];stats=dict(ambiguous_nodes=0,terminal_off_segments_excluded=0,chains=0)
    for layer,st in ((0,style),(1,cross_style(style))):
        a,b,c=reconstruct_layer(mesh,4,st,layer);ons.extend(a);offs.extend(b)
        for k in stats:stats[k]+=c[k]
        index=np.flatnonzero(layer_ids(old)==layer)
        for j,key in enumerate(CORE):
            regenerated=np.asarray([v[j] for v in a],dtype=old[key].dtype).reshape(old[key][index].shape)
            np.testing.assert_array_equal(regenerated,old[key][index],err_msg='saved path differs from legacy reconstruction: '+key)
    gaps=dict(points=np.asarray([v[0] for v in offs],float).reshape(-1,2,3),
              bary=np.asarray([v[1] for v in offs],float).reshape(-1,2,3),face=np.asarray([v[2] for v in offs],np.int32))
    for name,j,dtype in [('chain_id',3,np.int64),('plane_index',4,np.int64),('period_index',5,np.int64),
                         ('arc_start',6,float),('arc_end',7,float),('left_stroke_id',8,np.int64),
                         ('right_stroke_id',9,np.int64),('layer_id',10,np.uint8)]:
        gaps[name]=np.asarray([v[j] for v in offs],dtype)
    identities={};ids=[]
    for item in offs:
        key=(item[10],item[3],item[5])
        if key not in identities:identities[key]=9_000_000_000+len(identities)
        ids.append(identities[key])
    gaps['stroke_id']=np.asarray(ids,np.int64)
    gaps['visibility_mask']=np.full(len(ids),1<<4,np.uint64)
    filled={k:v.copy() for k,v in old.items()}
    if enabled:
        for k in filled:
            if k not in gaps:raise ValueError('unhandled saved attribute '+k)
            filled[k]=np.concatenate([filled[k],gaps[k].astype(filled[k].dtype)])
    stats.update(old_segments=len(old['points']),old_strokes=len(np.unique(old['stroke_id'])),
        gap_segments=len(ids),internal_gaps=len(identities),
        added_world_length=float(np.linalg.norm(gaps['points'][:,1]-gaps['points'][:,0],axis=1).sum()),
        legacy_reconstruction_exact=True,period=.155,on_length=.12,off_length=.035)
    return filled,gaps,stats


def render_gap_pair(mesh,old,gaps,meta,camera):
    # Temporary coverage groups encode provenance, not a new direction layer.
    # This permits one identical ray-surface query for both arms and gap-only ink.
    tagged={k:np.concatenate([old[k],gaps[k].astype(old[k].dtype)]) for k in CORE}
    tagged['layer_id']=np.r_[layer_ids(old),layer_ids(gaps)+2].astype(np.uint8)
    tagged['visibility_mask']=np.r_[visibility_masks(old,4),visibility_masks(gaps,4)]
    data=_coverage(mesh,{4:tagged},meta['styles'],camera,2);cov=data['coverage'][4]
    shape=(camera['height']*2,camera['width']*2)
    zero=np.zeros(shape,bool);oldcov=cov.get(0,zero)|cov.get(1,zero);gapcov=cov.get(2,zero)|cov.get(3,zero)
    strength=meta['styles']['4'].get('ink_strength',.8)
    low=lambda x:(x.astype(np.float32)*strength).reshape(camera['height'],2,camera['width'],2).mean((1,3))
    pair=dict(old=low(oldcov),filled=low(oldcov|gapcov),gap_only=low(gapcov),new_coverage=low(gapcov&~oldcov))
    return pair,{k:v for k,v in data.items() if k!='coverage'}


def gap_samples(mesh,gaps,camera,pair,support,filled_scale):
    uv=[];depth=[];seg=[];weight=[]
    for i,points in enumerate(gaps['points']):
        xy,z=project(points,camera);length=float(np.linalg.norm(xy[1]-xy[0]))
        n=max(1,int(np.ceil(length/.25)));t=(np.arange(n)+.5)/n
        uv.append(xy[0]+t[:,None]*(xy[1]-xy[0]));depth.append(1/((1-t)/z[0]+t/z[1]))
        seg.append(np.full(n,i,np.int32));weight.append(np.full(n,length/n))
    uv=np.concatenate(uv);depth=np.concatenate(depth);seg=np.concatenate(seg);weight=np.concatenate(weight)
    hit,face,region=cast_points(mesh,camera,uv)
    inside=(uv[:,0]>=0)&(uv[:,1]>=0)&(uv[:,0]<camera['width'])&(uv[:,1]<camera['height'])
    status=np.zeros(len(uv),np.uint8);status[~inside|~np.isfinite(hit)]=1
    status[(status==0)&(region!=4)]=2;status[(status==0)&(np.abs(depth-hit)>.004)]=3;status[depth<=.2]=4
    samples=dict(uv=uv,segment_index=seg,gap_id=gaps['stroke_id'][seg],length_weight=weight,status=status,
                 center_depth=depth,hit_depth=hit,hit_face=face)
    s=sample_support(samples,support);samples['support']=s
    for key in pair:samples[key+'_alpha']=sample_support(samples,pair[key])
    visible=status==0;summary=dict(projected_length=float(weight.sum()),proxy_visible_length=float(weight[visible].sum()),
        rejected_length={str(k):float(weight[status==k].sum()) for k in (1,2,3,4)},gap_count=len(np.unique(samples['gap_id'])))
    for key,alpha in [('gap_before_S',samples['gap_only_alpha']),('gap_raw',samples['gap_only_alpha']*s),
                      ('gap_matched',samples['gap_only_alpha']*s*filled_scale),('old_raw',samples['old_alpha']*s),
                      ('filled_raw',samples['filled_alpha']*s),('filled_matched',samples['filled_alpha']*s*filled_scale),
                      ('new_raw',samples['new_coverage_alpha']*s)]:
        present=alpha>.05
        summary[key]=dict(visible_supported_length=float(weight[visible&present].sum()),
                          visible_missing_length=float(weight[visible&~present].sum()),
                          occluded_supported_length=float(weight[~visible&present].sum()))
    summary['scope']='Samples of added planned gaps only; alpha from union masks may include another gap/stroke; exact proxy rays, not independent surface/temporal GT. Incremental coverage excludes legacy coverage before downsampling.'
    return samples,summary
