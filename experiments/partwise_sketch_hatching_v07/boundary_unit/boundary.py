"""Paired, camera-independent gaps on immutable saved surface polylines.

B centers one gap on a frozen field-graph excluded face transition. C places
the same gap inside the longest remaining edge-free interval of that parent.
The whole parent is retained when no pair is possible. No path is extended.
"""
import runtime
import numpy as np

GAP=.035
EPS=1e-11

def slice_path(path,start,end,stroke_id):
    lengths=np.linalg.norm(path['points'][:,1]-path['points'][:,0],axis=1)
    cumulative=np.r_[0.,np.cumsum(lengths)];pieces={k:[] for k in path}
    for i,length in enumerate(lengths):
        lo=max(start,cumulative[i]);hi=min(end,cumulative[i+1])
        if hi-lo<=EPS:continue
        for key,values in path.items():
            value=values[i].copy()
            if key in ('points','bary'):
                if lo>cumulative[i] or hi<cumulative[i+1]:
                    t0=(lo-cumulative[i])/length;t1=(hi-cumulative[i])/length
                    value=np.stack([(1-t0)*values[i,0]+t0*values[i,1],(1-t1)*values[i,0]+t1*values[i,1]])
            elif key=='stroke_id':value=np.asarray(stroke_id,dtype=values.dtype)
            pieces[key].append(value)
    return {k:np.asarray(v,dtype=path[k].dtype).reshape((-1,)+path[k].shape[1:]) for k,v in pieces.items()}

def choose_pair(total,crossings,gap):
    for center,left,right in crossings:
        lo=center-gap/2;hi=center+gap/2
        if lo<=EPS or hi>=total-EPS:continue
        breaks=sorted(set([0.,total]+[s for s,_,_ in crossings]))
        intervals=[]
        for a,b in zip(breaks[:-1],breaks[1:]):
            # Subtract the complete B interval before choosing the longest C interval.
            for x,y in ((a,min(b,lo)),(max(a,hi),b)):
                if y-x>gap+2*EPS:intervals.append((x,y))
        if not intervals:continue
        a,b=min(intervals,key=lambda xy:(-(xy[1]-xy[0]),xy[0]))
        c=(a+b)/2;return dict(B_interval=[lo,hi],C_interval=[c-gap/2,c+gap/2],
            excluded_crossing_arc=center,excluded_face_pair=[left,right],C_available_interval=[a,b])
    return None

def paired_gaps(paths,excluded_pairs,gap=GAP,b_offset=2_000_000_000_000,c_offset=3_000_000_000_000):
    if gap!=GAP:raise ValueError('Only the frozen inherited gap is authorized')
    excluded={tuple(sorted(map(int,pair))) for pair in np.asarray(excluded_pairs).reshape(-1,2)}
    results={'B':[],'C':[]};records=[]
    all_old=set(map(int,paths['stroke_id']))
    for index,sid in enumerate(np.unique(paths['stroke_id'])):
        selection=paths['stroke_id']==sid;p={k:a[selection] for k,a in paths.items()}
        points=p['points'];lengths=np.linalg.norm(points[:,1]-points[:,0],axis=1)
        if (lengths<=0).any():raise ValueError('zero length source segment')
        if len(points)>1:np.testing.assert_allclose(points[:-1,1],points[1:,0],atol=1e-8,rtol=0)
        cumulative=np.cumsum(lengths);total=float(cumulative[-1]);crossings=[]
        for i in range(len(points)-1):
            left,right=int(p['face'][i]),int(p['face'][i+1])
            if left!=right and tuple(sorted((left,right))) in excluded:crossings.append((float(cumulative[i]),left,right))
        pair=choose_pair(total,crossings,gap)
        record=dict(source_h_stroke_id=int(sid),original_parent_stroke_id=int(p.get('parent_stroke_id',p['stroke_id'])[0]),
            layer_id=int(p.get('layer_id',np.zeros(len(points),int))[0]),source_length=total,
            excluded_crossings=len(crossings),crossing_arcs=[v[0] for v in crossings],eligible=pair is not None)
        if pair is None:
            record['reason']='no_excluded_crossing' if not crossings else 'no_equal_gap_pair_with_two_nonempty_children'
            for arm in results:results[arm].append(p)
        else:
            record.update(pair);record['reason']='paired';record['removed_length']=gap;record['retained_length']=total-gap
            for arm,offset in [('B',b_offset),('C',c_offset)]:
                lo,hi=pair[arm+'_interval'];ids=[offset+2*index,offset+2*index+1]
                if all_old.intersection(ids):raise ValueError('new identity collision')
                children=[slice_path(p,0.,lo,ids[0]),slice_path(p,hi,total,ids[1])]
                if any(len(x['face'])==0 for x in children):raise ValueError('empty child')
                results[arm].extend(children);record[arm+'_child_ids']=ids
        records.append(record)
    arrays={arm:{k:np.concatenate([x[k] for x in group]) for k in paths} for arm,group in results.items()}
    if set(map(int,arrays['B']['stroke_id']))&set(map(int,arrays['C']['stroke_id']))-all_old:
        raise ValueError('B/C new identities overlap')
    return arrays['B'],arrays['C'],records
