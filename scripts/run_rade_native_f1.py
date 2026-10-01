"""GPU F1: one native pass per TRAIN-derived camera, source equations, display-only media."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import cv2
import imageio_ffmpeg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src import common
from src.rade_native_f1 import render_native_f1,build_source_state
from src.hao_mukai_source_2026 import compute_fields

out=ROOT/'artifacts'/'hao_mukai_rade_native_f1'/'lego_r0';out.mkdir(parents=True,exist_ok=True)
cams,_=common.load_cameras('lego');g=common.load_gaussians('lego')
assert cams[0].name=='r_0'
def run(cam):
    raw=render_native_f1(g,cam);s=build_source_state(raw);f=compute_fields(s)
    valid=raw['topk_id']>=0
    assert (raw['topk_id'][~valid]==-1).all()
    assert (raw['topk_w'][~valid]==0).all()
    assert (raw['topk_id'][valid]<len(g['mu'])).all()
    assert np.isfinite(raw['rgb']).all() and np.isfinite(raw['depth']).all()
    assert np.isfinite(f['S_L']).all()
    assert np.max(raw['topk_w'].sum(-1)-raw['alpha'])<3e-6
    return raw,s,f
raw,s,f=run(cams[0])
np.savez_compressed(out/'native_states_r0.npz',**raw)
np.savez_compressed(out/'typed_fields_r0.npz',**f)
sl=f['S_L'];pos=sl[sl>0];gain=float(np.quantile(pos,.99)) if len(pos) else 1.
def rgb8(x):return (np.clip(x,0,1)[...,::-1]*255).astype(np.uint8)
def mono(x):return cv2.cvtColor((np.clip(x,0,1)*255).astype(np.uint8),cv2.COLOR_GRAY2BGR)
keys=['E_V','E_D','E_A','E_N','E_C','E_G','L','S_L','E_T']
ims=[rgb8(raw['rgb']),mono(raw['alpha']),mono(1-sl),mono(1-np.clip(sl/gain,0,1))]
labels=['RaDe frozen SH0 RGB','RaDe alpha','1-S_L absolute','1-S_L P99 display ONLY']
for key in keys:
    v=f[key];positive=v[v>0];scale=float(np.quantile(positive,.99)) if len(positive) else 1.
    ims.append(cv2.applyColorMap((np.clip(v/max(scale,1e-8),0,1)*255).astype(np.uint8),cv2.COLORMAP_MAGMA));labels.append(key+' P99 display ONLY')
while len(ims)%4:ims.append(np.full_like(ims[0],255));labels.append('')
tiles=[]
for im,label in zip(ims,labels):
    im=cv2.resize(im,(480,480),interpolation=cv2.INTER_AREA)
    tile=np.full((526,480,3),255,np.uint8);tile[46:]=im
    cv2.putText(tile,label,(8,32),cv2.FONT_HERSHEY_SIMPLEX,.66,(0,0,0),2,cv2.LINE_AA);tiles.append(tile)
figure=np.concatenate([np.concatenate(tiles[i:i+4],axis=1) for i in range(0,len(tiles),4)])
assert cv2.imwrite(str(out/'native_f1_panel.png'),figure)
# TRAIN r_0 to TRAIN r_10 interpolated orbit; every video frame rendered natively afresh.
from scripts import temporal_m1b as T
path=T.orbit_cameras(cams[0],cams[10],240,np.median(g['mu'],axis=0))
indices=[0,4,8,12,16,20,24,28]
video=out/'native_f1_short.mp4';tmp=out/'native_f1_short.partial.mp4'
writer=imageio_ffmpeg.write_frames(str(tmp),(1152,424),fps=8,codec='libx264',quality=7,pix_fmt_in='rgb24',pix_fmt_out='yuv420p',macro_block_size=4)
writer.send(None);frames=[]
try:
    for i,k in enumerate(indices):
        r,st,fields=(raw,s,f) if i==0 else run(path[k])
        lin=fields['S_L'];images=[rgb8(r['rgb']),mono(1-lin),mono(1-np.clip(lin/gain,0,1))]
        panels=[cv2.resize(z,(384,384),interpolation=cv2.INTER_AREA) for z in images]
        canvas=np.full((424,1152,3),255,np.uint8)
        canvas[40:]=np.concatenate(panels,axis=1)
        for j,text in enumerate(['RaDe RGB','1-S_L absolute','1-S_L FIXED P99 DISPLAY']):
            cv2.putText(canvas,text,(384*j+8,29),cv2.FONT_HERSHEY_SIMPLEX,.62,(0,0,0),2,cv2.LINE_AA)
        writer.send(canvas[...,::-1].copy())
        frames.append({'index':i,'orbit_index':k,'nonzero_S_L':int((lin>1e-6).sum()),'rgb_frame_sha256':hashlib.sha256(canvas.tobytes()).hexdigest()})
        print('FRAME',i,k,frames[-1]['nonzero_S_L'],flush=True)
finally:writer.close()
tmp.replace(video)
summary={'attribution':'Independent reconstruction of Weiren Hao / Tomohiko Mukai SA2026 Eq1-5; native renderer derived from Zhang et al RaDe-GS d72f207; NOT author official code',
         'input':'frozen vanilla Lego PLY, TRAIN r_0, no mesh/TEST/retrain/filter_3D, SH0 only',
         'gaussians':len(g['mu']),'r0_shape':list(raw['alpha'].shape),
         'positive_alpha_pixels':int((raw['alpha']>.05).sum()),
         'top4_weight_coverage_mean':float(s['topk_mass'][raw['alpha']>.05].mean()),
         'top4_weight_coverage_p05':float(np.quantile(s['topk_mass'][raw['alpha']>.05],.05)),
         'max_excess_top4_weight':float(np.max(raw['topk_w'].sum(-1)-raw['alpha'])),
         'S_L_nonzero':int((sl>1e-6).sum()),'S_L_p99':float(np.quantile(sl,.99)),
         'display_fixed_gain':gain,'video_frames':frames,'fps':8,
         'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
         'states_sha256':hashlib.sha256((out/'native_states_r0.npz').read_bytes()).hexdigest()}
(out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='video_frames'},indent=2),flush=True)
