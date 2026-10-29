import os, sys
sys.dont_write_bytecode = True
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json, hashlib, time, datetime, shutil
import numpy as np

CODE = Path(__file__).resolve().parent
ROOT = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/hough_line_asset_curves_v02')
OUT = ROOT/'units/unit_001'
BASE = ROOT.parent/'c2l50_multiview05_v01'
RENDER_CODE = Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
START = '2026-10-29T07:03:15+00:00'
DEADLINE = datetime.datetime.fromisoformat(START).timestamp()+35*60
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()
def js(p,x):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False))
    tmp.replace(p)
def load_np(p):
    with np.load(p,allow_pickle=False) as z: return {k:z[k] for k in z.files}
def check_budget(reserve=0):
    if time.time() >= DEADLINE-reserve: raise TimeoutError('FROZEN_WALL_TIME_BOUND')
    assert shutil.disk_usage('/').free >= 2**30
    assert shutil.disk_usage(OUT).free >= 10*2**30
def state(phase,**kw):
    p=OUT/'STATUS.json'; a=json.loads(p.read_text()) if p.exists() else {'scenes':{s:'NOT_RUN' for s in ('scan24','ficus','scan65')}}
    a.update(phase=phase,utc=now(),**kw); js(p,a)
    print(phase,json.dumps(kw,ensure_ascii=False),flush=True)
def unit(x):
    x=np.asarray(x,float); return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-30)
def renderer_modules():
    sys.path.insert(0,str(RENDER_CODE))
    import format as fmt
    import renderer
    return fmt,renderer
CFG = dict(window_pieces=8,coarse_degrees=[-6,0,6],fine_degrees=[-2,0,2],coarse_bin_p=.5,fine_bin_p=.25,
    support_distance_p=.75,support_angle_deg=15.,min_kernels=8,min_pieces=3,min_span_p=2.,
    irls_steps=3,huber_p=.5,axis_weight=.25,handle_max_length=.6,move_p=.75,angle_deg=15.,
    length_ratio=[.95,1.05],corner_deg=35.,corner_chord_pieces=2,check_sites=33,
    bend_trigger_deg=10.,sag_trigger_p=.5,bend_ratio=[.8,1.2],
    near_straight_tangent_quantile=.9,near_straight_angle_deg=15.,near_straight_sag_p=.75,
    seed=0,background=[1,1,1],render_floor=.12**2,
    views={'scan24':['0012','0036'],'ficus':['test_r_1','test_r_79'],'scan65':['0012','0036']},
    start_utc=START,deadline_utc=datetime.datetime.fromtimestamp(DEADLINE,datetime.timezone.utc).isoformat(),
    confidence='UNKNOWN; neutral confidence weight one',source_GS='FORBIDDEN_NOT_READ',
    support_check='discrete at all kernel samples and 33 uniform sites; not continuous proof',
    line_group_scope='within each original parent short window; no cross-parent welding',
    inverse_transform='world = local * window_pixel_scale + window_origin',
    no_new_gaps=True,no_parameter_search=True)
def freeze():
    assert not (OUT/'config.json').exists(), 'Configuration is immutable'
    reg=json.loads((BASE/'REGISTRY.json').read_text())['scenes']
    cameras={s:[next(c for c in reg[s]['cameras'] if c['view']==v) for v in vs] for s,vs in CFG['views'].items()}
    js(CODE/'config.json',CFG); js(OUT/'config.json',CFG); js(OUT/'CAMERAS.json',cameras)
    js(OUT/'START.json',dict(start_utc=START,freeze_utc=now(),deadline_utc=CFG['deadline_utc'],decision_sha256=sha(OUT/'DECISION.json'),config_sha256=sha(OUT/'config.json'),cameras_sha256=sha(OUT/'CAMERAS.json'),affinity=sorted(os.sched_getaffinity(0)),scientific_runs_started=False))
    state('FROZEN_IMPLEMENTATION',administrative_timeouts_are_not_scientific_failures=True)
if __name__=='__main__': freeze()
