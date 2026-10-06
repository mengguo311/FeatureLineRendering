"""Frozen disjoint roles. No loader exists for closed old low/far TEST."""
import json,shutil
import numpy as np
from PIL import Image
from runtime import EXP,OUT,INPUT,V1,ART,atomic_json,sha
from contracts import validate_roles,angle_status,writable_path
from targets import camera,render_target
CFG=json.loads((EXP/'configs/run.json').read_text())
CHECKPOINT=INPUT/'models/panels_high/chkpnt7000.pth'
SELECTION=INPUT/'controls/panels_high/selection.json'
IDENTITY=INPUT/'controls/panels_high/identity.json'
LABELS=INPUT/'controls/panels_high/fixed_labels.npz'

def freeze_data():
    path=OUT/'data_manifest.json'
    if path.exists():
        d=json.loads(path.read_text());validate_roles(d['roles'])
        for p,h in d['files'].items():assert sha(OUT/p)==h
        return d
    old=json.loads((V1/'experiments/object_neighborhood_edge_control_v1/data/manifests/cameras.json').read_text())
    roles={'train':old['splits']['train']}
    for role,angles in [('dev-in',[-25.1,-15.1,-5.1,4.9,14.9,17.3]),('dev-out',[22.,26.,30.,38.]),('diagnostic-supervision',[23.,27.,31.,35.]),('dev-path',np.linspace(22.1,38.1,36)),('test-new-in',[-22.3,-9.3,3.3,13.3]),('test-new-out',[40.3,44.3,48.3])]:
        roles[role]=[{'id':f'{role}_{i:03d}','theta_deg':float(t),'elevation_deg':float(9 if role.startswith('test') else 5+2*np.sin(np.deg2rad(t*3))), 'transform_matrix':camera(t,9 if role.startswith('test') else 5+2*np.sin(np.deg2rad(t*3)),3.8).tolist()} for i,t in enumerate(angles)]
    validate_roles(roles)
    atomic_json(ART/'data_roles.json',{'roles':roles,'frozen_before_model_selection':True,'TEST_CLOSED':True,'test_condition':CFG['test_new_condition']})
    files={}
    dest=writable_path(OUT/'data/native_train')
    shutil.copytree(INPUT/'data/panels_high/native_train',dest)
    for p in dest.rglob('*'):
        if p.is_file():files[str(p.relative_to(OUT))]=sha(p)
    for role,frames in roles.items():
        if role.startswith('test'):continue
        for f in frames:
            p=OUT/'data'/role/(f['id']+'.npz');p.parent.mkdir(parents=True,exist_ok=True)
            if role=='train':
                orig=INPUT/'data/panels_high/train'/f['id']/'A_target.npz';shutil.copyfile(orig,p)
            else:np.savez_compressed(p,**render_target(f,'panels_high',CFG))
            files[str(p.relative_to(OUT))]=sha(p)
    d={'roles':roles,'files':files,'config_sha':sha(EXP/'configs/run.json'),'test_state':'TEST_CLOSED','provenance':'v1 high train copied byte-exact; new analytic plane targets same fixed radiance and 2x box supersampling; no old low/far test reads'}
    atomic_json(path,d);atomic_json(ART/'data_freeze.json',d);return d

def view(frame,role):
    if role.startswith('test'):raise RuntimeError('TEST_CLOSED')
    z=np.load(OUT/'data'/role/(frame['id']+'.npz'))
    r={k:z[k] for k in z.files};r['float_rgb']=r['rgb'].copy()
    if role=='train':r['rgb']=np.asarray(Image.open(OUT/'data/native_train'/(frame['id']+'.png')),dtype=np.float32)[...,:3]/255
    elif role=='diagnostic-supervision':r['rgb']=(np.round(r['rgb']*255)/255).astype(np.float32)
    return r

def input_snapshot():
    paths=[CHECKPOINT,SELECTION,IDENTITY,LABELS,INPUT/'controls/panels_high/C1_control.pth',INPUT/'controls/panels_high/C1_control_edit.json',INPUT/'models/panels_high/actual_config.json']
    # Hash all original tracked v1 source/results and original instructions, never raw agent logs.
    for root in (V1/'experiments/object_neighborhood_edge_control_v1',V1/'artifacts/object_neighborhood_edge_control_v1'):
        paths += [p for p in root.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    for root in (INPUT/'data/panels_high/train',INPUT/'data/panels_high/native_train',INPUT/'vendor/gaussian-splatting',INPUT/'build/stock',INPUT/'build/knn'):
        paths += [p for p in root.rglob('*') if p.is_file() and not p.is_symlink() and '.git' not in p.parts and '__pycache__' not in p.parts]
    return {str(p):sha(p) for p in sorted(set(paths))}

def selection():
    d=json.loads(IDENTITY.read_text());s=json.loads(SELECTION.read_text());uids=np.asarray(d['uid']);labels=np.asarray(d['label']);mask=np.isin(uids,s['selections']['C1']['uids'])
    assert mask.sum()==1379
    assert sha(CHECKPOINT)==s['initial_checkpoint_sha256']=='cc440283b70bf62cd98dfedf24bf47383a147b70483deec4f849763f3f7847c6'
    return uids,labels,mask
