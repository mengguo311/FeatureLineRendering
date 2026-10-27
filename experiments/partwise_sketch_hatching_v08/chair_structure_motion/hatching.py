"""Persistent mesh/plane intersections, joined only through actual mesh edges.

World-space paths are generated once and stored with face/barycentric anchors.
Authored region boundaries stop paths. A view never changes a hatch path.
"""
import runtime
import numpy as np

def cutting_normal(region, angle, plane=None):
    a=np.deg2rad(angle)
    if plane=='xz' or (plane is None and region==3):
        return np.array([np.cos(a),0.,np.sin(a)])
    return np.array([np.cos(a),np.sin(a),0.])

def validate_style(style):
    for k in ('angle','spacing','length','width'):
        if k not in style or not np.isfinite(style[k]):
            raise ValueError('style needs finite angle/spacing/length/width')
    if not .008<=style['spacing']<=.5 or not .02<=style['length']<=2. or not .2<=style['width']<=8.:
        raise ValueError('spacing [.008,.5], length [.02,2] world; width [.2,8] pixels')
    if style.get('plane','xy') not in ('xy','xz'):raise ValueError('cutting plane must be xy or xz')
    if type(style.get('cross_enabled',False)) is not bool:raise ValueError('cross_enabled must be boolean')
    for key,default,lo,hi in [('cross_angle',60.,5.,175.),('cross_spacing',.06,.008,.5),('ink_strength',.80,0.,1.)]:
        value=style.get(key,default)
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,float,np.number)) or not np.isfinite(value) or not lo<=value<=hi:
            raise ValueError(f'{key} must be finite in [{lo},{hi}]')

def layer_ids(paths):
    """Legacy assets have only layer0; new assets store explicit layer IDs."""
    return paths.get('layer_id',np.zeros(len(paths['points']),np.uint8))

def visibility_masks(paths, region):
    """Saved capsule support across manual splits; legacy paths use their owner.

    Bits refer to current proxy region labels, never Gaussian or semantic IDs.
    The face anchor still belongs to exactly one region. Only raster footprints
    retain the parent's support, so relabeling need not trim existing round caps.
    """
    masks=paths.get('visibility_mask', np.full(len(paths['points']), 1 << region, np.uint64))
    # Import validation accepts signed integer arrays too; NumPy cannot safely
    # combine a uint64 label buffer with an int64 scalar without this cast.
    return masks.astype(np.uint64,copy=False)

def cross_style(style):
    return dict(style,angle=style['angle']+style.get('cross_angle',60.),spacing=style.get('cross_spacing',.06))

def add_cross_layer(mesh,region,style,base):
    """Append only the new direction. Existing base arrays are never regenerated."""
    cross,stat=generate_region(mesh,region,cross_style(style))
    if not len(cross['points']):raise ValueError('cross layer has no proxy support at this spacing')
    if len(np.unique(cross['stroke_id']))>=500_000_000:raise ValueError('cross layer ID budget exceeded')
    cross['stroke_id']=cross['stroke_id']+500_000_000
    data={k:np.concatenate([base[k],cross[k]]) for k in ('points','bary','face','stroke_id')}
    if 'visibility_mask' in base:
        data['visibility_mask']=np.concatenate([visibility_masks(base,region),visibility_masks(cross,region)])
    data['layer_id']=np.concatenate([np.zeros(len(base['points']),np.uint8),np.ones(len(cross['points']),np.uint8)])
    stat.update(layer_id=1,angle_degrees=cross_style(style)['angle'],spacing=style.get('cross_spacing',.06))
    return data,stat

def generate_layers(mesh,region,style):
    data,stat=generate_region(mesh,region,style)
    if style.get('cross_enabled',False):
        data,cross=add_cross_layer(mesh,region,style,data)
        stat['cross_layer']=cross
    return data,stat

def generate_region(mesh, region, style):
    validate_style(style)
    ids=np.flatnonzero(mesh['regions']==region)
    if not len(ids):
        raise ValueError('region has no proxy faces')
    normal=cutting_normal(region,style['angle'],style.get('plane'))
    q=mesh['vertices']@normal
    qt=q[mesh['faces'][ids]]
    spacing=style['spacing'];max_length=style['length'];gap=.035
    first=int(np.floor(qt.min()/spacing));last=int(np.ceil(qt.max()/spacing))
    segments=[];barys=[];owners=[];stroke_ids=[];stroke=region*10**9
    candidate_segments=0;ambiguous_nodes=0
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
            if len(ends)!=2:
                continue
            index=len(records);records.append((int(face),np.asarray(ends),keys))
            for end,key in enumerate(keys):nodes.setdefault(key,[]).append((index,end))
        candidate_segments+=len(records)
        ambiguous_nodes+=sum(len(v)>2 for v in nodes.values())
        used=set()
        starts=sorted((key,items[0][0],items[0][1]) for key,items in nodes.items() if len(items)!=2)
        starts+= [(rec[2][0],i,0) for i,rec in enumerate(records)]
        for _,i,entry in starts:
            if i in used:continue
            arc=0.;piece=-1;path_id=None
            while i not in used:
                used.add(i);face,b,keys=records[i]
                if entry==1:b=b[::-1]
                xyz=b@mesh['tri'][face];length=float(np.linalg.norm(xyz[1]-xyz[0]))
                s=0.
                while s<length-1e-12:
                    absolute=arc+s;period=max_length+gap
                    current=int(np.floor((absolute+1e-10)/period));within=absolute-current*period
                    on=within<max_length-1e-10
                    end=min(length,s+max(1e-10,(max_length if on else period)-within))
                    if on and end-s>1e-10:
                        if current!=piece:
                            stroke+=1;path_id=stroke;piece=current
                        t0,t1=s/length,end/length
                        bb=np.stack([(1-t0)*b[0]+t0*b[1],(1-t1)*b[0]+t1*b[1]])
                        barys.append(bb);segments.append(bb@mesh['tri'][face]);owners.append(face);stroke_ids.append(path_id)
                    s=end
                arc+=length
                candidates=nodes[keys[1-entry]]
                if len(candidates)!=2:break
                nxt=[x for x in candidates if x[0]!=i]
                if not nxt:break
                i,entry=nxt[0]
    data=dict(points=np.asarray(segments,float).reshape(-1,2,3),bary=np.asarray(barys,float).reshape(-1,2,3),
              face=np.asarray(owners,np.int32),stroke_id=np.asarray(stroke_ids,np.int64))
    return data,dict(region=region,segments=len(segments),paths=len(np.unique(stroke_ids)),
                     candidate_segments=candidate_segments,ambiguous_nodes=ambiguous_nodes,
                     length_world=float(np.linalg.norm(np.diff(data['points'],axis=1),axis=2).sum()),
                     construction='parallel world planes; exact shared mesh-edge continuation; periodic arclength gaps; authored face-region stop')
