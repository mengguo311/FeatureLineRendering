"""Encode saved fixed-camera ink edits and decode every frame losslessly."""
import runtime
from runtime import ACTIVE_UNIT,js,sha,now,output_guard
import subprocess,json
from pathlib import Path
import numpy as np
from PIL import Image
from run_hybrid import protocol

FFMPEG=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')

def main():
    p=protocol(ACTIVE_UNIT);results={}
    for scene,s in p['scenes'].items():
        c=s['evaluation_cameras'][p['fixed_camera_ink_ramp']['view_index']]
        folder=ACTIVE_UNIT/'results'/scene/c['view']/'ink_ramp'
        movie=output_guard(folder/'ink_edit_ffv1.mkv')
        if movie.exists():raise FileExistsError(movie)
        encode=[str(FFMPEG),'-v','error','-n','-threads','1','-framerate',str(p['fixed_camera_ink_ramp']['fps']),
                '-i',str(folder/'frame_%03d.png'),'-c:v','ffv1','-level','3','-threads','1',str(movie)]
        result=subprocess.run(encode,capture_output=True,timeout=60)
        result.check_returncode()
        decode=[str(FFMPEG),'-v','error','-threads','1','-i',str(movie),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','pipe:1']
        back=subprocess.run(decode,capture_output=True,timeout=60);back.check_returncode()
        expected=np.stack([np.asarray(Image.open(folder/f'frame_{i:03d}.png').convert('RGB'))
                           for i in range(len(p['fixed_camera_ink_ramp']['levels']))])
        actual=np.frombuffer(back.stdout,np.uint8).reshape(expected.shape)
        exact=[bool(np.array_equal(x,y)) for x,y in zip(expected,actual)]
        assert all(exact)
        differences=[float(np.abs(expected[i].astype(float)-expected[0]).sum()) for i in range(len(expected))]
        assert differences[-1]>0 and all(a<=b for a,b in zip(differences,differences[1:]))
        results[scene]=dict(movie=str(movie),sha256=sha(movie),camera=c,frames=len(expected),
            all_frames_decoded_exact=exact,edit_effect_L1_from_zero_ink=differences,
            encode_argv=encode,decode_argv=decode,encode_rc=result.returncode,decode_rc=back.returncode,
            scope='Fixed-camera ink strength edit; paper substrate fixed. Not an orbit or temporal-stability certification.')
    js(ACTIVE_UNIT/'MEDIA_VALIDATION.json',dict(utc=now(),ffmpeg_path=str(FFMPEG),ffmpeg_sha256=sha(FFMPEG),scenes=results))
    print(json.dumps(results,indent=2),flush=True)

if __name__=='__main__':main()
