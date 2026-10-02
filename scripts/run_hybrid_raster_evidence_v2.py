#!/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
"""Execute the frozen same-source native raster evidence experiment, stage 1 only."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ.setdefault('TMPDIR', str(ROOT/'out/hybrid_raster_evidence_v2/tmp'))
import numpy as np
from PIL import Image
from src.hybrid_raster_stage import read_inputs, frame_specs, require_evaluation_lock, SCENES
from src.hybrid_raster_io import (hash_file, canonical_hash, atomic_json, seal_frame,
    valid_seal, white_ink, overlay_ink, panel, save_contact_sheet, encode_video)
from src.hybrid_raster_evidence import raw_fields, fit_normalization, compute_evidence, validate_raw

OUT = ROOT/'out/hybrid_raster_evidence_v2'
ART = ROOT/'artifacts/hybrid_raster_evidence_v2'
PROTOCOL = ART/'PROTOCOL.md'
SOURCES = ('src/hybrid_raster_native.py', 'src/hybrid_raster_evidence.py',
           'src/hao_mukai_source_2026.py', 'src/hybrid_raster_stage.py',
           'src/hybrid_raster_io.py', 'scripts/run_hybrid_raster_evidence_v2.py')


def status(phase, **kwargs):
    previous = {}
    if (ART/'STATUS.json').exists():
        previous = json.loads((ART/'STATUS.json').read_text())
    if phase != 'ENGINEERING_INVALID_OR_UNDETERMINED':
        for key in ('blocker','failed_phase','elapsed_seconds','restart'):
            previous.pop(key,None)
    previous.update(stage='direction_1_same_source_raster_evidence', phase=phase,
                    updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **kwargs)
    atomic_json(ART/'STATUS.json', previous, replace=True)
    print(json.dumps(previous, ensure_ascii=False), flush=True)


def read_npz(path):
    with np.load(path, allow_pickle=False) as data:
        return {key:data[key].copy() for key in data.files}


def current_sources():
    return {p:hash_file(ROOT/p) for p in SOURCES}


def calibration_gate():
    from src.hybrid_raster_native import source_hashes
    path = OUT/'calibration/CALIBRATION.json'
    if not path.is_file():
        raise RuntimeError('ENGINEERING_INVALID: native calibration report missing')
    value = json.loads(path.read_text())
    if value.get('status') != 'PASS':
        raise RuntimeError('ENGINEERING_INVALID: native calibration has not passed')
    sources=source_hashes()
    if value.get('source') != sources:
        raise RuntimeError('ENGINEERING_INVALID: current native build differs from calibrated sources')
    if value.get('inputs_sha256') != hash_file(ROOT/'artifacts/direct_curve_global_fit_probe/INPUTS.json'):
        raise RuntimeError('ENGINEERING_INVALID: calibration input manifest differs')
    for variant in sources['variants'].values():
        if hash_file(variant['path']) != variant['sha256']:
            raise RuntimeError('ENGINEERING_INVALID: calibrated native binary changed')
    return value, hash_file(path)


def base_config():
    from src.hybrid_raster_native import source_hashes
    calibration, digest = calibration_gate()
    return {'protocol_sha256':hash_file(PROTOCOL), 'input_manifest_sha256':hash_file(
        ROOT/'artifacts/direct_curve_global_fit_probe/INPUTS.json'),
        'calibration_sha256':digest, 'sources':current_sources(), 'native_build':source_hashes(),
        'renderer':{'colors':'SH0', 'background':'white', 'filter_3D':False,
                    'kernel_size':0, 'topk':4, 'resolution':'native', 'same_traversal':True},
        'scope':'2D-only; no old I curves; no routing; no temporal identity propagation'}


def raw_context(spec, checkpoint):
    return {'scene':spec['scene'], 'key':spec['key'], 'camera':spec['camera'],
            'camera_hash':canonical_hash(spec['camera']),
            'checkpoint_sha256':checkpoint['sha256'],
            'renderer_source_sha256':hash_file(ROOT/'src/hybrid_raster_native.py'),
            'calibration_sha256':hash_file(OUT/'calibration/CALIBRATION.json'),
            'render_recipe':{'SH':0,'topk':4,'background':'white','kernel_size':0}}


def load_scene(scene, inputs):
    from src.hybrid_raster_native import load_checkpoint
    checkpoint = inputs['scenes'][scene]['checkpoint']
    if hash_file(checkpoint['path']) != checkpoint['sha256']:
        raise RuntimeError(f'Frozen checkpoint changed: {scene}')
    return load_checkpoint(checkpoint['path'])


def get_raw(spec, checkpoint, g):
    from src.hybrid_raster_native import render_native
    from types import SimpleNamespace
    context = raw_context(spec, checkpoint)
    final = OUT/'raw'/spec['scene']/spec['key']
    if valid_seal(final, context):
        return read_npz(final/'native.npz'), final/'native.npz'
    if shutil.disk_usage(OUT).free < 1024**3:
        raise RuntimeError('ENGINEERING_UNDETERMINED: less than 1 GiB disk space remains')
    camera = spec['camera']
    mat = np.asarray(camera['w2c'], dtype=np.float64)
    cam = SimpleNamespace(K=np.asarray(camera['native_K']), w2c=mat,
                          H=camera['native_height'], W=camera['native_width'],
                          center=np.linalg.inv(mat)[:3,3], name=spec['key'])
    calibrated,_=calibration_gate()
    cache=[r for r in calibrated['frames'] if spec['split']=='F' and r['scene']==spec['scene']
           and r['index']==spec['index'] and r['exact_input_camera']==spec['camera']
           and r['checkpoint_sha256']==checkpoint['sha256']]
    if cache:
        cached=cache[0]
        if hash_file(cached['path']) != cached['sha256']:
            raise RuntimeError('Calibrated same-camera native cache changed')
        raw=read_npz(cached['path'])
    else:
        raw = render_native(g, cam, patched=True)
    validate_raw(raw, gaussian_count=len(g['mu']))
    stage = OUT/'staging'/f"raw_{spec['scene']}_{spec['key']}_{os.getpid()}"
    stage.mkdir(parents=True, exist_ok=False)
    if cache:os.link(cache[0]['path'],stage/'native.npz')
    else:np.savez_compressed(stage/'native.npz', **raw)
    atomic_json(stage/'camera.json', context)
    atomic_json(stage/'checkpoint_qualification.json',g['_metadata'])
    seal_frame(stage, final, context)
    return raw, final/'native.npz'


def response_image(x):
    import cv2
    x = np.uint8(np.round(np.clip(x,0,1)*255))
    return cv2.cvtColor(cv2.applyColorMap(x, cv2.COLORMAP_MAGMA), cv2.COLOR_BGR2RGB)


def frame_context(spec, checkpoint, config, normalization):
    return {**raw_context(spec, checkpoint), 'parameter_hash':canonical_hash(
        {'config':config, 'normalization':normalization}), 'source_hashes':config['sources']}


def make_frame(spec, checkpoint, g, config, normalization, group='frames'):
    context = frame_context(spec, checkpoint, config, normalization)
    final = OUT/group/spec['scene']/spec['key']
    if valid_seal(final, context):
        return {'scene':spec['scene'], 'key':spec['key'], 'context':context,
                'seal_sha256':hash_file(final/'SEAL.json')}
    raw, raw_path = get_raw(spec, checkpoint, g)
    result = compute_evidence(raw, normalization)
    stage = OUT/'staging'/f"frame_{spec['scene']}_{spec['key']}_{os.getpid()}"
    stage.mkdir(parents=True, exist_ok=False)
    os.link(raw_path, stage/'native.npz')
    np.savez_compressed(stage/'typed.npz', **result['fields'])
    np.savez_compressed(stage/'responses.npz', **result['arrays'])
    np.savez_compressed(stage/'provenance.npz', **result['provenance'])
    atomic_json(stage/'camera.json', context)
    diagnostics = {**result['diagnostics'], 'scene':spec['scene'], 'split':spec['split'],
                   'frame':spec['key'], 'native_sha256':hash_file(raw_path),
                   'camera_hash':context['camera_hash'], 'parameter_hash':context['parameter_hash']}
    atomic_json(stage/'diagnostics.json', diagnostics)
    rgb = np.uint8(np.round(np.clip(raw['rgb'],0,1)*255))
    Image.fromarray(rgb).save(stage/'rgb.png')
    arrays = result['arrays']
    for name in ('A','B','C','A_matched','B_matched','C_matched','author_absolute','author_gain'):
        Image.fromarray(white_ink(arrays[name])).save(stage/f'{name}_ink.png')
        Image.fromarray(overlay_ink(rgb, arrays[name])).save(stage/f'{name}_overlay.png')
    labels = ['Common native SH0 RGB','A RGB+depth+alpha', 'B OUR dense raster',
              'C automatic complement','Author S_L / fixed F P99']
    images = [rgb] + [white_ink(arrays[k]) for k in ('A','B','C','author_gain')]
    panel(images, labels, columns=5).save(stage/'line_panel.png')
    panel([overlay_ink(rgb,arrays[k]) for k in ('A','B','C')], labels[1:4], columns=3).save(stage/'overlay_panel.png')
    panel([white_ink(arrays[k+'_matched']) for k in ('A','B','C')],
          ['A opacity-mass matched','B opacity-mass matched','C opacity-mass matched'], columns=3).save(stage/'matched_panel.png')
    field_keys = ['delta_D','delta_A','delta_N','delta_C','delta_G','visibility_raw',
                  'E_D','E_A','E_N','E_C','E_G','E_V','q','S_L','E_T']
    fields = result['fields']
    scales = normalization['scales']
    ims=[]
    for key in field_keys:
        scale = scales.get(key,1.)
        ims.append(response_image(fields[key]/max(float(scale),1e-12)))
    panel(ims,field_keys,columns=5).save(stage/'response_panel.png')
    seal_frame(stage, final, context)
    print(f"SEALED {spec['scene']} {spec['key']}", flush=True)
    return {'scene':spec['scene'], 'key':spec['key'], 'context':context,
            'seal_sha256':hash_file(final/'SEAL.json')}


def frozen_json(path, value):
    if path.exists():
        if canonical_hash(json.loads(path.read_text())) != canonical_hash(value):
            raise RuntimeError(f'Frozen file changed: {path}')
    else:
        atomic_json(path,value)


def pilot():
    inputs=read_inputs(); config=base_config(); fields=[]
    for scene in ('lego','chair'):
        g=load_scene(scene,inputs)
        for spec in frame_specs(inputs,scene,'F'):
            if spec['index'] not in (1,41):continue
            raw,_=get_raw(spec,inputs['scenes'][scene]['checkpoint'],g)
            fields.append(raw_fields(raw))
    normalization=fit_normalization(fields)
    records=[]
    for scene in ('lego','chair'):
        g=load_scene(scene,inputs)
        for spec in frame_specs(inputs,scene,'F'):
            if spec['index'] not in (1,41):continue
            records.append(make_frame(spec,inputs['scenes'][scene]['checkpoint'],g,config,normalization,group='pilot'))
    frozen_json(OUT/'PILOT.json',{'normalization':normalization,'records':records,
                'qualification':'F1/F41 engineering slice only; final global normalization uses all primary F'})
    status('PILOT_COMPLETE',C_opened=False)


def primary_f():
    inputs = read_inputs()
    config = base_config()
    config_path = OUT/'CONFIG.json'
    if config_path.exists():
        if json.loads(config_path.read_text()) != config:
            raise RuntimeError('Source/config changed after production was frozen')
    else:
        atomic_json(config_path, config)
    if (OUT/'LOCK.json').exists():
        require_evaluation_lock(OUT)
        status('PRIMARY_F_COMPLETE', parameter_hash=json.loads((OUT/'LOCK.json').read_text())['parameter_hash'])
        return
    fields=[]; records=[]
    for scene in ('lego','chair'):
        g = load_scene(scene, inputs)
        checkpoint = inputs['scenes'][scene]['checkpoint']
        for spec in frame_specs(inputs,scene,'F'):
            status('PRIMARY_F_NATIVE', current_scene=scene, current_frame=spec['key'])
            raw, path = get_raw(spec,checkpoint,g)
            fields.append(raw_fields(raw))
            records.append({'scene':scene,'key':spec['key'], 'native_sha256':hash_file(path),
                            'camera_hash':canonical_hash(spec['camera'])})
    normalization = fit_normalization(fields)
    del fields
    frozen_json(OUT/'NORMALIZATION.json', {'normalization':normalization,'F_native_sources':records})
    seals=[]
    for scene in ('lego','chair'):
        g=load_scene(scene,inputs)
        for spec in frame_specs(inputs,scene,'F'):
            status('PRIMARY_F_EVIDENCE', current_scene=scene, current_frame=spec['key'])
            seals.append(make_frame(spec,inputs['scenes'][scene]['checkpoint'],g,config,normalization))
    lock={'config':config,'normalization':normalization,'F_native_sources':records,'primary_F':seals,
          'parameter_hash':canonical_hash({'config':config,'normalization':normalization})}
    lock['lock_hash']=canonical_hash(lock)
    atomic_json(OUT/'LOCK.json',lock)
    frozen_json(ART/'PARAMETER_LOCK.json',lock)
    require_evaluation_lock(OUT)
    status('PRIMARY_F_COMPLETE', parameter_hash=lock['parameter_hash'], C_opened=False)


def evaluate(extra=False):
    lock=require_evaluation_lock(OUT)
    if lock['config'] != base_config():
        raise RuntimeError('Source/config changed after F-only lock')
    if extra:
        for scene in ('lego','chair'):
            for split in ('C','arc0'):
                for spec in frame_specs(read_inputs(),scene,split):
                    p=OUT/'frames'/scene/spec['key']
                    ctx=frame_context(spec,read_inputs()['scenes'][scene]['checkpoint'],lock['config'],lock['normalization'])
                    if not valid_seal(p,ctx):
                        raise RuntimeError('Extra scenes blocked until primary engineering complete')
    inputs=read_inputs()
    scenes=('drums','ficus') if extra else ('lego','chair')
    for scene in scenes:
        g=load_scene(scene,inputs)
        for split in (('F','C','arc0') if extra else ('C','arc0')):
            for spec in frame_specs(inputs,scene,split):
                status('EXTRA_EVALUATION' if extra else 'PRIMARY_EVALUATION', current_scene=scene,
                       current_frame=spec['key'],C_opened=True)
                make_frame(spec,inputs['scenes'][scene]['checkpoint'],g,lock['config'],lock['normalization'])
    status('EXTRA_COMPLETE' if extra else 'PRIMARY_COMPLETE')


def media(scenes):
    lock=require_evaluation_lock(OUT); inputs=read_inputs()
    if lock['config'] != base_config():
        raise RuntimeError('Source/config changed after F-only lock')
    for scene in scenes:
        frames=OUT/'frames'/scene; dest=OUT/'media'/scene
        frame_records=[]
        for split in ('F','C','arc0'):
            specs=frame_specs(inputs,scene,split)
            for spec in specs:
                ctx=frame_context(spec,inputs['scenes'][scene]['checkpoint'],lock['config'],lock['normalization'])
                if not valid_seal(frames/spec['key'],ctx):
                    raise RuntimeError(f'Media blocked by unsealed frame: {spec}')
                frame_records.append({'key':spec['key'],'seal_sha256':hash_file(frames/spec['key']/'SEAL.json')})
        media_context={'scene':scene,'parameter_hash':lock['parameter_hash'],'frames':frame_records,
                       'fps':12,'arc_frames':33,'native_full_resolution_tiles':True}
        if valid_seal(dest,media_context):
            status('MEDIA_COMPLETE',current_scene=scene,restart='verified media seal')
            continue
        stage=OUT/'staging'/f'media_{scene}_{os.getpid()}'
        stage.mkdir(parents=True,exist_ok=False)
        for split in ('F','C','arc0'):
            specs=frame_specs(inputs,scene,split)
            for arm in ('rgb','A','B','C','author_gain'):
                suffix='rgb.png' if arm=='rgb' else f'{arm}_ink.png'
                target=stage/f'{split}_{arm}_contact.png'
                save_contact_sheet([frames/s['key']/suffix for s in specs], target,
                                   labels=[s['key'] for s in specs], columns=3 if split=='arc0' else 4)
        manifest={'scene':scene,'parameter_hash':lock['parameter_hash'],'videos':{},'contacts':{}}
        for name,file in (('comparison','line_panel.png'),('overlay','overlay_panel.png'),('matched','matched_panel.png')):
            target=stage/f'arc0_{name}.mp4'
            record=encode_video((np.asarray(Image.open(frames/f'arc0_{i:03d}'/file)) for i in range(33)),
                                target,fps=12,expected_frames=33)
            manifest['videos'][name]={**record,'path':str(dest/target.name)}
        for path in sorted(stage.glob('*contact.png')):
            manifest['contacts'][path.name]={'path':str(dest/path.name),'sha256':hash_file(path)}
        for i in (0,16,32):
            for kind in ('line','overlay','matched'):
                source=frames/f'arc0_{i:03d}'/f'{kind}_panel.png'
                target=stage/f'arc0_{i:03d}_{kind}.png'
                os.link(source,target)
        atomic_json(stage/'MANIFEST.json',manifest)
        seal_frame(stage,dest,media_context)
        atomic_json(ART/f'{scene}_MEDIA.json',manifest,replace=True)
        status('MEDIA_COMPLETE',current_scene=scene)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',required=True,choices=('pilot','primary-f','primary-eval','extra','media'))
    p.add_argument('--scenes',nargs='+',choices=SCENES,default=list(SCENES))
    args=p.parse_args()
    (OUT/'tmp').mkdir(parents=True,exist_ok=True)
    (OUT/'staging').mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    ledger_path=OUT/'RUNTIME.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    gpu_phase=args.phase != 'media'
    if gpu_phase:
        used=sum(row.get('elapsed_seconds',0) for row in ledger if row.get('gpu_context_phase'))
        remaining=4*3600-used
        if remaining<=0:raise RuntimeError('GPU_PROCESS_WALL_BUDGET_EXHAUSTED')
        def budget_expired(signum,frame):
            raise RuntimeError('GPU_PROCESS_WALL_BUDGET_EXHAUSTED')
        signal.signal(signal.SIGALRM,budget_expired)
        signal.alarm(max(1,int(remaining)))
    entry={'phase':args.phase,'pid':os.getpid(),'start_epoch':time.time(),
           'gpu_context_phase':gpu_phase,'status':'RUNNING'}
    ledger.append(entry); atomic_json(ledger_path,ledger,replace=True)
    try:
        if args.phase=='pilot':pilot()
        elif args.phase=='primary-f':primary_f()
        elif args.phase=='primary-eval':evaluate()
        elif args.phase=='extra':evaluate(extra=True)
        else:media(args.scenes)
        entry['status']='COMPLETE'
    except Exception as exc:
        status('ENGINEERING_INVALID_OR_UNDETERMINED',failed_phase=args.phase,
               blocker=f'{type(exc).__name__}: {exc}',elapsed_seconds=time.monotonic()-start)
        entry['status']='FAILED';entry['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        if gpu_phase:signal.alarm(0)
        entry['elapsed_seconds']=time.monotonic()-start
        atomic_json(ledger_path,ledger,replace=True)


if __name__=='__main__':main()
