"""Whole-object comparisons and actual nine-camera arc, every frame decoded."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
import subprocess
import numpy as np
from PIL import Image
from run_frame_unit import protocol,fresh
from run_hybrid import read_npz,panel
from media_layer_ablation import FFMPEG

def main():
    p=protocol();out=fresh(UNIT/'media');images=[];labels=[];matched=[];ml=[];ink=[];il=[]
    for v in (v for v in p['views'] if v['kind']=='dev'):
        c=v['camera'];f=read_npz(UNIT/'dev'/c['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('paper','Fixed GS paper'),('xz_raw','World XZ natural'),('local_raw','Local frame natural')]:images.append(f[key]);labels.append(c['view']+' | '+label)
        for key,label in [('source','Original GS'),('paper','Fixed GS paper'),('xz_matched','XZ ink matched'),('local_matched','Local ink matched')]:matched.append(f[key]);ml.append(c['view']+' | '+label)
        for key in ('xz_raw','local_raw','xz_matched','local_matched'):ink.append(1-f[key+'_alpha']);il.append(c['view']+' | '+key)
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'Natural intensity; same original-GS paper and ID responsibility; new proxy paths',columns=4)
    panel(UNIT/'ALL_DEV_MATCHED.png',matched,ml,'Target ink RGB effect matched on4 BUILD; no DEV fitting; source paper fixed',columns=4)
    panel(UNIT/'ALL_DEV_INK.png',ink,il,'Separate original-ID-linked proxy ink; no native Gaussian hatching claim',columns=4)
    arc=[];al=[];frames=[]
    for i,v in enumerate(v for v in p['views'] if v['kind']=='arc'):
        c=v['camera'];f=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        keys=['xz_raw','local_raw','xz_matched','local_matched']
        panel(frame,[f[k] for k in keys],['World XZ natural','Local frame natural','XZ ink matched','Local ink matched'],
            f'Actual orbit {c["azimuth"]:.1f} deg / elevation24 / distance5.3; fixed world paths per arm',columns=4)
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for key in keys[:2]:arc.append(f[key]);al.append(f'{c["azimuth"]:.1f} deg | '+key)
    panel(UNIT/'ALL_ARC_FRAMES.png',arc,al,'All nine exposed rear cameras; front addition invisible; no temporal certification',columns=6)
    movie=out/'local_frame_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode();expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape)
    exact=[bool(np.array_equal(a,b)) for a,b in zip(expected,actual)];assert all(exact)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=len(frames),all_frames_decoded_exact=exact,encode_argv=enc,decode_argv=dec,
        encode_rc=r.returncode,decode_rc=d.returncode,movie_sha256=sha(movie),ffmpeg_sha256=sha(FFMPEG),movie=str(movie)))
    print('MEDIA nine frames decoded exactly',flush=True)

if __name__=='__main__':main()
