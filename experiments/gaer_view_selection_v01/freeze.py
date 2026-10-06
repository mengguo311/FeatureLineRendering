"""Freeze camera filename matches and verified read-only APIs before canonical data."""
import json,math,re,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from stage_runtime import ROOT,EXP,ART,OLD,OUT,atomic_json,sha,digest
from binding import NATIVE

def make_freeze():
    protocol=json.loads((EXP/'protocol.json').read_text())
    data_path=OLD/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json'
    data=json.loads(data_path.read_text()); scenes={};protected={str(data_path):sha(data_path)}
    for name in protocol['scenes']:
        r=data['scenes'][name]; model=Path(r['model'])
        if sha(model)!=r['model_sha256']:raise RuntimeError('original PLY hash mismatch')
        meta=Path(re.search("source_path='([^']+)'",r['cfg_args'])[1])/'transforms_train.json'
        m=json.loads(meta.read_text()); cameras=[]
        entries=[e for group in r['roles'].values() for e in group]
        for stem in protocol['views']:
            e,=[e for e in entries if Path(e['original_path']).stem==stem]
            j,f=next((j,f) for j,f in enumerate(m['frames']) if Path(f['file_path']).stem==stem)
            if sum(Path(f['file_path']).stem==stem for f in m['frames'])!=1:raise RuntimeError('ambiguous filename')
            c2w=np.array(f['transform_matrix'],np.float64);c2w[:3,1:3]*=-1;w2c=np.linalg.inv(c2w)
            err=float(np.abs(w2c-np.array(e['camera']['w2c'])).max())
            if err>1e-10:raise RuntimeError('camera mismatch')
            with Image.open(e['original_path']) as im:width,height=im.size
            if [height,width]!=protocol['resolution']:raise RuntimeError('native resolution mismatch')
            fovx=float(m['camera_angle_x']);fovy=2*math.atan(height/width*math.tan(fovx/2))
            camera=dict(key=stem,width=width,height=height,FoVx=fovx,FoVy=fovy,w2c=w2c.tolist(),
                metadata_index=j,frame_file=f['file_path'],metadata_path=str(meta),metadata_sha256=sha(meta),
                original_image=e['original_path'],original_image_sha256=sha(e['original_path']),metadata_w2c_error=err,
                previous_role=next(k for k,values in r['roles'].items() if e in values),formal_blind=False)
            camera['camera_sha256']=digest(camera);cameras.append(camera)
            protected[e['original_path']]=sha(e['original_path'])
        scenes[name]=dict(model=str(model),model_sha256=sha(model),count=r['ply']['count'],sh_degree=3,cameras=cameras)
        for p in (model,meta,Path(r['training_manifest'])):protected[str(p)]=sha(p)
    paths=[OLD/'experiments/gaer_attribution_buffer_v01/src'/n for n in ('native.py','runtime.py','scene_io.py')]
    paths += [OLD/'artifacts/gaer_attribution_buffer_v01'/n for n in ('BUILD.json','REPORT_ZH.md','REPRODUCE.md','FUTURE_CAVEATS.md','instructions/GAER_agent_experiment_prompt.txt','results/REPRODUCTION.json')]
    for variant,binary in [('patched','gaer_native_C'),('original','gaer_original_C')]:
        paths+=[OLD/'out/gaer_attribution_buffer_v01/native'/variant/'diff_gaussian_rasterization/__init__.py',
                OLD/'out/gaer_attribution_buffer_v01/torch_extensions'/binary/(binary+'.so')]
    paths+=[NATIVE/'build/stock/onec_stock_C.so',NATIVE/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization/diff_gaussian_rasterization/__init__.py']
    # Include all isolated native source files, without copying/rebuilding.
    for p in (OLD/'out/gaer_attribution_buffer_v01/native/patched').rglob('*'):
        if p.is_file() and p.suffix in ('.cu','.h','.cpp'):paths.append(p)
    protected.update({str(p):sha(p) for p in paths})
    methods={str(p.relative_to(ROOT)):sha(p) for p in sorted(EXP.rglob('*')) if p.is_file() and p.suffix in ('.py','.json')}
    freeze=dict(protocol_sha256=sha(EXP/'protocol.json'),protocol=protocol,scenes=scenes,protected_before=protected,
                source_method_sha256=digest(methods),source_method_files=methods,
                old_dirty_status=subprocess.check_output(['git','status','--short'],cwd=OLD,text=True),
                AGENTS_search='No AGENTS.md in workspace ancestors or searched project tree',
                reused_native_build=sha(OLD/'artifacts/gaer_attribution_buffer_v01/BUILD.json'),new_kernel_build=False)
    seal=ART/'PREREGISTRATION.json'
    if seal.exists():
        if digest(json.loads(seal.read_text()))!=digest(freeze):raise RuntimeError('preregistration changed; keep existing evidence')
    else: atomic_json(seal,freeze)
    return freeze

def check_protected(freeze):
    after={p:sha(p) for p in freeze['protected_before']}
    mismatches=[p for p in after if after[p]!=freeze['protected_before'][p]]
    return dict(passed=not mismatches,mismatches=mismatches,after=after)

if __name__=='__main__': print(json.dumps({'freeze_sha256':digest(make_freeze())}))
