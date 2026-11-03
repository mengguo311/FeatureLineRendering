from pathlib import Path
import os,sys,json,importlib.util,hashlib,time
sys.dont_write_bytecode=True
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='2'
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import numpy as np
from PIL import Image
u=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
c=json.loads((u/'CONFIG.json').read_text());req=json.loads((u/'RUN_REQUEST.json').read_text());assert hashlib.sha256((u/'CONFIG.json').read_bytes()).hexdigest()==req['config_sha256']
sys.path.insert(0,str(u/'source_snapshot'));spec=importlib.util.spec_from_file_location('parent_full_render',u/'source_snapshot/rendering.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);renderer=module.load_renderer(c['renderer'],c['helper_files'])
def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
assets={s:load(u/(s+'_GAUSSIANS.npz')) for s in ['ORIGINAL','FULL_POSITION_ONLY']};m=load(u/'MEMBERSHIP.npz');receipts=json.loads((u/'RENDER_RECEIPTS.json').read_text());cams=json.loads(Path(c['cameras']).read_text())[c['scene']];cams={x['view']:x for x in cams};records=[];start=time.monotonic();cache={}
def check(stage,view,path,rows=None):
 asset=assets[stage] if rows is None else {k:v[rows] for k,v in assets[stage].items()};render=renderer.render(asset,cams[view],background=(1,1,1),floor=.12**2);rgb=np.rint(np.clip(render['rgb'],0,1)*255).astype(np.uint8);saved=np.asarray(Image.open(u/path).convert('RGB'));assert rgb.shape==saved.shape;diff=np.abs(rgb.astype(np.int16)-saved.astype(np.int16));record=dict(stage=stage,view=view,path=path,rows=len(asset['means']),pixel_exact=bool(np.array_equal(rgb,saved)),max_rgb8_difference=int(diff.max()));records.append(record);assert record['pixel_exact'],record;return saved
for entry in receipts['images']:
 assert entry['rows']==279616;cache[entry['stage'],entry['view']]=check(entry['stage'],entry['view'],entry['path'])
assert len(receipts['images'])==4
quads=[]
for q in receipts['quadrants']:
 box=q['box'];x0,y0,x1,y1=box;full=cache[q['stage'],q['view']];saved=np.asarray(Image.open(u/q['crop']).convert('RGB'));equal=np.array_equal(full[y0:y1,x0:x1],saved);assert equal;quads.append(dict(path=q['crop'],box=box,pixels_exact=True))
assert len(quads)==16
for case in receipts['worst_cases']:
 gid=case['group_id'];view=case['view'];rows=np.flatnonzero(m['edge_id']==gid)
 for stage in assets:check(stage,view,f'images/WORST_{gid}_{stage}_{view}_ISOLATED.png',rows)
result=dict(native_gaussian_pngs_replayed=len(records),full_model_frames=4,fixed_quadrant_crops_checked=len(quads),all_saved_pngs_pixel_exact=all(x['pixel_exact'] for x in records),all_replayed_from_actual_cold_loaded_full_assets=True,renderer_floor=.12**2,backend='pinned CPU Gaussian EWA replica, not CUDA',elapsed_seconds=time.monotonic()-start,images=records,quadrants=quads)
(out/'INDEPENDENT_FULL_RENDER_REPLAY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['images','quadrants']}))
