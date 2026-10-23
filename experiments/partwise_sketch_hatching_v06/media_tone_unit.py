"""Complete-object sheets and all decoded frames of the actual short arc."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
import subprocess
import numpy as np
from PIL import Image
from run_tone_unit import protocol,fresh
from run_hybrid import read_npz,panel
from media_layer_ablation import FFMPEG
from stroke_tone import ARMS


def main():
    p=protocol();out=fresh(UNIT/'media');images=[];labels=[];matched=[];ml=[];inks=[];il=[]
    for v in (v for v in p['views'] if v['kind']=='dev'):
        c=v['camera'];a=read_npz(UNIT/'dev'/c['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('constant_raw','Constant / natural'),('tone_raw','Surface tone / natural'),('shuffled_raw','Shuffled / natural')]:
            images.append(a[key]);labels.append(c['view']+' | '+label)
        for arm in ARMS:
            matched.append(a[arm+'_matched']);ml.append(c['view']+' | '+arm+' / matched')
            inks.append(1-a[arm+'_matched_alpha']);il.append(c['view']+' | '+arm+' ink / matched')
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'Natural strength; fixed original-GS paper and original-ID S; unchanged351 strokes',columns=4)
    panel(UNIT/'ALL_DEV_MATCHED.png',matched,ml,'Actual visible RGB ink matched on four BUILD views; no DEV fitting; exposed diagnostic cameras',columns=3)
    panel(UNIT/'ALL_DEV_INK.png',inks,il,'Independent ink layers; same fixed geometry and original-ID responsibility',columns=3)
    arc=[];al=[];frames=[]
    for i,v in enumerate(v for v in p['views'] if v['kind']=='arc'):
        c=v['camera'];a=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        keys=[arm+'_'+mode for mode in ('raw','matched') for arm in ARMS]
        panel(frame,[a[k] for k in keys],['Constant natural','Surface tone natural','Shuffled natural','Constant matched','Surface tone matched','Shuffled matched'],
            f'Actual orbit {c["azimuth"]:.1f} deg / elevation24 / distance5.3; fixed3D paths and world-light tone',columns=3)
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for arm in ARMS:arc.append(a[arm+'_matched']);al.append(f'{c["azimuth"]:.1f} deg | '+arm+' matched')
    panel(UNIT/'ALL_ARC_FRAMES.png',arc,al,'All nine actual camera settings; fixed stroke weights; no temporal certification',columns=6)
    movie=out/'stroke_tone_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode()
    expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape)
    exact=[bool(np.array_equal(a,b)) for a,b in zip(expected,actual)];assert all(exact)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=len(frames),all_frames_decoded_exact=exact,
        encode_argv=enc,decode_argv=dec,encode_rc=r.returncode,decode_rc=d.returncode,ffmpeg_sha256=sha(FFMPEG),
        movie_sha256=sha(movie),movie=str(movie),scope='Actual nine-camera short arc, not a fixed-camera edit ramp; no independent temporal truth.'))
    print('MEDIA',movie,'nine decoded frames exact',flush=True)


if __name__=='__main__':main()
