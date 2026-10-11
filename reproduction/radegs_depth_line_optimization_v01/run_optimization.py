import argparse,hashlib,json,os,shutil,sys,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageFont
from line_core import optimize,features,trace,visibility_confidence,camera_center,focus_center,world_points,focus_weight,PARAMETERS
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/astra_near_line_optimization_v01')
E=T/'evidence';font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def atomic(p,obj):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n');os.replace(tmp,p)

def grid(p,images,titles,cols=2):
    w,h=images[0].size;canvas=Image.new('RGB',(cols*w,((len(images)+cols-1)//cols)*(h+32)),'white');d=ImageDraw.Draw(canvas)
    for i,(im,title) in enumerate(zip(images,titles)):
        x=(i%cols)*w;y=(i//cols)*(h+32);canvas.paste(im.convert('RGB'),(x,y+32));d.text((x+8,y+5),title,font=font,fill='black')
    canvas.save(p,quality=94)

def bw(a):return Image.fromarray(np.where(a,0,255).astype('uint8'))
def gray(a):return Image.fromarray(np.rint(np.clip(a,0,1)*255).astype('uint8'))

def main():
    a=argparse.ArgumentParser();a.add_argument('--scenes',nargs='+',required=True);a.add_argument('--run',required=True);args=a.parse_args()
    assert shutil.disk_usage('/').free>=10*2**30 and shutil.disk_usage(T).free>=50*2**30
    out=T/args.run;out.mkdir(exist_ok=False)
    atomic(out/'PARAMETERS.json',PARAMETERS)
    ds=json.loads((E/'depth_line_pilot/outputs/SUMMARY.json').read_text())
    sources=[s for s in ds['sources'] if '/30000/' in s['member'] and s['scene'] in args.scenes]
    records=[];ledger={}
    def record(p,expected=None):
        p=Path(p);key=str(p)
        if key not in ledger:ledger[key]={'sha256':sha(p),'bytes':p.stat().st_size}
        if expected:assert ledger[key]['sha256']==expected,(p,'SOURCE_HASH_MISMATCH')
        return ledger[key]['sha256']
    cache={}
    def load(p):
        p=Path(p);record(p)
        if str(p) not in cache:
            with np.load(p) as n:cache[str(p)]=(n['median_camera_z'].squeeze().copy(),n['alpha'].squeeze().copy())
        return cache[str(p)]
    for scene in args.scenes:
        cache.clear()
        scene_sources=[s for s in sources if s['scene']==scene]
        parent=Path(scene_sources[0]['original_source']).parent
        cams=json.loads((parent/'cameras_and_conventions.json').read_text())
        center=focus_center(cams);radii=[]
        for source in scene_sources:
            pp=Path(source['original_source']);zz,aa=load(pp);cc=next(c for c in cams if c['view']==pp.stem)
            vv=np.isfinite(zz)&(zz>0)&np.isfinite(aa)&(aa>=.5);h,w=zz.shape
            central=np.zeros_like(vv);central[int(h*.2):int(h*.8),int(w*.2):int(w*.8)]=True
            rr=np.linalg.norm(world_points(np.where(vv,zz,0),cc)-center,axis=-1)
            radii.append(float(np.percentile(rr[vv&central],95)))
        radius=float(np.median(radii))
        for s in [s for s in sources if s['scene']==scene]:
            start=time.monotonic();p=Path(s['original_source']);record(p,s['sha256']);view=p.stem;label=scene+'_'+view
            cp=p.parent/'cameras_and_conventions.json';record(cp);cams=json.loads(cp.read_text());cam=next(c for c in cams if c['view']==view)
            z,alpha=load(p);valid=np.isfinite(z)&(z>0)&np.isfinite(alpha)&(alpha>=.5)
            refcams=sorted([c for c in cams if c['view']!=view],key=lambda c:(float(np.linalg.norm(camera_center(c)-camera_center(cam))),c['view']))[:6]
            refs=[]
            for c in refcams:
                rz,ra=load(p.parent/(c['view']+'.npz'));rv=np.isfinite(rz)&(rz>0)&np.isfinite(ra)&(ra>=.5);refs.append((rz,rv,c))
            f=optimize(z,alpha,cam);mv=visibility_confidence(z,valid,cam,refs)
            focus=focus_weight(z,cam,center,radius)
            s2weight=f['confidence']*mv['weight']*focus
            f2=trace(f['response'],f['direction'],f['support'],s2weight)
            repeat=optimize(z,alpha,cam);assert np.array_equal(repeat['lines'],f['lines']),'SAME_CAMERA_NONDETERMINISM'
            baseline=E/'strength_series/outputs'/f'{label}_D.png';cut=E/'near_failure/outputs'/f'{label}_near_lines.png';record(baseline);record(cut)
            folder=out/label;folder.mkdir();shutil.copy2(baseline,folder/'D.png');shutil.copy2(cut,folder/'hardcut.png')
            bw(f['lines']).save(folder/'S1.png');bw(f2).save(folder/'S2.png')
            for key,v in dict(distance_weight=f['distance_weight'],local_confidence=f['confidence'],mv_weight=mv['weight'],selection_S1=f['selection_weight'],selection_S2=s2weight,world_focus_weight=focus,valid=valid,support=f['support']).items():gray(v).save(folder/(key+'.png'))
            np.savez_compressed(folder/'responses_weights.npz',response=f['response'].astype('float32'),direction=f['direction'].astype('float32'),fine=f['fine_response'].astype('float32'),coarse=f['coarse_response'].astype('float32'),distance_weight=f['distance_weight'].astype('float32'),local_confidence=f['confidence'].astype('float32'),mv_weight=mv['weight'].astype('float32'),mv_observations=mv['observations'],mv_occluded=mv['occluded'],world_focus_weight=focus.astype('float32'))
            grid(out/(label+'_fixedcamera_comparison.jpg'),[Image.open(baseline),Image.open(cut),bw(f['lines']),bw(f2)],[label+' | D (original)','Rejected hard camera-z cut','S1 robust + soft distance','S2 world focus + multiview / same features'])
            grid(out/(label+'_support.jpg'),[gray(valid),gray(f['support']),gray(focus),gray(f['confidence']),gray(mv['weight']),gray(s2weight)],['Original finite/positive + alpha>=0.5','Local derivative support (no depth cut)','World focus prior: white=1; floor=0.05','Local multiscale fit confidence','MV: 0.8 unknown; white=consistent','S2 segment selection confidence'],cols=3)
            rec=dict(scene=scene,view=view,checkpoint=30000,source=str(p),source_sha256=s['sha256'],camera_file=str(cp),camera=cam,references=[c['view'] for c in refcams],width=z.shape[1],height=z.shape[0],valid_pixels=int(valid.sum()),S1_pixels=int(f['lines'].sum()),S2_pixels=int(f2.sum()),D_pixels=int((np.array(Image.open(baseline))<128).sum()),hardcut_pixels=int((np.array(Image.open(cut))<128).sum()),mv_observed_fraction=float((mv['observations'][valid]>0).mean()),comparison=str(out/(label+'_fixedcamera_comparison.jpg')),support=str(out/(label+'_support.jpg')),native_dir=str(folder),same_camera_recompute_identical=True,focus_center=center.tolist(),focus_radius=radius,focus_radius_per_fixed_view=radii,seconds=time.monotonic()-start)
            records.append(rec);atomic(out/'RUN_MANIFEST.json',dict(method='depth_only_line_optimization_v01',records=records,source_ledger=ledger,parameters=PARAMETERS,units='author preprocessed scene units; not meters',pixel_centers='u-(width-1)/2, v-(height-1)/2; world-to-camera extrinsic',status='RUNNING',code_sha256=sha(Path(__file__).with_name('line_core.py'))))
            print(json.dumps({k:rec[k] for k in ['scene','view','S1_pixels','S2_pixels','seconds']}),flush=True)
    d=json.loads((out/'RUN_MANIFEST.json').read_text());d['status']='OUTPUTS_GENERATED_REQUIRES_VISUAL_REVIEW';atomic(out/'RUN_MANIFEST.json',d)
if __name__=='__main__':main()
