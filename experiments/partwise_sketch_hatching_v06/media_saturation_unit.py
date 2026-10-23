"""Natural and matched complete-object comparisons; decode every arc frame."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
import subprocess
import numpy as np
from PIL import Image
from run_saturation_unit import protocol,fresh
from run_hybrid import read_npz,panel
from media_layer_ablation import FFMPEG

def main():
    p=protocol();out=fresh(UNIT/'media');images=[];labels=[];matched=[];ml=[]
    for v in (v for v in p['views'] if v['kind']=='dev'):
        c=v['camera'];f=read_npz(UNIT/'dev'/c['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('weighted_raw_paper','Weighted paper'),('saturated_raw_paper','Same-ID saturated paper'),('weighted_raw','Weighted / fixed ink'),('saturated_raw','Saturated / fixed ink')]:
            images.append(f[key]);labels.append(c['view']+' | '+label)
        for key,label in [('weighted_matched_paper','Weighted matched paper'),('saturated_matched_paper','Saturated matched paper'),('weighted_matched','Weighted matched hybrid'),('saturated_matched','Saturated matched hybrid')]:
            matched.append(f[key]);ml.append(c['view']+' | '+label)
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'Same41058 original row permissions; natural intensity; identical linked proxy ink alpha',columns=5)
    panel(UNIT/'ALL_DEV_MATCHED.png',matched,ml,'Full-source RGB effect matched on4 BUILD; fixed ink alpha; DEV not fitted',columns=4)
    arc=[];al=[];frames=[]
    for i,v in enumerate(v for v in p['views'] if v['kind']=='arc'):
        c=v['camera'];f=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        keys=['weighted_raw','saturated_raw','weighted_matched','saturated_matched']
        panel(frame,[f[k] for k in keys],['Weighted natural','Same-ID saturated natural','Weighted source matched','Saturated source matched'],
            f'Actual orbit {c["azimuth"]:.1f} deg / elevation24 / distance5.3; fixed3D paths and ink alpha',columns=4)
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for key in keys[:2]:arc.append(f[key]);al.append(f'{c["azimuth"]:.1f} deg | '+key)
    panel(UNIT/'ALL_ARC_FRAMES.png',arc,al,'All nine rear cameras; added front patch invisible; no temporal certification',columns=6)
    movie=out/'same_support_saturation_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode();expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape)
    exact=[bool(np.array_equal(a,b)) for a,b in zip(expected,actual)];assert all(exact)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=len(frames),all_frames_decoded_exact=exact,encode_argv=enc,decode_argv=dec,
        encode_rc=r.returncode,decode_rc=d.returncode,movie_sha256=sha(movie),ffmpeg_sha256=sha(FFMPEG),movie=str(movie)))
    print('MEDIA nine frames decoded exactly',flush=True)

if __name__=='__main__':main()
