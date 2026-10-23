"""Full-object evidence and decoded real-camera short arc; no image enhancement."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
import subprocess
import numpy as np
from PIL import Image
from run_contour_unit import protocol,fresh
from run_hybrid import read_npz,panel
from media_layer_ablation import FFMPEG


def main():
    p=protocol();out=fresh(UNIT/'media');images=[];labels=[];inks=[];il=[]
    for v in (v for v in p['views'] if v['kind']=='dev'):
        c=v['camera'];a=read_npz(UNIT/'dev'/c['view']/'FRAME.npz')
        for key,label in [('source','Original GS'),('hatch_raw','Old hatch'),('outlined_raw','Owned contour / natural'),('outlined_matched','Owned contour / matched')]:
            images.append(a[key]);labels.append(c['view']+' | '+label)
        for key,label in [('hatch_raw_alpha','Old linked hatch'),('contour_ink','Contour before S'),('contour_alpha','Linked contour only'),('outlined_matched_alpha','Combined matched ink')]:
            inks.append(1-a[key]);il.append(c['view']+' | '+label)
    panel(UNIT/'ALL_DEV_VIEWS.png',images,labels,'Old natural ink budget matched on four BUILD views; fixed original-GS paper and S; no DEV fitting',columns=4)
    panel(UNIT/'ALL_DEV_INK.png',inks,il,'View contours and old3D paths separate; original-ID responsibility gates both; exposed diagnostic cameras',columns=4)
    arc=[];al=[];frames=[]
    for i,v in enumerate(v for v in p['views'] if v['kind']=='arc'):
        c=v['camera'];a=read_npz(UNIT/'arc'/c['view']/'FRAME.npz');frame=out/f'frame_{i:03d}.png'
        keys=['hatch_raw','outlined_raw','outlined_matched']
        panel(frame,[a[k] for k in keys]+[1-a[k+'_alpha'] for k in keys],
            ['Old hatch','Owned contour natural','Owned contour matched','Old ink','Combined ink natural','Combined ink matched'],
            f'Actual orbit {c["azimuth"]:.1f} deg / elevation24 / distance5.3; fixed3D hatch, view-dependent contours',columns=3)
        frames.append(np.asarray(Image.open(frame).convert('RGB')))
        for key in keys:arc.append(a[key]);al.append(f'{c["azimuth"]:.1f} deg | '+key)
    panel(UNIT/'ALL_ARC_FRAMES.png',arc,al,'All nine actual cameras; no independent temporal certification',columns=6)
    movie=out/'owned_contour_arc_ffv1.mkv'
    enc=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fps']),'-i',str(out/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
    r=subprocess.run(enc,capture_output=True,timeout=60);r.check_returncode()
    dec=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
    d=subprocess.run(dec,capture_output=True,timeout=60);d.check_returncode()
    expected=np.stack(frames);actual=np.frombuffer(d.stdout,np.uint8).reshape(expected.shape)
    exact=[bool(np.array_equal(a,b)) for a,b in zip(expected,actual)];assert all(exact)
    js(UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),frames=len(frames),all_frames_decoded_exact=exact,
        encode_argv=enc,decode_argv=dec,encode_rc=r.returncode,decode_rc=d.returncode,ffmpeg_sha256=sha(FFMPEG),
        movie_sha256=sha(movie),movie=str(movie),scope='Actual nine-camera short arc, not fixed-camera edit ramp; no independent temporal truth.'))
    print('MEDIA',movie,'nine decoded frames exact',flush=True)


if __name__=='__main__':main()
