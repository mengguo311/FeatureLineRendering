"""Complete-object native panels, geometry-defined closeups, and true camera videos."""
from runtime import *
import subprocess
from PIL import Image, ImageDraw, ImageFont

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def pair(frame):
    canvas=Image.new('RGB',(1024,544),'white'); draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype(FONT,16)
    sources=[]
    for i,(arm,title) in enumerate([('B1_like','B1-like: rings OFF'),('B2_existing','B2-existing: accepted rings ON')]):
        path=ROOT/'renders'/frame['sequence']/frame['id']/arm/'image.png'
        with Image.open(path) as image: canvas.paste(image.convert('RGB'),(i*512,32))
        draw.text((i*512+8,7),f'{title} | az {frame["azimuth"]:g}',font=font,fill='black')
        sources.append(dict(path=str(path),sha256=sha(path)))
    return canvas,sources

def contact(images,columns,thumb):
    h=round(544*thumb/1024); rows=(len(images)+columns-1)//columns
    canvas=Image.new('RGB',(columns*thumb,rows*h),'white')
    for i,img in enumerate(images):
        canvas.paste(img.resize((thumb,h),Image.Resampling.LANCZOS),((i%columns)*thumb,(i//columns)*h))
    return canvas

def main():
    p=json.loads((ROOT/'PROTOCOL.json').read_text())
    out=ROOT/'media'
    if out.exists(): raise FileExistsError(out)
    out.mkdir()
    mesh,_,_=load_asset(); curves=json.loads((ROOT/'audit/AUTHORED_CURVES.json').read_text())['curves']
    source_rows=[]; images_by_sequence={}; provenance=[]
    for seq in ('static','orbit','zoom'):
        frames=[f for f in p['frames'] if f['sequence']==seq]; imgs=[]
        for f in frames:
            img,sources=pair(f); imgs.append(img)
            path=output_path(out/'frames'/seq/f'{f["index"]:04}.png'); img.save(path)
            source_rows.append(dict(frame=f,sources=sources,pair_path=str(path),pair_sha256=sha(path)))
        images_by_sequence[seq]=imgs
        contact(imgs,1 if seq=='static' else 3,1024 if seq=='static' else 512).save(out/f'{seq}_all_frames.png')
    # Predefined geometry regions; no selection by visual result or darkness.
    groups=[('shade_top',1,2.35),('shade_bottom',1,1.4),('base_top',3,.16)]
    for f in [x for x in p['frames'] if x['sequence']=='static']:
        camera=core.camera(f['azimuth'],f['elevation'],f['distance'],512,600)
        for name,part,y in groups:
            points=np.concatenate([np.asarray(c['points']) for c in curves if c['part_ids']==[part] and abs(c['points'][0][1]-y)<1e-9])
            uv,_=core.project(points,camera)
            lo=np.maximum(np.floor(uv.min(axis=0)).astype(int)-10,0)
            hi=np.minimum(np.ceil(uv.max(axis=0)).astype(int)+11,512)
            box=tuple(map(int,(*lo,*hi))); w,h=int(hi[0]-lo[0]),int(hi[1]-lo[1])
            canvas=Image.new('RGB',(4*w,2*h+28),'white'); draw=ImageDraw.Draw(canvas)
            for i,arm in enumerate(('B1_like','B2_existing')):
                source=ROOT/'renders/static'/f['id']/arm/'image.png'
                with Image.open(source) as image:
                    crop=image.convert('RGB').crop(box).resize((2*w,2*h),Image.Resampling.NEAREST)
                    canvas.paste(crop,(2*w*i,28))
                draw.text((2*w*i+4,6),f'{arm} {name} az{f["azimuth"]}',fill='black')
                provenance.append(dict(source=str(source),source_sha256=sha(source),box_xyxy=box,scale=2,interpolation='nearest',region=name))
            canvas.save(out/f'{f["id"]}_{name}_2x.png')
    videos=[]
    for seq,count in (('orbit',12),('zoom',8)):
        video=out/f'{seq}_comparison.mkv'
        cmd=[FFMPEG,'-v','error','-threads','1','-filter_threads','1','-filter_complex_threads','1',
             '-framerate','6','-i',str(out/'frames'/seq/'%04d.png'),'-c:v','ffv1','-level','3','-threads','1','-pix_fmt','bgr0',str(video)]
        encoded=subprocess.run(cmd,capture_output=True,timeout=90)
        (out/f'{seq}_encode.log').write_bytes(encoded.stderr)
        receipt=dict(encode_command=cmd,encode_returncode=encoded.returncode)
        write_json(out/f'{seq}_encoding.json',receipt); encoded.check_returncode()
        decode=[FFMPEG,'-v','error','-threads','1','-filter_threads','1','-i',str(video),'-map','0:v:0',
                '-f','rawvideo','-pix_fmt','rgb24','-threads','1','-']
        result=subprocess.run(decode,capture_output=True,timeout=90)
        (out/f'{seq}_decode.log').write_bytes(result.stderr)
        receipt.update(decode_command=decode,decode_returncode=result.returncode)
        write_json(out/f'{seq}_encoding.json',receipt); result.check_returncode()
        expected_bytes=count*1024*544*3
        assert len(result.stdout)==expected_bytes, (len(result.stdout),expected_bytes)
        decoded=np.frombuffer(result.stdout,np.uint8).reshape(count,544,1024,3)
        matches=[]; rawhashes=[]
        for i in range(count):
            source=out/'frames'/seq/f'{i:04}.png'
            expected=np.asarray(Image.open(source).convert('RGB'))
            matches.append(bool(np.array_equal(decoded[i],expected)))
            rawhashes.append(hashlib.sha256(decoded[i].tobytes()).hexdigest())
        assert all(matches) and len(set(rawhashes))==count
        videos.append(dict(sequence=seq,video=str(video),sha256=sha(video),decoded_frames=count,expected_frames=count,
                           every_frame_rgb_exact=all(matches),unique_decoded_frames=len(set(rawhashes)),raw_frame_sha256=rawhashes,
                           size=[1024,544],fps=6,per_camera_renders=True,commands=receipt))
    write_json(out/'VALIDATION.json',dict(videos=videos,sources=source_rows,crops=provenance,all_valid=True,
                    scope='Offline comparison: native512 square panels; actual camera orbit/zoom from fixed paths; no timing/temporal performance claim.'))
    update_status('MEDIA_DECODE_VALIDATED')
    print(json.dumps(dict(valid=True,orbit_frames=12,zoom_frames=8,frame_exact=True)))

if __name__=='__main__': main()
