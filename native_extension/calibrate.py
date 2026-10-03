"""Fixed F1/F41 native calibration and bounded top32 export after protocol seal."""
from pathlib import Path
import hashlib,json,sys,os,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/gaussian_edge_attribution_v1';OUT=ROOT/'native_extension'
sys.path.insert(0,str(ART/'code'))
from native_attributes import NativeAttributeRenderer,atomic_json,sha256
SEAL=ART/'PROTOCOL_SEAL.json'
EXPECTED_SEAL='171c0b88f4eb8276bbbb97a2e025c68e4f40df81f9535bd722ef86107c000edf'
CACHE=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/transport/raw/mic')
def check(a,b,atol,label):
    a=np.asarray(a);b=np.asarray(b)
    if a.shape!=b.shape:raise ValueError('Calibration shape mismatch '+label)
    delta=float(np.max(np.abs(a.astype(np.float64)-b.astype(np.float64)),initial=0))
    if delta>atol:raise ValueError('Calibration mismatch '+label+': '+str(delta))
    return delta
def main():
    if sha256(SEAL)!=EXPECTED_SEAL:raise ValueError('Protocol seal is missing/changed')
    q=json.loads((CACHE/'F_001/checkpoint_qualification.json').read_text())
    r4=NativeAttributeRenderer(q['path'],q['sha256'],OUT/'calibration_logs')
    summary=dict(protocol_seal_sha256=EXPECTED_SEAL,keys=['F_001','F_041'],read_scope='F only, no C pixels',rows=[],full_projection='full native traversal, top4-trained fields remain top4 estimates',top32='larger truncated contributor list; not complete contributor ground truth')
    build=json.loads((OUT/'BUILD_TOP32.json').read_text())
    if build.get('returncode')!=0:raise ValueError('Top32 build unavailable')
    r32=NativeAttributeRenderer(q['path'],q['sha256'],OUT/'calibration_logs',library=build['library'],library_sha256=build['library_sha256'],topk=32)
    for key in summary['keys']:
        cam=json.loads((CACHE/key/'camera.json').read_text())
        if 'camera' in cam:cam=cam['camera']
        raw=np.load(CACHE/key/'native.npz')
        native=r4.render_rgb(cam,export_topk=True)
        row=dict(key=key,cache_comparison={})
        for field in ('rgb','alpha','depth','median_depth','topk_id','topk_w','topk_depth'):
            row['cache_comparison'][field]=check(native[field],raw[field],0 if field=='topk_id' else (3e-5 if 'depth' in field else 3e-6),field)
        n=len(r4.g['mu']);fields=np.zeros((n,3),np.float32);fields[:,0]=1.;fields[:,1]=(np.arange(n)%17==0);fields[:,2]=np.arange(n,dtype=np.float32)/max(n-1,1)
        attrs=r4.render_attributes(cam,fields)
        row['attributes_allones_alpha_max_abs']=check(attrs['rgb'][:,:,0],native['alpha'],3e-6,'allones alpha')
        row['attributes_original_alpha_max_abs']=check(attrs['alpha'],native['alpha'],0,'original alpha')
        row['attributes_original_depth_max_abs']=check(attrs['depth'],native['depth'],0,'original depth')
        top32=r32.render_rgb(cam,export_topk=True)
        row['top32_calibration']={}
        for field in ('rgb','alpha','depth','median_depth'):
            row['top32_calibration'][field]=check(top32[field],native[field],3e-5 if 'depth' in field else 3e-6,'top32 '+field)
        for field in ('topk_id','topk_w','topk_depth'):
            row['top32_calibration'][field+'_first4']=check(top32[field][...,:4],native[field],0 if field=='topk_id' else 3e-6,'top32 '+field)
        a=top32['alpha'];fg=a>.05
        cov={}
        for k in (4,16,32):
            mass=top32['topk_w'][...,:k].sum(-1);ratio=mass[fg]/a[fg]
            cov[str(k)]=dict(foreground_pixels=int(fg.sum()),captured_mass_fraction=float(mass[fg].sum()/a[fg].sum()),perpixel_mean=float(ratio.mean()),p05=float(np.quantile(ratio,.05)),min=float(ratio.min()),omitted_mass_sum=float(np.maximum(a-mass,0).sum()))
        row['coverage']=cov
        sampled=np.zeros_like(a,dtype=bool);sampled[4::16,4::16]=True
        row['uniform_grid']=dict(offset_xy=[4,4],stride=16,count=int(sampled.sum()),foreground_count=int((sampled&fg).sum()),top4_mass_fraction=float(top32['topk_w'][sampled,:4].sum()/np.maximum(a[sampled].sum(),1e-12)),top32_mass_fraction=float(top32['topk_w'][sampled].sum()/np.maximum(a[sampled].sum(),1e-12)))
        ids=top32['topk_id'];ws=top32['topk_w'];gather=fields[np.maximum(ids,0)]*(ids>=0)[...,None]
        reconstruction=(ws[...,None]*gather).sum(2)
        omit=np.maximum(a-ws.sum(-1),0)
        row['attribute_vs_top32_bound_max_excess']=float(np.max(np.abs(attrs['rgb']-reconstruction)-omit[...,None]))
        if row['attribute_vs_top32_bound_max_excess']>5e-6:raise ValueError('Full attribute reconstruction omitted-mass bound failed')
        p=OUT/(key+'_top32.npz');tmp=OUT/(key+'_top32.partial.npz')
        np.savez_compressed(tmp,**{k:top32[k] for k in ('rgb','alpha','depth','median_depth','topk_id','topk_w','topk_depth')});os.replace(tmp,p)
        row.update(top32_path=str(p),top32_sha256=sha256(p),full_attribute_unit_fields_sha256=hashlib.sha256(fields.tobytes()).hexdigest())
        summary['rows'].append(row);atomic_json(ART/'research/NATIVE_CALIBRATION.json',summary)
        print(key,json.dumps(row['coverage']),flush=True)
    summary.update(status='PASS',renderer=r4.metadata,top32_build=build)
    atomic_json(ART/'research/NATIVE_CALIBRATION.json',summary)
    print('GPU_RELEASED calibration complete',flush=True)
if __name__=='__main__':main()
