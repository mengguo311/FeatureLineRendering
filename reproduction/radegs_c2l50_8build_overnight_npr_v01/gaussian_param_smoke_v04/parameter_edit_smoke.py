"""CPU original-source 3DGS remove-cluster diagnostic; NOT verified part editing."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
if hasattr(os,'sched_setaffinity'):
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import numpy as np


def masked_source_asset(a, labels, cluster):
    labels=np.asarray(labels)
    if len(labels)!=len(a['opacity']):
        raise ValueError('source row mismatch')
    b=dict(a)
    b['opacity']=a['opacity'].copy()
    b['opacity'][labels==cluster]=0.
    return b


def calibration_mae(rendered, reference):
    if rendered['rgb'].shape!=reference['rgb'].shape or rendered['alpha'].shape!=reference['alpha'].shape:
        raise ValueError('camera output shape mismatch')
    if (not rendered['rgb'].size or not rendered['alpha'].size or
        not all(np.isfinite(x).all() for x in (rendered['rgb'],rendered['alpha'],reference['rgb'],reference['alpha']))):
        raise ValueError('nonfinite or empty calibration data')
    return (float(np.mean(np.abs(rendered['rgb']-reference['rgb']))),
            float(np.mean(np.abs(rendered['alpha']-reference['alpha']))))


def foreground_mae(rendered, reference):
    calibration_mae(rendered,reference)
    mask=reference['alpha']>.05
    if not mask.any():
        raise ValueError('no eligible foreground pixels')
    return (float(np.mean(np.abs(rendered['rgb'][mask]-reference['rgb'][mask]))),
            float(np.mean(np.abs(rendered['alpha'][mask]-reference['alpha'][mask]))))


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def image(rgb):
    from PIL import Image
    return Image.fromarray(np.uint8(np.clip(rgb,0,1)*255+0.5),'RGB')


def main():
    from threadpoolctl import threadpool_limits
    threadpool_limits(2)
    if hasattr(os,'sched_getaffinity') and len(os.sched_getaffinity(0))>2:
        raise SystemExit('CPU_AFFINITY_GATE_FAILED')
    from plyfile import PlyData
    from PIL import Image, ImageDraw
    t0=time.monotonic()
    base=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
    smoke=base/'c2l50_8build_gaussian_param_smoke_v04'
    prior=base/'c2l50_8build_part_prior_feasibility_v03/cpu_probe_v03'
    source=Path('/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training/ficus/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply')
    source_hash='9afacac137474a50c5db52e41d2f1656b1e5f22ee5b6804e7e819697679cebac'
    out=smoke/'edited_render_probe'
    if out.exists() or digest(source)!=source_hash:
        raise SystemExit('OUTPUT_EXISTS_OR_SOURCE_IDENTITY_FAILED')
    manifest=json.loads((smoke/'SUMMARY.json').read_text())
    if len(manifest['arms'])!=9 or manifest['source_sha256']!=source_hash:
        raise SystemExit('CLUSTER_MANIFEST_IDENTITY_FAILED')
    # Frozen BEFORE opening reserved RGB. These cluster IDs come from FIT-only K3
    # plus the world-Z low-band diagnostic; none are semantic pot IDs.
    selection=[('B_distance_long',1),('C_projected_long',2),('D_rgb_dc',2),
               ('I_fusion_xyz_sh_projected',1),('J_partfield_prior',2)]
    prior_summary=json.loads((prior/'k3_summary.json').read_text())
    prior_features=json.loads((prior/'full_manifest.json').read_text())
    if (prior_summary['source_sha256']!=source_hash or prior_features['source_sha256']!=source_hash
        or prior_summary['source_rows']!=284835 or prior_features['query_source_index']!='identity 0..284834'):
        raise SystemExit('PARTFIELD_SOURCE_INDEX_MISMATCH')
    labels={}
    for name,k in selection:
        path=(prior/'k3_labels.npy') if name=='J_partfield_prior' else (smoke/(name+'_labels.npy'))
        expected=(prior_summary['labels_sha256'] if name=='J_partfield_prior'
                  else manifest['arms'][name]['labels_sha256'])
        if digest(path)!=expected:
            raise SystemExit('LABEL_HASH_MISMATCH_'+name)
        labels[name]=np.load(path,allow_pickle=False)
    code=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
    sys.path.insert(0,str(code))
    from format import activate
    from renderer import render
    a=activate(PlyData.read(source)['vertex'].data.copy())
    if len(a['means'])!=284835:
        raise SystemExit('SOURCE_ROW_COUNT_MISMATCH')
    fit_path=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_gaussian_param_smoke_v04/reproduction/radegs_c2l50_8build_overnight_npr_v01/gaussian_param_smoke_v04/fit_cameras.json')
    if digest(fit_path)!='e0f2540da3a60dc4b274218badb1f5b843c1a2dac460253672bb0e27fe98b66e':
        raise SystemExit('FIT_CAMERA_MANIFEST_MISMATCH')
    fits=json.loads(fit_path.read_text())['fit_cameras']
    # Use reserved camera metadata only for EVALUATION after selection has frozen.
    registry_path=base/'c2l50_multiview05_v01/REGISTRY.json'
    if digest(registry_path)!='1115386cdf4186074e0858921a423141433757447b20c9e5857218d59de86e9c':
        raise SystemExit('CAMERA_REGISTRY_HASH_MISMATCH')
    reg=json.loads(registry_path.read_text())['scenes']['ficus']
    if reg['model']!=str(source) or reg['model_sha256']!=source_hash or next(c for c in reg['cameras'] if c['view']=='train_r_80')!=fits[0]:
        raise SystemExit('REGISTRY_CAMERA_SOURCE_MISMATCH')
    cameras=[fits[0]]+[next(c for c in reg['cameras'] if c['view']==v) for v in ('test_r_14','test_r_79')]
    input_hashes={'train_r_80':'53e8dc0aac950b8042697c2422963aa13acac758f03a37026799436bfd63e8bf',
                  'test_r_14':'f80a1f801a58d6ceaf520609efc863bd2514eaedbf78e74955d14fe23ecfe54f',
                  'test_r_79':'aa8a61e2964918f97c87628a5ee8f0f487d2b252943bb0b54cc2cd30b6f020e6'}
    results={'status':'ORIGINAL_KERNEL_REMOVE_CLUSTER_RENDER_DIAGNOSTIC_NOT_SEMANTIC_PARTS',
             'source_sha256':source_hash,'fit_view':fits[0]['view'],
             'evaluation_views':['test_r_14','test_r_79'],
             'calibration_gate_full_rgb_mae':.015,'calibration_gate_full_alpha_mae':.015,
             'calibration_gate_foreground_rgb_mae':.03,'calibration_gate_foreground_alpha_mae':.03,
             'camera_registry_sha256':'1115386cdf4186074e0858921a423141433757447b20c9e5857218d59de86e9c',
             'reference_input_sha256':input_hashes,
             'source_gaussian_count':len(a['means']),'selection':selection,'views':{}}
    out.mkdir(parents=True)
    # Gate every view before spending compute on the edited variants.
    baselines={}
    for c in cameras:
        view=c['view']
        input_path=base/'c2l50_multiview05_v01/scenes/ficus/inputs'/(view+'.npz')
        if digest(input_path)!=input_hashes[view]:
            raise SystemExit('REFERENCE_INPUT_IDENTITY_FAILED_'+view)
        raw=np.load(input_path,allow_pickle=False)
        target={'rgb':raw['rgb'],'alpha':raw['alpha']}
        baseline=render(a,c,background=(1,1,1),floor=.3)
        rgb_error, alpha_error=calibration_mae(baseline,target)
        foreground_rgb,foreground_alpha=foreground_mae(baseline,target)
        results['views'][view]={'unmodified_rgb_mae':rgb_error,'unmodified_alpha_mae':alpha_error,
                                'foreground_rgb_mae':foreground_rgb,'foreground_alpha_mae':foreground_alpha}
        print('UNMODIFIED_CALIBRATION',view,rgb_error,alpha_error,foreground_rgb,foreground_alpha,flush=True)
        if rgb_error>.015 or alpha_error>.015 or foreground_rgb>.03 or foreground_alpha>.03:
            results['status']='RENDER_CALIBRATION_FAILED_NO_EDIT_VALIDATION'
            (out/'STATUS.json').write_text(json.dumps(results,indent=2)+'\n')
            raise SystemExit('CALIBRATION_GATE_FAILED_'+view)
        baselines[view]=baseline
    for c in cameras:
        view=c['view']
        sheet=Image.new('RGB',(800*(1+len(selection)),800+42),'white')
        draw=ImageDraw.Draw(sheet)
        sheet.paste(image(baselines[view]['rgb']),(0,42))
        draw.text((12,12),'FULL SOURCE / '+view,fill='black')
        results['views'][view]['selected']={}
        for index,(name,k) in enumerate(selection):
            n=int(np.count_nonzero(labels[name]==k))
            edited=masked_source_asset(a,labels[name],k)
            r=render(edited,c,background=(1,1,1),floor=.3)
            delta=np.abs(r['rgb']-baselines[view]['rgb'])
            results['views'][view]['selected'][name]={'cluster':k,'removed_original_rows':n,
                'mean_abs_rgb_delta':float(np.mean(delta)),
                'fraction_pixels_max_channel_delta_gt_0p05':float(np.mean(np.max(delta,axis=2)>.05))}
            print('EDIT_RENDER',view,name,k,n,results['views'][view]['selected'][name]['mean_abs_rgb_delta'],flush=True)
            sheet.paste(image(r['rgb']),(800*(index+1),42))
            draw.text((800*(index+1)+8,12),f'{name} / cluster {k} OFF',fill='black')
        file=out/(view+'_unedited_vs_clusters.png')
        sheet.save(file)
        results['views'][view]['figure']=file.name
        results['views'][view]['figure_sha256']=digest(file)
        (out/'STATUS.json').write_text(json.dumps(results,indent=2)+'\n')
    if not np.isfinite(a['opacity']).all() or digest(source)!=source_hash:
        raise SystemExit('SOURCE_MUTATED_OR_NONFINITE')
    results['status']='CPU_RENDERED_NOT_SEMANTICALLY_VALIDATED'
    results['wall_seconds']=round(time.monotonic()-t0,2)
    (out/'STATUS.json').write_text(json.dumps(results,indent=2)+'\n')
    print('CPU_EDIT_DIAGNOSTIC_DONE',json.dumps(results),flush=True)


if __name__=='__main__':
    main()
