"""Per-camera video of independent Hao–Mukai equation reconstruction.

Author method: Weiren Hao & Tomohiko Mukai, SIGGRAPH Asia 2026 Posters.
This is NOT their official RaDe-GS renderer or final line compositor.
"""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
import cv2
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src import common,render,raster_state
from src.hao_mukai_source_2026 import compute_fields


def compose_frame(rgb,sl,fixed_gain,frame_index,frame_total,size=640):
    """Three panels: proxy RGB / ABSOLUTE 1-S_L / FIXED-GAIN display only."""
    assert fixed_gain>0 and rgb.shape[:2]==sl.shape
    imgs=[np.clip(rgb,0,1),np.repeat((1-np.clip(sl,0,1))[...,None],3,axis=-1),
          np.repeat((1-np.clip(sl/fixed_gain,0,1))[...,None],3,axis=-1)]
    tile=[]
    for im in imgs:
        bgr=cv2.resize((im[...,::-1]*255).astype(np.uint8),(size,size),interpolation=cv2.INTER_AREA)
        tile.append(bgr[...,::-1])
    bottom=np.concatenate(tile,axis=1)
    canvas=np.full((size+76,size*3,3),255,np.uint8)
    canvas[76:]=bottom
    def text(t,x,y,font=.58):
        cv2.putText(canvas,t,(x,y),cv2.FONT_HERSHEY_SIMPLEX,font,(15,15,15),1,cv2.LINE_AA)
    text('HAO / MUKAI 2026 equations - independent disc-proxy reconstruction, NOT official RaDe-GS',10,22,.65)
    text('Proxy RGB',10,53)
    text('1-S_L absolute, unmodified',size+10,53)
    text('1-S_L fixed P99 gain (DISPLAY ONLY)',2*size+10,53)
    text('frame %03d / %03d'%(frame_index+1,frame_total),size*3-190,53)
    return canvas


def main():
    import torch,imageio_ffmpeg
    p=argparse.ArgumentParser()
    p.add_argument('--count',type=int,default=48)
    p.add_argument('--fps',type=int,default=12)
    a=p.parse_args()
    assert a.count==48 and a.fps==12,'Frozen video protocol: 48 real frames at 12 fps'
    cams,_=common.load_cameras('lego')
    g=common.load_gaussians('lego');keep=render.defloat_mask(g['mu'],g['opacity'])
    # Both endpoints belong to TRAIN camera set; generated intermediate poses are rendered afresh.
    from scripts import temporal_m1b as T
    path=T.orbit_cameras(cams[0],cams[10],240,np.median(g['mu'][keep],axis=0))
    indices=np.linspace(0,239,a.count,dtype=int).tolist()
    root=ROOT/'artifacts'/'hao_mukai_source_2026_repro'/'video'
    root.mkdir(parents=True,exist_ok=True)
    out=root/'lego_arc0_haomukai_equation_proxy.mp4'
    tmp=root/'lego_arc0_haomukai_equation_proxy.partial.mp4'
    gain=json.loads((ROOT/'artifacts'/'hao_mukai_source_2026_repro'/'lego'/'STATS.json').read_text())['display_only_p99_positive_S_L']
    width=640*3;height=640+76
    writer=imageio_ffmpeg.write_frames(str(tmp),(width,height),fps=a.fps,codec='libx264',quality=7,pix_fmt_in='rgb24',pix_fmt_out='yuv420p',macro_block_size=4)
    writer.send(None)
    frames=[]
    try:
        for frame_idx,k in enumerate(indices):
            st=raster_state.render_state(g,keep,path[k],device='cuda',K=4,include_topk_attributes=True)
            s=raster_state.numpy_state(st)
            fields=compute_fields(s)
            sl=fields['S_L']
            assert np.isfinite(sl).all() and sl.shape==s['alpha'].shape
            frame=compose_frame(s['albedo'],sl,gain,frame_idx,a.count)
            writer.send(frame)
            frames.append({'frame':frame_idx,'camera_orbit_index':k,'rgb_frame_sha256':hashlib.sha256(frame.tobytes()).hexdigest(),
                           'S_L_nonzero':int((sl>1e-6).sum()),'fragments':int(s['n_frag'])})
            del st,s,fields,sl,frame
            torch.cuda.empty_cache()
            print('FRAME',frame_idx+1,'/',a.count,'orbit',k,flush=True)
    finally:
        writer.close()
    assert len(frames)==a.count
    tmp.replace(out)
    summary={'attribution':'Weiren Hao & Tomohiko Mukai 2026 formulas; independent NOT-official disc-proxy reconstruction',
             'original_method':'https://mukai-lab.org/content/SA2026PosterHao.pdf',
             'scene':'lego','start_train_camera':cams[0].name,'end_train_camera':cams[10].name,
             'intermediate_cameras':'interpolated positions, actual per-frame rasterization and equation evaluation',
             'camera_indices':indices,'fps':a.fps,'frames':frames,'source_fixed_gain':float(gain),
             'gain_scope':'only the third display panel, frozen from Lego train camera r_0',
             'absolute_panel':'middle 1-S_L, no normalization','video_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (root/'VIDEO.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('VIDEO',out,'BYTES',out.stat().st_size,'SHA256',summary['video_sha256'],flush=True)

if __name__=='__main__':main()
