"""Generate the frozen synthetic RGB/camera bridge; all outputs pinned to unit006."""
from common import *
import time,shutil
from datetime import datetime,timezone
from PIL import Image,ImageDraw
U=OUT.parent/'unit_006'


def load():
    p=json.loads((U/'PROTOCOL.json').read_text())
    a=np.load(U/'oracle_only/lamp_mesh.npz',allow_pickle=False)
    return p,core.finalize_mesh(a['vertices'],a['faces'],a['parts'])


def raster(mesh,c):
    """Nearest face and optical-z, using perspective-correct triangle depth."""
    n=c['size'];depth=np.full((n,n),np.inf);owner=np.full((n,n),-1,np.int32)
    uv,z=core.project(mesh['vertices'],c)
    for fi,face in enumerate(mesh['faces']):
        p=uv[face];zz=z[face]
        if zz.min()<=0:continue
        lo=np.maximum(np.ceil(p.min(axis=0)).astype(int),0)
        hi=np.minimum(np.floor(p.max(axis=0)).astype(int),n-1)
        if np.any(hi<lo):continue
        a,b,d=p
        den=(b[1]-d[1])*(a[0]-d[0])+(d[0]-b[0])*(a[1]-d[1])
        if abs(den)<1e-12:continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        w0=((b[1]-d[1])*(xx-d[0])+(d[0]-b[0])*(yy-d[1]))/den
        w1=((d[1]-a[1])*(xx-d[0])+(a[0]-d[0])*(yy-d[1]))/den
        w2=1-w0-w1
        inside=(w0>=-1e-9)&(w1>=-1e-9)&(w2>=-1e-9)
        inv=w0/zz[0]+w1/zz[1]+w2/zz[2]
        dd=np.divide(1,inv,out=np.full_like(inv,np.inf),where=inside&(inv>0))
        view=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1];take=dd<view
        view[take]=dd[take];owner[lo[1]:hi[1]+1,lo[0]:hi[0]+1][take]=fi
    return depth,owner


def make_camera(p,az,el):
    k=p['camera'];c=core.camera(az,el,k['distance'],k['resolution'][0],k['focal_px'])
    c['center']=np.asarray(k['principal_point'],float)
    cv=np.eye(4);cv[:3,:3]=c['R'].T;cv[:3,3]=c['eye']
    return c,cv@np.diag([1,-1,-1,1])


def render_rgb(mesh,p,c):
    n=c['size'];s=p['camera']['supersample'];high=dict(c)
    high.update(size=n*s,focal=c['focal']*s,center=c['center']*s+(s-1)/2)
    _,owner=raster(mesh,high);valid=owner>=0
    r=p['renderer'];light=np.asarray(r['lighting']['world_light_to_source']);light=light/np.linalg.norm(light)
    gain=r['lighting']['ambient']+r['lighting']['diffuse']*np.maximum(0,mesh['normals']@light)
    mat=np.asarray([r['materials_linear_rgb'][str(x)] for x in mesh['parts']])
    face_rgb=mat*gain[:,None]
    linear=np.ones((n*s,n*s,3));linear[valid]=face_rgb[owner[valid]]
    linear=linear.reshape(n,s,n,s,3).mean(axis=(1,3))
    srgb=np.where(linear<=0.0031308,12.92*linear,1.055*np.power(linear,1/2.4)-0.055)
    rgb=np.rint(np.clip(srgb,0,1)*255).astype(np.uint8)
    depth,lowowner=raster(mesh,c);fg=lowowner>=0
    part=np.zeros((n,n),np.uint8);part[fg]=mesh['parts'][lowowner[fg]]
    normals=np.zeros((n,n,3),np.float32);normals[fg]=mesh['normals'][lowowner[fg]]
    depth[~fg]=0
    return rgb,dict(depth_z=depth.astype(np.float32),normal_world=normals,part_id=part,coverage=valid.reshape(n,s,n,s).mean(axis=(1,3)).astype(np.float32))


def contact(frames,split,root):
    cols=6;tile=192;head=28;rows=(len(frames)+cols-1)//cols
    sheet=Image.new('RGB',(cols*tile,rows*(tile+head)+32),'white');draw=ImageDraw.Draw(sheet)
    draw.text((8,8),f'{split.upper()} | Synthetic RGB input | All {len(frames)} views',fill='black')
    for i,f in enumerate(frames):
        x=(i%cols)*tile;y=32+(i//cols)*(tile+head)
        with Image.open(root/f['rgb_path']) as im:sheet.paste(im.resize((tile,tile),Image.Resampling.LANCZOS),(x,y+head))
        draw.text((x+4,y+3),f"{i:02d} az{f['azimuth_deg']:g} el{f['elevation_deg']:g}",fill='black')
    sheet.save(U/'figures'/f'{split}_all_views.png')
    ids=[0,len(frames)//2,len(frames)-1]
    full=Image.new('RGB',(512*3,540),'white');d=ImageDraw.Draw(full)
    for col,i in enumerate(ids):
        f=frames[i];d.text((col*512+8,8),f"{split.upper()} {i} | az{f['azimuth_deg']:g} el{f['elevation_deg']:g}",fill='black')
        with Image.open(root/f['rgb_path']) as im:full.paste(im,(col*512,28))
    full.save(U/'figures'/f'{split}_first_middle_last.png')


def run():
    p,mesh=load();assert not (U/'dataset').exists()
    lock=json.loads((U/'SOURCE_LOCK.json').read_text())
    for row in lock['files']:assert sha(Path(row['path']))==row['sha256'],row['path']
    for row in p['inputs']:assert sha(Path(row['path']))==row['sha256'],row['path']
    (U/'figures').mkdir(exist_ok=True)
    records=[];summary={};counts={}
    for split in ('train','dev','test'):
        root=U/'dataset'/('train' if split=='train' else f'evaluation/{split}')
        (root/'rgb').mkdir(parents=True);(U/'oracle_only'/split).mkdir()
        frames=[];trans=[]
        for ei,el in enumerate(p['camera']['elevations_deg']):
            for ai,az in enumerate(p['splits'][split]['azimuths_deg']):
                start=time.monotonic();ident=f'{split}_e{ei}_a{ai:02d}'
                c,gl=make_camera(p,az,el);rgb,oracle=render_rgb(mesh,p,c)
                dest=root/'rgb'/f'{ident}.png';Image.fromarray(rgb).save(dest)
                np.savez_compressed(U/'oracle_only'/split/f'{ident}.npz',**oracle)
                f=dict(id=ident,split=split,azimuth_deg=az,elevation_deg=el,distance=p['camera']['distance'],width=c['size'],height=c['size'],focal_px=c['focal'],principal_point=c['center'],R_w2c=c['R'],t_w2c=c['t'],eye_world=c['eye'],c2w_opengl=gl,rgb_path=f'rgb/{ident}.png',rgb_sha256=sha(dest))
                frames.append(f);trans.append(dict(file_path=f'./rgb/{ident}',rotation=0,transform_matrix=gl))
                uv,z=core.project(mesh['vertices'],c)
                records.append(dict(id=ident,split=split,render_and_save_seconds=time.monotonic()-start,vertex_uv_min=uv.min(axis=0),vertex_uv_max=uv.max(axis=0),min_vertex_depth=z.min(),visible_pixels_by_part={str(k):int((oracle['part_id']==k).sum()) for k in (1,2,3)}))
        write_json(root/'cameras.json',dict(split=split,frames=frames))
        angle=2*np.arctan(c['size']/(2*c['focal']))
        write_json(root/f'transforms_{split}.json',dict(camera_angle_x=angle,frames=trans))
        if split=='train':write_json(root/'transforms_test.json',dict(camera_angle_x=angle,frames=[]))
        contact(frames,split,root);counts[split]=len(frames)
        summary[split]=dict(count=len(frames),root=str(root),camera_sha256=sha(root/'cameras.json'))
        print(f'{split}: {len(frames)} RGB/cameras saved',flush=True)
    write_json(U/'dataset/DATASET.json',dict(schema='lamp_rgb_camera_v1',splits={'train':'train/cameras.json','dev':'evaluation/dev/cameras.json','test':'evaluation/test/cameras.json'},counts=counts,claim='AUTHORED_SYNTHETIC_RGB_INPUT_ONLY_NOT_RECONSTRUCTED',protocol_sha256=sha(U/'PROTOCOL.json')))
    write_json(U/'GENERATION.json',dict(frames=records,splits=summary,count=sum(counts.values()),completed_utc=datetime.now(timezone.utc).isoformat(),rendering=p['renderer']))
    write_json(U/'oracle_only/ORACLE.json',dict(role='GT_DIAGNOSTIC_ONLY_NEVER_MAIN_RECONSTRUCTED_PROXY',geometry_source_sha256=sha(U/'oracle_only/lamp_mesh.npz'),background=dict(depth_z=0,normal_world=[0,0,0],part_id=0),depth='positive camera optical z at output pixel centers',normal='oriented world-space face normal; background zero',part_id={'1':'shade','2':'stem','3':'base'},coverage='2x2 supersample foreground fraction; independent center-sample IDs may be0 at partially covered pixels',prohibition='Do not give this directory to training or initialize geometry/labels from it. Do not use held-out RGB for reconstruction.'))
    print(json.dumps(native({'frames':len(records),'render_save_seconds':sum(x['render_and_save_seconds'] for x in records)})))


def cold():
    p,mesh=load();c,_=make_camera(p,0,10);rgb,_=render_rgb(mesh,p,c)
    dest=U/'cold_replay/train_e0_a00.png';dest.parent.mkdir(exist_ok=True);assert not dest.exists();Image.fromarray(rgb).save(dest)
    old=U/'dataset/train/rgb/train_e0_a00.png'
    with Image.open(old) as im: equal=bool(np.array_equal(rgb,np.asarray(im)))
    write_json(U/'COLD_REPLAY.json',dict(id='train_e0_a00',rgb_exact=equal,png_sha256=sha(dest),original_sha256=sha(old),claim='One deterministic generation check, not reconstruction/quality validation'))
    assert equal

if __name__=='__main__':
    {'run':run,'cold':cold}[sys.argv[1]]()
