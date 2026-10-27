"""Sparse own-path observations of original CPU-GS accepted events, not ownership."""
import runtime
import numpy as np

def stencil(uv,inside,width,height):
    rows=[];pixels=[];offsets=[0];weights=[]
    for (x,y),valid in zip(uv,inside):
        local={}
        if valid:
            if not (0<=x<=width-1 and 0<=y<=height-1):raise ValueError('invalid in-frame anchor')
            ix,iy=int(np.floor(x)),int(np.floor(y));tx,ty=x-ix,y-iy
            for xx,yy,b in [(ix,iy,(1-tx)*(1-ty)),(min(ix+1,width-1),iy,tx*(1-ty)),
                            (ix,min(iy+1,height-1),(1-tx)*ty),(min(ix+1,width-1),min(iy+1,height-1),tx*ty)]:
                if b>0:local[(xx,yy)]=local.get((xx,yy),0.)+float(b)
        for xy,b in local.items():pixels.append(xy);weights.append(b)
        offsets.append(len(pixels))
    xy=np.asarray(sorted(set(pixels)),np.int32).reshape(-1,2)
    lookup={tuple(v):i for i,v in enumerate(xy)}
    sid=np.array([lookup[v] for v in pixels],np.int64)
    return xy,np.asarray(offsets,np.int64),sid,np.asarray(weights,float)

def make_csr(anchors,ref_offsets,ref_sid,beta,trace,status,own,sample_ok,pixel_depth,strength,depth_tolerance):
    n=len(anchors);order=np.argsort(trace['sample_index'],kind='stable');sorted_sid=trace['sample_index'][order]
    chunks={k:[] for k in trace if k!='sample_index'}
    chunks.update(pixel_index=[],pixel_weight=[],own_ink=[],depth_consistent=[],sample_consistent=[],region_strength=[],eligible=[])
    offsets=[0];raw=[];goodmass=[];smass=[];ownmean=[];states=[]
    ids=np.asarray(trace['source_index'])
    if len(ids) and ((ids<0).any() or (ids>=len(strength)).any()):raise ValueError('original source ID outside universe')
    for j,a in enumerate(anchors):
        ownmean.append(sum(beta[r]*own[j,ref_sid[r]] for r in range(ref_offsets[j],ref_offsets[j+1])))
        total=accepted=regional=0.;count=0
        for r in range(ref_offsets[j],ref_offsets[j+1]):
            s=int(ref_sid[r]);ix=order[np.searchsorted(sorted_sid,s,'left'):np.searchsorted(sorted_sid,s,'right')]
            d=trace['depth'][ix];depth_ok=np.isfinite(d)&np.isfinite(pixel_depth[s])&(np.abs(d-pixel_depth[s])<=depth_tolerance)
            rs=strength[ids[ix]]
            eligible=depth_ok & bool(sample_ok[s]) & (status[j]=='visible') & (own[j,s]>1/255) & (rs>0)
            for k in trace:
                if k!='sample_index':chunks[k].extend(trace[k][ix])
            chunks['pixel_index'].extend([s]*len(ix));chunks['pixel_weight'].extend([beta[r]]*len(ix))
            chunks['own_ink'].extend([own[j,s]]*len(ix));chunks['depth_consistent'].extend(depth_ok)
            chunks['sample_consistent'].extend([bool(sample_ok[s])]*len(ix));chunks['region_strength'].extend(rs);chunks['eligible'].extend(eligible)
            w=beta[r]*trace['weight'][ix];total+=w.sum();accepted+=w[eligible].sum();regional+=(w*rs).sum();count+=len(ix)
        offsets.append(offsets[-1]+count);raw.append(total);goodmass.append(accepted);smass.append(regional)
        state=str(status[j]) if status[j]!='visible' else 'no_own_ink' if ownmean[-1]<=1/255 else 'supported_sample' if accepted>0 else 'no_eligible_source'
        states.append(state)
    integer={'source_index','culled_local_index','pixel_index'};boolean={'eligible','depth_consistent','sample_consistent'}
    out={k:np.asarray(v,np.int64 if k in integer else bool if k in boolean else float) for k,v in chunks.items()}
    out.update(offsets=np.asarray(offsets,np.int64),stroke_id=np.asarray([a['stroke_id'] for a in anchors],np.int64),
        fraction=np.asarray([a['fraction'] for a in anchors]),weighted_mass=np.asarray(raw),eligible_mass=np.asarray(goodmass),
        regional_mass=np.asarray(smass),own_pre=np.asarray(ownmean),state=np.asarray(states),visibility=np.asarray(status),
        ref_offsets=np.asarray(ref_offsets),ref_pixel_index=np.asarray(ref_sid),ref_weight=np.asarray(beta))
    return out

def select_highlights(csr,stroke_ids,source_count):
    output={}
    for stroke in stroke_ids:
        blocks=[]
        for k in np.flatnonzero(csr['stroke_id']==stroke):
            lo,hi=csr['offsets'][k:k+2];mask=csr['eligible'][lo:hi]
            blocks.extend(csr['source_index'][lo:hi][mask])
        ids=np.unique(np.asarray(blocks,np.int64))
        if len(ids) and ((ids<0).any() or (ids>=source_count).any()):raise ValueError('original source ID outside universe')
        output[int(stroke)]=ids
    return output

def query_arrays(csr,stroke,fraction):
    indices=np.flatnonzero(csr['stroke_id']==stroke)
    if not len(indices):return dict(stroke_id=int(stroke),state='not_sampled',scope='No support inferred for unmeasured paths or regenerated identities')
    indices=indices[np.isclose(csr['fraction'][indices],fraction,atol=1e-12,rtol=0)]
    if len(indices)!=1:raise ValueError('anchor fraction was not sampled; use 0.2, 0.5 or 0.8')
    k=int(indices[0]);lo,hi=map(int,csr['offsets'][k:k+2])
    fields=['source_index','alpha','T','weight','depth','center_z','pixel_index','pixel_weight','own_ink','depth_consistent','sample_consistent','region_strength','eligible']
    return dict(stroke_id=int(stroke),fraction=float(fraction),anchor_index=k,state=str(csr['state'][k]),
        visibility=str(csr['visibility'][k]),accepted_events=hi-lo,eligible_events=int(csr['eligible'][lo:hi].sum()),
        weighted_mass=float(csr['weighted_mass'][k]),eligible_mass=float(csr['eligible_mass'][k]),
        regional_mass=float(csr['regional_mass'][k]),own_pre=float(csr['own_pre'][k]),
        events={f:csr[f][lo:hi].tolist() for f in fields},
        scope='All raw events retained at the bilinear pixel stencil; eligible is a proxy-based diagnostic, not physical ownership. Unsampled path intervals uncertified.')
