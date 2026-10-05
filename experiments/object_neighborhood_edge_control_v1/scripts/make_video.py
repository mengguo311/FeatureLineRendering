"""Encode actual native-rendered path frames; stream-decode and seal every frame."""
import argparse
import json
import os
import sys
import subprocess
import hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,ART,EXP,atomic_json,sha,resource_guard

def video(scene,method):
    guard=resource_guard(gpu=False)
    sys.path.append(str(OUT/'deps'));import imageio_ffmpeg
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    frames=json.loads((EXP/f'results/manifests/{scene}_{method}_path_frames.json').read_text())
    if not frames:raise RuntimeError('no path frames')
    base=OUT/'renders'/scene/method/'path'
    for f in frames:
        if sha(base/f'{f["index"]:04d}.png')!=f['png_sha256']:raise RuntimeError('frame seal mismatch')
    dest=ART/'videos'/f'{scene}_{method}_pilot_36frames.mp4';dest.parent.mkdir(parents=True,exist_ok=True)
    args=[ffmpeg,'-y','-threads','2','-framerate','12','-i',str(base/'%04d.png'),'-frames:v',str(len(frames)),
          '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
    log=OUT/'logs'/f'encode_{scene}_{method}.txt'
    with log.open('w') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
    # Explicit full decode, all actual frame pixels are read and hashed, no sample audit.
    from PIL import Image
    width,height=Image.open(base/'0000.png').size
    decode_log=OUT/'logs'/f'decode_{scene}_{method}.txt'
    hashes=[]
    with decode_log.open('w') as f:
        proc=subprocess.Popen([ffmpeg,'-threads','2','-i',str(dest),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE,stderr=f)
        size=width*height*3
        while True:
            data=proc.stdout.read(size)
            if not data:break
            if len(data)!=size:raise RuntimeError('partial decoded frame')
            hashes.append(hashlib.sha256(data).hexdigest())
        if proc.wait():raise RuntimeError('full video decode failed')
    if len(hashes)!=len(frames):raise RuntimeError('decoded frame count mismatch')
    result={'video':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size,'codec':'H264',
        'pixel_format':'yuv420p','faststart':True,'width':width,'height':height,'fps':12,
        'actual_native_rendered_frames':len(frames),'decoded_frames':len(hashes),
        'distinct_cameras':len(set(x['camera_sha256'] for x in frames)),
        'distinct_decoded_frames':len(set(hashes)),'decoded_frame_sha256':hashes,
        'source_frame_manifest_sha256':sha(EXP/f'results/manifests/{scene}_{method}_path_frames.json'),
        'ffmpeg_binary_sha256':sha(Path(ffmpeg)),'command':args,'guard':guard,
        'presentation':'GT task A / original natural trained B0 / method same camera; pilot one seed, not formal120frames'}
    atomic_json(EXP/f'results/manifests/{scene}_{method}_video.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('method');a=p.parse_args();video(a.scene,a.method)
