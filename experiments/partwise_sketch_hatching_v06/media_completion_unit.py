"""Complete-object natural/matched panels and decoded actual nine-camera arc."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
import subprocess
import numpy as np
from PIL import Image
from run_completion_unit import protocol,fresh
from run_hybrid import read_npz,panel
from media_layer_ablation import FFMPEG


def main():
    p=protocol();out=fresh(UNIT/'media');images=[];labels=[];matched=[];matched_labels=[]
    for v in [v for v in p['views'] if v['kind']=='dev']:
        c=v['camera'];f=read_npz(UNIT/'dev'/c['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('original_paper','Original paper'),('completed_paper','Completed paper'),('original_hybrid','Original / fixed ink'),('completed_hybrid','Completed / fixed ink')]:
            images.append(f[key]);labels.append(c['view']+' | '+label)
        for key,label in [('original_matched_paper','Original matched paper'),('completed_matched_paper','Completed matched paper'),('original_matched_hybrid','Original matched hybrid'),('completed_matched_hybrid','Completed matched hybrid')]:
            matched.append(f[key]);matched_labels.append(c['view']+' | '+label)
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'All four exposed DEV views / natural source strengths / unchanged original-ID-linked proxy ink',columns=5)
    panel(UNIT/'ALL_DEV_MATCHED.png',matched,matched_labels,'Actual source-RGB effect matched on four original BUILD views; no per-view fitting',columns=4)
    arc=[];al=[];frames=[]
    for i,v in enumerate(v for v in p['views'] if v['kind']=='arc'):
        c=v['camera'];f=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        keys=['original_paper','completed_paper','original_hybrid','completed_hybrid']
        panel(frame,[f[k] for k in keys],['Original paper','Completed paper','Original / fixed ink','Completed / fixed ink'],
              f'Actual orbit {c["azimuth"]:.1f} deg / elevation24 / distance5.3; natural strength; UNKNOWN unchanged',columns=4)
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for key,label in [('original_hybrid','Original'),('completed_hybrid','Completed')]:arc.append(f[key]);al.append(f'{c["azimuth"]:.1f} deg | '+label)
    panel(UNIT/'ALL_ARC_FRAMES.png',arc,al,'All nine actual camera frames / same fixed 3D paths and ink alpha / no temporal certification',columns=6)
    movie=out/'paper_completion_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode()
    expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape)
    exact=[bool(np.array_equal(a,b)) for a,b in zip(expected,actual)];assert all(exact)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=len(frames),all_frames_decoded_exact=exact,
       encode_argv=enc,decode_argv=dec,encode_rc=r.returncode,decode_rc=d.returncode,
       ffmpeg_sha256=sha(FFMPEG),movie_sha256=sha(movie),movie=str(movie),scope='Actual short camera arc; no independent temporal ground truth.'))
    print('MEDIA',movie,'all nine frames exact',flush=True)


if __name__=='__main__':main()
