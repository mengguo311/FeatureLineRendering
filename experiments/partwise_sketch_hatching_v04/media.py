"""Actual-frame contact sheets and lossless full-video decode validation."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse
import json
import subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont

FFMPEG=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')

def contact(path,items,cols=4,size=384,title=''):
    rows=(len(items)+cols-1)//cols
    out=Image.new('RGB',(cols*size,45+rows*(size+25)),'white');draw=ImageDraw.Draw(out)
    draw.text((10,10),title,fill='black')
    for i,(label,image) in enumerate(items):
        x=i%cols*size;y=45+i//cols*(size+25)
        draw.text((x+5,y+5),label,fill='black')
        out.paste(image.convert('RGB').resize((size,size)),(x,y+25))
    out.save(path)

def create(unit):
    unit=Path(unit);out=unit/'media';out.mkdir(exist_ok=True)
    p=json.loads((unit/'PROTOCOL.json').read_text())
    items=[]
    for i,c in enumerate(p['static_cameras']):
        refpath=p['references'].get(c['view'],str(unit/f'source_model/frame_{i:03d}_rgb.png'))
        ref=Image.open(refpath).convert('RGBA')
        white=Image.new('RGBA',ref.size,'white');white.alpha_composite(ref)
        label='reference RGB' if c['view'] in p['references'] else 'source GS RGB'
        items.append((c['view']+' | '+label,white))
        for label,key in [('Model-derived proxy','proxy'),('Authored height regions','region_rgb'),('Fixed 3D hatch baseline','image')]:
            items.append((label,Image.open(unit/f'renders/static_baseline/frame_{i:03d}_{key}.png')))
    contact(out/'reference_proxy_regions_hatch.png',items,title=p['scene'].title()+' | original model -> exploratory TSDF proxy -> persistent 3D hatching')
    before_after=[]
    for i,c in enumerate(p['static_cameras']):
        for name in ('baseline','edited'):
            before_after.append((c['view']+' | '+name,Image.open(unit/f'renders/static_{name}/frame_{i:03d}_image.png')))
    contact(out/'local_edit_all_views.png',before_after,cols=4,title='Middle region angle 45 -> 95 degrees | upper/lower paths preserved')
    if (unit/'renders/static_original').exists():
        for start,group in [(0,'historical'),(4,'new')]:
            comparisons=[]
            for i,c in list(enumerate(p['static_cameras']))[start:start+4]:
                comparisons.append((c['view']+' | source GS RGB',Image.open(unit/f'source_model/frame_{i:03d}_rgb.png')))
                for label,arm,key in [('Original proxy','original','proxy'),('Bounded smooth proxy','baseline','proxy'),
                                      ('Original hatching','original','image'),('Candidate hatching','baseline','image')]:
                    comparisons.append((label,Image.open(unit/f'renders/static_{arm}/frame_{i:03d}_{key}.png')))
            contact(out/f'refinement_{group}_views.png',comparisons,cols=5,size=384,
                    title='Chair | same styles and cameras | geometry only | complete objects, including weak views')
    video_receipts=[]
    for name in ('orbit','zoom'):
        folder=unit/f'renders/{name}';files=sorted(folder.glob('frame_*_image.png'))
        contact(out/(name+'_all_frames.png'),[(f'{name} {i:02d}',Image.open(f)) for i,f in enumerate(files)],cols=4,size=320,
                title='Actual cameras, same saved 3D asset | all frames including weak views')
        video=out/(name+'.mkv')
        command=[str(FFMPEG),'-nostdin','-v','error','-threads','1','-filter_threads','1','-framerate','6','-i',
                 str(folder/'frame_%03d_image.png'),'-c:v','ffv1','-level','3','-pix_fmt','bgr0','-threads','1','-y',str(video)]
        encoded=subprocess.run(command,capture_output=True,text=True,timeout=120);encoded.check_returncode()
        decode=[str(FFMPEG),'-nostdin','-v','error','-threads','1','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','-']
        decoded=subprocess.run(decode,capture_output=True,timeout=120);decoded.check_returncode()
        raw=np.frombuffer(decoded.stdout,np.uint8).reshape(-1,512,512,3)
        assert len(raw)==len(files)
        for a,f in zip(raw,files):np.testing.assert_array_equal(a,np.asarray(Image.open(f).convert('RGB')))
        video_receipts.append(dict(name=name,encode_command=command,encode_returncode=encoded.returncode,
                                   decode_command=decode,decode_returncode=decoded.returncode,frames=len(files),
                                   all_decoded_frames_exact=True,sha256=sha(video)))
    js(out/'VIDEO_VALIDATION.json',dict(utc=now(),videos=video_receipts,
                                      scope='all actual frames decoded exactly; not a temporal-stability certification'))
    print(json.dumps(video_receipts),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);create(p.parse_args().unit)
