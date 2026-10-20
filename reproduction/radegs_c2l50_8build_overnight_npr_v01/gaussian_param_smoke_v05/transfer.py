"""CPU-only transfer of frozen source-kernel smoke to chair/lego/drums.

All identifiers are original seed_1729 PLY rows. Clusters are exploratory, not parts.
The 8192-point PartField encoder is a subsampled probe, not official full-cloud inference.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
if hasattr(os,'sched_setaffinity'):
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import numpy as np

ROOT=Path('/home/u00134/3dgs_line/tier1/out/multiscene_foundation')
PRIOR_ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03')
NATIVE_CODE=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
EXPECTED={
 'chair':('13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d',256690),
 'lego':('fa9bea3fa4f8d349fa873a66d892c53cd1263499caec6421c286350a5bb7cbbc',310475),
 'drums':('d4b67123927613ade6b7e2f38ed6bf724fc5e348dbcca84a2be1352ec5113a8b',360012),
}
CHECKPOINT_HASH='463efc8a3afd3913142aa025e0125c00f16ef452b8de6a132ebe32bbe7877ee4'
OFFICIAL_CODE_SHA='373025dbd283bb44cc4a6dc78c99994dbc91de32'


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):
            h.update(b)
    return h.hexdigest()


def camera_from_transform(frame,angle_x,width,view):
    c2w=np.asarray(frame['transform_matrix'],dtype=np.float64)
    if c2w.shape!=(4,4) or not np.isfinite(c2w).all():
        raise ValueError('invalid camera matrix')
    cv=np.linalg.inv(c2w@np.diag([1.,-1.,-1.,1.]))
    fx=.5*width/np.tan(float(angle_x)/2.)
    return dict(view=view,split='train' if view.startswith('train_') else 'test',
                width=width,height=width,fx=fx,fy=fx,cx=(width-1)/2,cy=(width-1)/2,
                extrinsic=cv.tolist(),original_c2w_gl=c2w.tolist(),
                coordinate='OpenGL c2w y/z column sign flip -> x-right/y-down/z-forward; integer pixel centers',
                units='NeRF Synthetic scene units, not meters')


def original_row_labels(compact_labels,support):
    support=np.asarray(support,dtype=bool)
    compact_labels=np.asarray(compact_labels,dtype=np.uint8)
    if support.ndim!=1 or compact_labels.shape!=(int(support.sum()),) or np.any(compact_labels>2):
        raise ValueError('source-ID/label mismatch')
    labels=np.full(len(support),255,dtype=np.uint8)
    labels[support]=compact_labels
    return labels


def best_axis_null(xyz,mask):
    xyz=np.asarray(xyz)
    mask=np.asarray(mask,dtype=bool)
    if xyz.shape!=(len(mask),3) or not np.isfinite(xyz).all() or not 0<mask.sum()<len(mask):
        raise ValueError('invalid axis-null input')
    n=int(mask.sum())
    best=None
    for j,axis in enumerate('xyz'):
        order=np.argsort(xyz[:,j],kind='stable')
        for side,ids in (('low',order[:n]),('high',order[-n:])):
            chosen=np.zeros(len(mask),dtype=bool);chosen[ids]=True
            intersection=int(np.count_nonzero(chosen&mask))
            score=intersection/(2*n-intersection)
            if best is None or score>best['iou']:
                best=dict(axis=axis,side=side,intersection=intersection,iou=float(score),mask=chosen)
    return best


def cameras(scene,width):
    base=ROOT/'inputs'/scene/'seed_1729'
    out={}
    for split in ('train','test'):
        raw=json.loads((base/f'transforms_{split}.json').read_text())
        for f in raw['frames']:
            view=('train_' if split=='train' else 'test_')+Path(f['file_path']).name
            if view in ('train_r_79','train_r_7','test_r_14','test_r_79'):
                out[view]=camera_from_transform(f,raw['camera_angle_x'],width,view)
    if set(out)!=set(('train_r_79','train_r_7','test_r_14','test_r_79')):
        raise ValueError('missing fixed fit/evaluation cameras')
    return out


def source_asset(scene):
    from plyfile import PlyData
    path=ROOT/'training'/scene/'seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply'
    expected,n=EXPECTED[scene]
    if sha256(path)!=expected:
        raise ValueError('source SHA mismatch')
    raw=PlyData.read(path)['vertex'].data
    if len(raw)!=n or 'source_index' in raw.dtype.names or len(raw.dtype.names)!=62:
        raise ValueError('source schema mismatch')
    return path,raw


def native_pilot(scene,raw,cams):
    sys.path.insert(0,str(NATIVE_CODE))
    from format import activate
    from renderer import render
    a=activate(raw.copy())
    c=cams['train_r_79']
    result=render(a,c,background=(1,1,1),floor=.3)
    path=ROOT/'training'/scene/'seed_1729/quality/measurements/native/train_079.npz'
    with np.load(path,allow_pickle=False) as data:
        delta={k:float(np.mean(np.abs(result['rgb']-data[k]))) for k in ('rgb_0','rgb_1')}
    return delta


def partfield_features(scene,xyz,out):
    from threadpoolctl import threadpool_limits
    threadpool_limits(2)
    import subprocess
    import torch
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if torch.cuda.is_available():
        raise RuntimeError('CUDA visible')
    checkpoint=PRIOR_ROOT/'checkpoint/model_objaverse.ckpt'
    code=PRIOR_ROOT/'third_party/PartField'
    if sha256(checkpoint)!=CHECKPOINT_HASH or subprocess.check_output(['git','-C',str(code),'rev-parse','HEAD'],text=True).strip()!=OFFICIAL_CODE_SHA:
        raise ValueError('PartField checkpoint/code identity mismatch')
    if subprocess.run(['git','-C',str(code),'diff','--quiet','HEAD','--'],check=False).returncode:
        raise ValueError('official code dirty')
    sys.path.insert(0,str(code))
    from yacs.config import CfgNode
    from partfield.config.defaults import _C
    import partfield.model_trainer_pvcnn_only_demo as official
    from partfield.model.PVCNN.encoder_pc import sample_triplane_feat
    # Reuse v03 normalization/subsampling EXACTLY (fixed original row IDs).
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'part_prior_v03'))
    from cpu_partfield_probe import normalize_full_cloud,fixed_source_subset
    x=normalize_full_cloud(xyz.astype('f4'))
    ids=fixed_source_subset(len(x),8192)
    cfg=_C.clone();cfg.merge_from_file(str(code/'configs/final/demo.yaml'))
    cfg.is_pc=True;cfg.use_2d_feat=False
    constructor=official.TriPlanePC2Encoder
    def cpu_constructor(*args,**kwargs):
        kwargs['device']='cpu'
        return constructor(*args,**kwargs)
    official.TriPlanePC2Encoder=cpu_constructor
    model=official.Model(cfg)
    torch.serialization.add_safe_globals([CfgNode,set])
    loaded=torch.load(checkpoint,map_location='cpu',weights_only=True)
    model.load_state_dict(loaded['state_dict'],strict=True)
    model.eval()
    if any(p.device.type!='cpu' for p in model.parameters()):
        raise RuntimeError('PartField on non-CPU device')
    pending=out/'partfield_features.part.npy'
    dest=out/'partfield_features.npy'
    if pending.exists() or dest.exists():
        raise FileExistsError('refuse to overwrite features')
    t=time.monotonic()
    with torch.inference_mode():
        inp=torch.from_numpy(x[ids]).unsqueeze(0)
        encoded=model.pvcnn(inp,inp)
        planes=model.triplane_transformer(encoded)[:,:,64:]
        if planes.shape[:3]!=(1,3,448):
            raise ValueError('wrong PartField plane shape')
        arr=np.lib.format.open_memmap(pending,mode='w+',dtype='f4',shape=(len(x),448))
        for start in range(0,len(x),2048):
            feat=sample_triplane_feat(planes,torch.from_numpy(x[start:start+2048]).unsqueeze(0)).squeeze(0).numpy()
            if feat.shape!=(len(x[start:start+2048]),448) or not np.isfinite(feat).all():
                raise ValueError('bad PartField feature block')
            arr[start:start+len(feat)]=feat
        arr.flush();del arr
    os.replace(pending,dest)
    return dict(feature_sha256=sha256(dest),checkpoint_sha256=CHECKPOINT_HASH,
                encoder_input_rows=len(ids),encoder_subset_sha256=hashlib.sha256(ids.tobytes()).hexdigest(),
                elapsed_seconds=round(time.monotonic()-t,2),feature_shape=[len(x),448],
                caveat='8192 deterministic original centers encoded, all original centers queried; not official full-cloud inference')


def run(scene,output):
    from threadpoolctl import threadpool_limits
    threadpool_limits(2)
    if output.exists():
        raise FileExistsError('refuse existing scene output')
    path,raw=source_asset(scene)
    output.mkdir(parents=True)
    xyz=np.stack([raw[k] for k in ('x','y','z')],axis=1).astype(np.float64)
    cams=cameras(scene,400)
    print('SOURCE_READY',scene,len(xyz),sha256(path),flush=True)
    result={'status':'RUNNING_NOT_SEMANTIC_PARTS','scene':scene,'source':str(path),
            'source_sha256':EXPECTED[scene][0],'source_rows':len(xyz),'source_index':'original PLY row i',
            'fit_views':['train_r_79','train_r_7'],'reserved_views':['test_r_14','test_r_79'],
            'cpu_threads':2,'cuda_visible':False,'k':3,'n_init':3,'max_iter':100,
            'reserved_pixels_opened_for_features':False}
    def save():
        (output/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()
    result['pilot_native_rgb_mae_by_background'] = native_pilot(scene,raw,cams)
    print('NATIVE_PILOT',scene,result['pilot_native_rgb_mae_by_background'],flush=True)
    # Feature construction is the same nine-arm recipe as v04, except a shared
    # FIT-positive-depth mask is explicitly retained; outsiders are UNKNOWN=255.
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'gaussian_param_smoke_v04'))
    from parameter_smoke import covariance_and_world_axis,projected_major_sigma,distance_weighted_world_axis,sh_dc_rgb,equal_block_features,prepare_arm_features,proxy_stats
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score
    from format import activate
    from renderer import project_cov,colors,render
    logscales=np.stack([raw[f'scale_{k}'] for k in range(3)],axis=1)
    q=np.stack([raw[f'rot_{k}'] for k in range(4)],axis=1)
    cov,long_axis=covariance_and_world_axis(logscales,q)
    a=activate(raw.copy())
    if not np.allclose(a['covariance'],cov,rtol=1e-6,atol=1e-9):
        raise ValueError('native covariance mismatch')
    dc=sh_dc_rgb(np.stack([raw[f'f_dc_{k}'] for k in range(3)],axis=1))
    valid=np.ones(len(xyz),dtype=bool)
    projection=[];distance=[];rgb=[]
    for v in result['fit_views']:
        c=cams[v]
        uv,z,screen=project_cov(xyz,cov,c,.3)
        okay=(z>.2)&np.isfinite(z)&np.isfinite(uv).all(1)&np.isfinite(screen).all((1,2))
        valid &= okay
        result[v+'_projectable_rows']=int(okay.sum())
        result[v+'_in_frame_center_rows']=int(np.count_nonzero(okay&(uv[:,0]>=0)&(uv[:,0]<400)&(uv[:,1]>=0)&(uv[:,1]<400)))
        projection.append(screen);distance.append(z);rgb.append(colors(a,c))
    if valid.sum()<len(xyz)//2:
        raise ValueError('insufficient common camera support')
    result['common_support_rows']=int(valid.sum());result['unknown_rows']=int((~valid).sum())
    xv=xyz[valid]
    projection=[projected_major_sigma(p[valid],.3) for p in projection]
    distance=[distance_weighted_world_axis(long_axis[valid],z[valid],cams[v]['fx'],cams[v]['fy']) for v,z in zip(result['fit_views'],distance)]
    rgb=[x[valid] for x in rgb]
    proj=np.mean(np.log(np.stack(projection,axis=1)),axis=1)[:,None]
    dist=np.mean(np.log(np.stack(distance,axis=1)),axis=1)[:,None]
    sh=np.concatenate(rgb,axis=1)
    arms={
      'A_world_long':np.max(logscales[valid],axis=1)[:,None],
      'B_distance_long':dist,'C_projected_long':proj,'D_rgb_dc':dc[valid],
      'E_rgb_sh_fit_concat':sh,'F_rgb_sh_fit_mean':np.mean(rgb,axis=0),
      'G_xyz':xv,
      'H_shape_opacity':np.column_stack([np.sort(logscales[valid],axis=1),raw['opacity'][valid]]),
      'I_fusion_xyz_sh_projected':equal_block_features([xv,sh,proj]),
    }
    result['arms']={}
    for name,features in arms.items():
        t=time.monotonic()
        f=prepare_arm_features(name,features)
        k=KMeans(n_clusters=3,random_state=0,n_init=3,max_iter=100,algorithm='lloyd')
        alt=KMeans(n_clusters=3,random_state=1,n_init=3,max_iter=100,algorithm='lloyd')
        labels=original_row_labels(k.fit_predict(f).astype('u1'),valid)
        alt_l=alt.fit_predict(f)
        if sorted(np.unique(labels[valid]).tolist())!=[0,1,2]:
            raise ValueError('empty arm cluster')
        file=output/(name+'_labels.npy');np.save(file,labels)
        counts=np.bincount(labels[valid],minlength=3).tolist()
        result['arms'][name]=dict(counts=counts,seed_stability_ari=float(adjusted_rand_score(labels[valid],alt_l)),
           source_index='original PLY row i; 255 UNKNOWN if no FIT projection',labels_sha256=sha256(file),
           elapsed_seconds=round(time.monotonic()-t,2),n_iter=int(k.n_iter_),alt_n_iter=int(alt.n_iter_))
        save();print('ARM_DONE',scene,name,counts,flush=True)
    result['partfield']=partfield_features(scene,xyz,output)
    f=np.load(output/'partfield_features.npy',mmap_mode='r')
    t=time.monotonic()
    k=KMeans(n_clusters=3,random_state=0,n_init=3,max_iter=100,algorithm='lloyd')
    labels=k.fit_predict(f).astype('u1')
    label_path=output/'partfield_labels.npy';np.save(label_path,labels)
    del f
    nulls={}
    for cluster in range(3):
        mask=(labels==cluster)
        null=best_axis_null(xyz,mask)
        nulls[str(cluster)]={key:value for key,value in null.items() if key!='mask'}
    result['partfield'].update(counts=np.bincount(labels,minlength=3).tolist(),labels_sha256=sha256(label_path),
       kmeans_seconds=round(time.monotonic()-t,2),axis_nulls=nulls,
       ari_vs_xyz_on_fit_support=float(adjusted_rand_score(labels[valid],np.load(output/'G_xyz_labels.npy')[valid])),
       warning='axis-null cardinality and choice selected post-hoc; this is an oracle diagnostic')
    save();print('PARTFIELD_DONE',scene,result['partfield']['counts'],nulls,flush=True)
    # Preselect the least axis-explained feature cluster BEFORE opening reserved pixels.
    chosen=min(range(3),key=lambda c:nulls[str(c)]['iou'])
    null=best_axis_null(xyz,labels==chosen)
    baseline_cols=[('original',None),('PartField '+str(chosen),labels==chosen),
       ('axis '+null['axis']+' '+null['side'],null['mask'])]
    # Also show the other two PartField clusters, not just a cherry-picked candidate.
    for c in range(3):
        if c!=chosen: baseline_cols.append(('PartField '+str(c),labels==c))
    result['selected_cluster_rule']='minimum oracle single-axis IoU before reserved read; NOT semantic selection'
    result['selected_cluster']=chosen
    result['view_results']={}
    from PIL import Image,ImageDraw
    for v in ('train_r_79','test_r_14','test_r_79'):
        camera=cams[v]
        original=render(a,camera,background=(1,1,1),floor=.3)
        img=Image.new('RGB',(400*len(baseline_cols),430),'white')
        draw=ImageDraw.Draw(img)
        delta={}
        for j,(name,mask) in enumerate(baseline_cols):
            if mask is None: rendered=original
            else:
                b=dict(a);b['opacity']=a['opacity'].copy();b['opacity'][mask]=0
                rendered=render(b,camera,background=(1,1,1),floor=.3)
                diff=np.abs(rendered['rgb']-original['rgb'])
                delta[name]={'removed_rows':int(mask.sum()),'full_rgb_mae_vs_original':float(diff.mean()),
                   'fraction_pixels_max_channel_delta_gt_0p05':float(np.mean(np.max(diff,axis=2)>.05))}
            im=Image.fromarray(np.uint8(np.clip(rendered['rgb'],0,1)*255+.5),'RGB')
            img.paste(im,(j*400,30))
            draw.text((j*400+8,6),name+' OFF' if mask is not None else 'ORIGINAL',fill='black')
        file=output/(v+'_original_vs_off.png');img.save(file)
        result['view_results'][v]={'rgb_comparison':delta,'image_sha256':sha256(file),
            'image':file.name,'view_is_fit':v in result['fit_views']}
        save();print('RENDER_DONE',scene,v,flush=True)
    if sha256(path)!=EXPECTED[scene][0]:
        raise ValueError('source mutated')
    result['status']='CPU_RENDERED_EXPLORATORY_NOT_SEMANTICALLY_VALIDATED'
    save();print('SCENE_DONE',scene,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scene',required=True,choices=sorted(EXPECTED))
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--pilot',action='store_true')
    args=parser.parse_args()
    if args.pilot:
        _,raw=source_asset(args.scene)
        print('NATIVE_PILOT',args.scene,native_pilot(args.scene,raw,cameras(args.scene,400)))
    else:
        run(args.scene,args.output)
