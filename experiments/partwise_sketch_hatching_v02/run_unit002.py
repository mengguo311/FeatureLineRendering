"""One frozen full-lamp contour repair; explicit unit002 outputs only."""
from common import *
import argparse
import copy
import time
import shutil
import subprocess
from datetime import datetime,timezone
from PIL import Image,ImageDraw
from renderer import render

PREVIOUS=OUT
OUT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_002')

def resources():
    size=sum(p.stat().st_size for p in OUT.parent.rglob('*') if p.is_file())
    assert shutil.disk_usage(WORK).free>=2**30
    assert shutil.disk_usage(OUT).free>=10*2**30 and size<20*2**30
    return {'task_output_bytes':size,'cpu_affinity':sorted(os.sched_getaffinity(0)),'numeric_threads':1,'gpu':False}

def image_array(a):return np.uint8(np.rint(np.clip(a,0,1)*255))
def png(path,array):
    path.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(image_array(array)).save(path)

def contact(paths,labels,destination,columns=4,thumb=256):
    sheet=Image.new('RGB',(columns*thumb,((len(paths)+columns-1)//columns)*(thumb+25)),'white')
    draw=ImageDraw.Draw(sheet)
    for i,(path,label) in enumerate(zip(paths,labels)):
        x=(i%columns)*thumb;y=(i//columns)*(thumb+25)
        with Image.open(path) as im:
            im=im.convert('RGB');im.thumbnail((thumb,thumb),Image.Resampling.LANCZOS);sheet.paste(im,(x,y+25))
        draw.text((x+3,y+5),label,fill='black')
    destination.parent.mkdir(parents=True,exist_ok=True);sheet.save(destination)

def inputs():
    mesh,strokes,cfg=load_inputs() # Explicitly reads unit001 immutable inputs.
    cfg['renderer']['contour_visibility']='visible_centerline'
    edited=load_strokes(PREVIOUS/'inputs/angle_edited.npz')
    return mesh,strokes,edited,cfg

def check_lock():
    lock=json.loads((OUT/'SOURCE_LOCK.json').read_text())
    for path,digest in lock['files'].items():assert sha(path)==digest,path
    resources()

def save(folder,name,result,seconds):
    folder=OUT/folder;folder.mkdir(parents=True,exist_ok=True)
    png(folder/f'{name}.png',result['image'])
    png(folder/f'{name}_contours.png',1-result['contours'])
    np.savez_compressed(folder/f'{name}.npz',**{k:result[k] for k in ('image','hatch','contours','rings','depth','parts')})
    write_json(folder/f'{name}.json',dict(seconds=seconds,camera=result['camera'],diagnostics=result['diagnostics']))

def draw(mesh,strokes,cfg,az):
    t=time.perf_counter();result=render(mesh,strokes,cfg,azimuth=az,elevation=20,distance=4.5)
    return result,time.perf_counter()-t

def dev():
    mesh,strokes,edited,cfg=inputs()
    old=copy.deepcopy(cfg);old['renderer']['contour_visibility']='surface_fragments'
    for name,c in [('legacy',old),('candidate',cfg)]:
        result,seconds=draw(mesh,strokes,c,0);save('dev',name,result,seconds)
    contact([OUT/'dev'/f'{n}{suffix}.png' for n in ('legacy','candidate') for suffix in ('','_contours')],
            ['Legacy full | DEV 0','Legacy contours','Candidate full | DEV 0','Candidate contours'],OUT/'figures/dev_comparison.png')
    write_json(OUT/'DEV_RESULT.json',{'candidate_count':1,'azimuth':0,'note':'Single prescribed candidate; no parameter sweep or evaluation tuning.'})

def freeze():
    files=[WORK/'experiments/partwise_sketch_hatching/core.py',WORK/'experiments/partwise_sketch_hatching/core_walk_v2.py']
    files+=sorted((WORK/'experiments/partwise_sketch_hatching_v02').glob('*.py'))
    files += [OUT/'PROTOCOL.json',WORK/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json']
    files += [PREVIOUS/'inputs'/n for n in ('lamp_mesh.npz','mixed.npz','angle_edited.npz')]
    files += [PREVIOUS/n for n in ('STATUS.json','NEXT.json','SEAL.json','PROTOCOL.json','TEMPORAL_PROBES.json','VISUAL_REVIEW.json')]
    mapping={str(p):sha(p) for p in files}
    for p in files:
        if p.is_relative_to(WORK):dest=OUT/'source_snapshot'/p.relative_to(WORK)
        elif p.is_relative_to(PREVIOUS):dest=OUT/'input_snapshot'/p.relative_to(PREVIOUS)
        else:continue
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    write_json(OUT/'SOURCE_LOCK.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'files':mapping,
                                     'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()})

def stills():
    from validate_unit002 import contour_metrics
    mesh,strokes,edited,cfg=inputs();rows=[];paths=[];labels=[]
    old=copy.deepcopy(cfg);old['renderer']['contour_visibility']='surface_fragments'
    wide=copy.deepcopy(cfg);wide['widths_by_part']['1']=2.
    for az in (30,120,210,300):
        rendered={}
        for name,ss,cc in [('legacy',strokes,old),('base',strokes,cfg),('angle',edited,cfg),('width',strokes,wide)]:
            result,seconds=draw(mesh,ss,cc,az);save('stills',f'{name}_{az:03}',result,seconds);rendered[name]=result
            paths.append(OUT/'stills'/f'{name}_{az:03}.png');labels.append(f'{name} | az {az}')
        dep,parts=core.analytic_reference(cfg['asset'],rendered['base']['camera'])
        np.savez_compressed(OUT/'stills'/f'reference_{az:03}.npz',depth=dep,parts=parts)
        png(OUT/'stills'/f'parts_{az:03}.png',core.label_image(parts)/255.)
        rows.append({'azimuth':az,'legacy':contour_metrics(rendered['legacy']['contours'],parts),
                     'candidate':contour_metrics(rendered['base']['contours'],parts)})
        write_json(OUT/'STILLS_PARTIAL.json',rows);print(f'stills {az} complete',flush=True)
    write_json(OUT/'CONTOUR_STILLS.json',rows)
    contact(paths,labels,OUT/'figures/full_lamp_comparison.png')
    contact([OUT/'stills'/f'{n}_{az:03}_contours.png' for az in (30,120,210,300) for n in ('legacy','base')],
            [f'{n} contours | az {az}' for az in (30,120,210,300) for n in ('legacy','base')],OUT/'figures/contour_comparison.png',columns=2,thumb=512)
    parts=np.load(OUT/'stills/reference_030.npz')['parts']
    for p,name in ((1,'shade'),(2,'stem'),(3,'base')):
        y,x=np.where(parts==p);box=(max(0,int(x.min())-8),max(0,int(y.min())-8),min(512,int(x.max())+9),min(512,int(y.max())+9))
        for version in ('legacy','base'):
            with Image.open(OUT/'stills'/f'{version}_030.png') as im:im.crop(box).save(OUT/'figures'/f'{version}_crop_{name}.png')

def orbit():
    from validate_unit002 import contour_metrics
    mesh,strokes,edited,cfg=inputs();rows=[];folder=OUT/'frames/orbit';folder.mkdir(parents=True,exist_ok=True)
    old=copy.deepcopy(cfg);old['renderer']['contour_visibility']='surface_fragments'
    for i in range(24):
        az=15*i;result,seconds=draw(mesh,strokes,cfg,az);save('frames/orbit',f'{i:04}',result,seconds)
        legacy,_=draw(mesh,[],old,az)
        depth,parts=core.analytic_reference(cfg['asset'],result['camera'])
        np.savez_compressed(folder/f'reference_{i:04}.npz',depth=depth,parts=parts)
        rows.append(dict(frame=i,azimuth=az,elevation=20,distance=4.5,render_seconds=seconds,
                         candidate=contour_metrics(result['contours'],parts),legacy=contour_metrics(legacy['contours'],parts)))
        write_json(OUT/'ORBIT_PARTIAL.json',rows)
        print(f'orbit {i+1}/24',flush=True);resources()
    write_json(OUT/'TRAJECTORY_orbit.json',rows)
    contact([folder/f'{i:04}.png' for i in range(24)],[f'Orbit {i:02} | az {15*i}' for i in range(24)],OUT/'figures/orbit_all_frames.png',columns=6,thumb=192)
    contact([folder/f'{i:04}.png' for i in (0,12,23)],[f'Orbit {i:02} | az {15*i}' for i in (0,12,23)],OUT/'figures/orbit_first_middle_last.png',columns=3,thumb=512)
    dest=OUT/'videos/orbit.mkv';dest.parent.mkdir(exist_ok=True)
    cmd=[FFMPEG,'-v','error','-y','-threads','1','-filter_threads','1','-framerate','12','-i',str(folder/'%04d.png'),'-c:v','ffv1','-level','3','-threads','1','-pix_fmt','bgr0',str(dest)]
    result=subprocess.run(cmd,capture_output=True,timeout=90)
    (OUT/'runtime/orbit_encode.log').write_bytes(result.stderr)
    write_json(OUT/'VIDEO_orbit.json',{'encode_command':cmd,'encode_returncode':result.returncode,'frames':24,'fps':12,'size':[512,512]})
    assert result.returncode==0

def hidden_review():
    data=json.loads((PREVIOUS/'TEMPORAL_PROBES.json').read_text());records=[];paths=[];labels=[]
    folder=OUT/'hidden_review';folder.mkdir(exist_ok=True)
    for row in data['rows']:
        raw=row['samples']
        for j,(cls,present) in enumerate(zip(raw['class'],raw['profile_present'])):
            if cls!='hidden' or not present:continue
            source=PREVIOUS/'probes'/f'{row["frame"]:02}_{row["stroke_id"].replace(":","_")}.png'
            array=np.array(Image.open(source));uv=np.array(raw['uv']);x,y=uv[j]
            box=(int(np.floor(x))-12,int(np.floor(y))-12,int(np.floor(x))+13,int(np.floor(y))+13)
            crop=Image.fromarray(255-array).convert('RGB').crop(box).resize((250,250),Image.Resampling.NEAREST)
            draw=ImageDraw.Draw(crop);t=uv[min(j+1,len(uv)-1)]-uv[max(j-1,0)];n=np.array([-t[1],t[0]])/max(np.linalg.norm(t),1e-12)
            q=(uv[j]-box[:2]+.5)*10
            draw.line([tuple(q-2*n*10),tuple(q+2*n*10)],fill='red',width=2)
            draw.ellipse((q[0]-3,q[1]-3,q[0]+3,q[1]+3),outline='blue',width=2)
            name=f'hit_{len(records):02}.png';crop.save(folder/name);paths.append(folder/name)
            labels.append(f'hit {len(records):02} f{row["frame"]} sample{j}')
            records.append(dict(stroke_id=row['stroke_id'],part=row['part'],frame=row['frame'],sample=j,
                                uv=raw['uv'][j],analytic_depth_gap=raw['analytic_depth_gap'][j],
                                profile_peak=raw['profile_peak'][j],source=str(source),source_sha256=sha(source),crop=name))
    write_json(OUT/'HIDDEN_PROFILE_REVIEW.json',{'count':len(records),'records':records,
        'eligibility':'Unchanged unit001 hidden + profile-present classification; all hits retained.',
        'display':'Original isolated hatch, nearest-neighbor 10x; red +/-2px normal profile and blue sample center.',
        'limitation':'Profile support may be another segment; crops do not prove centerline leakage.'})
    contact(paths,labels,OUT/'figures/hidden_profiles_all.png',columns=4,thumb=256)
    print(json.dumps({'retained_hidden_profile_hits':len(records)}))

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['dev','freeze','stills','orbit','hidden']);a=p.parse_args()
    resources()
    if a.stage not in ('dev','freeze'):check_lock()
    {'dev':dev,'freeze':freeze,'stills':stills,'orbit':orbit,'hidden':hidden_review}[a.stage]()

if __name__=='__main__':main()
