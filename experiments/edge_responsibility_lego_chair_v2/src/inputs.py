"""Freeze reference samples, analytic constructs and independent probes before ranking."""
import json, math, subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from runtime import ROOT,EXP,ART,OUT,OLD,NATIVE,sha,digest,atomic_json,source_hashes,event,guard
from evidence import build_reference
from adapter import C0

CONFIG = dict(seed=1729, gpu=0, cpu_threads=2, group_budget=64, groups_per_view=3,
              rank_reference_fraction=.10,rank_reference_cap=32768,
              construction_dc_delta=.01,construction_scale_delta=.01,
              independent_dc_delta=.006,independent_scale_delta=.006,
              construction_dc_direction=[1.,0.,0.], independent_dc_direction=[.5,-.75,.25],
              construction_scale_direction=[1.,1.,1.], independent_scale_direction=[1.,-.5,.25],
              outside_rms_budget=.0005,flat_rms_budget=.0005,minimum_edge_rms=.0001,
              noise_multiplier=20.,minimum_action_floor=.0001,stability_relative_tolerance=.25,
              identity_abs_tolerance=3e-5, identity_weight_tolerance=2e-5,
              prediction_relative_tolerance=.25, prediction_absolute_floor=3e-5,
              display_diff_gain=20.,subset_background=[1,1,1], optimization_steps=336,
              original_TEST_RGB_read=False,formal_blind_TEST=False,
              human_visual_GO='PENDING',semantic_internal_certification='UNAVAILABLE',
              synthetic_presence_threshold=.02,synthetic_localization_tolerance_px=4.,
              heldout_indices=[0,8,18,30],render_new_arc33=True)

def load_reference(entry):
    if entry['role'] not in ('edit-train','dev','edit-holdout'):raise ValueError('not approved original TRAIN role')
    if '/train/' not in entry['path'] or not entry['original_train'] or not entry['GS_TRAIN_seen']:
        raise ValueError('not original TRAIN / GS-seen')
    if sha(entry['path'])!=entry['expected_photo_sha256']:raise ValueError('source image changed')
    rgba=np.asarray(Image.open(entry['path']).convert('RGBA'),np.float64)/255
    rgb=rgba[...,:3]*rgba[...,3:]+1-rgba[...,3:]
    size=(entry['camera']['width'],entry['camera']['height'])
    rgb=np.asarray(Image.fromarray((rgb*255).astype(np.uint8)).resize(size,Image.Resampling.BICUBIC),np.float32)/255
    aa=np.asarray(Image.fromarray(rgba[...,3].astype(np.float32),mode='F').resize(size,Image.Resampling.BILINEAR),np.float32).clip(0,1)
    return rgb,aa

def synthetic_camera(yaw,roll):
    # Fixed view rotation around the world origin. Plane at z=3.
    cy,sy=math.cos(yaw),math.sin(yaw);cr,sr=math.cos(roll),math.sin(roll)
    ry=np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    rz=np.array([[cr,-sr,0],[sr,cr,0],[0,0,1]])
    w=np.eye(4);w[:3,:3]=rz@ry
    # Rotate about the center of the plane so seam remains image centered.
    center=np.array([0,0,3.]);w[:3,3]=center-w[:3,:3]@center
    return dict(width=128,height=128,FoVx=.65,FoVy=.65,w2c=w.tolist(),
                K=[[128/(2*math.tan(.325)),0,63.5],[0,128/(2*math.tan(.325)),63.5],[0,0,1]],
                projection='official native symmetric projection; covariance floor .3')

def project(point,camera):
    q=np.asarray(camera['w2c'])@np.r_[point,1.]
    return np.array([camera['K'][0][0]*q[0]/q[2]+63.5,camera['K'][1][1]*q[1]/q[2]+63.5])

def construct_plane(kind,visible_fold=True):
    # Dense overlapping anisotropic Gaussians. Truth is the construction rule.
    ax=np.linspace(-.85,.85,40);x,y=np.meshgrid(ax,ax)
    xyz=np.stack([x.ravel(),y.ravel(),np.full(x.size,3.)],1);left=xyz[:,0]<0
    col=np.full((len(xyz),3),.45)
    if kind=='material_step':col[left]=[.15,.20,.25];col[~left]=[.8,.65,.5]
    if kind=='low_contrast':col[left]=.449;col[~left]=.451
    if kind=='fold_depth_step':
        xyz[~left,2]+=.10
        if visible_fold:col[left]=.25;col[~left]=.65
    if kind=='texture_detail':
        stripes=((np.floor((xyz[:,0]+.85)/.17).astype(int))%2)==0
        col[stripes]=.2;col[~stripes]=.8
    n=len(xyz);rest=np.zeros((n,15,3),np.float32)
    # Nonzero SH3 component shared across the surface: direction dependence is native.
    rest[:,11,:]=.015
    arrays=dict(_xyz=xyz.astype(np.float32),_features_dc=((col-.5)/C0).astype(np.float32)[:,None,:],
                _features_rest=rest,_opacity=np.full((n,1),np.log(.98/.02),np.float32),
                _scaling=np.tile(np.log([.045,.045,.012]),(n,1)).astype(np.float32),
                _rotation=np.tile([1,0,0,0],(n,1)).astype(np.float32),
                construct_instance_id=np.where(left,0,1).astype(np.int32))
    return arrays

def freeze_synthetic():
    kinds=['constant_plane','same_color_different_ids','material_step','fold_depth_step','texture_detail','low_contrast']
    cameras=[synthetic_camera(y,r) for y,r in [(0,0),(.04,.12),(-.05,-.15),(.06,.25)]]
    cases=[]
    for kind in kinds:
        for j,cam in enumerate(cameras):
            visible=(kind=='material_step' or (kind=='fold_depth_step' and j>=2))
            variant='visible' if kind=='fold_depth_step' and visible else 'default'
            path=OUT/'synthetic_constructs'/f'{kind}_{variant}.npz';path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists():np.savez_compressed(path,**construct_plane(kind,visible))
            center=project([0,0,3],cam);point=project([.1,0,3],cam);normal=(point-center)/np.linalg.norm(point-center)
            # Texture probes are explicitly detail. No structural semantic target is assigned.
            sample=dict(id=f'{kind}_{j}',center=center.tolist(),normal=normal.tolist(),radius=12.,samples=97,
                        class_name='texture_detail' if kind=='texture_detail' else 'clear_color_transition',
                        expected_visible_rgb=visible,expected_geometry=(kind=='fold_depth_step'),
                        independent_truth='known 3D plane/material/depth/instance construction, never gradient labels',
                        u=None,c_star=[.45,.45,.45])
            cases.append(dict(id=f'{kind}_{j}',kind=kind,camera=cam,model_path=str(path.relative_to(ROOT)),
                              model_sha256=sha(path),sample=sample,
                              expected_visible_rgb=visible,expected_geometry=kind=='fold_depth_step',
                              expected_semantic_instance_boundary=kind=='same_color_different_ids',
                              expected_accept=visible,texture_is_legitimate_detail=kind=='texture_detail'))
    # Extra native occlusion, hidden, cancellation and SH clamp fixtures.
    extras=[]
    for name in ['same_color_front_back','hidden','cancelling','sh_clamp']:
        xyz=np.array([[0,0,2.5],[0,0,2.55],[0,0,2.6],[-.18,0,3],[.18,0,3.02]],np.float32)
        cols=np.ones((5,3)) if name in ('same_color_front_back','hidden') else np.array([[.5]*3,[.5]*3,[.5]*3,[.1]*3,[.9]*3])
        if name=='sh_clamp':cols[0]=[-.2,.5,.7]
        opacity=np.array([.99,.99,.99,.9,.9]) if name=='hidden' else np.array([.6,.3,.2,.9,.9])
        scales=np.array([[.7,.7,.02]]*3+[[.12,.3,.02]]*2)
        rest=np.zeros((5,15,3),np.float32);rest[:,11,1]=.05
        if name in ('same_color_front_back','hidden'):rest*=0
        path=OUT/'synthetic_constructs'/f'extra_{name}.npz'
        np.savez_compressed(path,_xyz=xyz,_features_dc=((cols-.5)/C0).astype(np.float32)[:,None,:],
              _features_rest=rest,_opacity=np.log(opacity/(1-opacity)).astype(np.float32)[:,None],
              _scaling=np.log(scales).astype(np.float32),_rotation=np.tile([1,0,0,0],(5,1)).astype(np.float32))
        extras.append(dict(id=name,model_path=str(path.relative_to(ROOT)),model_sha256=sha(path),camera=cameras[0],
                           sample=dict(id=name,center=[63.5,63.5],normal=[1.,0.],radius=12.,samples=97,u=[1.,0,0],c_star=[.5,.5,.5])))
    return dict(cases=cases,extras=extras,frames=24,freeze_before_any_score=True)

def freeze():
    guard('CPU_INPUT_FREEZE',gpu=False)
    freeze_path=ART/'INPUT_FREEZE.json'
    if freeze_path.exists():
        obj=json.loads(freeze_path.read_text())
        if obj['source_hashes']!=source_hashes():raise RuntimeError('frozen sources changed; preserve campaign and start explicit revision')
        return obj
    old_path=OLD/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json'
    old=json.loads(old_path.read_text());protected={}
    for base in [OLD/'experiments/edge_control_lego_chair_v1',OLD/'artifacts/edge_control_lego_chair_v1',ROOT/'artifacts/edge_control_lego_chair_followup']:
        for p in sorted(base.rglob('*')):
            if p.is_file() and not p.is_symlink():protected[str(p)]=sha(p)
    for p in old['read_only_dependencies']:protected[p]=sha(p)
    scenes={}
    for scene,s in old['scenes'].items():
        actual=sha(s['model'])
        if actual!=s['model_sha256']:raise RuntimeError('original model SHA mismatch')
        views=[]
        for role,entries in s['roles'].items():
            for entry in entries:
                if role=='edit-holdout' and entry['index'] not in CONFIG['heldout_indices']:continue
                rgb,aa=load_reference(entry)
                ref,maps=build_reference(rgb,aa,scene,entry['key'])
                path=OUT/'reference_freeze'/scene/f'{entry["key"]}.npz';path.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(path,**maps)
                views.append(dict(entry=entry,reference=ref,maps_path=str(path.relative_to(ROOT)),maps_sha256=sha(path)))
                event(f'freeze/{scene}/{entry["key"]}','TARGETS_FROZEN',samples=len(ref['samples']),flat=len(ref['flat']))
        scenes[scene]=dict(model=s['model'],model_sha256=actual,gaussian_count=s['ply']['count'],degree=3,
                           views=views,arc=s['arc'],orbit=s['orbit'],labels=s['labels'],
                           holdout_status='exploratory original TRAIN / prior GS-seen edit-holdout; no formal blind TEST')
        atomic_json(ART/f'{scene}_TARGET_FREEZE.json',scenes[scene])
    obj=dict(schema='edge-responsibility-v2-inputs-1',config=CONFIG,source_hashes=source_hashes(),
             request_commit='2eb5c8fb2b2e3bca68ff159bd6920c351e7f9a62',
             execution_initial_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             legacy_source_commit='cd4dc554bc406a2cc392a3d004e8d28338a33b4b',
             old_data_freeze_sha256=sha(old_path),protected_sha256=protected,scenes=scenes,synthetic=freeze_synthetic(),
             seed=1729,inputs_complete_before_scores=True,original_TEST_RGB_read=False,
             colorspace='native display PNG RGB compositing; sRGB EOTF only on complete renders for linear profile features',
             parameter_semantics='DC deltas in effective unclamped RGB units/C0; log scale deltas; opacity logit diagnostic only',
             independent_test='prefixed different DC/scale directions and .006 amplitude vs .01 construction; plus heldout views')
    atomic_json(freeze_path,obj);event('CPU_INPUT_FREEZE','COMPLETE',sha256=sha(freeze_path));return obj

if __name__=='__main__':freeze()
