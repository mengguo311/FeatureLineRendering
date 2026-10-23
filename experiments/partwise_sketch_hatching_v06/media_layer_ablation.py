"""Actual nine-camera arc and complete-object comparison sheets."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,output_guard,now
from pathlib import Path
import subprocess
import json
import numpy as np
from PIL import Image,ImageDraw
from run_hybrid import read_npz,png,panel

FFMPEG=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')

def main():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());out=output_guard(UNIT/'media');out.mkdir(exist_ok=False)
    images=[];labels=[]
    for c in p['scene']['evaluation_cameras']:
        a=read_npz(UNIT/'dev'/c['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('cross_raw','Cross / unit001 strength'),('cross_matched','Cross / matched'),('base_matched','Single / matched')]:
            images.append(a[key]);labels.append(c['view']+' | '+label)
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'All four exposed DEV views; matched BUILD ink only; original-GS paper + proxy ink',columns=4)
    arc=[];arc_labels=[];frames=[]
    for i,c in enumerate(p['arc_cameras']):
        a=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        panel(frame,[a[k] for k in ('source','cross_matched','base_matched')],
              ['Original GS','Cross / BUILD matched','Single direction / BUILD matched'],
              f'Actual camera arc {c["azimuth"]:.1f} deg / elevation24 / distance5.3; fixed3D paths and original IDs')
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for key,label in [('cross_matched','Cross'),('base_matched','Single')]:arc.append(a[key]);arc_labels.append(f'{c["azimuth"]:.1f} deg | '+label)
    panel(UNIT/'ALL_ARC_FRAMES.png',arc,arc_labels,'All nine actual cameras; no temporal ground truth, no per-frame tuning',columns=6)
    movie=out/'layer_comparison_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode()
    expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape)
    exact=[bool(np.array_equal(a,b)) for a,b in zip(expected,actual)];assert all(exact)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=9,all_frames_decoded_exact=exact,
        encode_argv=enc,decode_argv=dec,encode_rc=r.returncode,decode_rc=d.returncode,
        ffmpeg_sha256=sha(FFMPEG),movie_sha256=sha(movie),movie=str(movie),scope='Actual nine-camera short arc, not fixed-camera ramp or general temporal certification.'))
    print('MEDIA',movie,'all nine decoded frames exact',flush=True)

if __name__=='__main__':main()
