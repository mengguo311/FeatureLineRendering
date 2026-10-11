"""CPU-only raw depth audit, fixed-scale previews, and complete verified tar.

Source NPZ bytes are copied directly into the archive, never normalized/masked.
The masks are separate derived arrays; RGB and GT never modify depth.
"""
import argparse,csv,hashlib,io,json,os,shutil,sys,tarfile,time,importlib.util
from pathlib import Path
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'official_code_fix_v01';D=H/'depth_only_v01'
os.environ['MPLCONFIGDIR']=str(D/'cache/matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
P=Path(__file__).resolve().parent;W=P.parents[3]
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
from depth_checks import valid_depth,compare_cameras,paired_thumbnail

def summary(d,mask=None):
    x=d[np.isfinite(d)] if mask is None else d[mask]
    return {'count':int(x.size),'range':None if not x.size else [float(x.min()),float(x.max())],
            'quantiles_0_1_50_99_100':None if not x.size else np.quantile(x,[0,.01,.5,.99,1]).tolist()}

def deliver(config_path,out=None):
    c=json.loads(Path(config_path).read_text());scene=c['scene'];model=Path(c['model']);out=Path(out) if out else D/'deliveries'/scene
    out.mkdir(parents=True,exist_ok=False);aux=out/'metadata';aux.mkdir();(out/'masks').mkdir()
    assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(D).free>=50*1024**3
    for stage in ('train','export'):
        assert verify_seal(Path(c['state_dir'])/(stage+'.seal.json'),stage,c['inputs']),stage
    records=[json.loads(x) for x in (model/'iteration_loss.jsonl').read_text().splitlines()]
    assert [r['iteration'] for r in records]==list(range(1,30001))
    dirs={15000:model/'depth_normal_15000',30000:model/'depth_normal'}
    cams={i:json.loads((d/'cameras_and_conventions.json').read_text()) for i,d in dirs.items()}
    compare_cameras(cams[15000],cams[30000]);count=c['expected_scene']['views'];assert len(cams[15000])==count
    loader=O/'source/scene/colmap_loader.py';spec=importlib.util.spec_from_file_location('colmap_loader_standalone',loader);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    poses=mod.read_extrinsics_binary(Path(c['data'])/'sparse/0/images.bin');byname={Path(v.name).stem:v for v in poses.values()}
    chosen=[0,count//2,count-1];rows=[];comparisons=[];entries={};selected={};all_thumbs=[];schema=None
    for index,cam in enumerate(cams[15000]):
        view=cam['view'];h,w=cam['height'],cam['width'];e=np.array(cam['extrinsic']);pose=byname[view]
        ref=np.eye(4);ref[:3,:3]=mod.qvec2rotmat(pose.qvec);ref[:3,3]=pose.tvec
        assert np.isfinite(e).all() and np.allclose(e,ref,atol=2e-7,rtol=2e-7)
        assert np.allclose(e[3],[0,0,0,1]) and np.allclose(e[:3,:3]@e[:3,:3].T,np.eye(3),atol=2e-6)
        pair={}
        for iteration in dirs:
            path=dirs[iteration]/(view+'.npz')
            with np.load(path) as z:
                keys=list(z.files);a=z['alpha'];depth=z['median_camera_z'];expected=z['expected_camera_z'];rgb=z['rgb'] if index in chosen else None
                assert all(z[k].dtype==np.float32 and z[k].shape==(1,h,w) for k in ('median_camera_z','expected_camera_z','alpha'))
                assert np.isfinite(depth).all() and np.isfinite(expected).all() and np.isfinite(a).all(),(view,iteration,'nonfinite')
                assert a.min()>=0 and a.max()<=1,(view,iteration,'alpha out of range')
                schema={k:{'shape':list(z[k].shape),'dtype':str(z[k].dtype)} for k in keys}
            valid=valid_depth(depth,a);vexp=valid_depth(expected,a)
            row={'iteration':iteration,'view':view,'pixels':int(depth.size),'finite_depth':int(np.isfinite(depth).sum()),'positive_depth':int((depth>0).sum()),'alpha_ge_half':int((a>=.5).sum()),'valid_count':int(valid.sum()),'valid_fraction':float(valid.mean()),'raw_median':summary(depth),'valid_median':summary(depth,valid),'raw_expected':summary(expected),'valid_expected':summary(expected,vexp),'alpha':summary(a),'valid_outside_preview_0_4':int((valid&((depth<0)|(depth>4))).sum())}
            rows.append(row);maskpath=out/'masks'/(str(iteration)+'_'+view+'.npz');np.savez_compressed(maskpath,median_valid=valid,expected_valid=vexp)
            entries['checkpoints/'+str(iteration)+'/'+view+'.npz']=path;entries['valid_masks/'+maskpath.name]=maskpath
            pair[iteration]={'depth':depth[0],'alpha':a[0],'valid':valid[0],'rgb':rgb}
        inter=pair[15000]['valid']&pair[30000]['valid'];delta=pair[30000]['depth']-pair[15000]['depth']
        comparisons.append({'view':view,'intersection_valid_count':int(inter.sum()),'signed_delta_scene_units':summary(delta,inter),'absolute_delta_scene_units':summary(abs(delta),inter),'alpha_mean_delta':float((pair[30000]['alpha']-pair[15000]['alpha']).mean())})
        if index in chosen:selected[view]=pair
        all_thumbs.append((view,paired_thumbnail(*[np.ma.masked_where(~pair[i]['valid'],pair[i]['depth'])[::5,::5] for i in (15000,30000)])))
        print(scene,view,'valid15/30',[rows[-2]['valid_fraction'],rows[-1]['valid_fraction']],flush=True)
    for iteration,directory in dirs.items():
        assert {p.stem for p in directory.glob('*.npz')}=={x['view'] for x in cams[iteration]}
        entries['cameras/'+str(iteration)+'.json']=directory/'cameras_and_conventions.json'
    cmap=plt.get_cmap('viridis').copy();cmap.set_bad('#999999');fig,axs=plt.subplots(3,4,figsize=(15,10))
    for r,(view,pair) in enumerate(selected.items()):
        h,w=pair[15000]['depth'].shape
        ref=np.asarray(Image.open(Path(c['data'])/'images'/(view+'.png')).convert('RGB').resize((w,h)))
        axs[r,0].imshow(ref);axs[r,0].set_title('RGB reference / training view '+view)
        for col,i in ((1,15000),(2,30000)):
            im=axs[r,col].imshow(np.ma.masked_where(~pair[i]['valid'],pair[i]['depth']),cmap=cmap,vmin=0,vmax=4);axs[r,col].set_title('Median camera-z '+str(i)+' / [0,4]')
            fig.colorbar(im,ax=axs[r,col],fraction=.046,pad=.02,label='scene units')
        both=pair[15000]['valid']&pair[30000]['valid'];im=axs[r,3].imshow(np.ma.masked_where(~both,pair[30000]['depth']-pair[15000]['depth']),cmap='coolwarm',vmin=-.1,vmax=.1);axs[r,3].set_title('30k minus15k / fixed [-.1,.1]');fig.colorbar(im,ax=axs[r,3],fraction=.046,pad=.02)
        for ax in axs[r]:ax.set_axis_off()
    fig.suptitle(scene+' / official_code_fix_v01 / exact raw camera-z; gray=invalid(alpha<.5/nonfinite/nonpositive)\nFixed scales for every view/checkpoint; RGB/GT never alters depth. Training-view diagnosis only.');fig.tight_layout();fig.savefig(out/'DEPTH_15K_30K.png',dpi=135);plt.close(fig)
    fig,axs=plt.subplots(3,4,figsize=(15,9))
    for r,(view,pair) in enumerate(selected.items()):
        for j,i in enumerate((15000,30000)):
            axs[r,j].imshow(pair[i]['alpha'],cmap='gray',vmin=0,vmax=1);axs[r,j].set_title(view+' alpha '+str(i)+' [0,1]')
            axs[r,j+2].imshow(pair[i]['valid'],cmap='gray',vmin=0,vmax=1);axs[r,j+2].set_title('Valid finite,z>0,alpha>=.5 / '+str(i))
        for ax in axs[r]:ax.set_axis_off()
    fig.tight_layout();fig.savefig(out/'ALPHA_VALIDITY.png',dpi=135);plt.close(fig)
    ncols=7;nrows=(count+6)//7;fig,axs=plt.subplots(nrows,ncols,figsize=(19,2.1*nrows),squeeze=False)
    for ax,(view,array) in zip(axs.flat,all_thumbs):ax.imshow(array,cmap=cmap,vmin=0,vmax=4);ax.set_title(view+' 15k | 30k',fontsize=8)
    for ax in axs.flat:ax.set_axis_off()
    fig.suptitle(scene+' all views / median camera-z fixed [0,4] scene units; left15k right30k; gray invalid');fig.tight_layout();fig.savefig(out/'ALL_VIEWS_DEPTH.png',dpi=130);plt.close(fig)
    review={'scene':scene,'method_variant':'official_code_fix_v01','status':'NUMERICAL_DEPTH_REVIEW_PASSED_VISUAL_REVIEW_REQUIRED','checkpoints':[15000,30000],'views_per_checkpoint':count,'raw_npz_files':count*2,'rows':rows,'fixed_camera_comparisons':comparisons,'all_depth_alpha_finite':True,'all_views_have_valid_depth':all(r['valid_count']>0 for r in rows),'camera_matches_COLMAP_and_checkpoints':True,'preview_limits':[0,4],'preview_clipped_valid_pixels':sum(r['valid_outside_preview_0_4'] for r in rows),'quality_scope':'training-view finite/coverage/visual diagnosis only; no depth GT accuracy,3D stability or heldout generalization proof','GT_used':False,'scientificdone':False}
    assert review['all_views_have_valid_depth'];atomic_json(aux/'DEPTH_REVIEW.json',review)
    provenance={'method_variant':'official_code_fix_v01','workflow':'depth_only_v01','scene':scene,'training_records':len(records),'final_gaussians':records[-1]['points'],'config_original_path':str(Path(config_path).resolve()),'config_sha256':sha256(config_path),'native_sha256':c['inputs']['native'],'source_commit':'2d4bc087f1b4bd62c96054fbe89d273490526b81','official_pointer_fix':'5f5cd3b0ecb329645bde45216fa826e9e85a7e1c','independent_fixes':'Jn/eigen conditioning/exact coefficient-conic VJP + zero-alpha quotient guard; see official_code_fix_v01 source/native manifests','source_manifest_path':str(O/'build/MANIFEST.json'),'source_manifest_sha256':sha256(O/'build/MANIFEST.json'),'environment_lock_path':str(O/'ENVIRONMENT_LOCK.json'),'environment_lock_sha256':sha256(O/'ENVIRONMENT_LOCK.json'),'training':{k:c[k] for k in ['wd','wn','iterations','regularization_from_iter','resolution_divisor','geometry_start_inclusive','optimizer_final_step']},'train_export_seals':{s:{'path':str(Path(c['state_dir'])/(s+'.seal.json')),'sha256':sha256(Path(c['state_dir'])/(s+'.seal.json'))} for s in ('train','export')},'immutable_source_NPZ_bytes':True}
    atomic_json(aux/'PROVENANCE.json',provenance)
    conventions={'schema':schema,'layout':'CHW, numpy float32; two complete depth fields plus raw alpha, original RGB/normal included unchanged','median_camera_z':'C24 rendered median affine camera-z, not ray distance','expected_camera_z':'C24 alpha-weighted depth divided by alpha; zero-support safe quotient; separate from median','unit':'author preprocessed training/COLMAP scene coordinate units; NOT asserted meters or mm; no metric conversion applied','extrinsic':'4x4 world-to-camera for column vectors [Xc,Yc,Zc,1]^T = E*[Xw,Yw,Zw,1]^T; x right,y down,z forward','intrinsic_pixel_centers':'K=[[fx,0,W/2],[0,fy,H/2],[0,0,1]], pixel coordinates(u+.5,v+.5). Equivalently integer-index centers use cx=(W-1)/2,cy=(H-1)/2','unprojection':'Xc=(u+.5-W/2)*z/fx; Yc=(v+.5-H/2)*z/fy; Zc=z. World point=inverse(E)*camera point. No scene rescaling.','validmask':'isfinite(z) & (z>0) & isfinite(alpha) & (alpha>=0.5), separate per depth field; no GT mask or RGB applied','unmodified_raw':'all raw depth pixels kept, including invalid pixels; PNG display masks do not alter NPZ','preview':'same [0,4] scene-unit color scale at15k and30k for every view; values outside range counted and retained raw; delta display[-.1,.1] is visualization only','checkpoint_position':'15k is after first C24 geometry update (inclusive15000);30k contains final forward, original C24 no final optimizer update','not_verified':'absolute metric depth accuracy,temporal/multiview3D stability,heldout NVS/generalization'}
    atomic_json(aux/'CAMERA_AND_DEPTH_CONVENTIONS.json',conventions)
    (aux/'README_ZH.md').write_text('本包保留两个checkpoint的全部原始NPZ字节，包含median_camera_z、expected_camera_z、alpha及原有RGB/normal。深度为float32的预处理场景单位，不是归一化PNG，也不能未经标定当米。valid_masks是额外文件，不更改原深度。相机与像素中心公式见CAMERA_AND_DEPTH_CONVENTIONS.json；来源见PROVENANCE.json；逐视图数值见DEPTH_REVIEW.json。训练视图诊断不证明GT深度精度或泛化。本交付不需要mesh/Chamfer。\n')
    for p in aux.iterdir():entries['metadata/'+p.name]=p
    for p in out.glob('*.png'):entries['previews/'+p.name]=p
    manifest={'scene':scene,'method_variant':'official_code_fix_v01','checkpoints':[15000,30000],'views_per_checkpoint':count,'raw_depth_arrays':count*4,'raw_npz_files':count*2,'files':{n:{'source_path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p)} for n,p in entries.items()},'no_mesh_or_GT_evaluation':True,'archive_format':'tar; contained NPZ already ZIP-compressed','scientificdone':False}
    atomic_json(out/'DEPTH_ONLY_MANIFEST.json',manifest);entries['DEPTH_ONLY_MANIFEST.json']=out/'DEPTH_ONLY_MANIFEST.json'
    sums=''.join(sha256(p)+'  '+n+'\n' for n,p in sorted(entries.items()));(out/'SHA256SUMS').write_text(sums);entries['SHA256SUMS']=out/'SHA256SUMS'
    archive=out/(scene+'_official_15k30k_raw_depth.tar');tmp=archive.with_suffix('.tar.partial')
    with tarfile.open(tmp,'w') as t:
        for name,path in sorted(entries.items()):t.add(path,arcname=name,recursive=False)
    os.replace(tmp,archive)
    with tarfile.open(archive) as t:
        assert len(t.getmembers())==len(entries)
        for member in t.getmembers():
            assert member.isfile() and member.name in entries and not member.name.startswith('/') and '..' not in Path(member.name).parts
            hh=hashlib.sha256()
            with t.extractfile(member) as f:
                for b in iter(lambda:f.read(8<<20),b''):hh.update(b)
            assert hh.hexdigest()==sha256(entries[member.name]),member.name
    receipt={'status':'PACKAGE_VERIFIED_NUMERIC_PASS_VISUAL_PENDING','scene':scene,'method_variant':'official_code_fix_v01','raw_npz_files':count*2,'views_per_checkpoint':count,'archive_path':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':sha256(archive),'manifest_path':str(out/'DEPTH_ONLY_MANIFEST.json'),'manifest_sha256':sha256(out/'DEPTH_ONLY_MANIFEST.json'),'safe_members_and_content_hashes_verified':True,'previews':[str(out/n) for n in ('DEPTH_15K_30K.png','ALPHA_VALIDITY.png','ALL_VIEWS_DEPTH.png')],'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scientificdone':False}
    atomic_json(out/'DELIVERY.json',receipt);(out/'ARCHIVE_SHA256SUMS').write_text(receipt['archive_sha256']+'  '+archive.name+'\n');print(receipt,flush=True)
    return receipt
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--output');args=a.parse_args();deliver(args.config,args.output)
