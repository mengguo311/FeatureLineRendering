import json,math
from pathlib import Path
import numpy as np
from PIL import Image
from runtime import ART,EXP,OUT,ROOT,V1,sha,digest,atomic_json
from adapter import inspect_ply
BASE=Path('/home/u00134/3dgs_line')
TIER=BASE/'tier1/out/multiscene_foundation'
REP=BASE/'representative_edge_gaussians_three_v1/artifacts/representative_edge_gaussians_three_v1'
HYBRID=BASE/'hybrid_raster_evidence_v2/artifacts/hybrid_raster_evidence_v2'
RESOLVED_INPUT=BASE/'hybrid_raster_evidence_v2/artifacts/direct_curve_global_fit_probe/INPUTS.json'
def config():return json.loads((EXP/'configs/pilot.json').read_text())
def camera_spec(frame,fov,width=512,native_width=800,native_height=800):
    c=np.asarray(frame['transform_matrix'],dtype=float).copy();c[:3,1:3]*=-1
    height=round(native_height*width/native_width);fy=native_width/(2*math.tan(fov/2))
    fy_scaled=fy*height/native_height
    return {'width':width,'height':height,'native_width':native_width,'native_height':native_height,'FoVx':fov,'FoVy':2*math.atan(height/(2*fy_scaled)),'w2c':np.linalg.inv(c).tolist(),'K':[[width/(2*math.tan(fov/2)),0,(width-1)/2],[0,fy_scaled,(height-1)/2],[0,0,1]],'projection':'stock symmetric centered pixel convention, n=0.01 f=100, unchanged 0.3 covariance pixel floor'}
def freeze_data():
    cfg=config();rep=json.loads((REP/'INPUT_HASH_MANIFEST.json').read_text());old=json.loads(RESOLVED_INPUT.read_text());lock=json.loads((HYBRID/'PARAMETER_LOCK.json').read_text())
    dependencies=[REP/'INPUT_HASH_MANIFEST.json',REP/'S0_SEAL.json',HYBRID/'PARAMETER_LOCK.json',RESOLVED_INPUT,V1/'build/stock/onec_stock_C.so',V1/'build/knn/onec_knn_C.so',V1/'vendor/gaussian-splatting/gaussian_renderer/__init__.py',V1/'vendor/gaussian-splatting/scene/gaussian_model.py',V1/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization/diff_gaussian_rasterization/__init__.py']
    allscenes={}
    for s in cfg['scenes']:
        training=TIER/'training'/s/'seed_1729'; staged=TIER/'inputs'/s/'seed_1729'
        manifest=json.loads((training/'manifest.json').read_text());complete=json.loads((training/'completion.json').read_text());path=Path(complete['path'])
        modelsha=sha(path)
        if modelsha!=complete['sha256']:raise ValueError('source checkpoint integrity')
        cfgtext=(training/'checkpoints/cfg_args').read_text()
        if 'sh_degree=3' not in cfgtext or 'white_background=True' not in cfgtext:raise ValueError('unexpected source config')
        header=inspect_ply(path,3)
        metadata=json.loads((staged/'transforms_train.json').read_text());frames={int(Path(f['file_path']).name[2:]):f for f in metadata['frames']}
        original_meta=Path('/home/u00134/cglib/data/full')/s/'transforms_train.json'
        original=json.loads(original_meta.read_text());orig_frames={int(Path(f['file_path']).name[2:]):f for f in original['frames']}
        expected={x['path']:x for x in manifest['staged_data']['files']}
        roles={};used=set()
        for role,indices in [('edit-train',cfg['train_indices']),('dev',cfg['dev_indices']),('edit-holdout',cfg['holdout_indices'])]:
            entries=[]
            for index in indices:
                if index in used or index not in frames:raise ValueError('split overlap/not GS TRAIN')
                used.add(index);photo=staged/'train'/f'r_{index}.png';source=Path(expected[f'train/r_{index}.png']['source'])
                # Holdout image bytes are not opened until a model/dev seal exists.
                native=(800,800) if role=='edit-holdout' else Image.open(photo).size
                cam=camera_spec(frames[index],metadata['camera_angle_x'],cfg['resolution_width'],*native)
                entries.append({'key':f'r_{index:03d}','index':index,'role':role,'path':str(photo),'original_path':str(source),'expected_photo_sha256':expected[f'train/r_{index}.png']['sha256'],'camera':cam,'camera_hash':digest(cam),'original_train':True,'GS_TRAIN_seen':True,'previous_research_key':next((f['key'] for f in rep['scenes'][s]['frames'] if f.get('camera',{}).get('index')==index),None),'qualification':'exploratory edit holdout; GS seen; prior broader usage cannot establish independent blind TEST'})
            roles[role]=entries
        arcs=[]
        for i,f in enumerate(rep['scenes'][s]['frames'][16:]):
            c=f['camera'];w=cfg['resolution_width'];h=round(c['native_height']*w/c['native_width']);k=np.array(c['native_K'],float);k[0]*=w/c['native_width'];k[1]*=h/c['native_height'];k[0,2]=(w-1)/2;k[1,2]=(h-1)/2
            cam={'width':w,'height':h,'native_width':c['native_width'],'native_height':c['native_height'],'FoVx':2*math.atan(w/(2*k[0,0])),'FoVy':2*math.atan(h/(2*k[1,1])),'w2c':c['w2c'],'K':k.tolist(),'projection':'stock symmetric centered pixel convention, unchanged 0.3 covariance pixel floor'}
            arcs.append({'key':f'arc0_{i:03d}','role':'prior-seen visualization arc','camera':cam,'camera_hash':digest(cam),'source_camera_hash':f['camera_hash'],'reference_photo':None})
        # A complete orbit is visualization only, with no invented photo supervision.
        center=np.asarray(old['scenes'][s]['center'],float);radius=4.031129;orbit=[]
        for i,az in enumerate(np.linspace(0,2*np.pi,33,endpoint=False)):
            pos=center+radius*np.array([np.cos(az)*np.cos(.55),np.sin(az)*np.cos(.55),np.sin(.55)])
            forward=(center-pos);forward/=np.linalg.norm(forward);right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
            c2w=np.eye(4);c2w[:3,:3]=np.stack([right,up,-forward],axis=1);c2w[:3,3]=pos
            cam=camera_spec({'transform_matrix':c2w.tolist()},metadata['camera_angle_x'],cfg['resolution_width'])
            orbit.append({'key':f'orbit_{i:03d}','role':'360-degree visualization only; no GT/no optimization','camera':cam,'camera_hash':digest(cam),'reference_photo':None})
        allscenes[s]={'model':str(path),'model_sha256':modelsha,'ply':header,'cfg_args':cfgtext,'training_manifest':str(training/'manifest.json'),'training_source_commit':manifest['source_commit'],'actual_GS_TRAIN_indices':sorted(frames),'original_TRAIN_indices':sorted(orig_frames),'previous_usage':[{'key':f['key'],'camera_hash':f['camera_hash'],'index':f.get('camera',{}).get('index')} for f in rep['scenes'][s]['frames']],'roles':roles,'arc':arcs,'orbit':orbit,'labels':{'genuine_part_labels_found':False,'searched_roots':[str(staged),str(original_meta.parent)],'available_annotation':'Blender RGBA alpha coverage only; no Gaussian/part/physical contact identity'},'original_TEST_images_read':False}
        dependencies.extend([path,training/'manifest.json',training/'entry.json',training/'checkpoints/cfg_args',staged/'transforms_train.json',original_meta])
    out={'schema':'actual-two-scene-data-freeze-v1','config_sha256':sha(EXP/'configs/pilot.json'),'config':cfg,'scenes':allscenes,'read_only_dependencies':{str(p):sha(p) for p in dependencies},'requested_hybrid_INPUTS_missing':str(HYBRID/'INPUTS.json'),'resolved_hybrid_input':str(RESOLVED_INPUT),'resolved_input_matches_lock':sha(RESOLVED_INPUT)==lock['config']['input_manifest_sha256'],'split_scope':'original TRAIN images only; no original TEST image opens; exploration, not new independent TEST'}
    atomic_json(ART/'DATA_FREEZE.json',out);return out
def load_reference(entry,holdout_seal=None):
    if entry['role']=='edit-holdout' and (holdout_seal is None or not Path(holdout_seal).exists()):raise PermissionError('holdout closed until dev/model freeze')
    if entry['role']=='edit-holdout':
        seal=json.loads(Path(holdout_seal).read_text());scene=Path(entry['original_path']).parent.parent.name
        if seal.get('scene')!=scene or seal.get('data_freeze_sha256')!=sha(ART/'DATA_FREEZE.json') or not seal.get('edit_sha256') or not seal.get('dev_summary'):raise PermissionError('holdout requires authentic scene/data/edits/dev seal')
        if seal['selection_freeze_sha256']!=sha(ART/f'{scene}_SELECTION_FREEZE.json') or seal['target_freeze_sha256']!=sha(ART/f'{scene}_TARGET_FREEZE.json'):raise PermissionError('selection/target seal changed')
        for name,expected in seal['edit_sha256'].items():
            if sha(OUT/scene/'edits'/name)!=expected:raise PermissionError('edit changed after dev freeze')
    p=Path(entry['path']);actual=sha(p)
    if actual!=entry['expected_photo_sha256']:raise ValueError('photo source SHA')
    a=np.asarray(Image.open(p).convert('RGBA'),np.float64)/255
    rgb=a[:,:,:3]*a[:,:,3:4]+(1-a[:,:,3:4])
    size=(entry['camera']['width'],entry['camera']['height'])
    # Mirror source training: composite display RGB on white, quantize, then PIL resize.
    rgb=np.asarray(Image.fromarray((rgb*255).astype(np.uint8)).resize(size,Image.Resampling.BICUBIC),np.float32)/255
    aa=np.asarray(Image.fromarray(a[:,:,3].astype(np.float32),mode='F').resize(size,Image.Resampling.BILINEAR),np.float32).clip(0,1)
    return rgb,aa
