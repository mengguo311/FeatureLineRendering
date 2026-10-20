"""Frozen exact shared-edge ties; unchanged candidate and attachment adapter."""
import round009_common as c
import argparse
import copy
import importlib.metadata
import json
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import core
import mesh_attachment as adapter
import patch_fixture as oracle
import coverage_fixture as old_oracle
import visibility_primitive as candidate
import run_round008 as prior
from visibility_trial import depth_check

P = json.loads((c.D/'PROTOCOL.json').read_text())
TESTS = ['INHERITED_ATTACHMENT','INHERITED_PATCH','INHERITED_CANDIDATE',
         'INHERITED_ORACLE','INHERITED_TEMPORAL','INHERITED_STAGE']
NEW = ['round009_common.py','round009_receipt.py','run_round009.py','seal_round009.py']


def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    verification=c.verify_prior();c.write(c.R/'PRIOR_SEAL_VERIFY.json',verification)
    old=json.loads((c.W/'docs/partwise_sketch_hatching/round_008/ASSET_LOCK.json').read_text())
    for path,h in old['sources'].items():assert c.sha(c.W/path)==h,path
    for name,key in [('visibility_primitive.py','candidate_source_sha256'),('mesh_attachment.py','adapter_source_sha256')]:
        assert c.sha(c.W/'experiments/partwise_sketch_hatching'/name)==P[key]
    paths={c.W/p for p in old['sources']}
    paths|={c.W/'experiments/partwise_sketch_hatching'/n for n in NEW}
    paths|={p for p in c.D.iterdir() if p.is_file()}
    paths|={c.W/'docs/partwise_sketch_hatching/round_008'/n for n in ['ASSET_LOCK.json','REPORT_ZH.md','REPRODUCE.md']}
    inputs=[c.P/n for n in ['STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json','metrics.json','REGRESSION.json','VALIDATION.json']]
    c.write(c.D/'ASSET_LOCK.json',{'protocol_commit':'583f3896',
        'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),
        'sources':{str(p.relative_to(c.W)):c.sha(p) for p in sorted(paths)},
        'inputs':{str(p):c.sha(p) for p in inputs},'prior_seal':verification,
        'resources':c.resources(),'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','Pillow']}})
    c.status('source_locked_awaiting_acceptance')
    print(json.dumps({'frozen_cases':len(P['cases']),'prior':verification}),flush=True)


def depth_ok(a,b):
    d=depth_check(a,b)
    return d, bool(d['finite_masks_equal'] and d['max_abs_error'] is not None and d['max_abs_error']<=P['oracle']['depth_epsilon'])


def assess(a):
    """Array-based gates reused by deliberate evidence corruptions."""
    expected=a['expected_tie_mask'];actual=a['oracle_dual_mask'];foot=a['reference_expanded']>0
    tied=expected&foot
    checks={
        'exact_analytic_tie_mask':bool(np.array_equal(actual,expected) and expected.sum()==65),
        'exact_analytic_equal_depth':bool(np.array_equal(a['oracle_owner_faces_depth'][:,expected],np.full((2,65),4.))),
        'nonempty_footprint_ties':bool(tied.any()),
        'both_single_faces_exact_at_all_ties':bool(np.array_equal(a['single_face_depths'],np.full((2,65),4.))),
        'combined_exact_at_all_ties':bool(np.array_equal(a['joint_tie_depth'],np.full(65,4.))),
        'pre_z_exact':bool(np.array_equal(a['candidate_pre_z'],a['reference_pre_z'])),
        'footprint_exact':bool(np.array_equal(a['candidate_footprint'],a['reference_expanded'])),
        'matched_high_exact':bool(np.array_equal(a['candidate_high'],a['matched_reference'])),
        'matched_final_exact':bool(np.array_equal(a['candidate_final_uint8'],a['matched_final_uint8'])),
        'all_footprint_ties_retained':bool(np.all(a['candidate_gate'][tied]) and np.all(a['candidate_high'][tied]==P['primitive']['ink'])),
        'scene_parts_exact':bool(np.array_equal(a['candidate_scene_owner'],a['oracle_part'])),
    }
    checks['scene_depth_valid']=depth_ok(a['candidate_scene_depth'],a['oracle_scene'])[1]
    checks['owner_depth_valid']=depth_ok(a['candidate_owner_depth'][foot],a['oracle_owner'][foot])[1]
    for variant in ['reverse_owners','reverse_faces','reverse_both']:
        for key in ['high','final_uint8','gate','owner_depth','scene_depth','scene_owner']:
            checks[variant+'_'+key+'_exact']=bool(np.array_equal(a[variant+'_'+key],a['candidate_'+key]))
    return checks


def evaluate_case(spec):
    g=P['geometry'];pp=P['primitive'];cam=old_oracle.camera(P)
    mesh=core.finalize_mesh(g['vertices'],g['faces'],g['parts'])
    path=np.array(spec['path'],float);owners=list(g['owners']);segments=list(spec['segment_faces'])
    original=(mesh,owners,segments,path);before=prior.fingerprint(original)
    att=adapter.validate_attachment(*original)['diagnostics']
    independent_att=oracle.validate_attachment(path,segments,g['analytic_faces'],g['shared_edge'])
    yy,xx=np.mgrid[:cam['size'],:cam['size']];grid=np.stack((xx,yy),axis=-1)
    truth=oracle.truth(grid,g['analytic_faces'],[],cam)
    pre,expanded,*_=oracle.raw_footprint(path,cam,pp)
    expected=np.zeros(pre.shape,bool);tie=P['exact_ties'];lo,hi=tie['high_columns_inclusive']
    expected[tie['high_row'],lo:hi+1]=True
    dual=np.isfinite(truth['owner_faces_depth']).all(axis=0)
    reference=expanded*truth['visible'];final=old_oracle.down(reference,P['camera']['supersample'])
    a={**{'oracle_'+k:v for k,v in truth.items()},'reference_pre_z':pre,'reference_expanded':expanded,
       'matched_reference':reference,'matched_final_uint8':final,'expected_tie_mask':expected,
       'oracle_dual_mask':dual,'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],
       'mesh_parts':mesh['parts'],'stroke_path':path,'segment_faces':np.array(segments)}
    variants={};errors={};identities={}
    for name,reverse_faces,reverse_owners in [('candidate',False,False),('reverse_owners',False,True),('reverse_faces',True,False),('reverse_both',True,True)]:
        m=core.finalize_mesh(mesh['vertices'],mesh['faces'][::-1],mesh['parts'][::-1]) if reverse_faces else mesh
        o=[1-i for i in owners] if reverse_faces else owners.copy()
        s=[1-i for i in segments] if reverse_faces else segments.copy()
        if reverse_owners:o=o[::-1]
        fingerprint=prior.fingerprint((m,o,s,path))
        try:
            result=adapter.render_validated(m,o,s,path,candidate.render,cam,pp['ink'],P['camera']['supersample'],pp['high_width_filter_size'],pp['dense_step_high_px'],pp['depth_tolerance_world'])
            variants[name]=result;a.update({name+'_'+k:v for k,v in result.items()})
        except Exception as exc:errors[name]=type(exc).__name__+': '+str(exc)
        identities[name]=fingerprint==prior.fingerprint((m,o,s,path))
    uv=grid[expected]
    try:
        a['single_face_depths']=np.stack([candidate.owner_depth(mesh,[fi],cam,uv)[0] for fi in owners])
        a['joint_tie_depth'],a['joint_tie_representative_face']=candidate.owner_depth(mesh,owners,cam,uv)
    except Exception as exc:errors['tie_queries']=type(exc).__name__+': '+str(exc)
    checks=assess(a) if not errors else {'no_candidate_exception':False}
    checks.update(no_candidate_exception=not errors,attachment_valid=independent_att['valid'],
                  no_input_mutation=all(identities.values()) and before==prior.fingerprint(original),
                  noncoplanar=bool(abs(float(mesh['normals'][0]@mesh['normals'][1]))<1.-1e-9))
    tied=expected&(expanded>0)
    m={'case_id':spec['id'],'attachment':att,'independent_attachment':independent_att,
       'errors':errors,'gates':checks,'case_go':all(checks.values()),
       'analytic_ties':int(dual.sum()),'prescribed_ties':int(expected.sum()),
       'tie_depth_world':4.,'analytic_tie_depth_gap_max':float(np.max(abs(truth['owner_faces_depth'][0,expected]-truth['owner_faces_depth'][1,expected]))),
       'footprint_tie_sites':int(tied.sum()),'footprint_sites':int((expanded>0).sum()),
       'matched_visible_sites':int(((expanded>0)&truth['visible']).sum()),
       'unchanged_variant_inputs':identities,'input_fingerprint':before,
       'representative_face_identity':'Not invariant physical identity; either incident face valid at exact edge',
       'scene_depth':depth_ok(a['candidate_scene_depth'],truth['scene'])[0] if 'candidate' in variants else None,
       'owner_depth':depth_ok(a['candidate_owner_depth'][expanded>0],truth['owner'][expanded>0])[0] if 'candidate' in variants else None,
       'high_ink_sum':float(a['candidate_high'].sum()) if 'candidate' in variants else None,
       'final_ink_sum':float(a['candidate_final_uint8'].sum()/255.) if 'candidate' in variants else None}
    return m,a


def sensitivity(a):
    """Inject failures into saved evidence, never into candidate or frozen geometry."""
    cases=[];tie=np.argwhere(a['expected_tie_mask']&(a['reference_expanded']>0))[0];y,x=map(int,tie)
    for name,key,index,value,target in [
        ('drop_analytic_tie','oracle_dual_mask',(y,x),False,'exact_analytic_tie_mask'),
        ('unequal_analytic_depth','oracle_owner_faces_depth',(1,y,x),4.01,'exact_analytic_equal_depth'),
        ('miss_single_face','single_face_depths',(0,32),np.inf,'both_single_faces_exact_at_all_ties'),
        ('drop_rendered_tie','candidate_high',(y,x),0.,'matched_high_exact'),
        ('corrupt_final_pixel','candidate_final_uint8',(0,0),1,'matched_final_exact'),
        ('order_dependent_ink','reverse_faces_high',(y,x),0.,'reverse_faces_high_exact')]:
        altered={k:v.copy() for k,v in a.items()};altered[key][index]=value
        gates=assess(altered)
        cases.append({'name':name,'expected_failed_gate':target,'detected':not gates[target],
                      'failed_gates':[k for k,v in gates.items() if not v]})
    return {'baseline_passes':all(assess(a).values()),'controls':cases,
            'all_detected':all(q['detected'] for q in cases)}


def negative_control():
    old=prior.prior.P;spec=old['negative_controls']['multidepth_connected']
    cam,faces,extras,mesh,path=oracle.fixture(old,spec,negative=True)
    owners=old['geometry']['owner_faces'];segments=spec['segment_owner_faces'];pp=old['primitive']
    att=adapter.validate_attachment(mesh,owners,segments,path)['diagnostics']
    yy,xx=np.mgrid[:cam['size'],:cam['size']];truth=oracle.truth(np.stack((xx,yy),axis=-1),faces,extras,cam)
    pre,foot,*_=oracle.raw_footprint(path,cam,pp);amb=(foot>0)&truth['ambiguous']
    gaps=abs(truth['owner_faces_depth'][0,amb]-truth['owner_faces_depth'][1,amb]);error=None
    try:adapter.render_validated(mesh,owners,segments,path,candidate.render,cam,pp['ink'],old['camera']['supersample'],pp['high_width_filter_size'],pp['dense_step_high_px'],pp['depth_tolerance_world'])
    except ValueError as exc:error=str(exc)
    out={'attachment':att,'ambiguous_footprint_sites':int(amb.sum()),
         'depth_gap_min':float(gaps.min()) if len(gaps) else None,'error':error,
         'pass':bool(amb.any() and error and 'ambiguous' in error)}
    raw={'path':path,'vertices':mesh['vertices'],'faces':mesh['faces'],'oracle_depths':truth['owner_faces_depth'],
         'ambiguous_footprint':amb,'footprint':foot,'pre_z':pre}
    return out,raw


def historical_replay():
    count=0;records=[]
    for spec in prior.F['cases']:
        m,a=prior.evaluate_case(spec);name=spec['id']
        assert m==json.loads((c.P/'raw'/f'{name}.json').read_text()),name
        old=dict(np.load(c.P/'raw'/f'{name}.npz'));assert set(old)==set(a)
        for k in a:np.testing.assert_array_equal(a[k],old[k],err_msg=f'{name}/{k}');count+=1
        records.append({'case_id':name,'exact':True,'arrays':len(a)})
    older=prior.historical_replay(save=False)
    return {'round008_cases':records,'round008_arrays_exact':count,'prior_visibility':older,
            'all_metrics_exact':True,'all_exact':count==181 and older['all_exact']}


def contact(records,arrays,negative):
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    titles=['Candidate','Matched analytic truth','Reversed face order','Absolute ink error','Exact dual-hit footprint']
    sheet=Image.new('RGB',(1320,750),'white');d=ImageDraw.Draw(sheet)
    d.text((12,8),'Exact shared-edge raster ties | All frozen full views | Analytic GT diagnostic only',font=font(21),fill='black')
    d.text((12,38),'One noncoplanar patch, one fixed camera. Blue: surface; orange: ties inside stroke footprint. No phase sweep.',font=font(15),fill='black')
    for row,(m,a) in enumerate(zip(records,arrays)):
        top=78+row*306
        d.text((12,top),f"{m['case_id']} | GO {m['case_go']} | global ties {m['analytic_ties']} | footprint ties {m['footprint_tie_sites']}",font=font(16),fill='black')
        bg=np.full((64,64,3),255.,float)
        support=np.asarray(Image.fromarray(np.uint8(np.isfinite(a['oracle_scene'])*255)).resize((64,64),Image.Resampling.NEAREST))>0
        bg[support]=[215,233,245]
        panels=[]
        for key in ['candidate_final_uint8','matched_final_uint8','reverse_faces_final_uint8']:
            ink=a.get(key,np.zeros((64,64),np.uint8))/255.
            panels.append(Image.fromarray(np.uint8(bg*(1-ink[...,None]))))
        err=abs(a.get('candidate_high',np.zeros((128,128)))-a['matched_reference'])
        panels.append(Image.fromarray(np.uint8(255*(1-np.clip(err,0,1)))))
        ties=np.full((128,128,3),255,np.uint8);ties[np.isfinite(a['oracle_scene'])]=[215,233,245]
        ties[a['expected_tie_mask']]=[70,120,170]
        ties[a['expected_tie_mask']&(a['reference_expanded']>0)]=[230,110,20]
        panels.append(Image.fromarray(ties))
        for col,panel in enumerate(panels):
            x=8+col*264;d.text((x,top+26),titles[col],font=font(14),fill='black')
            sheet.paste(panel.resize((256,256),Image.Resampling.NEAREST).convert('RGB'),(x,top+48))
    d.text((12,704),f"Connected distinct-depth control: {negative['ambiguous_footprint_sites']} ambiguous sites; rejected: {negative['pass']}",font=font(16),fill='black')
    d.text((12,729),'Matched-footprint evidence only. Centered width, AA tails, face identity and general temporal stability are not established.',font=font(13),fill='black')
    sheet.save(c.R/'figures/full_view_contact_sheet.png')


def summary(records,regression,negative,mutations):
    gates={'two_cases_complete':len(records)==2,'all_case_gates':all(m['case_go'] for m in records),
           'connected_distinct_depth_rejected':negative['pass'],'regressions_exact':regression['all_exact'],
           'sensitivity_detects_failures':mutations['baseline_passes'] and mutations['all_detected']}
    for name in TESTS:gates[name.lower()]=json.loads((c.R/(name+'.json')).read_text())['returncode']==0
    return {'complete':True,'exact_shared_edge_go':all(gates.values()),'gates':gates,'cases':records,
            'regression':regression,'negative_control':negative,'sensitivity':mutations,
            'limits':['Finite analytic tie diagnostic only','P1/lamp/reconstruction/temporal stability unproven',
                      'Centered footprint bias and AA tails unchanged','Face representative identity not unique at edge']}


def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for name in ['raw','figures']:(c.R/name).mkdir(exist_ok=True)
    c.status('evaluating_frozen_exact_ties');records=[];arrays=[];start=time.monotonic()
    for spec in P['cases']:
        c.resources();m,a=evaluate_case(spec);records.append(m);arrays.append(a)
        c.write(c.R/'raw'/f"{spec['id']}.json",m);np.savez_compressed(c.R/'raw'/f"{spec['id']}.npz",**a)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'cases':records})
        print(json.dumps({'case':spec['id'],'go':m['case_go'],'footprint_ties':m['footprint_tie_sites'],'errors':m['errors']}),flush=True)
    negative,na=negative_control();c.write(c.R/'negative_control.json',negative);np.savez_compressed(c.R/'raw/negative_control.npz',**na)
    mutations=sensitivity(arrays[0]) if records[0]['case_go'] else {'baseline_passes':False,'all_detected':False,'reason':'Primary case failed; no successful baseline for evidence mutation'}
    c.write(c.R/'SENSITIVITY.json',mutations)
    regression=historical_replay();c.write(c.R/'REGRESSION.json',regression)
    contact(records,arrays,negative);out=summary(records,regression,negative,mutations)
    out['wall_seconds']=time.monotonic()-start;out['resources']=c.resources();c.write(c.R/'metrics.json',out)
    c.status('evaluated_awaiting_exact_replay',scientific_verdict='EXACT_TIE_GO_PENDING_REPLAY' if out['exact_shared_edge_go'] else 'EXACT_TIE_NO_GO')
    print(json.dumps({'go':out['exact_shared_edge_go'],'gates':out['gates']}),flush=True)


def validate():
    c.verify_lock();c.verify_prior();c.resources();saved=json.loads((c.R/'metrics.json').read_text());records=[];arrays=[];count=0
    for spec in P['cases']:
        m,a=evaluate_case(spec);assert m==json.loads((c.R/'raw'/f"{spec['id']}.json").read_text())
        old=dict(np.load(c.R/'raw'/f"{spec['id']}.npz"));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k]);count+=1
        records.append(m);arrays.append(a)
    negative,na=negative_control();assert negative==json.loads((c.R/'negative_control.json').read_text())
    old=dict(np.load(c.R/'raw/negative_control.npz'));assert set(na)==set(old)
    for k in na:np.testing.assert_array_equal(na[k],old[k]);count+=1
    mutations=sensitivity(arrays[0]) if records[0]['case_go'] else saved['sensitivity']
    regression=historical_replay();out=summary(records,regression,negative,mutations)
    for k in out:assert out[k]==saved[k],k
    result={'complete':True,'new_cases_exact':len(records),'new_arrays_exact':count,'all_metrics_exact':True,
            'negative_exact':True,'regression':regression,'exact_shared_edge_go':out['exact_shared_edge_go'],
            'prior_seal':c.verify_prior(),'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',result);c.status('validated_awaiting_report')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','evaluate','validate'])
    args=parser.parse_args();globals()[args.command]()
