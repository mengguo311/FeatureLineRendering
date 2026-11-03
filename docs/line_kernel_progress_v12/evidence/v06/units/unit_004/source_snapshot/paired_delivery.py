"""Paired progress and deterministic native-image diagnostics; no model fitting."""
from runtime_io import *

def save_pair(out,binding,context_id,choices,receipts):
    out=Path(out)
    nz(out/'LINKS.npz',**{k:np.asarray(v,np.int64) for k,v in choices.items()})
    js(out/'RECEIPTS.json',dict(context_id=context_id,arms=receipts))
    checkpoint(out,['LINKS.npz','RECEIPTS.json'],binding,'PAIRED_COMPONENT_COMPLETE')

def restore_pair(out,binding,context_id):
    cp=verify_checkpoint(out,binding);assert cp['stage']=='PAIRED_COMPONENT_COMPLETE'
    rec=json.loads((Path(out)/'RECEIPTS.json').read_text());assert rec['context_id']==context_id
    with np.load(Path(out)/'LINKS.npz',allow_pickle=False) as z:choices={a:z[a].tolist() for a in ('greedy','joint')}
    return choices,rec['arms']

def evidence_rows(d,ids):
    ids=sorted(set(ids))
    return np.sort(np.concatenate([d['leaves'][cid].rows for cid in ids])) if ids else np.empty(0,np.int64)

def prior_scope_receipt(c,selected,processed,contexts):
    if 'prior_scope' not in c:return dict(status='NOT_APPLICABLE_FIXTURE')
    prior=json.loads(Path(c['prior_scope']).read_text())
    scope=set(next(x for x in prior['contexts'] if x['context_id']==1)['eligible_edge_ids'])
    needed={ctx['context_id'] for ctx in contexts if scope.intersection(ctx['eligible_edge_ids'])}
    assert scope=={eid for ctx in contexts for eid in ctx['eligible_edge_ids'] if eid in scope},'PRIOR_EDGE_MISSING'
    if not needed.issubset(processed):return dict(status='NOT_RUN_UNPROCESSED_COMPONENT',required_components=sorted(needed))
    actual={}
    for arm in ('greedy','joint'):
        with np.load(c['prior_links'][arm],allow_pickle=False) as z:expected=sorted(set(z['record_index'].tolist())&scope)
        actual[arm]=sorted(set(selected[arm])&scope)
        assert actual[arm]==expected,'PRIOR_SOLVED_SCOPE_MISMATCH '+arm
    return dict(status='EXACT_SELECTED_LINKS_REPRODUCED',eligible_records=sorted(scope),actual=actual,no_extra_fit_or_solve=True)

def diagnostic_cases(c,d,saved,contexts,seeds):
    # Selection is symmetric in both arms; no images are consulted.
    bykey={};keys={};missing=[]
    def key(g):return tuple((int(z['carrier_id']),bool(z['reverse'])) for z in g['leaves'])
    for arm,(_,groups) in saved.items():
        keys[arm]={key(g) for g in groups}
        for g in groups:bykey.setdefault(key(g),g)
    rank=lambda k:(-bykey[k]['supported_length_p'],bykey[k]['edge_id'],k)
    chosen={}
    def take(ks,n,label):
        ranked=sorted(ks,key=rank)[:n]
        if not ranked:missing.append(label)
        for k in ranked:chosen.setdefault(k,[]).append(label)
    for tag,ids in seeds[:len(c['seed_groups'])]:
        for arm in ('greedy','joint'):take([k for k in keys[arm] if set(x[0] for x in k)&set(ids)],1,tag+'_'+arm)
    take(keys['greedy']^keys['joint'],3,'top3_different_paths')
    take(bykey,3,'top3_supported_paths')
    take([k for k in bykey if len(k)>=3],1,'largest_three_leaf_path')
    kinds={int(cid):str(kind) for cid,kind in zip(d['arrays']['carrier_id'],d['arrays']['kind'])}
    take([k for k in bykey if any(kinds[x[0]]=='polyline' for x in k)],1,'largest_polyline_leaf_path')
    incident={}
    for i,(a,b) in enumerate(d['pairs']):incident.setdefault(a,[]).append(i);incident.setdefault(b,[]).append(i)
    component={cid:ctx for ctx in contexts for cid in ctx['carriers']}
    cases=[]
    for k in sorted(chosen,key=rank):
        core=sorted(x[0] for x in k);comp_ids=sorted({component[x]['context_id'] for x in core})
        comps=[ctx for ctx in contexts if ctx['context_id'] in comp_ids]
        halo=sorted({cid for ctx in comps for cid in ctx['evidence_carriers']})
        cases.append(dict(case_id='PATH_'+str(bykey[k]['edge_id'])+'_'+hashlib.sha256(repr(k).encode()).hexdigest()[:8],labels=chosen[k],core_carriers=core,evidence_carriers=halo,component_ids=comp_ids,incident_record_ids=sorted({i for ctx in comps for i in ctx['incident_record_ids']})))
    for a,b in c['negative_pairs']:
        core=[a,b];records=sorted(set(incident.get(a,[])+incident.get(b,[])));halo=set(core)
        for i in records:halo.update(d['pairs'][i])
        # Include full decision components and their evidence if either seed participates.
        comps={component[x]['context_id']:component[x] for x in core if x in component}
        for ctx in comps.values():halo.update(ctx['evidence_carriers']);records=sorted(set(records)|set(ctx['incident_record_ids']))
        cases.append(dict(case_id='NEGATIVE_'+str(a)+'_'+str(b),labels=['saved_negative_unknown_truth'],core_carriers=core,evidence_carriers=sorted(halo),component_ids=sorted(comps),incident_record_ids=records))
    return dict(cases=cases,missing=missing,selection='symmetric union over both arms; support descending then ID; not physical labels')

def crop_pair(paths,outputs):
    images=[]
    for path in paths:
        with Image.open(path) as im:images.append(im.convert('RGB'))
    arr=[np.asarray(im) for im in images]
    assert arr[0].shape==arr[1].shape
    mask=np.any(arr[0]<254,axis=2)|np.any(arr[1]<254,axis=2);yy,xx=np.where(mask)
    if not len(xx):return dict(empty=True,bbox=None,crops=[],native_paths=list(map(str,paths)))
    h,w=mask.shape;box=[max(0,int(xx.min())-16),max(0,int(yy.min())-16),min(w,int(xx.max())+17),min(h,int(yy.max())+17)]
    for im,out in zip(images,outputs):
        crop=im.crop(box);crop=crop.resize((crop.width*4,crop.height*4),Image.Resampling.NEAREST)
        if not Path(out).exists():atomic(out,lambda f,im=crop:im.save(f,format='PNG'))
    return dict(empty=False,bbox=box,scale=4,interpolation='nearest',touches_native_boundary=bool(xx.min()==0 or yy.min()==0 or xx.max()==w-1 or yy.max()==h-1),crops=list(map(str,outputs)),native_paths=list(map(str,paths)))

def render_diagnostics(unit,c,d,saved,selection,render,cams,guard,binding):
    base=Path(unit)/'scenes/scan24';root=base/'diagnostics';root.mkdir(parents=True,exist_ok=True)
    if not (root/'SELECTION.json').exists():js(root/'SELECTION.json',selection)
    images={a:[] for a in saved};crops=[]
    for case in selection['cases']:
        guard();core=evidence_rows(d,case['core_carriers']);halo=evidence_rows(d,case['evidence_carriers'])
        rowpath=root/(case['case_id']+'_ROWS.npz')
        if not rowpath.exists():nz(rowpath,core_rows=core,evidence_rows=halo,core_carriers=np.array(case['core_carriers']),evidence_carriers=np.array(case['evidence_carriers']),incident_record_ids=np.array(case['incident_record_ids']))
        for kind,rr in [('GROUP',core),('CONTEXT',halo)]:
            for cam in cams:
                pair=[];outc=[]
                for arm,(m,_) in saved.items():
                    guard();out=base/'stages'/arm/'diagnostics';out.mkdir(parents=True,exist_ok=True)
                    name=case['case_id']+'_'+kind+'_'+cam['view'];path=out/(name+'.png');pair.append(path);outc.append(out/(name+'_CROP4.png'))
                    if not path.exists():
                        sub={k:d['asset'][k][rr] for k in ('means','covariance','opacity')};sub['colors']=colors(m['edge_id'][rr])
                        save_image(path,render(sub,cam,(1,1,1),.0144)['rgb'])
                    images[arm].append(str(path.relative_to(base/'stages'/arm)))
                guard();receipt=crop_pair(pair,outc);receipt.update(case_id=case['case_id'],kind=kind,view=cam['view']);crops.append(receipt)
                if not receipt['empty']:
                    for arm,path in zip(saved,outc):images[arm].append(str(path.relative_to(base/'stages'/arm)))
        # Versioned diagnostic progress; complete prior cases survive later failure.
        cp=root/(case['case_id']+'_CHECKPOINT.json')
        if not cp.exists():js(cp,dict(complete=True,config_sha256=binding,rows_sha256=sha(rowpath),images={str(p.relative_to(unit)):sha(p) for a in saved for p in (base/'stages'/a/'diagnostics').glob(case['case_id']+'*.png')}))
    if not (root/'CROPS.json').exists():js(root/'CROPS.json',dict(records=crops,rule='union RGB8<254, pad16 clip 4xnearest; no camera change'))
    return images
