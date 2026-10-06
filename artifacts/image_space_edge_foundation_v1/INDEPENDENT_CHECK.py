"""CPU post-production audit. No detector/score is used to certify semantics."""
import hashlib,json,os,re,struct,subprocess,sys,time
from pathlib import Path
import numpy as np
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/image_space_edge_foundation_v1/src'))
from runtime import ART,OUT,DATA_PATH,PRIOR_PATH,sha,atomic_json,source_hashes,guard
from presentation import ffmpeg

def run():
    checks=0;failures=[];records=[]
    def check(value,name):
        nonlocal checks
        checks+=1
        if not value:failures.append(name)
    guard('independent_CPU_audit')
    freeze=json.loads((ART/'PRODUCTION_FREEZE.json').read_text())
    check(source_hashes()==freeze['source_hashes'],'production_sources_immutable')
    sealcount=0;sealedfiles=0
    for p in sorted((ART/'seals').glob('*.json')):
        s=json.loads(p.read_text());sealcount+=1
        for filename,h in s['outputs'].items():
            check((ROOT/filename).exists() and sha(ROOT/filename)==h,'seal:'+filename);sealedfiles+=1
    before=json.loads((OUT/'BASELINE_BEFORE.json').read_text());changed=[]
    for filename,h in before['hashes'].items():
        equal=Path(filename).is_file() and sha(filename)==h
        check(equal,'protected:'+Path(filename).name)
        if not equal:changed.append(Path(filename).name)
    prior=json.loads(PRIOR_PATH.read_text());prior_mismatch=[]
    for filename,h in prior['protected_sha256'].items():
        p=Path(filename);p=p if p.is_absolute() else ROOT/p
        equal=p.is_file() and sha(p)==h;check(equal,'prior_baseline:'+p.name)
        if not equal:prior_mismatch.append(p.name)
    heads=dict(l.split(' ',1) for l in subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],cwd=ROOT,text=True).splitlines())
    target='refs/heads/image-space-edge-foundation-v1'
    oldheads={k:v for k,v in before['heads'].items() if k!=target}
    check(all(heads.get(k)==v for k,v in oldheads.items()),'old_branch_heads_unchanged')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    check(branch=='image-space-edge-foundation-v1','exact_branch')
    check(sha(DATA_PATH)==freeze['data_freeze_sha256'],'data_freeze_unchanged')
    nativeframes=0;native_unique={};model_hashes={}
    data=json.loads(DATA_PATH.read_text())
    for scene,s in freeze['scenes'].items():
        model_hashes[scene]=sha(data['scenes'][scene]['model']);check(model_hashes[scene]==s['model_sha256'],'model:'+scene)
        for role,views in s['groups'].items():
            images=[]
            for v in views:
                p=OUT/'raw'/scene/role/v['key'];z=np.load(p/'native.npz');rgb=z['rgb'];a=z['alpha']
                nativeframes+=1;check(rgb.shape==(800,800,3),'native_shape:'+scene+'/'+role+'/'+v['key'])
                check(np.isfinite(rgb).all() and np.isfinite(a).all(),'native_finite:'+scene+'/'+v['key'])
                saved=np.asarray(Image.open(p/'native.png'));expected=np.round(np.clip(rgb,0,1)*255).astype(np.uint8)
                check(np.array_equal(saved,expected),'native_png_exact:'+scene+'/'+role+'/'+v['key'])
                images.append(hashlib.sha256(rgb.tobytes()).hexdigest())
            native_unique[scene+'/'+role]=len(set(images));check(len(set(images))==len(views),'actual_distinct_RGB:'+scene+'/'+role)
        fixed=json.loads((ART/'results'/f'{scene}_fixed_spatial.json').read_text())
        for v in s['groups']['fixed']:
            key=v['key'];directory=OUT/'fixed_fields'/scene/key
            f=np.load(directory/'fields.npz');p=np.load(directory/'profiles.npz');z=np.load(OUT/'raw'/scene/'fixed'/key/'native.npz')
            check(np.array_equal(f['union'],np.maximum(f['detail'],f['structural'])),'detail_not_hidden:'+scene+'/'+key)
            check(np.allclose(np.sum(f['normal']**2,2),1,atol=3e-6),'unit_screen_normal:'+scene+'/'+key)
            for name in ['raw','detail','structural','union','unknown','confidence','profile_confidence']:
                a=f[name];check(np.isfinite(a).all() and a.min()>=-1e-6 and a.max()<=1.000001,'field_range:'+scene+'/'+key+'/'+name)
            check(np.allclose(p['plus']-p['minus'],p['signed_contrast'],atol=1e-7),'two_sided_signed_contrast:'+scene+'/'+key)
            valid=p['valid'];res=p['residual'][valid]
            check(np.all(res<=freeze['config']['residual_max']),'bounded_fit_residual:'+scene+'/'+key)
            paths=json.loads((directory/'chains.json').read_text())['chains']
            measured=0.
            for c in paths:
                xy=np.asarray(c['xy']);length=np.linalg.norm(np.diff(xy,axis=0),axis=1).sum();measured+=length
                check(abs(length-c['arc_length'])<1e-7,'chain_native_arc_length:'+scene+'/'+key)
            candidates=np.load(directory/'rgb_controls.npz')
            controls=np.load(OUT/'guarded_RGB_v2'/scene/'fixed'/(key+'.npz'));rgb=controls['original']
            check(np.array_equal(rgb,candidates['original']),'guard_original_unchanged:'+scene+'/'+key)
            check(np.array_equal(controls['alpha'],z['alpha']),'alpha_unchanged:'+scene+'/'+key)
            for arm in ['sharpen','soften']:
                out=controls[arm];band=controls[arm+'_band'];diff=abs(out-rgb)
                check(np.array_equal(out[~band],rgb[~band]),'exact_outside_band:'+scene+'/'+key+'/'+arm)
                check(float(diff.max())<=.080001,'bounded_RGB_delta:'+scene+'/'+key+'/'+arm)
                newly=((out<0)|(out>1))&~((rgb<0)|(rgb>1))
                raw_newly=((candidates[arm]<0)|(candidates[arm]>1))&~((rgb<0)|(rgb>1))
                check(not newly.any(),'no_new_clipping:'+scene+'/'+key+'/'+arm)
                check(not band[z['alpha']<.995].any(),'foreground_only_control:'+scene+'/'+key+'/'+arm)
                check(float(diff[f['raw']<.02].max(initial=0))==0.,'nonedge_exact:'+scene+'/'+key+'/'+arm)
                records.append(dict(scene=scene,key=key,arm=arm,max_delta=float(diff.max()),outside_max=float(diff[~band].max(initial=0)),
                                    changed_pixels=int(np.any(diff>0,2).sum()),nonedge_max_delta=float(diff[f['raw']<.02].max(initial=0)),
                                    alpha_byte_equal=True,new_clipped_values=int(newly.sum()),raw_candidate_new_clipped_values=int(raw_newly.sum())))
            public=np.load(ART/'media'/scene/'fixed'/key/'raw_fields.npz')
            for name in public.files:check(np.array_equal(public[name],f[name].astype(public[name].dtype)),'public_field_exact:'+scene+'/'+key+'/'+name)
        for v in s['groups']['arc']:
            key=v['key'];f=np.load(OUT/'arc_fields'/scene/key/'fields.npz');t=np.load(OUT/'temporal'/scene/(key+'.npz'))
            check(np.array_equal(f['union'],t['spatial']),'same_spatial_OFF_ON:'+scene+'/'+key)
            check(not np.any((t['spatial']==0)&(t['temporal']!=0)),'death_resets:'+scene+'/'+key)
            check(abs(t['temporal']-t['spatial']).max()<=.120001,'temporal_clamp:'+scene+'/'+key)
    videos=[]
    for scene in ['lego','chair']:
        result=json.loads((ART/'results'/f'{scene}_arc_media.json').read_text())
        for video in result['videos']:
            path=ROOT/video['path'];ff=ffmpeg()
            info=subprocess.run([ff,'-hide_banner','-i',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stderr
            check('Video: h264' in info and 'yuv420p' in info,'actual_H264_yuv420p:'+video['path'])
            proc=subprocess.Popen([ff,'-v','error','-threads','2','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
            nbytes=video['width']*video['height']*3;hashes=[];orig_hashes=[];errors=[];i=0
            while True:
                buf=bytearray()
                while len(buf)<nbytes:
                    b=proc.stdout.read(nbytes-len(buf))
                    if not b:break
                    buf.extend(b)
                if not buf:break
                check(len(buf)==nbytes,'decode_complete_frame:'+scene)
                if len(buf)!=nbytes:break
                hashes.append(hashlib.sha256(buf).hexdigest())
                frame=np.frombuffer(buf,np.uint8).reshape(video['height'],video['width'],3)
                original=frame[44:844,:800];orig_hashes.append(hashlib.sha256(original.tobytes()).hexdigest())
                source=np.asarray(Image.open(OUT/'raw'/scene/'arc'/f'arc0_{i:03d}'/'native.png'))
                mse=float(np.mean((original.astype(np.float32)/255-source.astype(np.float32)/255)**2));errors.append(mse)
                check(mse<.001,'decoded_actual_native_RGB:'+scene+'/'+str(i));i+=1
            check(proc.wait()==0,'decode_exit:'+scene)
            check(len(hashes)==33 and len(set(hashes))==33 and len(set(orig_hashes))==33,'all33_actual_distinct:'+video['path'])
            check(hashes==video['decoded_sha256'],'independent_video_decode_hashes:'+video['path'])
            blob=path.read_bytes();pos=0;boxes=[]
            while pos+8<=len(blob):
                size,kind=struct.unpack('>I4s',blob[pos:pos+8]);size=int(size)
                if size==1:size=struct.unpack('>Q',blob[pos+8:pos+16])[0]
                if size==0:size=len(blob)-pos
                boxes.append(kind.decode(errors='replace'))
                if size<8:break
                pos+=size
            check('moov' in boxes and boxes.index('moov')<boxes.index('mdat'),'actual_faststart:'+video['path'])
            videos.append(dict(path=video['path'],decoded_frames=len(hashes),distinct_RGB_without_labels=len(set(orig_hashes)),max_native_RGB_MSE=max(errors),codec='H264',pixel_format='yuv420p',faststart=True))
    synth=json.loads((ART/'results/synthetic.json').read_text())
    for row in synth['moving_disocclusion']:
        check(row['zero_evidence_ghosts']==0,'constructed_moving_death:'+str(row['frame']))
        check(row['ghost_mass_outside_truth_3px']<.01,'constructed_moving_ghost:'+str(row['frame']))
    for name in ['width','color_step']:
        z=np.load(OUT/'anchored_synthetic'/(name+'.npz'));im=z['original'];minus=im[64,0];plus=im[64,-1];delta=plus-minus
        def width(a):
            row=a[64];t=(row-minus)@delta/(delta@delta);x=np.arange(len(row))
            return float(np.interp(.9,t,x)-np.interp(.1,t,x))
        widths={k:width(z[k]) for k in ['original','sharpen','soften']}
        check(widths['sharpen']<widths['original']<widths['soften'],'independent_known_width:'+name)
        for arm in ['sharpen','soften']:
            row=z[arm][64];fraction=(row-minus)@delta/(delta@delta)
            check(np.diff(fraction).min()>=-1e-6,'no_transition_ringing:'+name+'/'+arm)
            check(fraction.min()>=-1e-6 and fraction.max()<=1.000001,'no_plateau_overshoot:'+name+'/'+arm)
            check(np.array_equal(z[arm][~z[arm+'_band']],im[~z[arm+'_band']]),'synthetic_outside_exact:'+name+'/'+arm)
    outcome=dict(status='PASS' if not failures else 'FAIL',checks=checks,failures=failures,seal_units=sealcount,sealed_files=sealedfiles,
                 protected_files=len(before['hashes']),protected_changes=changed,prior_freeze_mismatches=prior_mismatch,old_branch_heads_unchanged=True,
                 model_sha256_after=model_hashes,native_input_frames=nativeframes,native_unique_by_scene_role=native_unique,videos=videos,
                 raw_candidate_control_status='FAIL' if any(r['raw_candidate_new_clipped_values'] for r in records) else 'PASS',
                 guarded_control_status='PASS' if not any(r['new_clipped_values'] for r in records) else 'FAIL',
                 RGB_control_guards=records,scope='independent CPU integrity/interface/media audit; not human semantic or visual science GO')
    atomic_json(ART/'tests/INDEPENDENT_AUDIT.json',outcome)
    print(json.dumps({k:v for k,v in outcome.items() if k not in ['RGB_control_guards','native_unique_by_scene_role']},indent=2))
    if failures:raise SystemExit(1)
if __name__=='__main__':run()
