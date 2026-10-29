from pilotio import *

def audit():
    guard(); status('M0_RUNNING')
    lock=json.loads((ORCH/'INPUT_LOCK.json').read_text()); verified={}
    for p,want in lock['files'].items():
        got=sha(p); verified[p]=dict(expected=want,actual=got,match=got==want)
        if got!=want:
            js(OUT/'input_hash_audit.json',verified); raise AssertionError('INPUT_HASH_MISMATCH '+p)
    js(OUT/'input_hash_audit.json',verified)
    registry=json.loads((BASE/'REGISTRY.json').read_text())['scenes']; summary={}
    for scene,entry in lock['scenes'].items():
        root=Path(entry['full']); a=load_np(root/'gaussians.npz'); s=load_np(root/'SHARED_CONTROL_AND_SAMPLING.npz')
        obs=load_np(root/'OBSERVATIONS.npz'); mapping=load_np(root/'OBSERVATION_TO_PARENT.npz')
        parents=json.loads((root/'parents.json').read_text()); local=s['control'][s['control_index']]
        rec=(local*s['basis'][:,:,None]).sum(1); error=float(abs(rec-a['means']).max())
        assert error<=1e-10*max(1,float(abs(a['means']).max())),(scene,error)
        deriv=(local*s['derivative_basis'][:,:,None]).sum(1); tangent=unit(deriv)
        uv_error=[]; angles=[]; view_counts=[]; control_obs=np.full(len(s['control']),-1,np.int64)
        control_parent=np.full(len(s['control']),-1,np.int32)
        for i,p in enumerate(parents):
            start,end=s['parent_control_offsets'][i]; P=s['control'][start:end]; uv=np.asarray(p['uv'])[:len(P)]
            proj,z=project(P,p['camera']); uv_error.extend(np.linalg.norm(proj-uv,axis=1))
            assert np.all(z>0)
            assert np.allclose(P,np.asarray(p['control'])[:len(P)],atol=1e-12,rtol=0)
            ids=np.asarray(p['observation_ids'])[:len(P)]; control_obs[start:end]=ids; control_parent[start:end]=i
            assert np.array_equal(obs['uv'][ids],uv)
            assert np.all(obs['view_index'][ids]==list(obs['view_names']).index(p['view']))
            view_counts.append(len(p['source_views']))
            # Project the geometric segment tangent at its midpoint through the perspective Jacobian.
            if len(P)>1:
                E=np.asarray(p['camera']['extrinsic']); mid=(P[:-1]+P[1:])/2; q=mid@E[:3,:3].T+E[:3,3]
                d=np.diff(P,axis=0)@E[:3,:3].T; c=p['camera']
                v=np.c_[c['fx']*(d[:,0]*q[:,2]-q[:,0]*d[:,2]),c['fy']*(d[:,1]*q[:,2]-q[:,1]*d[:,2])]
                valid=(np.linalg.norm(v,axis=1)>1e-20)&(np.linalg.norm(np.diff(uv,axis=0),axis=1)>0)
                cos=np.abs((unit(v[valid])*unit(np.diff(uv,axis=0)[valid])).sum(1))
                angles.extend(np.degrees(np.arccos(np.clip(cos,-1,1))))
        assert max(uv_error)<=1e-6,(scene,max(uv_error))
        same=(a['primitive_id'][1:]==a['primitive_id'][:-1])&(a['internal_piece_id'][1:]==a['internal_piece_id'][:-1])
        spacing=np.linalg.norm(np.diff(a['means'],axis=0),axis=1); reliable=same&(spacing>1e-14)&np.isfinite(spacing)
        h=float(np.median(spacing[reliable])); assert h>0
        center=np.median(a['means'],axis=0)
        duplicate=len(a['means'])-len(np.unique(np.round((a['means']-center)/h,6),axis=0))
        sample_obs=control_obs[s['control_index']]
        d=OUT/'audit'/scene; d.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(d/'line_samples.npz',sample_id=np.arange(len(rec),dtype=np.int64),line_gaussian_id=np.arange(len(rec),dtype=np.int64),xyz=rec,tangent=tangent,parent_id=a['primitive_id'],piece_id=a['internal_piece_id'],arc_t=a['arc_t'],control_index=s['control_index'],basis=s['basis'],observation_end_ids=sample_obs,source_gaussian_id=np.full(len(rec),-1,np.int64),confidence=np.ones(len(rec)),confidence_known=np.zeros(len(rec),bool),tangent_confidence_calibrated=np.zeros(len(rec),bool))
        js(d/'cameras.json',registry[scene]['cameras'])
        js(d/'normalization.json',dict(center=center,scale=h,forward='(xyz-center)/h',inverse='normalized*h+center',units='original scene units, not meters'))
        summary[scene]=dict(line_gaussians=len(rec),controls=len(s['control']),parents=len(parents),observations=len(obs['uv']),mapped_observation_rows=len(mapping['observation_id']),unique_mapped_observations=len(np.unique(mapping['observation_id'])),means_max_abs_error=error,reprojection_pixel=quant(uv_error),projected_tangent_degrees=quant(angles),h=h,h_definition='median nonzero adjacent line-Gaussian spacing within ordered parent and piece',spacing=quant(spacing[reliable]),duplicate_xyz_quantized_1e6h_count=duplicate,actual_source_view_histogram={str(k):view_counts.count(k) for k in sorted(set(view_counts))},source_GS_association='UNKNOWN; -1 sentinel, distinct namespace',confidence='UNKNOWN; neutral weight 1, not inferred from GS opacity',tangent='derived from ordered optimized controls; calibration UNKNOWN',all_samples_exported=True,omitted_samples=0)
        js(OUT/'input_audit.json',summary); status('M0_SCENE_DONE',scene=scene,n=len(rec))
    js(OUT/'manifest.json',dict(decision_sha256=sha(OUT/'DECISION.json'),input_lock_sha256=sha(ORCH/'INPUT_LOCK.json'),config_sha256=sha(CODE/'config.json'),code_base='a25b78758716debb2e55841d305389d564187576',literature=json.loads((ORCH/'LITERATURE_PROVENANCE.json').read_text()),claim='fixed-fused-input postprocessing',no_original_GS_ownership=True,not_run=CFG['not_run']))
    shutil.copyfile(CODE/'config.json',OUT/'config.json')
    status('M0_DONE',scenes=list(summary))
if __name__=='__main__': audit()
