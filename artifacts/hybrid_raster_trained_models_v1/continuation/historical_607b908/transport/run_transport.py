"""Frozen NPR transport. No dataset image loading and no normalization fitting."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
sys.dont_write_bytecode=True
from adapters import (ROOT,ART,OUT,OLD,F,C,SCENES,PARAMETER_HASH,LOCK_SHA,
    inherited,frame_specs,frozen_json,hash_file,canonical_hash,atomic_json,valid_seal,seal_frame)
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from src import hybrid_raster_native as native
from src.hybrid_raster_evidence import compute_evidence,validate_raw
from src.hybrid_raster_io import white_ink,overlay_ink,panel,save_contact_sheet,encode_video,validate_video

# Only native logging destination changes. Its original GPU guard remains unchanged.
# In particular NATIVE stays the old isolated read-only patched/unpatched builds.
native.STAGE=OUT
LABELS=['RGB: common native SH0','A: RGB/depth/alpha','B: OUR dense six channels',
        'C: automatic complement','AUTHOR: independent Eq1-5, NOT official']
ARMS=('A','B','C','author_gain')


def status(phase,**kwargs):
    value={'phase':phase,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**kwargs}
    atomic_json(ART/'STATUS.json',value,replace=True)
    central=ART.parent/'STATUS.json'
    old=json.loads(central.read_text()) if central.exists() else {}
    old.update(phase='NPR_'+phase,transport=value,updated_utc=value['utc'])
    atomic_json(central,old,replace=True)
    print(json.dumps(value,ensure_ascii=False),flush=True)


def read_npz(path):
    with np.load(path,allow_pickle=False) as data:return {k:data[k].copy() for k in data.files}


def require_release(scene):
    """No GPU until exact checkpoint/cameras are contained in pushed Git history."""
    manifest_path=ART/scene/'CAMERAS.json'
    manifest=json.loads(manifest_path.read_text())
    receipt=json.loads((ART/'RENDER_FREEZE.json').read_text())
    commit=receipt['commit']
    if receipt['camera_manifest_sha256'][scene]!=hash_file(manifest_path):raise RuntimeError('Camera freeze receipt differs')
    rel=manifest_path.relative_to(ROOT).as_posix()
    frozen=subprocess.check_output(['git','show',commit+':'+rel],cwd=ROOT)
    if hashlib.sha256(frozen).hexdigest()!=hash_file(manifest_path):raise RuntimeError('Exact cameras not committed')
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/hybrid-raster-trained-models-v1'],cwd=ROOT,text=True).split()[0]
    subprocess.run(['git','merge-base','--is-ancestor',commit,remote],cwd=ROOT,check=True)
    if hash_file(manifest['checkpoint']['path'])!=manifest['checkpoint']['sha256']:raise RuntimeError('Frozen checkpoint changed')
    training_lock=manifest['training_checkpoint_lock']
    if hash_file(training_lock['path'])!=training_lock['sha256']:raise RuntimeError('Training checkpoint lock changed')
    if manifest['parameter_hash']!=PARAMETER_HASH:raise RuntimeError('Scientific parameters changed')
    return manifest


def calibration_context(manifest,heritage):
    return {'camera_manifest_sha256':hash_file(ART/manifest['scene']/'CAMERAS.json'),
            'checkpoint_sha256':manifest['checkpoint']['sha256'],'native_build':heritage['native_build'],
            'calibration_indices':F,'tolerances':{'general_max_abs':3e-6,'depth_or_max_abs':1e-5,'depth_and_max_rel':3e-6}}


def calibrate(manifest,g,heritage):
    scene=manifest['scene'];dest=OUT/'calibration'/scene;path=dest/'CALIBRATION.json'
    context=calibration_context(manifest,heritage)
    if path.exists():
        prior=json.loads(path.read_text())
        if prior['status']!='PASS' or prior['context']!=context:raise RuntimeError('Existing calibration not resumable; preserve and investigate')
        for frame in prior['frames']:
            if hash_file(frame['path'])!=frame['sha256']:raise RuntimeError('Calibration native cache changed')
            if hash_file(frame['unpatched_path'])!=frame['unpatched_sha256']:raise RuntimeError('Unpatched calibration cache changed')
        return prior
    dest.mkdir(parents=True,exist_ok=True)
    report={'status':'RUNNING','scene':scene,'context':context,'frames':[]}
    atomic_json(dest/'STATUS.json',report,replace=True)
    try:
        for spec in frame_specs(manifest)[:8]:
            status('CALIBRATING',scene=scene,key=spec['key'],completed=len(report['frames']),expected=8)
            a=native.render_native(g,spec['camera'],patched=True)
            b=native.render_native(g,spec['camera'],patched=False)
            result=native.compare_calibration(a,b)
            row={'scene':scene,'index':spec['index'],'camera':spec['camera'],'camera_hash':canonical_hash(spec['camera']),
                 'checkpoint_sha256':manifest['checkpoint']['sha256'],'calibration':result}
            path_frame=dest/(spec['key']+'.npz');temp=path_frame.with_suffix('.npz.partial')
            if path_frame.exists():raise RuntimeError('Unsealed calibration cache exists; preserve instead of overwrite')
            with temp.open('xb') as stream:np.savez_compressed(stream,**a)
            os.rename(temp,path_frame)
            path_unpatched=dest/(spec['key']+'_unpatched.npz');temp_unpatched=path_unpatched.with_suffix('.npz.partial')
            if path_unpatched.exists():raise RuntimeError('Unsealed unpatched calibration cache exists')
            with temp_unpatched.open('xb') as stream:np.savez_compressed(stream,**b)
            os.rename(temp_unpatched,path_unpatched)
            row.update(path=str(path_frame),sha256=hash_file(path_frame),gaussian_count=len(g['mu']),
                       unpatched_path=str(path_unpatched),unpatched_sha256=hash_file(path_unpatched))
            report['frames'].append(row);atomic_json(dest/'STATUS.json',report,replace=True)
            if result['status']!='PASS':raise RuntimeError('Patched/unpatched calibration tolerance failed')
            del a,b
        report['status']='PASS';frozen_json(dest/'CALIBRATION.json',report)
        frozen_json(ART/scene/'CALIBRATION.json',report)
    except Exception as exc:
        report['status']='ENGINEERING_INVALID';report['error']=repr(exc)
        atomic_json(dest/'STATUS.json',report,replace=True)
        atomic_json(ART/scene/'CALIBRATION_FAILURE.json',report,replace=True)
        raise
    return report


def context_for(spec,manifest,heritage,calibration):
    return {'scene':spec['scene'],'key':spec['key'],'camera':spec['camera'],'camera_hash':canonical_hash(spec['camera']),
            'checkpoint_sha256':manifest['checkpoint']['sha256'],'camera_manifest_sha256':hash_file(ART/spec['scene']/'CAMERAS.json'),
            'renderer_source_sha256':heritage['sources']['src/hybrid_raster_native.py'],
            'calibration_sha256':hash_file(OUT/'calibration'/spec['scene']/'CALIBRATION.json'),
            'render_recipe':{'SH':0,'topk':4,'background':'white','kernel_size':0},
            'scientific_parameter_hash':PARAMETER_HASH,'inherited_lock_sha256':LOCK_SHA,
            'source_hashes':heritage['sources'],'adapter_source_hashes':{
                'adapters.py':hash_file(ART/'adapters.py'),'run_transport.py':hash_file(__file__)}}


def get_raw(spec,manifest,g,heritage,calibration):
    context=context_for(spec,manifest,heritage,calibration);dest=OUT/'raw'/spec['scene']/spec['key']
    if valid_seal(dest,context):return read_npz(dest/'native.npz'),dest/'native.npz',context
    if shutil.disk_usage(OUT).free<1024**3:raise RuntimeError('Less than 1GiB output storage remains')
    stage=OUT/'staging'/f"raw_{spec['scene']}_{spec['key']}_{os.getpid()}";stage.mkdir(parents=True,exist_ok=False)
    cache=[r for r in calibration['frames'] if spec['split']=='F' and r['index']==spec['index'] and r['camera']==spec['camera']]
    if cache:
        row=cache[0]
        if hash_file(row['path'])!=row['sha256']:raise RuntimeError('Calibrated raw cache changed')
        raw=read_npz(row['path']);os.link(row['path'],stage/'native.npz')
    else:
        raw=native.render_native(g,spec['camera'],patched=True)
        np.savez_compressed(stage/'native.npz',**raw)
    validate_raw(raw,gaussian_count=len(g['mu']))
    atomic_json(stage/'camera.json',context);atomic_json(stage/'checkpoint_qualification.json',g['_metadata'])
    seal_frame(stage,dest,context)
    return raw,dest/'native.npz',context


def response_image(x):
    import cv2
    x=np.uint8(np.round(np.clip(x,0,1)*255))
    return cv2.cvtColor(cv2.applyColorMap(x,cv2.COLORMAP_MAGMA),cv2.COLOR_BGR2RGB)


def make_frame(spec,manifest,g,lock,heritage,calibration):
    context=context_for(spec,manifest,heritage,calibration);dest=OUT/'frames'/spec['scene']/spec['key']
    if valid_seal(dest,context):return {'key':spec['key'],'seal_sha256':hash_file(dest/'SEAL.json'),'context':context}
    raw,rawpath,context=get_raw(spec,manifest,g,heritage,calibration)
    result=compute_evidence(raw,lock['normalization'])
    stage=OUT/'staging'/f"frame_{spec['scene']}_{spec['key']}_{os.getpid()}";stage.mkdir(parents=True,exist_ok=False)
    os.link(rawpath,stage/'native.npz')
    for name,data in [('typed',result['fields']),('responses',result['arrays']),('provenance',result['provenance'])]:np.savez_compressed(stage/(name+'.npz'),**data)
    atomic_json(stage/'camera.json',context)
    diagnostics={**result['diagnostics'],'scene':spec['scene'],'split':spec['split'],'frame':spec['key'],
                 'native_sha256':hash_file(rawpath),'camera_hash':context['camera_hash'],'parameter_hash':PARAMETER_HASH,
                 'in_sample_disclosure':'C belongs to GS TRAIN and only held out from NPR parameter fitting; inherited recipe never refitted'}
    atomic_json(stage/'diagnostics.json',diagnostics)
    rgb=np.uint8(np.round(np.clip(raw['rgb'],0,1)*255));Image.fromarray(rgb).save(stage/'rgb.png');arrays=result['arrays']
    for arm in ('A','B','C','A_matched','B_matched','C_matched','author_absolute','author_gain'):
        Image.fromarray(white_ink(arrays[arm])).save(stage/f'{arm}_ink.png')
        Image.fromarray(overlay_ink(rgb,arrays[arm])).save(stage/f'{arm}_overlay.png')
    panel([rgb]+[white_ink(arrays[k]) for k in ARMS],LABELS,columns=5).save(stage/'line_panel.png')
    panel([rgb]+[overlay_ink(rgb,arrays[k]) for k in ARMS],LABELS,columns=5).save(stage/'overlay_panel.png')
    panel([rgb]+[white_ink(arrays[k+'_matched']) for k in ('A','B','C')]+[white_ink(arrays['author_gain'])],
          ['RGB', 'A: matched ink mass','B: matched ink mass','C: matched ink mass','AUTHOR fixed gain (not mass-matched)'],columns=5).save(stage/'matched_panel.png')
    fieldkeys=['delta_D','delta_A','delta_N','delta_C','delta_G','visibility_raw','E_D','E_A','E_N','E_C','E_G','E_V','q','S_L','E_T']
    images=[response_image(result['fields'][key]/max(float(lock['normalization']['scales'].get(key,1.)),1e-12)) for key in fieldkeys]
    panel(images,fieldkeys,columns=5).save(stage/'response_panel.png')
    seal_frame(stage,dest,context)
    return {'key':spec['key'],'seal_sha256':hash_file(dest/'SEAL.json'),'context':context}


def run_scene(scene):
    lock,heritage=inherited();manifest=require_release(scene)
    g=native.load_checkpoint(manifest['checkpoint']['path'],manifest['checkpoint']['sha256'])
    calibration=calibrate(manifest,g,heritage)
    records=[]
    for spec in frame_specs(manifest):
        status('RENDERING',scene=scene,key=spec['key'],completed=len(records),expected=49)
        records.append(make_frame(spec,manifest,g,lock,heritage,calibration))
    if len(records)!=49 or len({r['key'] for r in records})!=49:raise RuntimeError('Frame count mismatch')
    summary={'scene':scene,'status':'ENGINEERING_VALID_SCIENTIFIC_REVIEW_PENDING','expected_frames':49,'actual_frames':len(records),
             'parameter_hash':PARAMETER_HASH,'camera_manifest_sha256':hash_file(ART/scene/'CAMERAS.json'),
             'checkpoint':manifest['checkpoint'],'calibration':{'path':str(OUT/'calibration'/scene/'CALIBRATION.json'),'sha256':hash_file(OUT/'calibration'/scene/'CALIBRATION.json')},
             'records':records,'missing':[]}
    frozen_json(ART/scene/'FRAMES.json',summary);status('SCENE_COMPLETE',scene=scene,frames=49)


def telegram_frames(frames,kind):
    labels={'comparison':['RGB SH0','A RGB/depth/alpha','B OUR dense','C complement','AUTHOR independent\nNOT official'],
            'overlay':['RGB SH0','A overlay','B OUR overlay','C overlay','AUTHOR independent\nNOT official'],
            'matched':['RGB SH0','A matched mass','B matched mass','C matched mass','AUTHOR fixed gain\nNOT mass-matched']}[kind]
    suffix={'comparison':'line','overlay':'overlay','matched':'matched'}[kind]
    try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
    except OSError:font=ImageFont.load_default()
    for i in range(33):
        # Remove old32-pixel label header, resize entire 4000x800 pixel strip, redraw labels at readable resolution.
        with Image.open(frames/f'arc0_{i:03d}'/f'{suffix}_panel.png') as im:
            pixels=im.convert('RGB').crop((0,32,4000,832)).resize((1600,320),Image.Resampling.LANCZOS)
        sheet=Image.new('RGB',(1600,368),'white');sheet.paste(pixels,(0,48));draw=ImageDraw.Draw(sheet)
        for j,label in enumerate(labels):draw.multiline_text((j*320+6,5),label,font=font,fill='black')
        yield np.asarray(sheet)


def encode_telegram(frames,path):
    import imageio_ffmpeg
    exe=imageio_ffmpeg.get_ffmpeg_exe();tmp=path.with_suffix('.partial.mp4')
    cmd=[exe,'-hide_banner','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1600x368','-r','12','-i','-',
         '-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart','-frames:v','33',str(tmp)]
    if path.exists() or tmp.exists():raise FileExistsError(path)
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        count=0
        for frame in frames:process.stdin.write(frame.tobytes());count+=1
        process.stdin.close();stderr=process.stderr.read();process.stderr.close();code=process.wait()
        if code or count!=33:raise RuntimeError(f'ffmpeg failed {code}, count {count}: '+stderr.decode(errors='replace'))
    except BaseException:
        if process.poll() is None:
            process.stdin.close();process.wait()
        raise
    record=validate_video(tmp,expected_frames=33,expected_size=(1600,368),require_distinct=True)
    # moov must precede mdat for progressive-download faststart. H264/pixel format verified with ffmpeg decode diagnostics.
    data=tmp.read_bytes();moov=data.find(b'moov');mdat=data.find(b'mdat')
    if min(moov,mdat)<0 or moov>mdat:raise RuntimeError('faststart atoms invalid')
    probe=subprocess.run([exe,'-hide_banner','-i',str(tmp),'-f','null','-'],capture_output=True,text=True)
    if probe.returncode or 'h264' not in probe.stderr or 'yuv420p' not in probe.stderr:raise RuntimeError('Telegram codec/pixel format verification failed')
    os.rename(tmp,path)
    return {**record,'path':str(path),'sha256':hash_file(path),'codec':'h264','pixel_format':'yuv420p','faststart':True,'fps':12,'input_frames':33,
            'encoder_path':exe,'encoder_sha256':hash_file(exe),'command':cmd,'decode_stderr':probe.stderr}


def media(scene):
    lock,heritage=inherited();manifest=require_release(scene);records=json.loads((ART/scene/'FRAMES.json').read_text())
    frames=OUT/'frames'/scene
    for record in records['records']:
        if not valid_seal(frames/record['key'],record['context']) or hash_file(frames/record['key']/'SEAL.json')!=record['seal_sha256']:raise RuntimeError('Frame seal changed')
    context={'scene':scene,'camera_manifest_sha256':hash_file(ART/scene/'CAMERAS.json'),'frames_manifest_sha256':hash_file(ART/scene/'FRAMES.json'),'parameter_hash':PARAMETER_HASH}
    dest=OUT/'media'/scene
    if valid_seal(dest,context):return json.loads((dest/'MANIFEST.json').read_text())
    stage=OUT/'staging'/f'media_{scene}_{os.getpid()}';stage.mkdir(parents=True,exist_ok=False)
    result={'scene':scene,'parameter_hash':PARAMETER_HASH,'videos':{},'contacts':{},'first_mid_last':{}}
    specs=frame_specs(manifest)
    for split in ('F','C','arc0'):
        selected=[x for x in specs if x['split']==split]
        for arm in ('rgb','A','B','C','author_gain'):
            suffix='rgb.png' if arm=='rgb' else f'{arm}_ink.png';name=f'{split}_{arm}_contact.png'
            record=save_contact_sheet([frames/x['key']/suffix for x in selected],stage/name,labels=[x['key'] for x in selected],columns=3 if split=='arc0' else 4)
            result['contacts'][name]={**record,'path':str(dest/name)}
    for name,file in [('comparison','line_panel.png'),('overlay','overlay_panel.png'),('matched','matched_panel.png')]:
        target=stage/f'arc0_{name}.mp4'
        def images():
            for i in range(33):
                with Image.open(frames/f'arc0_{i:03d}'/file) as im:yield np.asarray(im.convert('RGB'))
        record=encode_video(images(),target,fps=12,expected_frames=33)
        result['videos'][name]={**record,'path':str(dest/target.name)}
        target=stage/f'arc0_{name}_telegram1600.mp4';record=encode_telegram(telegram_frames(frames,name),target)
        result['videos'][name+'_telegram1600']={**record,'path':str(dest/target.name)}
    for i in (0,16,32):
        for kind in ('line','overlay','matched'):
            name=f'arc0_{i:03d}_{kind}.png';os.link(frames/f'arc0_{i:03d}'/f'{kind}_panel.png',stage/name)
            result['first_mid_last'][name]={'path':str(dest/name),'sha256':hash_file(stage/name)}
    if (len(result['videos']),len(result['contacts']),len(result['first_mid_last']))!=(6,15,9):
        raise RuntimeError('Media artifact count mismatch')
    atomic_json(stage/'MANIFEST.json',result);seal_frame(stage,dest,context)
    frozen_json(ART/scene/'MEDIA.json',result);status('MEDIA_COMPLETE',scene=scene,videos=6,contacts=15)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True,choices=['render','media']);parser.add_argument('--scene',required=True,choices=SCENES)
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True);(OUT/'staging').mkdir(exist_ok=True)
    os.environ.setdefault('TMPDIR',str(OUT/'tmp'));(OUT/'tmp').mkdir(exist_ok=True)
    start=time.monotonic();ledgerpath=OUT/'RUNTIME.json';ledger=json.loads(ledgerpath.read_text()) if ledgerpath.exists() else []
    gpu=args.phase=='render';entry={'scene':args.scene,'phase':args.phase,'pid':os.getpid(),'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gpu_context_phase':gpu,'status':'RUNNING'}
    if gpu:
        used=sum(x.get('elapsed_seconds',0) for x in ledger if x.get('gpu_context_phase'));remaining=4*3600-used
        if remaining<=0:raise RuntimeError('TRANSPORT_GPU_WALL_BUDGET_EXHAUSTED')
        def expired(sig,frame):raise RuntimeError('TRANSPORT_GPU_WALL_BUDGET_EXHAUSTED')
        signal.signal(signal.SIGALRM,expired);signal.alarm(max(1,int(remaining)))
    ledger.append(entry);atomic_json(ledgerpath,ledger,replace=True)
    try:
        if gpu:run_scene(args.scene)
        else:media(args.scene)
        entry['status']='COMPLETE'
    except BaseException as exc:
        entry['status']='FAILED';entry['error']=repr(exc);entry['traceback']=traceback.format_exc()
        status('ENGINEERING_INVALID_OR_UNDETERMINED',scene=args.scene,failed_phase=args.phase,error=repr(exc))
        raise
    finally:
        if gpu:signal.alarm(0)
        entry['elapsed_seconds']=time.monotonic()-start;atomic_json(ledgerpath,ledger,replace=True)

if __name__=='__main__':main()
