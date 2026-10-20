"""Frozen P0 experiment runner. prepare binds assets; run executes one sealed evaluation."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import core

WORK=Path(__file__).resolve().parents[2]
DOC=WORK/'docs/partwise_sketch_hatching/round_001'
ROUND=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p0p1_v01/rounds/round_001')
PROTO=DOC/'PROTOCOL.json'
CFG=json.loads(PROTO.read_text())
START=time.monotonic()


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def write_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n');tmp.replace(path)


def status(stage,state='in_progress',verdict='UNMEASURED',extra=None):
    value={'stage':stage,'execution_state':state,'scientific_verdict':verdict,
           'tests':['TESTS_RED.json','TESTS_GREEN.json'],'artifacts':['assets/lamp_mesh.npz','metrics.json' if (ROUND/'metrics.json').exists() else 'pending'],
           'blockers':['CPU-only prevents RaDe-GS training','No lamp RGB+cameras found in bounded inventory','Independent temporal disappearance/flicker metric not implemented'],
           'updated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if extra: value.update(extra)
    write_json(ROUND/'STATUS.json',value)


def resource_check():
    r=CFG['resources']
    root=shutil.disk_usage('/').free;hdd=shutil.disk_usage('/mnt/hdd1').free
    used=sum(p.stat().st_size for p in ROUND.rglob('*') if p.is_file())
    runtime=sum(p.stat().st_size for p in (WORK/'.runtime_p0').rglob('*') if p.is_file())
    if root<r['root_free_min_bytes'] or hdd<r['hdd_free_min_bytes'] or used+runtime>r['output_cap_bytes']:
        raise RuntimeError('Resource floor/output cap violated')
    if time.monotonic()-START>570: raise RuntimeError('Invocation nearing ten-minute bound')
    return {'root_free_bytes':root,'hdd_free_bytes':hdd,'round_bytes':used,'isolated_dependency_bytes':runtime,'affinity':sorted(os.sched_getaffinity(0))}


def prepare():
    resource_check()
    (ROUND/'assets').mkdir(exist_ok=True)
    mesh=core.make_lamp(CFG['asset'])
    path=ROUND/'assets/lamp_mesh.npz'
    np.savez_compressed(path,vertices=mesh['vertices'],faces=mesh['faces'],parts=mesh['parts'])
    files=list((WORK/'experiments/partwise_sketch_hatching').glob('*.py'))+[PROTO,DOC/'COMPREHENSION.json',DOC/'UNDERSTANDING_ZH.md',WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md']
    lock={'protocol_commit':'da8c8387','implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
          'asset':{'path':str(path),'sha256':digest(path),'vertices':len(mesh['vertices']),'triangles':len(mesh['faces']),
                   'provenance':'authored procedural analytic GT; not reconstructed'},
          'files':{str(p.relative_to(WORK)):digest(p) for p in files},
          'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write_json(DOC/'ASSET_LOCK.json',lock)
    status('assets_prepared_awaiting_lock_commit')
    print(json.dumps(lock,indent=2))


def verify_lock():
    lock=json.loads((DOC/'ASSET_LOCK.json').read_text())
    for p,sha in lock['files'].items():
        if digest(WORK/p)!=sha: raise RuntimeError('Unfrozen source/config: '+p)
    if digest(lock['asset']['path'])!=lock['asset']['sha256']: raise RuntimeError('Asset hash mismatch')
    tracked=subprocess.run(['git','diff','HEAD','--','docs/partwise_sketch_hatching/round_001/ASSET_LOCK.json'],cwd=WORK,capture_output=True,text=True,check=True)
    if tracked.stdout: raise RuntimeError('Lock not committed')
    subprocess.run(['git','ls-files','--error-unmatch','docs/partwise_sketch_hatching/round_001/ASSET_LOCK.json'],cwd=WORK,capture_output=True,check=True)
    return lock


def image_save(path,array):
    a=np.clip(np.asarray(array)*255,0,255).astype(np.uint8) if np.asarray(array).dtype!=np.uint8 else array
    Image.fromarray(a).save(path)


def contact_sheet(entries,path,columns=4,width=256):
    rows=(len(entries)+columns-1)//columns
    sheet=Image.new('RGB',(columns*width,rows*(width+30)),(244,244,241));d=ImageDraw.Draw(sheet)
    for i,(name,file) in enumerate(entries):
        x=(i%columns)*width;y=(i//columns)*(width+30)
        im=Image.open(file).convert('RGB').resize((width,width),Image.Resampling.LANCZOS)
        sheet.paste(im,(x,y+30));d.text((x+8,y+8),name,fill=(30,30,30))
    sheet.save(path)


def stats(values):
    values=np.asarray(values)
    return {'count':int(values.size),'mean':float(values.mean()),'median':float(np.median(values)),'p95':float(np.percentile(values,95)),'max':float(values.max())}


def evaluate():
    lock=verify_lock();resources=resource_check()
    if (ROUND/'metrics.json').exists(): raise RuntimeError('Refusing to overwrite completed evaluation')
    for name in ('stills','strokes','frames','videos','references','figures','runtime'):
        (ROUND/name).mkdir(exist_ok=True)
    z=np.load(lock['asset']['path']);mesh=core.finalize_mesh(z['vertices'],z['faces'],z['parts'])
    status('generating_fixed_surface_strokes')
    generation={};styles={}
    for style in CFG['strokes']['styles']:
        t=time.perf_counter();styles[style]=core.generate_strokes(mesh,CFG,style);generation[style]=time.perf_counter()-t
        core.save_strokes(ROUND/'strokes'/f'{style}.npz',styles[style])
    t=time.perf_counter();edited=core.edit_part(mesh,styles['mixed'],CFG,1,35);edit_latency=time.perf_counter()-t
    core.save_strokes(ROUND/'strokes/mixed_shade_edit35.npz',edited)
    baseline=styles['mixed']
    deterministic=core.stroke_digest(baseline)==core.stroke_digest(core.generate_strokes(mesh,CFG,'mixed'))
    other_before=core.stroke_digest([s for s in baseline if s['part']!=1])
    other_after=core.stroke_digest([s for s in edited if s['part']!=1])
    attachment=[];residual=[];lengths=[]
    bbox=float(np.linalg.norm(np.ptp(mesh['vertices'],axis=0)))
    for s in baseline:
        p=core.anchor_points(mesh,s)
        attachment.extend(core.analytic_distance(p,CFG['asset']['profiles_ry'][str(s['part'])]))
        tri=mesh['tri'][s['faces']]
        residual.extend(abs(np.sum((p-tri[:,0])*mesh['normals'][s['faces']],axis=1)))
        lengths.append(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()))
    views=[];frame_times=[];entries=[];mixed_results={}
    status('rendering_frozen_test_stills')
    for style in CFG['strokes']['styles']:
        for ci,view in enumerate(CFG['splits']['test']):
            resource_check();a=view['azimuth_deg'];e=view['elevation_deg']
            t=time.perf_counter();result=core.render(mesh,styles[style],CFG,a,e);elapsed=time.perf_counter()-t
            frame_times.append(elapsed)
            filename=f'{style}_az{a:03d}.png';image_save(ROUND/'stills'/filename,result['image'])
            entries.append((f'{style.title()} | azimuth {a} deg',ROUND/'stills'/filename))
            if style=='mixed': mixed_results[a]=result
            print(f'still {filename} seconds={elapsed:.3f}',flush=True)
    for view in CFG['splits']['test']:
        resource_check();a=view['azimuth_deg'];result=mixed_results[a];c=result['camera']
        ref_depth,ref_parts=core.analytic_reference(CFG['asset'],c)
        np.savez_compressed(ROUND/'references'/f'analytic_az{a:03d}.npz',depth=ref_depth,parts=ref_parts)
        image_save(ROUND/'stills'/f'parts_az{a:03d}.png',core.label_image(ref_parts))
        entries.append((f'GT parts | azimuth {a} deg',ROUND/'stills'/f'parts_az{a:03d}.png'))
        t=time.perf_counter();after=core.render(mesh,edited,CFG,a,view['elevation_deg']);elapsed=time.perf_counter()-t
        frame_times.append(elapsed);image_save(ROUND/'stills'/f'edit_az{a:03d}.png',after['image'])
        image_save(ROUND/'stills'/f'edit_delta_az{a:03d}.png',1-np.clip(abs(after['image']-result['image'])*4,0,1))
        em=core.edit_metrics(result['image'],after['image'],ref_parts,1,CFG['metrics']['boundary_band_px'])
        interior=ndimage.distance_transform_edt(~core.contour_mask(ref_parts))>2
        valid=(ref_parts>0)&(result['parts']>0)&interior&np.isfinite(ref_depth)&np.isfinite(result['depth'])
        diff=abs(ref_depth[valid]-result['depth'][valid])
        points=np.concatenate([core.anchor_points(mesh,s) for s in baseline])
        uv,pz=core.project(points,c)
        visible=core.visible_points(points,c,ref_depth,CFG['renderer']['visibility_tolerance_world'])
        pix=np.rint(uv).astype(int)
        inside=(pix[:,0]>=0)&(pix[:,0]<512)&(pix[:,1]>=0)&(pix[:,1]<512)
        visible&=inside
        idx=np.flatnonzero(visible);visible[idx]&=ref_parts[pix[idx,1],pix[idx,0]]>0
        support=core.support_error(result['hatch']>.04,uv[visible])
        drift=core.support_error(np.roll(result['hatch']>.04,6,axis=1),uv[visible])
        leaked=after['image'].copy();leaked[460:480,20:40]=0
        leak=core.edit_metrics(result['image'],leaked,ref_parts,1,2)
        views.append({'azimuth_deg':a,'edit':em,'injected_leak':leak,
                      'analytic_depth_abs_error_world':stats(diff),'depth_valid_pixels':int(valid.sum()),
                      'analytic_foreground_pixels':int((ref_parts>0).sum()),
                      'part_disagreement_interior':float(np.mean(ref_parts[valid]!=result['parts'][valid])),
                      'render_support':support,'injected_6px_drift_support':drift,
                      'support_sample_coverage':float(visible.mean()),
                      'note':'Rendered support is ambiguous nearest-ink diagnostic, not temporal correspondence or flicker.'})
    contact_sheet(entries,ROUND/'figures/full_view_contact_sheet.png')
    contact_sheet([('Before: mixed',ROUND/'stills/mixed_az030.png'),('After: shade +35 deg',ROUND/'stills/edit_az030.png'),('4x absolute image change',ROUND/'stills/edit_delta_az030.png'),('Independent GT part mask',ROUND/'stills/parts_az030.png')],ROUND/'figures/edit_contact_sheet.png')
    # Save measured metrics before videos for recovery from interruption.
    raw={'protocol_id':CFG['protocol_id'],'source_lock_sha256':digest(DOC/'ASSET_LOCK.json'),
         'protocol_sha256':digest(PROTO),'claim_scope':CFG['claim_scope'],
         'mesh':lock['asset'],'seed':CFG['seed'],'resources_before':resources,
         'stroke_counts':{k:len(v) for k,v in styles.items()},'generation_seconds':generation,'edit_regeneration_seconds':edit_latency,
         'deterministic_regeneration':deterministic,'non_target_strokes_identical':other_before==other_after,
         'non_target_before_sha256':other_before,'non_target_after_sha256':other_after,
         'bbox_diagonal_world':bbox,'attachment_analytic_world':stats(attachment),
         'attachment_analytic_bbox_fraction':stats(np.array(attachment)/bbox),'attachment_self_proxy_world':stats(residual),
         'stroke_lengths_world':stats(lengths),'per_view':views,'frame_seconds_raw':frame_times,
         'unmeasured':CFG['unmeasured'],'manual_input':'Procedural GT part IDs, hand-set direction/style/profile rules; zero click-assisted annotation because not implemented.',
         'videos':{},'evaluation_complete':False}
    write_json(ROUND/'metrics_partial.json',raw)
    video_camera_records={}
    for kind in ('orbit','zoom','edit'):
        status('rendering_video_'+kind)
        params=CFG['videos'][kind];N=params['frames'];folder=ROUND/'frames'/kind;folder.mkdir(exist_ok=True)
        video_camera_records[kind]=[]
        for i in range(N):
            resource_check()
            if kind=='orbit': a=360*i/N;distance=4.5;strokes=baseline
            elif kind=='zoom': a=30;distance=4.0+1.6*(1-np.cos(2*np.pi*i/(N-1)))/2;strokes=baseline
            else: a=30;distance=4.5;strokes=baseline if i<12 else edited
            t=time.perf_counter();result=core.render(mesh,strokes,CFG,a,20,distance);elapsed=time.perf_counter()-t
            frame_times.append(elapsed)
            image_save(folder/f'{i:04d}.png',result['image'])
            video_camera_records[kind].append({'index':i,'azimuth_deg':a,'elevation_deg':20,'distance':distance,'seconds':elapsed,'stroke_digest':core.stroke_digest(strokes)})
            if i%6==0: print(f'{kind} {i+1}/{N} seconds={elapsed:.3f}',flush=True)
        contact_sheet([(f'{kind.title()} frame {i:02d}',folder/f'{i:04d}.png') for i in range(N)],ROUND/'figures'/f'{kind}_all_frames.png',columns=6,width=160)
        raw['videos'][kind]=encode_decode(kind,N)
        write_json(ROUND/'metrics_partial.json',raw)
    write_json(ROUND/'camera_trajectories.json',video_camera_records)
    gates={'determinism':deterministic,'part_isolation':other_before==other_after,
           'attachment_self_proxy':max(residual)<=CFG['go_no_go']['barycentric_max_residual'],
           'nonzero_target_edit':all(v['edit']['inside_delta']>10 for v in views),
           'far_non_target_leakage':all(v['edit']['far_other_parts_fraction']<=.02 for v in views),
           'analytic_depth':all(v['analytic_depth_abs_error_world']['p95']<=.01 for v in views),
           'injected_leakage_response':all(v['injected_leak']['outside_fraction']>v['edit']['outside_fraction'] for v in views),
           'injected_drift_response':all(v['injected_6px_drift_support']['mean_px']>v['render_support']['mean_px'] for v in views),
           'video_decode':all(v['decoded_frames']==CFG['videos'][k]['frames'] and v['distinct_decoded_frames']>=2 for k,v in raw['videos'].items())}
    raw.update({'evaluation_complete':True,'gates':gates,'engineering_go':all(gates.values()),
                'frame_seconds_raw':frame_times,'frame_seconds_summary':stats(frame_times),'resources_after':resource_check(),
                'total_invocation_seconds':time.monotonic()-START})
    write_json(ROUND/'metrics.json',raw)
    status('evaluation_complete_pending_visual_review','complete','P0_ENGINEERING_GO' if all(gates.values()) else 'P0_NO_GO',{'gates':gates})
    print(json.dumps({'gates':gates,'timing':raw['frame_seconds_summary'],'videos':raw['videos']},indent=2))


def encode_decode(kind,expected):
    sys.path.insert(0,str(WORK/'.runtime_p0'))
    import imageio_ffmpeg
    exe=imageio_ffmpeg.get_ffmpeg_exe()
    out=ROUND/'videos'/f'{kind}.mp4'
    cmd=[exe,'-hide_banner','-loglevel','error','-threads','2','-framerate',str(CFG['videos']['fps']),'-i',str(ROUND/'frames'/kind/'%04d.png'),'-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-crf','18','-y',str(out)]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    (ROUND/'runtime'/f'{kind}_encode.stderr').write_text(result.stderr)
    if result.returncode: raise RuntimeError('ffmpeg encode failed')
    cmd=[exe,'-hide_banner','-loglevel','error','-threads','2','-i',str(out),'-f','rawvideo','-pix_fmt','rgb24','-threads','2','pipe:1']
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0;hashes=[];changes=[];previous=None
    while True:
        chunk=p.stdout.read(512*512*3)
        if not chunk: break
        if len(chunk)!=512*512*3: raise RuntimeError('Partial decoded frame')
        hashes.append(hashlib.sha256(chunk).hexdigest())
        im=np.frombuffer(chunk,np.uint8)
        if previous is not None: changes.append(float(np.mean(abs(im.astype(float)-previous))))
        previous=im.astype(float);count+=1
    stderr=p.stderr.read().decode();rc=p.wait(timeout=30)
    (ROUND/'runtime'/f'{kind}_decode.stderr').write_text(stderr)
    if rc or count!=expected or len(set(hashes))<2: raise RuntimeError('Full video decode assertion failed')
    return {'path':str(out),'encode_returncode':result.returncode,'decode_returncode':rc,'decoded_frames':count,
            'distinct_decoded_frames':len(set(hashes)),'decoded_frame_sha256':hashes,'consecutive_mean_abs_rgb_change':changes,
            'ffmpeg_path':exe,'ffmpeg_sha256':digest(exe),'fps':CFG['videos']['fps'],'resolution':[512,512],
            'note':'Full decode/nonidentity checks do not establish absence of flicker.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args()
    try:
        prepare() if args.action=='prepare' else evaluate()
    except Exception as exc:
        status('interrupted_or_failed','engineering_invalid','INCOMPLETE',{'error':f'{type(exc).__name__}: {exc}'})
        raise
