"""Same-camera native RGB panels and fully decoded actual native camera videos."""
import hashlib,json,subprocess,time
from pathlib import Path
import numpy as np
import torch
from PIL import Image,ImageDraw,ImageFont
from runtime import ART,OUT,V1,result,sha,atomic_json,guard
from adapter import make_camera,render,selected_contribution
from preparation import save_png
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(n):return ImageFont.truetype(FONT,n)
PANELS=[('reference','Reference TRAIN PNG'),('B0','B0 full SH3'),('relative_color_ordinary','Ordinary color / 336'),('relative_color','Relative color / 336'),('relative_cov_ordinary','Ordinary cov / 336'),('relative_cov','Relative cov / 336'),('candidate_overlay','Selected full-model alpha*T')]
def array_image(a):return Image.fromarray(np.round(np.clip(a,0,1)*255).astype(np.uint8))
def load_arrays(scene,role,arm,key):return dict(np.load(OUT/scene/'evaluation'/role/arm/key/'native.npz'))
def montage(scene,views,role='dev'):
    chosen=views[:4];nativewidth=views[0]['entry']['camera']['width'];figdir=ART/'figures';figdir.mkdir(exist_ok=True)
    sheet=Image.new('RGB',(len(PANELS)*256,len(chosen)*(256+44)+50),'white');draw=ImageDraw.Draw(sheet);draw.text((12,10),f'{scene.upper()} | {role} | fixed camera / full SH3 | exploratory',font=font(24),fill='black')
    manifest=[]
    for row,v in enumerate(chosen):
        base=load_arrays(scene,role,'B0',v['key']);heat=base['selected_full_model_T'];b=base['rgb'];overlay=b*.72+np.stack([np.ones_like(heat),.25*np.ones_like(heat),np.zeros_like(heat)],axis=-1)*.28*heat[:,:,None];overlay=np.where((heat>1e-4)[:,:,None],overlay,b)
        images={'reference':v['gt'].cpu().numpy().transpose(1,2,0),'candidate_overlay':overlay}
        for arm,label in PANELS:
            if arm not in images:images[arm]=load_arrays(scene,role,arm,v['key'])['rgb']
        full=Image.new('RGB',(nativewidth*len(PANELS),nativewidth+70),'white');fd=ImageDraw.Draw(full)
        roi=v['evidence']['roi'];x0,y0,x1,y1=roi
        cell=max(x1-x0,210)
        crop=Image.new('RGB',(cell*4,(y1-y0)+64),'white');cd=ImageDraw.Draw(crop)
        cropkeys=['reference','B0','relative_cov_ordinary','relative_cov']
        for col,(key,label) in enumerate(PANELS):
            im=array_image(images[key]);full.paste(im,(col*nativewidth,70));fd.text((col*nativewidth+8,6),label,font=font(21),fill='black');fd.text((col*nativewidth+8,35),f'{v["key"]} / {key}',font=font(16),fill='black')
            y=50+row*300;sheet.paste(im.resize((256,256),Image.Resampling.LANCZOS),(col*256,y+44));draw.text((col*256+5,y+3),label,font=font(13),fill='black');draw.text((col*256+5,y+23),f'{v["key"]} / {key}',font=font(12),fill='black')
        for col,key in enumerate(cropkeys):
            crop.paste(array_image(images[key]).crop(tuple(roi)),(col*cell+(cell-(x1-x0))//2,64));cd.text((col*cell+4,4),key,font=font(13),fill='black');cd.text((col*cell+4,24),f'{v["key"]} native pixels',font=font(11),fill='black')
        name=f'{scene}_{role}_{v["key"]}_same_camera';full.save(figdir/f'{name}.jpg',quality=93);crop.save(figdir/f'{name}_native_edge.png')
        # Also publish an enlarged crop preserving raw native pixels by nearest resize.
        crop.resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST).save(figdir/f'{name}_edge_zoom.png')
        manifest.append({'scene':scene,'key':v['key'],'camera_hash':v['entry']['camera_hash'],'subplot_keys':[x[0] for x in PANELS],'native_roi':roi,'roi_source':'fixed original TRAIN-role target, reference only','same_camera_figure':str(figdir/f'{name}.jpg'),'edge_crop':str(figdir/f'{name}_native_edge.png'),'candidate_map':'full-model alpha*T; all primitives stay in native occlusion traversal; no selected-only model'})
    sheet.save(figdir/f'{scene}_{role}_fourview_contactsheet.jpg',quality=95)
    result(f'{scene}_{role}_figure_manifest',manifest);return manifest
def videos(scene,cameras,models,ids,name='arc0'):
    guard(f'{scene}/videos/{name}');ff=V1/'deps/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2';records=[];(ART/'videos').mkdir(exist_ok=True)
    for arm,m in models.items():
        directory=OUT/scene/'video_frames'/name/arm;directory.mkdir(parents=True,exist_ok=True);framehash=[]
        for i,entry in enumerate(cameras):
            with torch.no_grad():im=render(m,make_camera(entry['camera']))
            path=directory/f'{i:03d}.png';save_png(path,im);framehash.append(sha(path))
        video=ART/'videos'/f'{scene}_{arm}_{name}_33.mp4'
        subprocess.run([str(ff),'-y','-loglevel','error','-threads','2','-framerate','12','-i',str(directory/'%03d.png'),'-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
        raw=subprocess.check_output([str(ff),'-v','error','-threads','2','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'])
        w=cameras[0]['camera']['width'];h=cameras[0]['camera']['height'];bytes_per=w*h*3
        if len(raw)!=len(cameras)*bytes_per:raise AssertionError('incomplete video decode')
        hashes=[hashlib.sha256(raw[i*bytes_per:(i+1)*bytes_per]).hexdigest() for i in range(len(cameras))]
        if len(set(hashes))!=len(cameras):raise AssertionError('non-distinct frame decode')
        records.append({'scene':scene,'arm':arm,'path':str(video),'video_sha256':sha(video),'bytes':video.stat().st_size,'frames':len(cameras),'width':w,'height':h,'codec':'H264','pixel_format':'yuv420p','faststart':True,'decoded_frames':len(hashes),'distinct_decoded_frames':len(set(hashes)),'decoded_frame_sha256':hashes,'raw_native_png_sha256':framehash,'camera_hashes':[e['camera_hash'] for e in cameras],'full_native_RGB':True,'reference_photos':False,'scope':cameras[0]['role']})
    result(f'{scene}_media_{name}',records);return records
