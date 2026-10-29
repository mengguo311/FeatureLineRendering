from runtime import *
from core import *
from assetio import *
from collections import Counter

REASONS={'not_processed':0,'too_short':1,'protected_corner_piece':2,'degenerate':3,'accepted':4,
         'displacement':5,'angle':6,'length':7,'support_tube':8,'bend':9,'sag_or_bend_sign':10,'original':11}
def roughness(t,pid):
    valid=pid[1:]==pid[:-1];c=np.sum(t[1:]*t[:-1],axis=1)[valid]
    angle=np.degrees(np.arccos(np.clip(c,-1,1)))
    return dict(mean_adjacent_angle_deg=float(angle.mean()),rms_adjacent_angle_deg=float(np.sqrt(np.mean(angle**2))),p95_adjacent_angle_deg=float(np.quantile(angle,.95)))
def main(scene):
    check_budget(180);starttime=time.monotonic();dest=OUT/scene;dest.mkdir(exist_ok=True)
    status=json.loads((OUT/'STATUS.json').read_text());states=status['scenes'];states[scene]='PARTIAL';state('SCENE_RUNNING',scenes=states,scene=scene)
    js(dest/'START.json',dict(scene=scene,utc=now(),configuration_sha256=sha(OUT/'config.json')))
    inp=BASE/'arms/C/scenes'/scene/'full';a=load_np(inp/'gaussians.npz');s=load_np(inp/'SHARED_CONTROL_AND_SAMPLING.npz');parents=json.loads((inp/'parents.json').read_text())
    fmt,_=renderer_modules();raw=fmt.read_ply(inp/'gaussians.ply');n=len(a['means']);m=len(s['piece_control_indices'])
    assert n=={'scan24':458490,'ficus':285956,'scan65':279616}[scene]
    for k in ('primitive_id','internal_piece_id','arc_t','opacity'):np.testing.assert_array_equal(s[k],a[k])
    reconstructed=(s['control'][s['control_index']]*s['basis'][:,:,None]).sum(1)
    err=float(np.max(abs(reconstructed-a['means'])));assert err<1e-10
    oldt=unit((s['control'][s['control_index']]*s['derivative_basis'][:,:,None]).sum(1))
    piece=a['internal_piece_id'];assert (np.diff(piece)>=0).all();assert (np.diff(a['primitive_id'])>=0).all()
    pstart=np.searchsorted(piece,np.arange(m+1));assert (np.diff(pstart)>0).all()
    parent_piece=a['primitive_id'][pstart[:-1]];parent_starts=np.searchsorted(parent_piece,np.arange(len(parents)+1))
    js(dest/'AUDIT.json',dict(kernels=n,pieces=m,parents=len(parents),controls=len(s['control']),means_reconstruction_max=err,
        all_samples=True,confidence='UNKNOWN; opacity not used as confidence',source_GS_ids='UNKNOWN',original_roughness=roughness(oldt,a['primitive_id']),
        provenance_files={name:sha(inp/name) for name in ('parents.json','ASSOCIATIONS.json','OBSERVATION_TO_PARENT.npz','OBSERVATIONS.npz','SHARED_CONTROL_AND_SAMPLING.npz','LENGTH_AND_PARENT.npz')}))
    js(dest/'LEDGER_REASONS.json',REASONS)
    methods={}
    for name in ('DIRECT','HOUGH'):
        methods[name]=dict(means=a['means'].copy(),tangent=oldt.copy(),curves=build_curve_state(s,a),
            ledger=dict(reason=np.zeros(n,np.uint8),processed=np.zeros(n,bool),window_id=np.full(n,-1,np.int32),hough_group_id=np.full(n,-1,np.int32),hough_support=np.zeros(n,bool)),
            stats=dict(method=name,actual_fitter_calls=0,actual_irls_iterations=0,reused_direct_windows=0,accepted_windows=0,rejections={},point_direction_votes=0,hough_valid_groups=0,hough_guided_windows=0,hough_support_kernels=0))
    windows=0;near_count=0;protected=0;too_short=0;vote_start=time.monotonic()
    with (dest/'WINDOWS.jsonl').open('w') as log:
        for pid in range(len(parents)):
            if pid%100==0:check_budget(180)
            first,last=parent_starts[pid:pid+2];pairs=s['piece_control_indices'][first:last]
            assert len(pairs)>0
            assert np.array_equal(pairs[:-1,1],pairs[1:,0])
            P=np.vstack([s['control'][pairs[0,0]],s['control'][pairs[:,1]]]);closed=bool(parents[pid]['closed'])
            if closed:assert np.array_equal(P[0],P[-1])
            corners,guard=corner_mask(P,closed);T=knot_tangents(P,closed)
            edge=0
            while edge<len(pairs):
                stop=edge+1
                if not guard[edge]:
                    while stop<len(pairs) and stop-edge<CFG['window_pieces'] and not guard[stop]:stop+=1
                j0,j1=int(first+edge),int(first+stop);lo,hi=int(pstart[j0]),int(pstart[j1]);ids=slice(lo,hi)
                windows+=1;record=dict(window_id=windows-1,parent_id=pid,piece_start=j0,piece_stop=j1,kernels=hi-lo)
                for v in methods.values():v['ledger']['window_id'][ids]=windows-1;v['ledger']['processed'][ids]=True
                skip='protected_corner_piece' if guard[edge] else 'too_short' if stop-edge<3 or hi-lo<3 else None
                sub=P[edge:stop+1];ds=np.linalg.norm(np.diff(sub,axis=0),axis=1);L=float(ds.sum());p=float(np.median(s['pixel'][ids]))
                if L<1e-10*p or np.linalg.norm(sub[-1]-sub[0])<1e-10*p:skip='degenerate'
                if skip:
                    protected+=hi-lo if skip=='protected_corner_piece' else 0;too_short+=hi-lo if skip=='too_short' else 0
                    for v in methods.values():v['ledger']['reason'][ids]=REASONS[skip]
                    record.update(status=skip);log.write(json.dumps(record)+'\n');edge=stop;continue
                cum=np.r_[0.,np.cumsum(ds)];localpiece=piece[ids]-j0;t=(cum[localpiece]+s['basis'][ids,1]*ds[localpiece])/L
                x=a['means'][ids];ot=oldt[ids];pix=s['pixel'][ids];anchor,axis=tls(x)
                sag=np.linalg.norm(np.cross(x-sub[0],unit(sub[-1]-sub[0])),axis=1).max()/p
                angular=np.degrees(np.arccos(np.clip(abs(ot@axis),0,1)))
                near=bool(np.quantile(angular,CFG['near_straight_tangent_quantile'])<=CFG['near_straight_angle_deg'] and sag<=CFG['near_straight_sag_p'])
                near_count+=int(near);record['near_straight']=near
                B=fit_cubic(sub,t,x,T[edge],T[stop],p,axis if near else None,anchor if near else None)
                ok,reason,met=fidelity(B,sub,t,x,ot,pix,p)
                direct=methods['DIRECT'];direct['stats']['actual_fitter_calls']+=1;direct['stats']['actual_irls_iterations']+=CFG['irls_steps']
                candidates={'DIRECT':(B,ok,reason,met)};hh=methods['HOUGH']
                if near:
                    vote=hough_axis(x,ot,piece[ids],p,sub[-1]-sub[0]);hh['stats']['point_direction_votes']+=vote['point_direction_votes']
                    record['hough']={k:v for k,v in vote.items() if k not in ('axis','anchor','support')}
                    if vote['axis'] is not None:
                        hh['stats']['hough_valid_groups']+=1;hh['stats']['hough_support_kernels']+=vote['support_count'];hh['stats']['hough_guided_windows']+=1
                        localids=np.arange(lo,hi)[vote['support']];hh['ledger']['hough_group_id'][localids]=windows-1;hh['ledger']['hough_support'][localids]=True
                        BH=fit_cubic(sub,t,x,T[edge],T[stop],p,vote['axis'],vote['anchor']);okh,rh,mh=fidelity(BH,sub,t,x,ot,pix,p)
                        hh['stats']['actual_fitter_calls']+=1;hh['stats']['actual_irls_iterations']+=CFG['irls_steps'];candidates['HOUGH']=(BH,okh,rh,mh)
                if 'HOUGH' not in candidates:candidates['HOUGH']=candidates['DIRECT'];hh['stats']['reused_direct_windows']+=1
                for name,(curve,accepted,why,metric) in candidates.items():
                    v=methods[name];v['ledger']['reason'][ids]=REASONS[why];record[name]=dict(accepted=accepted,reason=why,**metric)
                    if accepted:
                        q,d=eval_curve(curve,t);v['means'][ids]=q;v['tangent'][ids]=unit(d);apply_curve(v['curves'],j0,j1,ids,t,curve);v['stats']['accepted_windows']+=1
                    else:v['stats']['rejections'][why]=v['stats']['rejections'].get(why,0)+1
                log.write(json.dumps(record,allow_nan=False)+'\n');edge=stop
            if pid%1000==0:
                log.flush();print('PROGRESS',scene,'parent',pid,'windows',windows,'seconds',round(time.monotonic()-starttime,2),flush=True)
    js(dest/'PROCESSING.json',dict(windows=windows,near_straight_windows=near_count,protected_kernels=protected,too_short_kernels=too_short,fitting_seconds=time.monotonic()-vote_start,all_kernels_processed=True))
    # The complete original carrier is exported as an explicit reloadable comparator.
    origledger=dict(reason=np.full(n,REASONS['original'],np.uint8),processed=np.ones(n,bool),window_id=methods['DIRECT']['ledger']['window_id'])
    export_arm(dest/'ORIGINAL',a,s,raw,oldt,a['means'],oldt,build_curve_state(s,a),origledger,dict(method='ORIGINAL',actual_fitter_calls=0,actual_irls_iterations=0,roughness=roughness(oldt,a['primitive_id'])))
    for name,v in methods.items():
        assert v['ledger']['processed'].all();assert (v['ledger']['reason']!=0).all()
        v['stats']['roughness']=roughness(v['tangent'],a['primitive_id']);v['stats']['window_count']=windows
        export_arm(dest/name,a,s,raw,oldt,v['means'],v['tangent'],v['curves'],v['ledger'],v['stats'])
    delta=np.linalg.norm(methods['HOUGH']['means']-methods['DIRECT']['means'],axis=1)
    js(dest/'METHOD_COMPARISON.json',dict(hough_vs_direct_changed_means=int((delta>1e-12).sum()),hough_vs_direct_max_delta_pixel=float((delta/s['pixel']).max(initial=0)),
         hough_vs_direct_mean_delta_pixel=float(np.mean(delta/s['pixel'])),geometry_gain='NOT_ESTABLISHED; roughness is only a diagnostic',physical_group_purity='UNKNOWN',
         groups_cross_parent=False,confirmed_new_links=0,seconds=time.monotonic()-starttime))
    js(dest/'GEOMETRY_EXIT.json',dict(returncode=0,utc=now(),seconds=time.monotonic()-starttime,complete_geometry=True,rendering='PENDING'))
    state('GEOMETRY_EXPORTED',scene=scene,seconds=time.monotonic()-starttime)
if __name__=='__main__':main(sys.argv[1])
