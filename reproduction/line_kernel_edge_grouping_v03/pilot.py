"""One frozen pilot. All output is confined to unit_001."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='2'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import sys,json,time,datetime,hashlib,ast,ctypes,shutil,traceback
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from plyfile import PlyData,PlyElement
from grouping import run_arrays
CODE=Path(__file__).resolve().parent
OUT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_grouping_v03/units/unit_001')
BASE=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_multiview05_v01')
OLD=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
LIBROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_joint_gs_v01')
VIEWS={'scan24':['0012','0036'],'ficus':['test_r_1','test_r_79'],'scan65':['0012','0036']}
COUNTS={'scan24':458490,'ficus':285956,'scan65':279616}
PALETTE=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00','#56B4E9']
COLORS=np.asarray([[int(c[k:k+2],16)/255 for k in (1,3,5)] for c in PALETTE])
DEADLINE=datetime.datetime.fromisoformat('2026-10-29T09:26:08.496903+00:00').timestamp()

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def js(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(str(path))
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def guard():
    assert time.time()<DEADLINE-120,'administrative deadline reserve'
    assert shutil.disk_usage('/').free>=2**30 and shutil.disk_usage('/mnt/hdd1').free>=10*2**30
    assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())<8*2**30

def load_helpers():
    namespace=dict(np=np,ctypes=ctypes,ROOT=LIBROOT,_lib=None,Path=Path,PlyData=PlyData,PlyElement=PlyElement)
    for name,wanted in [('renderer.py',{'colors','project_cov','render'}),('format.py',{'read_ply'})]:
        source=OLD/name;tree=ast.parse(source.read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
        assert len(nodes)==len(wanted);exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),namespace)
    return namespace

def image_save(path,rgb):Image.fromarray(np.uint8(np.round(np.clip(rgb,0,1)*255))).save(path)
def panel(path,items,title,cell=(777,581),crop=False):
    w,h=cell;canvas=Image.new('RGB',(2*w,55+((len(items)+1)//2)*(h+42)),'white');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    draw.text((10,8),title,fill='black',font=font)
    for i,(label,file) in enumerate(items):
        im=Image.open(file).convert('RGB')
        if crop:
            ar=np.asarray(im);yy,xx=np.nonzero(ar.min(2)<253)
            if len(xx):im=im.crop((max(0,int(xx.min())-12),max(0,int(yy.min())-12),min(im.width,int(xx.max())+13),min(im.height,int(yy.max())+13)))
        im.thumbnail((w,h));x=(i%2)*w;y=55+(i//2)*(h+42);draw.text((x+8,y+4),label,fill='black',font=font);canvas.paste(im,(x+(w-im.width)//2,y+36+(h-im.height)//2))
    canvas.save(path)

def freeze():
    guard();registry=json.loads((BASE/'REGISTRY.json').read_text())['scenes'];cams={s:[next(c for c in registry[s]['cameras'] if c['view']==v) for v in VIEWS[s]] for s in VIEWS}
    config=dict(decision_sha256=sha(OUT/'DECISION.json'),created_utc=now(),deadline_utc='2026-10-29T09:26:08.496903+00:00',scene_order=['scan24','ficus','scan65'],counts=COUNTS,seedlet_max_kernels=6,seedlet_span_p=2,spatial_k=32,radius_p=4,gap_p=1.5,tangent_degrees=30,connector_degrees=35,hough_block_p=32,hough_halo_p=4,hough_directions=256,hough_votes=2,hough_bin_p=2,hough_peaks_per_block=8,hough_min_representatives=6,hough_extent_p=6,hough_residual_p=1,reconcile_shared=2,reconcile_angle=10,reconcile_offset_p=1,candidates_per_rep=64,hough_bonus=.85,ambiguity_fraction=.15,degree_cap=2,turn_window_p=8,turn_cap_degrees=90,component_rep_cap=20000,min_component_reps=3,min_supported_length_p=4,render_floor=.0144,palette=PALETTE,background=[1,1,1],other_gray=[.68,.68,.68],cpu_limit=2,source_files={str(p):sha(p) for p in sorted(CODE.glob('*.py'))},helper_files={str(p):sha(p) for p in [OLD/'renderer.py',OLD/'format.py',LIBROOT/'build/libjoint.so']},clarifications=['Parent provenance is absent from all candidate and scoring functions.','Eight strongest Hough bins per block are attempted once; no replenishment or tuning.','Any seedlet with an ambiguous port is UNKNOWN; all incident primary links are blocked.','All primary identities remain provisional geometric hypotheses.','Hough family reconciliation never directly assigns primary identity.'])
    js(OUT/'CONFIG.json',config);js(OUT/'CAMERAS.json',cams)
    js(OUT/'MEMBERSHIP_SCHEMA.json',dict(line_kernel_id='original zero-based NPZ/PLY row',edge_id='minimum original member row; -1 UNKNOWN',score='1/(1+maximum accepted chain link cost); geometric, not probability',reason_codes={'0':'local_supported_chain','1':'insufficient_supported_chain','2':'ambiguous_junction','3':'invalid_tangent'},link_status={'0':'geometric_reject','1':'legal_not_reciprocal_best','2':'ambiguous_node','3':'accepted_continuation','4':'turn_budget_cut','5':'component_budget_cut','6':'short_cycle_cut'},provisional='true: no independent physical identity verifier',source_GS_association='UNKNOWN',color_policy='six largest primary groups; all remaining kernels gray; no cross-method identity implied'))
    print('FROZEN',sha(OUT/'CONFIG.json'),flush=True)

def export_method(scene,method,result,a,r,p,helpers,cameras):
    guard();out=OUT/scene/method;out.mkdir(parents=True,exist_ok=False);n=len(a['means']);ids=result['edge_id'];assert len(ids)==n;valid=ids>=0
    membership=dict(line_kernel_id=np.arange(n,dtype=np.int64),edge_id=ids,representative_id=r['kernel_rep'],score=result['score'],reason_code=result['reason'],junction=result['junction'],provisional=result['provisional'],primitive_id=a['primitive_id'],internal_piece_id=a['internal_piece_id'],arc_t=a['arc_t'])
    np.savez_compressed(out/'MEMBERSHIP.npz',**membership);np.savez_compressed(out/'LINKS.npz',**result['links']);np.savez_compressed(out/'CHAINS.npz',nodes=result['chain_nodes'],offsets=result['chain_offsets'],representative_edge_id=result['rep_edge_id'])
    groups=[]; group_source={g['edge_id']:g for g in result['groups']}
    for edge,count in zip(*np.unique(ids[valid],return_counts=True)):
        mask=ids==edge;g=dict(group_source[int(edge)]);g.update(kernels=int(count),old_parent_count=int(len(np.unique(a['primitive_id'][mask]))),old_piece_count=int(len(np.unique(a['internal_piece_id'][mask]))),old_parent_ids=np.unique(a['primitive_id'][mask]).tolist());assert int(np.flatnonzero(mask).min())==edge;groups.append(g)
    groups.sort(key=lambda g:(-g['kernels'],g['edge_id']));top=groups[:6]
    js(out/'GROUPS.json',dict(scene=scene,method=method,p=p,groups=groups,top_palette=[dict(edge_id=g['edge_id'],color=PALETTE[k],kernels=g['kernels'],old_parents=g['old_parent_count']) for k,g in enumerate(top)]))
    col=np.full((n,3),.68)
    for k,g in enumerate(top):col[ids==g['edge_id']]=COLORS[k]
    display={k:v for k,v in a.items()};display['colors']=col
    np.savez_compressed(out/'DISPLAY_GAUSSIANS.npz',**display)
    raw=helpers['read_ply'](BASE/'arms/C/scenes'/scene/'full/gaussians.ply');dtype=list(raw.dtype.descr)+[('line_kernel_id','<i4'),('edge_id','<i4'),('internal_piece_id','<i4'),('group_score','<f4'),('group_reason','u1'),('group_provisional','u1')];extended=np.zeros(n,dtype=dtype)
    for k in raw.dtype.names:extended[k]=raw[k]
    for k,v in [('line_kernel_id',np.arange(n)),('edge_id',ids),('internal_piece_id',a['internal_piece_id']),('group_score',result['score']),('group_reason',result['reason']),('group_provisional',result['provisional'])]:extended[k]=v
    PlyData([PlyElement.describe(extended,'vertex')],text=False,byte_order='<',comments=['Complete dedicated C8 line kernels; original fields unchanged; edge membership only']).write(out/'EXTENDED.ply')
    for k in range(3):extended['f_dc_'+str(k)]=(col[:,k]-.5)/.28209479177387814
    PlyData([PlyElement.describe(extended,'vertex')],text=False,byte_order='<',comments=['DISPLAY ONLY: six largest groups colored; other kernels gray; original geometry and opacity']).write(out/'DISPLAY.ply')
    render=helpers['render'];fullitems=[];isolateditems=[]
    for c in cameras:
        guard();view=c['view'];rgb=render(display,c,background=(1,1,1),floor=.0144)['rgb'];file=out/(view+'_FULL.png');image_save(file,rgb);fullitems.append((method+' / '+view+' / ALL '+str(n)+' kernels',file))
        for rank,g in enumerate(top[:3]):
            mask=ids==g['edge_id'];asset={k:display[k][mask] for k in ('means','covariance','opacity','colors')};rgb=render(asset,c,background=(1,1,1),floor=.0144)['rgb'];file=out/(view+'_ISOLATED_'+str(rank+1)+'.png');image_save(file,rgb);isolateditems.append((f"{view} rank {rank+1}: {g['kernels']} kernels / {g['old_parent_count']} parents",file))
        print('RENDER',scene,method,view,flush=True)
    panel(out/'ISOLATED_PANEL.png',isolateditems,scene+' '+method+' | actual isolated groups; cropped display',cell=(600,400),crop=True)
    links=result['links'];accepted=links['status']==3;pair=links['pair'];cross=a['primitive_id'][r['mid'][pair[:,0]]]!=a['primitive_id'][r['mid'][pair[:,1]]]
    counts=np.asarray([g['kernels'] for g in groups],dtype=np.int64);statuscount={str(int(k)):int(v) for k,v in zip(*np.unique(links['status'],return_counts=True))}
    metric=dict(scene=scene,method=method,kernels=n,assigned=int(valid.sum()),unknown=int((~valid).sum()),coverage=float(valid.mean()),groups=len(groups),group_size_quantiles=np.quantile(counts,[0,.5,.9,.99,1]).tolist() if len(counts) else [],largest_fraction=float(counts.max(initial=0)/n),top_groups=top,cross_parent_groups=sum(g['old_parent_count']>1 for g in groups),accepted_links=int(accepted.sum()),accepted_cross_parent_links=int((accepted&cross).sum()),max_degree=result['max_degree'],max_accepted_gap_over_p=result['max_gap_over_p'],junction_kernels=int(result['junction'].sum()),link_status_counts=statuscount,candidate_cap_dropped=int(links['cap_dropped']),unsupported_gap_proposals=int((links['min_endpoint_gap']>1.5*p).sum()),source_GS_association='UNKNOWN',physical_identity_verified=False)
    js(out/'METRICS.json',metric)
    cases=[];case_arrays={}
    selectors=[('ambiguous',np.flatnonzero(links['status']==2)),('parallel_or_crossing_reject',np.flatnonzero((links['status']==0)&(links['tangent_angle']>30))),('unsupported_gap',np.flatnonzero(links['min_endpoint_gap']>1.5*p))]
    for label,choices in selectors:
        for e in choices[:2]:
            ii,jj=pair[e];rows=np.r_[r['member_rows'][r['member_offsets'][ii]:r['member_offsets'][ii+1]],r['member_rows'][r['member_offsets'][jj]:r['member_offsets'][jj+1]]];key=label+'_'+str(int(e));case_arrays[key]=rows;cases.append(dict(kind=label,link_row=int(e),representatives=[int(ii),int(jj)],kernel_rows=rows.tolist(),parents=np.unique(a['primitive_id'][rows]).tolist(),gap_over_p=float(links['min_endpoint_gap'][e]/p),tangent_degrees=float(links['tangent_angle'][e]),provisional=True))
    js(out/'NEGATIVE_CASES.json',cases);np.savez_compressed(out/'NEGATIVE_CASE_ROWS.npz',**case_arrays)
    # Cold disk reload, not in-memory equality claims.
    saved=dict(np.load(out/'MEMBERSHIP.npz'));assert np.array_equal(saved['line_kernel_id'],np.arange(n));assert np.array_equal(saved['edge_id'],ids)
    cold=dict(np.load(out/'DISPLAY_GAUSSIANS.npz'))
    for k in a:
        if k!='colors':assert cold[k].dtype==a[k].dtype and cold[k].shape==a[k].shape and cold[k].tobytes()==a[k].tobytes(),k
    coldraw=helpers['read_ply'](out/'EXTENDED.ply');coldcolored=helpers['read_ply'](out/'DISPLAY.ply')
    for k in raw.dtype.names:
        assert coldraw[k].tobytes()==raw[k].tobytes(),k
        if not k.startswith('f_dc_'):assert coldcolored[k].tobytes()==raw[k].tobytes(),k
    assert result['max_degree']<=2 and result['max_gap_over_p']<=1.5+1e-10
    c=cameras[0];coldrgb=render(cold,c,(1,1,1),.0144)['rgb'];png=np.asarray(Image.open(out/(c['view']+'_FULL.png')));assert np.array_equal(np.uint8(np.round(np.clip(coldrgb,0,1)*255)),png)
    js(out/'GEOMETRY_AUDIT.json',dict(cold_load=True,all_original_rows_accounted=True,NPZ_geometry_opacity_provenance_bitexact=True,extended_PLY_all_original_fields_bitexact=True,display_PLY_only_DC_changed=True,cold_render_png_bitexact=True,width_rotation_scale_unchanged=True,max_degree=result['max_degree'],max_gap_over_p=result['max_gap_over_p'],no_added_geometry=True,no_source_GS=True))
    js(out/'SEAL.json',dict(complete=True,files={f.name:sha(f) for f in sorted(out.iterdir()) if f.is_file()}))
    return metric,fullitems

def scene_run(scene):
    guard();out=OUT/scene;out.mkdir(exist_ok=False);js(out/'START.json',dict(scene=scene,pid=os.getpid(),utc=now(),expected_kernels=COUNTS[scene]));t0=time.monotonic();source=BASE/'arms/C/scenes'/scene/'full';lock=json.loads((OUT.parent.parent/'orchestration/INPUT_LOCK.json').read_text())['files']
    files=[source/name for name in ['gaussians.npz','gaussians.ply','SHARED_CONTROL_AND_SAMPLING.npz','LENGTH_AND_PARENT.npz','parents.json','OBSERVATION_TO_PARENT.npz','OBSERVATIONS.npz','ASSOCIATIONS.json']];hashes={str(f):sha(f) for f in files}
    for f,h in hashes.items():assert lock[f]==h,f
    js(out/'SOURCE_HASHES_BEFORE.json',hashes);a=dict(np.load(source/'gaussians.npz'));assert len(a['means'])==COUNTS[scene]
    with np.load(source/'SHARED_CONTROL_AND_SAMPLING.npz') as z:s={k:z[k] for k in ['control','control_index','derivative_basis','pixel']}
    def progress(*args):
        print(scene,*args,'seconds',round(time.monotonic()-t0,2),flush=True);guard()
    result=run_arrays(a,s,progress);r=result['r'];p=result['p'];np.savez_compressed(out/'REPRESENTATIVES.npz',**r);np.savez_compressed(out/'HOUGH_FAMILIES.npz',**result['hough_trace']);js(out/'HOUGH_STATS.json',result['hough_stats'])
    helpers=load_helpers();cameras=json.loads((OUT/'CAMERAS.json').read_text())[scene];allitems=[];metrics={}
    for method in ('baseline','hough'):
        metrics[method],items=export_method(scene,method,result[method],a,r,p,helpers,cameras);allitems.extend(items)
    panel(out/'FULL_COMPARISON.png',allitems,scene+' | full dedicated line Gaussian assets; top six colored; remainder gray',cell=(cameras[0]['width'],cameras[0]['height']))
    after={str(f):sha(f) for f in files};assert after==hashes;js(out/'SOURCE_HASHES_AFTER.json',after)
    js(out/'RESULT.json',dict(scene=scene,complete=True,seconds=time.monotonic()-t0,p=p,representatives=len(r['x']),hough=result['hough_stats'],metrics=metrics,visual_review='PENDING_MANUAL',no_geometry_fit=True));js(out/'CHILD_SUCCESS.json',dict(utc=now(),pid=os.getpid(),seconds=time.monotonic()-t0));print('SCENE_COMPLETE',scene,time.monotonic()-t0,flush=True)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--scene',choices=list(VIEWS));args=ap.parse_args()
    if args.freeze:freeze()
    else:scene_run(args.scene)
