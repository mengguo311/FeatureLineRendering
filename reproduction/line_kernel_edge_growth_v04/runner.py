"""One scene/level child. Checkpointing never modifies a predecessor."""
from common import *
from core import Engine, arc, project, union_intervals
import argparse, pickle, traceback
from collections import Counter

def load_scene(scene):
    source=BASE/scene/'full';old=OLD/scene;lock=json.loads((ORCH/'INPUT_LOCK.json').read_text())['files'];sealed=json.loads((ORCH/'V03_SEALED_REFERENCE.json').read_text())['files']
    files=[source/'gaussians.npz',source/'gaussians.ply',source/'SHARED_CONTROL_AND_SAMPLING.npz',old/'REPRESENTATIVES.npz',old/'baseline/MEMBERSHIP.npz',old/'baseline/CHAINS.npz',old/'baseline/GROUPS.json']
    hashes={str(f):sha(f) for f in files}
    for f in files:
        expected=lock.get(str(f)) if str(f).startswith(str(source)) else sealed.get(str(f.relative_to(OLD)))
        assert expected is not None and hashes[str(f)]==expected,('input hash',str(f))
    a=dict(np.load(source/'gaussians.npz'));r=dict(np.load(old/'REPRESENTATIVES.npz'));base=dict(np.load(old/'baseline/MEMBERSHIP.npz'));chains=dict(np.load(old/'baseline/CHAINS.npz'));p=json.loads((old/'baseline/GROUPS.json').read_text())['p']
    assert len(a['means'])==COUNTS[scene]
    with np.load(source/'SHARED_CONTROL_AND_SAMPLING.npz') as z:
        d=(z['control'][z['control_index']]*z['derivative_basis'][:,:,None]).sum(1)
    norm=np.linalg.norm(d,axis=1);t=d/np.maximum(norm[:,None],1e-15)
    return a,r,base,chains,p,t,hashes

def group_tables(engine,ids):
    groups=[]
    for cid in np.unique(ids[ids>=0]):
        c=engine.carriers[int(cid)];rows=c.rows;intervals,length,run,gap,total=engine.support(c.reps,c.q)
        parents,counts=np.unique(engine.a['primitive_id'][rows],return_counts=True);pieces=np.unique(engine.a['internal_piece_id'][rows]);contributions=[]
        for pid,n in zip(parents,counts):
            reps=c.reps[np.isin(engine.a['primitive_id'][engine.r['mid'][c.reps]],pid)];ln=engine.support(reps,c.q)[1] if len(reps) else 0.
            contributions.append(dict(parent=int(pid),kernels=int(n),supported_length_p=ln))
        groups.append(dict(edge_id=int(cid),kernels=len(rows),representatives=len(c.reps),model=c.kind,valid_v04=c.valid,baseline_preserved=c.baseline,provisional=True,origins=list(c.origins),version=c.version,old_parent_count=len(parents),old_piece_count=len(pieces),parent_contributions=contributions,supported_length_p=length,longest_continuous_run_p=run,max_gap_p=gap,total_gap_p=total,carrier_length_p=float(arc(c.q)[-1]),extent_p=np.ptp(engine.x[rows],axis=0).tolist()))
    return sorted(groups,key=lambda g:(-g['kernels'],g['edge_id']))

def export_carriers(path,engine):
    cc=[engine.carriers[k] for k in sorted(engine.carriers)];ko=[0];knots=[];ro=[0];reps=[];io=[0];intervals=[]
    for c in cc:
        knots.extend(c.q*engine.p);ko.append(len(knots));reps.extend(c.reps);ro.append(len(reps));ints=engine.support(c.reps,c.q)[0];intervals.extend(ints*engine.p);io.append(len(intervals))
    nz(path,carrier_id=np.array([c.cid for c in cc],np.int64),version=np.array([c.version for c in cc],np.int64),valid=np.array([c.valid for c in cc]),baseline=np.array([c.baseline for c in cc]),knot_offsets=np.array(ko),knots=np.asarray(knots),seed_offsets=np.array(ro),seedlets=np.asarray(reps,np.int32),interval_offsets=np.array(io),supported_intervals=np.asarray(intervals).reshape(-1,2))

def renders(scene,level,out,a,ids,groups,engine):
    hh=helpers();render=hh['render'];cams=json.loads((OUT/'CAMERAS.json').read_text())[scene];display={k:v for k,v in a.items()};display['colors']=colors(ids)
    nz(out/'DISPLAY_GAUSSIANS.npz',**display)
    cold=dict(np.load(out/'DISPLAY_GAUSSIANS.npz'))
    for k,v in a.items():
        if k!='colors':assert cold[k].dtype==v.dtype and cold[k].shape==v.shape and cold[k].tobytes()==v.tobytes(),k
    allitems=[];isolated=[];highlight=[]
    cross=[g for g in groups if g['old_parent_count']>1]
    by_length=sorted(cross,key=lambda g:(-g['supported_length_p'],g['edge_id']))[:3];selected={g['edge_id']:g for g in cross[:3]+by_length}
    js(out/'VISUAL_SELECTION.json',dict(rule='union of largest three cross-parent by kernels and by deduplicated supported length',groups=list(selected.values())))
    for cam in cams:
        guard(60);view=cam['view'];rgb=render(display,cam,background=(1,1,1),floor=.0144)['rgb'];f=out/(view+'_FULL.png');save_image(f,rgb);allitems.append((f'{scene} L{level} {view}: ALL kernels; UNKNOWN gray',f))
        if cam is cams[0]:
            replay=render(cold,cam,background=(1,1,1),floor=.0144)['rgb'];assert np.array_equal(np.uint8(np.rint(np.clip(replay,0,1)*255)),np.asarray(Image.open(f)))
        for rank,g in enumerate(selected.values()):
            mask=ids==g['edge_id'];asset={k:display[k][mask] for k in ('means','covariance','opacity','colors')};f=out/f'{view}_CROSS_ISOLATED_{rank+1}.png';save_image(f,render(asset,cam,(1,1,1),.0144)['rgb']);isolated.append((f"{view} ID {g['edge_id']} N={g['kernels']} parents={g['old_parent_count']}",f))
        hcolors=np.full_like(display['colors'],.68);mask=np.isin(ids,list(selected));hcolors[mask]=display['colors'][mask];hasset={k:display[k] for k in ('means','covariance','opacity')};hasset['colors']=hcolors
        f=out/(view+'_CROSS_HIGHLIGHT.png');save_image(f,render(hasset,cam,(1,1,1),.0144)['rgb']);highlight.append((f'{scene} L{level} {view}: selected cross-parent groups',f))
    panel(out/'FULL_PANEL.png',allitems,f'{scene} L{level}: original line Gaussian kernels')
    if isolated:panel(out/'CROSS_PARENT_PANEL.png',isolated,f'{scene} L{level}: native isolated kernels, fixed cameras')
    panel(out/'CROSS_HIGHLIGHT_PANEL.png',highlight,f'{scene} L{level}: whole asset and selected groups')
    # Source PLY is line-only. Display modifies DC colors only; all native geometry remains bit-exact.
    raw=hh['read_ply'](BASE/scene/'full/gaussians.ply');colored=raw.copy()
    for k in range(3):colored['f_dc_'+str(k)]=(display['colors'][:,k]-.5)/.28209479177387814
    PlyData([PlyElement.describe(colored,'vertex')],text=False,byte_order='<',comments=['Color-only v04; original dedicated line kernels; provisional membership in MEMBERSHIP.npz']).write(out/'DISPLAY.ply')
    coldraw=hh['read_ply'](out/'DISPLAY.ply')
    for k in raw.dtype.names:
        if not k.startswith('f_dc_'):assert raw[k].tobytes()==coldraw[k].tobytes(),k
    return dict(cold_load=True,all_original_noncolor_npz_fields_bitexact=True,display_ply_noncolor_fields_bitexact=True,cold_native_camera_rgb8_replay_bitexact=True,all_rows=len(ids),no_fitted_geometry_rendered=True)

def diagnostic_images(scene,out,engine,a,ids,groups):
    """Final lineage and minimum-cost hard cases, with exact actual kernel rows."""
    render=helpers()['render'];cams=json.loads((OUT/'CAMERAS.json').read_text())[scene];items=[];selections=[]
    cross=[g for g in groups if g['old_parent_count']>1];rank=sorted(cross,key=lambda g:(-g['supported_length_p'],g['edge_id']))
    chosen=rank[:1]+[g for g in rank if g['model']=='polyline'][:1];chosen={g['edge_id']:g for g in chosen}
    for cid,g in chosen.items():
        rows=engine.carriers[cid].rows
        for lev in range(5):
            oldids=np.load(OUT/scene/f'L{lev}/MEMBERSHIP.npz')['edge_id'];col=colors(oldids[rows]) if lev<4 else colors(np.full(len(rows),cid))
            for cam in cams:
                asset={k:a[k][rows] for k in ('means','covariance','opacity')};asset['colors']=col;file=out/f"LINEAGE_{cid}_L{lev}_{cam['view']}.png";save_image(file,render(asset,cam,(1,1,1),.0144)['rgb']);items.append((f"Final ID {cid}; L{lev}; {cam['view']}; same original rows",file))
        selections.append(dict(edge_id=cid,kernel_rows=rows.tolist(),rule='largest length cross-parent plus largest curved cross-parent'))
    if items:panel(out/'LINEAGE_PANEL.png',items,f'{scene}: fixed row sets across all levels; original geometry')
    js(out/'LINEAGE_SELECTION.json',selections)
    # Replay exact historical carrier supports from initial seed IDs and the merge DAG.
    init=np.load(OUT/scene/'L0/CARRIERS.npz');versions={}
    for k,cid in enumerate(init['carrier_id']):versions[(int(cid),0)]=init['seedlets'][init['seed_offsets'][k]:init['seed_offsets'][k+1]]
    records=[];accepted=[]
    for lev in range(1,5):
        ev=json.loads((OUT/scene/f'L{lev}/LINEAGE.json').read_text())
        for e in ev:
            reps=np.r_[versions[tuple(e['inputs'][0])],versions[tuple(e['inputs'][1])]];versions[tuple(e['output'])]=reps
            accepted.append((lev,e,reps))
        records.extend(json.loads((OUT/scene/f'L{lev}/CANDIDATES.json').read_text()))
    negative=[];nitems=[]
    for label in ('parallel','branch','unsupported_gap','endpoint_gap','endpoint_tangent','ambiguous','turn','self_contact','residual'):
        choices=sorted([r for r in records if r['reason']==label],key=lambda r:(r['cost'],r['level'],r['a'],r['b']))
        if not choices:negative.append(dict(category=label,status='NO_RECORDED_CASE'));continue
        rec=choices[0];pre=np.load(OUT/scene/f"L{max(0,rec['level']-1)}/MEMBERSHIP.npz");owner=pre['carrier_id'];cids=np.unique(owner[[rec['a'],rec['b']]]);rows=np.flatnonzero(np.isin(owner,cids));negative.append(dict(category=label,record=rec,kernel_rows=rows.tolist(),context='pre-level source carriers containing proposal seed IDs; may be a subset of an in-pass accumulated carrier'))
        for cam in cams:
            asset={k:a[k][rows] for k in ('means','covariance','opacity')};asset['colors']=colors(owner[rows]);f=out/f"NEGATIVE_{label}_{cam['view']}.png";save_image(f,render(asset,cam,(1,1,1),.0144)['rgb']);nitems.append((f"{label}; {cam['view']}; smallest candidate cost",f))
    js(out/'NEGATIVE_SELECTION.json',negative)
    if nitems:panel(out/'NEGATIVE_PANEL.png',nitems,f'{scene}: real rejected / ambiguous source-carrier contexts')

def run(scene,level):
    guard(120);out=OUT/scene/f'L{level}';out.mkdir(parents=True,exist_ok=False);js(out/'START.json',dict(pid=os.getpid(),utc=now(),scene=scene,level=level));start=time.monotonic()
    a,r,base,chains,p,t,hashes=load_scene(scene);js(out/'INPUT_HASHES_BEFORE.json',hashes);e=Engine(a,r,t,p)
    if level==0:
        e.initialize(base['edge_id'],chains);prev=base['edge_id'].copy()
    else:
        with (OUT/scene/f'L{level-1}/STATE.pkl').open('rb') as f:state=pickle.load(f)
        e.carriers=state['carriers'];e.aux=state['aux'];e.next_version=state['next_version'];prev=np.load(OUT/scene/f'L{level-1}/MEMBERSHIP.npz')['edge_id'];e.level=level
        if level==1:
            for _ in range(2):print('POOL',scene,level,e.pass_once(True),flush=True)
        else:
            print('MERGE',scene,level,e.pass_once(False),flush=True);print('POOL',scene,level,e.pass_once(True),flush=True)
    ids,reason,aux,owner=e.primary(base['edge_id'])
    if level==0:assert np.array_equal(ids,base['edge_id']);reason=base['reason_code'].copy()
    assert np.all(ids[base['edge_id']>=0]>=0),'baseline membership loss'
    membership=dict(line_kernel_id=np.arange(len(ids),dtype=np.int64),edge_id=ids,previous_edge_id=prev,baseline_edge_id=base['edge_id'],carrier_id=owner,representative_id=r['kernel_rep'],reason_code=reason,baseline_reason_code=base['reason_code'],auxiliary_carrier_id=aux,provisional=np.ones(len(ids),bool),primitive_id=a['primitive_id'],internal_piece_id=a['internal_piece_id'],arc_t=a['arc_t'])
    nz(out/'MEMBERSHIP.npz',**membership);cold=dict(np.load(out/'MEMBERSHIP.npz'))
    for k in membership:assert np.array_equal(cold[k],membership[k],equal_nan=True),k
    groups=group_tables(e,ids);js(out/'GROUPS.json',dict(scene=scene,level=level,p=p,groups=groups));export_carriers(out/'CARRIERS.npz',e)
    js(out/'LINEAGE.json',e.events);js(out/'CANDIDATES.json',e.records)
    metrics=dict(scene=scene,level=level,kernels=len(ids),assigned=int((ids>=0).sum()),UNKNOWN=int((ids<0).sum()),groups=len(groups),cross_parent_groups=sum(g['old_parent_count']>1 for g in groups),active_valid_carriers=sum(g['valid_v04'] for g in groups),frozen_baseline_groups=sum(not g['valid_v04'] for g in groups),dormant_carriers=len(e.carriers)-len(groups),fit_attempts=e.fit_count,reasons=dict(e.stats),source_GS_association='UNKNOWN',physical_identity_verified=False,all_unknown_seedlets_considered=True,changed_primary_rows=int((ids!=prev).sum()))
    audit=renders(scene,level,out,a,ids,groups,e)
    if level==4:diagnostic_images(scene,out,e,a,ids,groups)
    after={f:sha(f) for f in hashes};assert hashes==after,'source mutation';js(out/'INPUT_HASHES_AFTER.json',after)
    config=json.loads((OUT/'CONFIG.json').read_text())
    for f,h in config['helper_hashes'].items():assert sha(f)==h,'helper mutation'
    recovery=OUT/'engineering_recovery_v1/CONFIG.json'
    source_hashes=json.loads(recovery.read_text())['source_hashes'] if recovery.exists() else config['source_hashes']
    for f,h in source_hashes.items():assert sha(f)==h,'source changed during science'
    assert sha(OUT/'CAMERAS.json')==config['camera_sha256']
    js(out/'GEOMETRY_AUDIT.json',audit);metrics['seconds']=time.monotonic()-start;js(out/'METRICS.json',metrics)
    with (out/'STATE.pkl.partial').open('xb') as f:pickle.dump(dict(carriers=e.carriers,aux=e.aux,next_version=e.next_version),f,protocol=5)
    (out/'STATE.pkl.partial').rename(out/'STATE.pkl')
    js(out/'CHECKPOINT.json',dict(utc=now(),complete=True,files={f.name:sha(f) for f in out.iterdir() if f.is_file()}));print('LEVEL_COMPLETE',scene,level,metrics,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--scene',choices=list(COUNTS),required=True);ap.add_argument('--level',type=int,choices=range(5),required=True);args=ap.parse_args()
    try:run(args.scene,args.level)
    except BaseException as exc:
        out=OUT/args.scene/f'L{args.level}';out.mkdir(parents=True,exist_ok=True)
        if not (out/'FAILURE.json').exists():js(out/'FAILURE.json',dict(utc=now(),error=repr(exc),traceback=traceback.format_exc()))
        raise
