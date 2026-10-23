"""Complete-object panels and decoded nine-camera short arc for unit008."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
import subprocess
import numpy as np
from PIL import Image
from run_target_unit import protocol,fresh
from run_hybrid import read_npz,panel
from media_layer_ablation import FFMPEG

def main():
    p=protocol();out=fresh(UNIT/'media');images=[];labels=[];inks=[];il=[]
    for v in (v for v in p['views'] if v['kind']=='dev'):
        c=v['camera'];f=read_npz(UNIT/'dev'/c['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('old_raw','Old target'),('new_raw','Expanded target natural'),('new_matched','Expanded target matched')]:
            images.append(f[key]);labels.append(c['view']+' | '+label)
        for key,label in [('old_raw_alpha','Old linked ink'),('new_raw_alpha','New linked ink'),('new_matched_alpha','New matched ink'),('added_ink','Added proxy ink before S')]:
            inks.append(1-f[key]);il.append(c['view']+' | '+label)
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'Explicit target-scope change; original Gaussian IDs; source effects and ink budgets separately reported',columns=4)
    panel(UNIT/'ALL_DEV_INK.png',inks,il,'Old paths retained; only added-face paths generated; original-ID responsibility gates ink',columns=4)
    arc=[];al=[];frames=[]
    for i,v in enumerate(v for v in p['views'] if v['kind']=='arc'):
        c=v['camera'];f=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        keys=['old_raw','new_raw','new_matched']
        panel(frame,[f[k] for k in keys]+[1-f[k+'_alpha'] for k in keys],
            ['Old authored target','Expanded target natural','Expanded target matched','Old ink','Expanded ink','Expanded matched ink'],
            f'Actual orbit {c["azimuth"]:.1f} deg / elevation24 / distance5.3; fixed3D paths; exposed diagnostics',columns=3)
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for key in keys:arc.append(f[key]);al.append(f'{c["azimuth"]:.1f} deg | '+key)
    panel(UNIT/'ALL_ARC_FRAMES.png',arc,al,'All nine actual camera frames; no temporal/generalization certification',columns=6)
    movie=out/'target_completion_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode();expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape)
    exact=[bool(np.array_equal(a,b)) for a,b in zip(expected,actual)];assert all(exact)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=len(frames),all_frames_decoded_exact=exact,encode_argv=enc,decode_argv=dec,
        encode_rc=r.returncode,decode_rc=d.returncode,movie_sha256=sha(movie),movie=str(movie)))
    print('MEDIA nine frames decoded exactly',flush=True)

if __name__=='__main__':main()
