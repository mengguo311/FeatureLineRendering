"""All complete-object views and fully decoded actual camera-arc video."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
import subprocess
import numpy as np
from PIL import Image
from run_gap_unit import protocol,fresh
from run_hybrid import read_npz,panel
from media_layer_ablation import FFMPEG


def main():
    p=protocol();out=fresh(UNIT/'media');images=[];labels=[];matched=[];ml=[]
    for v in (v for v in p['views'] if v['kind']=='dev'):
        c=v['camera'];a=read_npz(UNIT/'dev'/c['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('paper','Fixed completed paper'),('old_raw','Old planned gaps'),('filled_raw','Internal gaps filled')]:
            images.append(a[key]);labels.append(c['view']+' | '+label)
        for key,label in [('old_matched','Old / matched'),('filled_matched','Filled / matched'),('old_matched_alpha','Old matched ink'),('filled_matched_alpha','Filled matched ink')]:
            matched.append(1-a[key] if key.endswith('alpha') else a[key]);ml.append(c['view']+' | '+label)
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'Natural ink strength; fixed original-GS paper and S; internal planned gap style variant',columns=4)
    panel(UNIT/'ALL_DEV_MATCHED.png',matched,ml,'Actual visible ink RGB L1 matched on four BUILD views; no per-view fitting; exposed DEV',columns=4)
    arc=[];al=[];frames=[]
    for i,v in enumerate(v for v in p['views'] if v['kind']=='arc'):
        c=v['camera'];a=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        keys=['old_raw','filled_raw','old_matched','filled_matched']
        panel(frame,[a[k] for k in keys],['Old raw','Filled raw','Old BUILD matched','Filled BUILD matched'],
            f'Actual orbit {c["azimuth"]:.1f} deg / elevation24 / distance5.3; fixed original-GS paper and S',columns=4)
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for key,label in [('old_matched','Old matched'),('filled_matched','Filled matched')]:arc.append(a[key]);al.append(f'{c["azimuth"]:.1f} deg | '+label)
    panel(UNIT/'ALL_ARC_FRAMES.png',arc,al,'All nine actual camera settings / fixed3D style variants / no temporal certification',columns=6)
    movie=out/'internal_gap_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode()
    expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape)
    exact=[bool(np.array_equal(a,b)) for a,b in zip(expected,actual)];assert all(exact)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=len(frames),all_frames_decoded_exact=exact,
        encode_argv=enc,decode_argv=dec,encode_rc=r.returncode,decode_rc=d.returncode,ffmpeg_sha256=sha(FFMPEG),
        movie_sha256=sha(movie),movie=str(movie),scope='Actual nine-camera short arc; no independent temporal truth.'))
    print('MEDIA',movie,'nine decoded frames exact',flush=True)


if __name__=='__main__':main()
