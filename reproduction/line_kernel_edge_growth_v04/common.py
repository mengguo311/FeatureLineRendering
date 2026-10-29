"""Frozen v04 paths, serial resource guards, atomic artifacts, isolated renderer."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
import json, time, datetime, hashlib, ast, ctypes, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from plyfile import PlyData, PlyElement
CODE=Path(__file__).resolve().parent
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
OUT=ROOT/'line_kernel_edge_growth_v04/units/unit_001'
ORCH=ROOT/'line_kernel_edge_growth_v04/orchestration'
OLD=ROOT/'line_kernel_edge_grouping_v03/units/unit_001'
BASE=ROOT/'c2l50_multiview05_v01/arms/C/scenes'
HELP=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
LIBROOT=ROOT/'c2l50_8build_joint_gs_v01'
COUNTS={'scan24':458490,'ficus':285956,'scan65':279616}
DEADLINE=datetime.datetime.fromisoformat('2026-10-29T14:40:30+00:00').timestamp()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def js(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    tmp=path.with_name(path.name+'.partial')
    with tmp.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
    tmp.rename(path)
def nz(path,**obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    tmp=path.with_name(path.name+'.partial')
    with tmp.open('xb') as f:np.savez_compressed(f,**obj)
    tmp.rename(path)
def guard(reserve=0):
    if time.time()>DEADLINE-reserve:raise TimeoutError('hard administrative deadline')
    assert shutil.disk_usage('/').free>=2**30 and shutil.disk_usage('/mnt/hdd1').free>=10*2**30
    assert sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file())<8*2**30
def helpers():
    ns=dict(np=np,ctypes=ctypes,ROOT=LIBROOT,_lib=None,Path=Path,PlyData=PlyData,PlyElement=PlyElement)
    for name,wanted in [('renderer.py',{'colors','project_cov','render'}),('format.py',{'read_ply'})]:
        tree=ast.parse((HELP/name).read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
        assert len(nodes)==len(wanted)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELP/name),'exec'),ns)
    return ns
def save_image(path,rgb):
    path=Path(path);tmp=path.with_name(path.stem+'.partial.png')
    Image.fromarray(np.uint8(np.rint(np.clip(rgb,0,1)*255))).save(tmp);tmp.rename(path)
def panel(path,items,title):
    w,h=777,581;im=Image.new('RGB',(2*w,50+((len(items)+1)//2)*(h+28)),'white');d=ImageDraw.Draw(im);d.text((8,8),title,fill='black')
    for k,(label,file) in enumerate(items):
        pic=Image.open(file).convert('RGB');pic.thumbnail((w,h));x=k%2*w;y=50+k//2*(h+28);d.text((x+6,y+3),label,fill='black');im.paste(pic,(x,y+26))
    im.save(path)
def colors(ids):
    # Stable across cameras and levels for an unchanged ID; lineage panels use final IDs.
    z=np.asarray(ids,dtype=np.int64);h=(z*2654435761)%4294967296
    c=np.stack([.12+.72*((h>>s)&255)/255 for s in (0,8,16)],1);c[z<0]=.68
    return c
def freeze():
    guard();d=json.loads((OUT/'DECISION.json').read_text())
    cams=json.loads((OLD/'CAMERAS.json').read_text());js(OUT/'CAMERAS.json',cams)
    config=dict(decision_sha256=sha(OUT/'DECISION.json'),start_utc='2026-10-29T13:55:43+00:00',deadline_utc='2026-10-29T14:40:30+00:00',decision=d,counts=COUNTS,
      numeric=dict(coordinate_unit='saved p',residual_max=1.,residual_q95=.5,tangent_deg=30.,knot_spacing=4.,knots=128,irls=3,huber=.5,member_cap=8192,fit_cap_per_level=30000,sample_spacing=1.,query_radius=4.,query_samples=32,candidate_carriers=8,gap=1.5,connector_deg=35.,vertex_turn_deg=30.,window_length=8.,window_turn_deg=60.,parallel_overlap=2.,parallel_angle=15.,parallel_offset=.5,branch_angle=20.,branch_seedlets=3,branch_span=2.,ambiguity=.15,min_reps=3,min_kernels=6,min_support=4.,numerical_epsilon=1e-8),
      clarifications=['Topology rounds use disjoint carrier pairs; pooling has no endpoint capacity.','Containment preserves the host polyline exactly.','Dormant singleton point carriers have a numerical 2e-8p auxiliary segment, never render geometry.','Fixed-parameter polyline IRLS uses linear interpolation basis on the proposal path; unobserved knots retain their proposal positions.','Candidate cost is maximum transverse distance/p plus maximum tangent angle/30.','All geometrically distinct near-tie carrier alternatives are unresolved; no arbitrary tie winner.','Nonadjacent segment self-contact uses exact segment distance.','Old baseline groups failing new guards remain assigned and frozen; they are not advertised as passing v04 guards.','No source RGB Gaussian files are opened.'],
      source_hashes={str(f):sha(f) for f in sorted(CODE.glob('*.py'))},helper_hashes={str(f):sha(f) for f in [HELP/'renderer.py',HELP/'format.py',LIBROOT/'build/libjoint.so']},camera_sha256=sha(OUT/'CAMERAS.json'))
    js(OUT/'CONFIG.json',config);js(OUT/'FREEZE_RECEIPT.json',dict(utc=now(),config_sha256=sha(OUT/'CONFIG.json'),decision_sha256=sha(OUT/'DECISION.json'),prior_v03_driver_pid=2656646,prior_driver_exited=not Path('/proc/2656646').exists()))
if __name__=='__main__':freeze()
