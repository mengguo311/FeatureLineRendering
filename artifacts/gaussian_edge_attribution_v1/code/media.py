"""Full-frame attribution visualizations, fixed-display-scale media and decoding audit."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from verify import sha256, atomic_json

_FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

def _font(size): return ImageFont.truetype(_FONT,size)

def _rgb(x):
    x=np.asarray(x)
    if x.dtype==np.uint8:return Image.fromarray(x)
    return Image.fromarray(np.rint(np.clip(x,0,1)*255).astype(np.uint8))

def mask_image(value,gain=1.0):
    """White zero; gray/black original visibility-weighted contribution."""
    value=np.asarray(value,dtype=np.float64)
    if value.ndim!=2 or not np.isfinite(value).all():raise ValueError('mask must be finite 2D')
    gray=np.rint((1-np.clip(value*gain,0,1))*255).astype(np.uint8)
    return Image.fromarray(np.repeat(gray[...,None],3,axis=-1))

def _save(image,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix.lower() in ('.jpg','.jpeg'):image.save(path,quality=92,subsampling=0,optimize=True)
    else:image.save(path)
    return {'path':str(path),'sha256':sha256(path),'width':image.width,'height':image.height,'bytes':path.stat().st_size}

def write_panel(out_path,rgb,evidence,baseline,two_sided,selected_q,title='',display_gain=1.,projection_kind='TOP4 cache'):
    rgb=np.asarray(rgb); h,w=rgb.shape[:2]
    for a in (evidence,baseline,two_sided,selected_q):
        if np.asarray(a).shape!=(h,w):raise ValueError('panel images must share full frame')
    if rgb.shape!=(h,w,3):raise ValueError('RGB shape invalid')
    header,footer=64,72
    canvas=Image.new('RGB',(w*5,h+header+footer),'white');draw=ImageDraw.Draw(canvas)
    q=np.clip(np.asarray(selected_q),0,1)[...,None]
    rgb_float=rgb.astype(np.float64)/(255 if rgb.dtype==np.uint8 else 1.)
    overlay=rgb_float*(1-.8*q)+np.array([0.,.66,.78])*(.8*q)
    tiles=[_rgb(rgb),mask_image(evidence),mask_image(baseline,display_gain),mask_image(two_sided,display_gain),_rgb(overlay)]
    labels=['原始 RGB','独立 2D 证据（仅比较）','固定 ID：贡献基线 P','固定 ID：双侧 P','固定 top10% 支持 Q 叠加']
    for i,(tile,label) in enumerate(zip(tiles,labels)):
        canvas.paste(tile,(i*w,header));draw.text((i*w+12,30),label,font=_font(23),fill=(20,20,20))
        if i:draw.line((i*w,header,i*w,header+h),fill=(215,215,215),width=1)
    draw.text((12,2),title,font=_font(20),fill=(20,20,20))
    draw.text((12,h+header+4),f'灰色 = 高斯贡献，非线条或明暗； P = Σ 原始(alpha·T) × 固定分数；显示增益 {display_gain:.5g}（仅显示）',font=_font(23),fill=(20,20,20))
    draw.text((12,h+header+36),f'分数：TOP4 截断估计；投影：{projection_kind}；固定资产 / 视角相关贡献范围；当前帧证据不参与选 ID',font=_font(23),fill=(20,20,20))
    info=_save(canvas,out_path);info.update(tile_size=[w,h],cropped=False,display_gain=float(display_gain),projection_kind=projection_kind)
    return info

def write_classes_tiers(out_path,projection,title='',display_gain=1.,projection_kind='TOP4 cache'):
    p=projection; h,w=np.asarray(p['alpha']).shape
    rows=[[(f'独立 {c} 证据',p['evidence_'+c],1.) for c in ('color','geometry','outline')]+[('独立 union 证据',p['evidence_union'],1.)],
          [(f'双侧固定 {c} top10% Q',p['class_'+c+'_Q_10'],1.) for c in ('color','geometry','outline')]+[('union top10% Q',p['selected_Q_10'],1.)],
          [(f'双侧固定 top{k}% Q',p['selected_Q_'+k],1.) for k in ('01','03','10','30')],
          [('基线 top10% Q',p['baseline_Q_10'],1.),('F1 单视图 top10% Q',p['single_Q_10'],1.),('同数量/可见性匹配随机 Q',p['random_Q_10'],1.),('原始 alpha（未裁切）',p['alpha'],1.)]]
    header,label_h,footer=40,38,60
    canvas=Image.new('RGB',(4*w,header+4*(h+label_h)+footer),'white'); draw=ImageDraw.Draw(canvas)
    draw.text((12,3),title+' | 类别、预声明全部层级及控制',font=_font(25),fill='black')
    for row,cells in enumerate(rows):
        y=header+row*(h+label_h)
        for col,(label,value,gain) in enumerate(cells):
            draw.text((col*w+10,y+2),label,font=_font(23),fill='black');canvas.paste(mask_image(value,gain),(col*w,y+label_h))
    draw.text((12,canvas.height-footer+3),f'所有灰度 Q = Σ 被选原始(alpha·T)，无权重重归一化；灰色代表贡献，非几何线；投影 {projection_kind}',font=_font(23),fill='black')
    draw.text((12,canvas.height-footer+31),'color=颜色；geometry=深度/遮挡证据类（无表面真值）；outline=视角相关轮廓；所有 ID 来自 F',font=_font(23),fill='black')
    info=_save(canvas,out_path);info.update(tile_size=[w,h],cropped=False,projection_kind=projection_kind)
    return info

def make_contact(paths,out_path,tile_width=1000,columns=2):
    paths=list(map(Path,paths))
    if not paths: raise ValueError('empty contact')
    with Image.open(paths[0]) as first: tile_height=round(first.height*tile_width/first.width)
    canvas=Image.new('RGB',(columns*tile_width,math.ceil(len(paths)/columns)*tile_height),'white')
    for i,path in enumerate(paths):
        with Image.open(path) as im:
            thumb=im.convert('RGB').resize((tile_width,tile_height),Image.Resampling.LANCZOS)
            canvas.paste(thumb,((i%columns)*tile_width,(i//columns)*tile_height))
    result=_save(canvas,out_path);result['frame_count']=len(paths);result['uncropped']=True
    return result

def _boxes(path):
    out=[]
    with open(path,'rb') as f:
        end=Path(path).stat().st_size
        while f.tell()<end:
            offset=f.tell();head=f.read(8)
            if len(head)!=8: raise ValueError('truncated MP4 box')
            size,kind=struct.unpack('>I4s',head)
            if size==1:size=struct.unpack('>Q',f.read(8))[0]
            if size==0:size=end-offset
            if size<8 or offset+size>end:raise ValueError('invalid MP4 box')
            out.append((kind.decode('ascii','replace'),offset,size));f.seek(offset+size)
    return out

def verify_video(path,expected_frames=33,panel_layout=False):
    import cv2
    cap=cv2.VideoCapture(str(path));hashes=[];sizes=[];rgb_hashes=[];attribution_hashes=[]
    fps=float(cap.get(cv2.CAP_PROP_FPS))
    while True:
        ok,frame=cap.read()
        if not ok:break
        hashes.append(hashlib.sha256(frame.tobytes()).hexdigest());sizes.append([frame.shape[1],frame.shape[0]])
        if panel_layout:
            h,w=frame.shape[:2];y0=math.ceil(h*64/936);y1=math.floor(h*864/936);tw=w//5
            rgb_hashes.append(hashlib.sha256(frame[y0:y1,:tw].tobytes()).hexdigest())
            attribution_hashes.append(hashlib.sha256(frame[y0:y1,2*tw:4*tw].tobytes()).hexdigest())
    cap.release(); boxes=_boxes(path); box_names=[b[0] for b in boxes]
    faststart='moov' in box_names and 'mdat' in box_names and box_names.index('moov')<box_names.index('mdat')
    import imageio_ffmpeg
    probe=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',str(path),'-map','0:v:0','-frames:v','0','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    stderr=probe.stderr
    h264=('Video: h264' in stderr);yuv420=('yuv420p' in stderr)
    checks={'decoded_count':len(hashes)==expected_frames,'all_frames_distinct':len(set(hashes))==expected_frames,
            'consistent_dimensions':len(set(map(tuple,sizes)))==1,'h264':h264,'yuv420p':yuv420,'faststart':faststart}
    if panel_layout:checks['all_RGB_content_frames_distinct_without_labels']=len(set(rgb_hashes))==expected_frames
    result={'path':str(path),'sha256':sha256(path),'bytes':Path(path).stat().st_size,'fps':fps,
            'decoded_frame_count':len(hashes),'distinct_decoded_frames':len(set(hashes)),
            'decoded_frame_sha256':hashes,'decoded_RGB_content_sha256':rgb_hashes,'decoded_attribution_content_sha256':attribution_hashes,
            'distinct_RGB_content_frames':len(set(rgb_hashes)) if panel_layout else None,
            'distinct_attribution_content_frames':len(set(attribution_hashes)) if panel_layout else None,
            'dimensions':sizes[0] if sizes else None,'checks':checks,'ok':all(checks.values()),
            'mp4_top_level_boxes':boxes,'decoder':'OpenCV BGR bytes SHA256; ffmpeg codec/pixel-format metadata'}
    if not result['ok']:raise ValueError(result)
    return result

def encode_video(paths,out_path,width=None,fps=8,panel_layout=False):
    import imageio_ffmpeg
    paths=list(map(Path,paths));out_path=Path(out_path);out_path.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(paths[0]) as first:
        target_w=width or first.width;target_h=round(first.height*target_w/first.width);target_h+=target_h%2
    if target_w%2:raise ValueError('video width must be even')
    partial=out_path.with_suffix('.partial.mp4')
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-nostdin','-y',
             '-f','rawvideo','-pix_fmt','rgb24','-s',f'{target_w}x{target_h}','-r',str(fps),'-i','pipe:0',
             '-an','-c:v','libx264','-threads','2','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(partial)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for path in paths:
            with Image.open(path) as im:
                im=im.convert('RGB')
                if im.size!=(target_w,target_h):im=im.resize((target_w,target_h),Image.Resampling.LANCZOS)
                process.stdin.write(im.tobytes())
        process.stdin.close();error=process.stderr.read();code=process.wait()
        if code:raise RuntimeError(error.decode(errors='replace'))
    finally:
        if process.poll() is None:process.kill();process.wait()
    os.replace(partial,out_path)
    result=verify_video(out_path,len(paths),panel_layout=panel_layout);result.update(encoder_command=command,encoder_path=imageio_ffmpeg.get_ffmpeg_exe(),encoder_sha256=sha256(imageio_ffmpeg.get_ffmpeg_exe()),source_frames=[{'path':str(p),'sha256':sha256(p)} for p in paths],uncut=True)
    return result

def build_scene_media(scene_dir,ordered_poses,arc_poses,panel_subdir='panels',fps=8):
    scene_dir=Path(scene_dir);out=scene_dir/'media';out.mkdir(parents=True,exist_ok=True)
    paths=[scene_dir/panel_subdir/(p+'.jpg') for p in ordered_poses]
    arc=[scene_dir/panel_subdir/(p+'.jpg') for p in arc_poses]
    if len(paths)!=49 or len(arc)!=33:raise ValueError('require complete 49 poses and uncut arc33')
    if len(set(ordered_poses))!=49 or len(set(arc_poses))!=33:raise ValueError('duplicate pose names')
    result={'requested_pose_count':49,'actual_pose_count':len(paths),'requested_arc_frames':33,'actual_arc_frames':len(arc),
            'pose_order':list(ordered_poses),'arc_order':list(arc_poses),
            'panels':[{'pose':p,'path':str(path),'sha256':sha256(path)} for p,path in zip(ordered_poses,paths)],
            'contact_all':make_contact(paths,out/'contact_all49.jpg',tile_width=1600,columns=2),
            'contact_first_mid_last':make_contact([arc[0],arc[len(arc)//2],arc[-1]],out/'contact_arc_first_mid_last.jpg',tile_width=2000,columns=1),
            'video_native':encode_video(arc,out/'arc33_native.mp4',fps=fps,panel_layout=True),
            'video_telegram1600':encode_video(arc,out/'arc33_telegram1600.mp4',width=1600,fps=fps,panel_layout=True)}
    atomic_json(out/'MEDIA.json',result)
    return result
