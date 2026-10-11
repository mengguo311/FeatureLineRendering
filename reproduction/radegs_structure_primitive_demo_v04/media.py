from common import *
from run import show_panel
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw,ImageFont
import subprocess,re,sys
FFMPEG=O/'dependencies/unpacked/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'

def arc_cameras(cs):
    Es=[np.asarray(cs[v]['extrinsic']) for v in BUILD];centers=np.array([-np.linalg.solve(e[:3,:3],e[:3,3]) for e in Es]);dirs=np.array([e[2,:3]/np.linalg.norm(e[2,:3]) for e in Es]);P=np.eye(3)[None]-dirs[:,:,None]*dirs[:,None,:]
    focus=np.linalg.solve(P.sum(0),np.einsum('nij,nj->i',P,centers));c0=cs['0024'];e0=np.asarray(c0['extrinsic']);C0=-np.linalg.solve(e0[:3,:3],e0[:3,3]);direction=core.normalize(C0-focus);up=core.normalize(-e0[1,:3]);dist=1.6*float(np.median(np.linalg.norm(centers-focus,axis=1)));arc=[]
    for angle in np.linspace(-8,8,33):
        C=focus+Rotation.from_rotvec(up*np.deg2rad(angle)).apply(direction)*dist;forward=core.normalize(focus-C);right=core.normalize(np.cross(forward,up));down=np.cross(forward,right);R=np.stack([right,down,forward]);E=np.eye(4);E[:3,:3]=R;E[:3,3]=-R@C;arc.append(dict(c0,extrinsic=E.tolist(),view='arc',arc_degrees=float(angle)))
    return {'focus':focus.tolist(),'distance':dist,'pose_only_framing':'three build optical-axis intersection; 1.6x median orbit radius; no model filtering','cameras':arc,'original_scene_occlusion':False}

def video(scene):
    guard();dst=T/'media_corrected'/scene;dst.mkdir(parents=True,exist_ok=True);cs=demo.cameras(scene);cam=arc_cameras(cs);js(dst/'ARC_CAMERAS.json',cam)
    a=dict(np.load(T/'results'/f'{scene}_full/optimized_gaussians.npz'));old=dict(np.load(O/'results_v2'/scene/'balanced_gaussians.npz'));fr=dst/'frames';fr.mkdir(exist_ok=True)
    for i,c in enumerate(cam['cameras']):
        r0=core.render(old,c);r1=core.render(a,c);show_panel(fr/f'{i:03d}.png',[('Old balanced / 3 build views',r0),('Shared structure primitive / fixed Gaussians',r1)],scene+f' {i+1}/33 | INK ONLY / NO ORIGINAL-SCENE OCCLUSION',cols=2,subtitle='True novel-camera Gaussian projection; no source-depth occluder; no per-frame detector')
    path=dst/'balanced_vs_structure.mp4';cmd=[str(FFMPEG),'-hide_banner','-loglevel','error','-threads','2','-filter_threads','2','-framerate','12','-i',str(fr/'%03d.png'),'-c:v','libx264','-threads','2','-crf','19','-pix_fmt','yuv420p','-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-movflags','+faststart','-y',str(path)]
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(dst/'ENCODE_LOG.txt').write_text(p.stdout);assert p.returncode==0
    decode=[str(FFMPEG),'-threads','2','-i',str(path),'-threads','2','-f','null','-'];p=subprocess.run(decode,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(dst/'DECODE_LOG.txt').write_text(p.stdout);assert p.returncode==0;nums=re.findall(r'frame=\s*(\d+)',p.stdout);assert nums and int(nums[-1])==33;assert 'yuv420p' in p.stdout and 'h264' in p.stdout
    atoms=[]
    with path.open('rb') as f:
        while True:
            b=f.read(8)
            if len(b)<8:break
            size=int.from_bytes(b[:4],'big');atoms.append(b[4:].decode('ascii',errors='replace'))
            if size==1:size=int.from_bytes(f.read(8),'big');f.seek(size-16,1)
            elif size>=8:f.seek(size-8,1)
            else:break
    assert atoms.index('moov')<atoms.index('mdat');js(dst/'VALIDATION.json',{'rendered_frames':len(list(fr.glob('*.png'))),'decoded_frames':33,'codec':'H264','pixel_format':'yuv420p','atoms':atoms,'encode_command':cmd,'decode_command':decode,'source_asset_sha256':sha(T/'results'/f'{scene}_full/optimized_gaussians.npz'),'old_asset_sha256':sha(O/'results_v2'/scene/'balanced_gaussians.npz'),'no_frame_detector':True,'novel_original_scene_occlusion':False})
    ims=[Image.open(fr/f'{i:03d}.png').convert('RGB') for i in (0,16,32)];canvas=Image.new('RGB',(ims[0].width,ims[0].height*3),'white')
    for i,im in enumerate(ims):canvas.paste(im,(0,i*im.height))
    canvas.save(dst/'first_middle_last.jpg',quality=92);seal(dst);print('VIDEO_VERIFIED',scene,33,flush=True)

def fair_roi():
    src=T/'results/scan24_roi';dst=T/'roi_fair_comparison';dst.mkdir(exist_ok=True);led=np.load(src/'observations.npz');cs=demo.cameras('scan24');raw=[]
    for vi,v in enumerate(BUILD):
        use=(led['source_view']==vi)&(led['reason']!=2)&np.isfinite(led['depth'])&(led['depth']>0);uv=led['uv'][use];z=led['depth'][use];p=z/np.sqrt(cs[v]['fx']*cs[v]['fy'])
        raw.append({'means':core.backproject(uv,z,cs[v]),'covariance':np.eye(3)[None]*(.45*p[:,None,None])**2,'opacity':np.minimum(.95,led['darkness'][use])})
    a={k:np.concatenate([r[k] for r in raw]) for k in raw[0]};np.savez_compressed(dst/'three_build_all_pixel_raw.npz',**a)
    initial=dict(np.load(src/'initial_gaussians.npz'));final=dict(np.load(src/'optimized_gaussians.npz'));v3=dict(np.load(V3/'roi_pilot/skeleton_opacity_fit.npz'))
    for v in BUILD:
        im=demo.read('scan24',v);D=demo.detect(im)['dark'];c=cs[v];x0,y0,x1,y1=CFG['roi_windows'][v];crop=lambda x:x[y0:y1,x0:x1]
        items=[('Original unchanged Spatial target',crop(1-D)),('RAW 3-build / same acquisition windows',crop(core.render(a,c,im['z'],im['alpha']))),('v03 opacity-only / source0000 ONLY',crop(core.render(v3,c,im['z'],im['alpha']))),('Primitive INIT / 3 build windows',crop(core.render(initial,c,im['z'],im['alpha']))),('Primitive OPTIMIZED / 3 build windows',crop(core.render(final,c,im['z'],im['alpha'])))]
        show_panel(dst/f'{v}_fair_comparison.jpg',items,'FIXED ROI / additional sources disclosed; v03 is not a matched ablation',cols=3,scale=3)
    js(dst/'SUMMARY.json',{'raw_gaussians':len(a['means']),'source_views':BUILD,'creation_domains':{'0000':CFG['roi'],'0024':CFG['roi_windows']['0024'],'0048':CFG['roi_windows']['0048']},'v03_only_one_creation_view':True});seal(dst)

if __name__=='__main__':
    if sys.argv[1]=='roi':fair_roi()
    else:video(sys.argv[1])
