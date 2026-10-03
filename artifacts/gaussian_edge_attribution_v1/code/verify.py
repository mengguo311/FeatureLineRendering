"""Independent, CPU-only integrity/reference checks for frozen attribution.

These intentionally do not import the production evidence/attribution implementation.
Only original raw alpha*T values enter the reference projections.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import numpy as np


def sha256(path):
    digest=hashlib.sha256()
    with open(path,'rb') as handle:
        for block in iter(lambda: handle.read(8<<20),b''): digest.update(block)
    return digest.hexdigest()


def atomic_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    partial=path.with_suffix(path.suffix+'.partial')
    partial.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    os.replace(partial,path)


def audit_workspace(workspace,estimated_write_bytes=40<<30,reserve_bytes=1<<30):
    root=Path(workspace).resolve()
    def git(*args): return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
    expected=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/mic_fixed3d_standalone/.git').resolve()
    common=Path(git('rev-parse','--git-common-dir')); common=(root/common).resolve() if not common.is_absolute() else common.resolve()
    toplevel=Path(git('rev-parse','--show-toplevel')).resolve()
    branch=git('branch','--show-current')
    alternates=common/'objects/info/alternates'
    alternate_env=bool(os.environ.get('GIT_ALTERNATE_OBJECT_DIRECTORIES'))
    free=shutil.disk_usage(root).free
    checks={'workspace_root':toplevel==root,'common_git_dir':common==expected,'branch':branch=='gaussian-edge-attribution-v1',
            'no_alternates_file':not alternates.exists(),'no_alternates_environment':not alternate_env,
            'disk_reserve_plus_payload':free>estimated_write_bytes+reserve_bytes}
    result={'checks':checks,'ok':all(checks.values()),'workspace':str(root),'git_common_dir':str(common),
            'git_dir':git('rev-parse','--git-dir'),'branch':branch,'head':git('rev-parse','HEAD'),
            'free_bytes':free,'estimated_write_bytes':estimated_write_bytes,'required_reserve_bytes':reserve_bytes,
            'scope_note':'Read-only git introspection; no root/shared git config or refs written by this validator.'}
    if not result['ok']: raise ValueError(result)
    return result


def verify_seal(seal_path):
    path=Path(seal_path).resolve(); root=path.parent
    seal=json.loads(path.read_text()); hashes={}
    if not isinstance(seal.get('files'),dict): raise ValueError('seal missing files mapping')
    for name,expected in seal['files'].items():
        target=(root/name).resolve()
        if target!=root and root not in target.parents: raise ValueError('seal file escapes root')
        if not target.is_file(): raise ValueError('sealed file missing: '+name)
        digest=sha256(target)
        if digest!=expected: raise ValueError('sealed hash mismatch: '+name)
        hashes[name]=digest
    if 'context_sha256' in seal:
        context_digest=hashlib.sha256(json.dumps(seal['context'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        # Native transport uses canonical compact JSON. Refuse corruption.
        if context_digest!=seal['context_sha256']: raise ValueError('context hash mismatch')
    return {'ok':True,'seal_sha256':sha256(path),'verified_files':hashes}


def validate_camera(camera,expected_size=(800,800)):
    c=camera.get('camera',camera)
    if (c['native_width'],c['native_height'])!=tuple(expected_size): raise ValueError('unexpected camera dimensions')
    w2c=np.asarray(c['w2c'],dtype=np.float64); k=np.asarray(c['native_K'],dtype=np.float64)
    if w2c.shape!=(4,4) or k.shape!=(3,3): raise ValueError('invalid camera matrix shape')
    if not np.isfinite(w2c).all() or not np.isfinite(k).all(): raise ValueError('nonfinite camera')
    if not np.allclose(w2c[3],[0,0,0,1],atol=1e-8): raise ValueError('invalid homogeneous camera row')
    if abs(np.linalg.det(w2c[:3,:3])-1)>1e-5: raise ValueError('camera rotation not proper')
    if not np.allclose(w2c[:3,:3]@w2c[:3,:3].T,np.eye(3),atol=1e-5): raise ValueError('nonorthonormal camera rotation')
    if k[0,0]<=0 or k[1,1]<=0 or abs(k[2,2]-1)>1e-8: raise ValueError('invalid intrinsics')
    return True


def _check_weights(ids,weights,count):
    ids=np.asarray(ids); weights=np.asarray(weights,dtype=np.float64)
    if ids.shape!=weights.shape or ids.ndim<2: raise ValueError('ID/weight shape mismatch')
    if ids.dtype.kind not in 'iu' or np.any(ids < -1) or np.any(ids>=count): raise ValueError('invalid original IDs')
    if not np.isfinite(weights).all() or np.any(weights<0) or np.any(weights[ids<0]!=0): raise ValueError('invalid raw contribution weights')
    return ids,weights


def reference_projection(ids,weights,scores):
    """Explicit slot loop, arbitrary K, no weight renormalization/recompositing."""
    scores=np.asarray(scores,dtype=np.float64)
    ids,weights=_check_weights(ids,weights,len(scores))
    if not np.isfinite(scores).all(): raise ValueError('nonfinite scores')
    result=np.zeros(ids.shape[:-1],dtype=np.float64)
    for slot in range(ids.shape[-1]):
        live=ids[...,slot]>=0
        result[live]+=weights[...,slot][live]*scores[ids[...,slot][live]]
    return result


def reference_id_statistics(ids,weights,evidence,sample_ids):
    """Independent O(sample IDs × pixels) reference, all pixels in denominator."""
    ids=np.asarray(ids); weights=np.asarray(weights,dtype=np.float64); evidence=np.asarray(evidence,dtype=np.float64)
    if ids.shape!=weights.shape or evidence.shape!=ids.shape[:-1]: raise ValueError('reference shape mismatch')
    sample_ids=np.asarray(sample_ids,dtype=np.int64)
    numerator=np.zeros(len(sample_ids)); denominator=np.zeros(len(sample_ids))
    flat_ids=ids.ravel();flat_weights=weights.ravel();flat_evidence=evidence.ravel();slots=ids.shape[-1]
    for j,gaussian_id in enumerate(sample_ids):
        positions=np.flatnonzero(flat_ids==gaussian_id)
        local_weights=flat_weights[positions]
        denominator[j]=local_weights.sum(dtype=np.float64)
        numerator[j]=(local_weights*flat_evidence[positions//slots]).sum(dtype=np.float64)
    score=np.divide(numerator,denominator,out=np.zeros_like(numerator),where=denominator>0)
    return dict(ids=sample_ids,numerator=numerator,denominator=denominator,negative=denominator-numerator,
                score=score,unknown=denominator==0)


def verify_projection_samples(raw,projection,scores,selected_masks,sample_seed=1729,sample_count=512,tolerance=2e-6):
    """Check cached P/Q with direct raw alpha*T; also bound full projections."""
    ids=raw['topk_id']; weights=raw['topk_w']; h,w=ids.shape[:2]
    rng=np.random.default_rng(sample_seed); flat=rng.choice(h*w,size=min(sample_count,h*w),replace=False)
    yy,xx=np.unravel_index(flat,(h,w)); id_sample=ids[yy,xx]; weight_sample=weights[yy,xx]
    checks={}; details={}
    for name,values in scores.items():
        expected=reference_projection(id_sample,weight_sample,values)
        key='top4_'+name if 'top4_'+name in projection else name
        actual=np.asarray(projection[key])[yy,xx]
        err=float(np.max(np.abs(actual-expected),initial=0)); checks[key]=err<=tolerance
        details[key]={'max_absolute_error':err,'samples':len(flat)}
        if key.startswith('top4_') and name in projection:
            deficit=float(np.max(expected-np.asarray(projection[name])[yy,xx],initial=0))
            checks[name+'_full_at_least_top4']=deficit<=tolerance
            details[name+'_full_at_least_top4']={'max_deficit':deficit}
    for name,mask in selected_masks.items():
        if name not in projection and 'top4_'+name not in projection: continue
        expected=reference_projection(id_sample,weight_sample,np.asarray(mask,dtype=np.float64))
        key='top4_'+name if 'top4_'+name in projection else name
        if key==name and 'top4_baseline_P' in projection:
            deficit=float(np.max(expected-np.asarray(projection[key])[yy,xx],initial=0))
            checks[key+'_bound']=deficit<=tolerance; details[key]={'max_deficit':deficit}
        else:
            err=float(np.max(np.abs(np.asarray(projection[key])[yy,xx]-expected),initial=0))
            checks[key]=err<=tolerance; details[key]={'max_absolute_error':err}
    return {'ok':all(checks.values()),'checks':checks,'details':details,'sample_seed':sample_seed,
            'pixel_yx':np.stack([yy,xx],axis=-1).tolist(),'reference':'original raw alpha*T, independent explicit slot loop'}
