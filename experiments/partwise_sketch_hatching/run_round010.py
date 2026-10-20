"""One frozen centered support diagnostic. No acceptance tuning or lamp integration."""
import round010_common as c
import argparse
import importlib.metadata
import json
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import core
import mesh_attachment as adapter
import centered_coverage as candidate
import visibility_primitive as legacy
import round010_fixture as oracle
import coverage_fixture
import patch_fixture
import run_round009 as prior
from visibility_trial import depth_check

P = json.loads((c.D/'PROTOCOL.json').read_text())
TESTS = ['INHERITED_ATTACHMENT','INHERITED_PATCH','INHERITED_CANDIDATE',
         'INHERITED_ORACLE','INHERITED_TEMPORAL','INHERITED_STAGE','GREEN_COVERAGE']
NEW = ['round010_common.py','round010_receipt.py','build_round010_protocol.py',
       'centered_coverage.py','test_centered_coverage.py','round010_fixture.py',
       'run_round010.py','seal_round010.py']


def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    verification = c.verify_prior(); c.write(c.R/'PRIOR_SEAL_VERIFY.json',verification)
    old = json.loads((c.W/'docs/partwise_sketch_hatching/round_009/ASSET_LOCK.json').read_text())
    for path,h in old['sources'].items(): assert c.sha(c.W/path)==h,path
    for name,key in [('visibility_primitive.py','candidate_source_sha256'),('mesh_attachment.py','adapter_source_sha256')]:
        assert c.sha(c.W/'experiments/partwise_sketch_hatching'/name)==P[key]
    paths = {c.W/p for p in old['sources']}
    paths |= {c.W/'experiments/partwise_sketch_hatching'/n for n in NEW}
    paths |= {p for p in c.D.iterdir() if p.is_file()}
    paths |= {c.W/'docs/partwise_sketch_hatching/round_009'/n for n in ['ASSET_LOCK.json','REPORT_ZH.md','REPRODUCE.md']}
    inputs = [c.P/n for n in ['STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json','metrics.json','REGRESSION.json','VALIDATION.json']]
    c.write(c.D/'ASSET_LOCK.json',{'protocol_commit':'58f996e4',
        'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),
        'sources':{str(p.relative_to(c.W)):c.sha(p) for p in sorted(paths)},
        'inputs':{str(p):c.sha(p) for p in inputs},'prior_seal':verification,
        'resources':c.resources(),'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','Pillow']}})
    c.status('source_locked_awaiting_acceptance')
    print(json.dumps({'frozen_new_cases':len(P['cases']),'prior':verification}),flush=True)


def depth_ok(a,b):
    result=depth_check(a,b)
    return result, bool(result['finite_masks_equal'] and result['max_abs_error'] is not None and result['max_abs_error']<=1e-9)


def assess(a, required):
    foot=a['oracle_support']; visible=foot & a['oracle_visible']
    hidden=foot & a['oracle_hidden']; unsupported=foot & a['oracle_unsupported']
    partitions={'visible':visible,'hidden':hidden,
                'unsupported_background':unsupported & ~np.isfinite(a['oracle_scene']),
                'unsupported_foreground':unsupported & np.isfinite(a['oracle_scene']),
                'samepart_unsupported':unsupported & (a['oracle_part']==1)}
    gates={'unclipped_footprint_exact':bool(np.array_equal(a['candidate_footprint'],foot*P['coverage']['ink'])),
           'high_exact':bool(np.array_equal(a['candidate_high'],a['reference_high'])),
           'final_exact':bool(np.array_equal(a['candidate_final_uint8'],a['reference_final_uint8'])),
           'nonempty_visible':bool(visible.any()),
           'visible_retained':bool(np.all(a['candidate_high'][visible]==P['coverage']['ink'])),
           'hidden_rejected':bool(np.all(a['candidate_high'][hidden]==0)),
           'unsupported_rejected':bool(np.all(a['candidate_high'][unsupported]==0)),
           'gate_exact':bool(np.array_equal(a['candidate_gate'],visible)),
           'scene_depth':depth_ok(a['candidate_scene_depth'],a['oracle_scene'])[1],
           'owner_depth':depth_ok(a['candidate_owner_depth'][foot],a['oracle_owner'][foot])[1],
           'scene_parts':bool(np.array_equal(a['candidate_scene_owner'],a['oracle_part']))}
    for name in required: gates['nonempty_'+name]=bool(partitions[name].any())
    for variant in P['controls']['variants']:
        for key in P['controls']['physical_arrays']:
            gates[variant+'_'+key]=bool(np.array_equal(a[variant+'_'+key],a['candidate_'+key]))
    return gates, {k:int(v.sum()) for k,v in partitions.items()}


def evaluate_case(spec, tie=False):
    if tie:
        g=prior.P['geometry']; cam=coverage_fixture.camera(prior.P)
        mesh=core.finalize_mesh(g['vertices'],g['faces'],g['parts'])
        path=np.asarray(spec['path'],float);owners=list(g['owners']);segments=list(spec['segment_faces'])
        yy,xx=np.mgrid[:cam['size'],:cam['size']];grid=np.stack((xx,yy),axis=-1)
        truth=patch_fixture.truth(grid,g['analytic_faces'],[],cam)
        # Exposed old control: direct analytic projection, not core.project.
        prescribed=np.array([[64.+64.*x/z,64.+64.*y/z] for x,y,z in spec['path']])
        required=['visible']
    else:
        mesh,cam,path,owners,segments,grid,truth=oracle.fixture(P,spec)
        prescribed=np.asarray(spec['projected_path'],float);required=spec['required']
    fingerprint=prior.prior.fingerprint((mesh,owners,segments,path))
    att=adapter.validate_attachment(mesh,owners,segments,path)['diagnostics']
    support=oracle.analytic_support(grid,prescribed,P['coverage']['high_width'],P['coverage']['boundary_epsilon_high_px'])
    reference=support*truth['visible']*P['coverage']['ink']
    a={**{'oracle_'+k:v for k,v in truth.items()},'oracle_support':support,
       'prescribed_projected_path':prescribed,'reference_high':reference,
       'reference_final_uint8':coverage_fixture.down(reference,2),
       'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],'mesh_parts':mesh['parts'],
       'path':path,'owners':np.array(owners),'segment_faces':np.array(segments)}
    errors={};immutable={}
    for name in ['candidate']+P['controls']['variants']:
        reverse_faces=name in ['reverse_faces','reverse_both']
        reverse_owners=name in ['reverse_owners','reverse_both']
        m=core.finalize_mesh(mesh['vertices'],mesh['faces'][::-1],mesh['parts'][::-1]) if reverse_faces else mesh
        n=len(mesh['faces']);o=[n-1-i for i in owners] if reverse_faces else owners.copy()
        s=[n-1-i for i in segments] if reverse_faces else segments.copy();q=path
        if reverse_owners:o=o[::-1]
        if name=='reverse_path':q=path[::-1];s=s[::-1]
        before=prior.prior.fingerprint((m,o,s,q))
        try:
            result=adapter.render_validated(m,o,s,q,candidate.render,cam,.8,2,2.,.006)
            a.update({name+'_'+k:v for k,v in result.items()})
        except Exception as exc:errors[name]=type(exc).__name__+': '+str(exc)
        immutable[name]=before==prior.prior.fingerprint((m,o,s,q))
    baseline=adapter.render_validated(mesh,owners,segments,path,legacy.render,cam,.8,2,2,.45,.006)
    a.update({'legacy_'+k:v for k,v in baseline.items()})
    gates,counts=assess(a,required) if not errors else ({'no_candidate_errors':False},{})
    gates['no_candidate_errors']=not errors
    gates['input_immutable']=all(immutable.values()) and fingerprint==prior.prior.fingerprint((mesh,owners,segments,path))
    gates['projection_matches_prescribed']=bool('candidate_projected_path' in a and np.max(abs(a['candidate_projected_path']-prescribed))<=P['coverage']['projection_check_epsilon'])
    tie_metrics=None
    if tie:
        expected=np.zeros(support.shape,bool);expected[64,32:97]=True
        both=np.isfinite(truth['owner_faces_depth']).all(axis=0);uv=grid[expected]
        singles=np.stack([legacy.owner_depth(mesh,[fi],cam,uv)[0] for fi in owners])
        joint=legacy.owner_depth(mesh,owners,cam,uv)[0]
        a.update(expected_tie_mask=expected,single_face_tie_depths=singles,joint_tie_depth=joint)
        tied=expected & support
        gates.update(exact_tie_mask=bool(np.array_equal(both,expected)),
                     exact_analytic_tie_depths=bool(np.array_equal(truth['owner_faces_depth'][:,expected],np.full((2,65),4.))),
                     exact_single_and_joint=bool(np.array_equal(singles,np.full((2,65),4.)) and np.array_equal(joint,np.full(65,4.))),
                     nonempty_centered_ties=bool(tied.any()),
                     retain_centered_ties=bool(not errors and np.all(a['candidate_high'][tied]==.8)))
        tie_metrics={'global_ties':int(both.sum()),'centered_footprint_ties':int(tied.sum())}
    m={'case_id':spec['id'],'exposed_tie_control':tie,'attachment':att,'counts':counts,'errors':errors,
       'gates':gates,'case_go':all(gates.values()),'input_fingerprint':fingerprint,'tie_metrics':tie_metrics,
       'footprint_sites':int(support.sum()),'reference_high_ink':float(reference.sum()),
       'candidate_support_error_sites':int(np.count_nonzero((a['candidate_footprint']>0)!=support)) if not errors else None,
       'legacy_unclipped_support_error_sites':int(np.count_nonzero((baseline['footprint']>0)!=support)),
       'legacy_visible_support_error_sites':int(np.count_nonzero((baseline['high']>0)!=(reference>0))),
       'legacy_final_L1':float(abs(baseline['final_uint8'].astype(float)-a['reference_final_uint8']).sum()/255),
       'candidate_final_L1':float(abs(a['candidate_final_uint8'].astype(float)-a['reference_final_uint8']).sum()/255) if not errors else None,
       'scene_depth':depth_ok(a['candidate_scene_depth'],truth['scene'])[0] if not errors else None,
       'owner_depth':depth_ok(a['candidate_owner_depth'][support],truth['owner'][support])[0] if not errors else None}
    return m,a


def negative_control():
    old=prior.prior.prior.P;spec=old['negative_controls']['multidepth_connected']
    cam,faces,extras,mesh,path=patch_fixture.fixture(old,spec,negative=True)
    owners=old['geometry']['owner_faces'];segments=spec['segment_owner_faces']
    att=adapter.validate_attachment(mesh,owners,segments,path)['diagnostics']
    yy,xx=np.mgrid[:cam['size'],:cam['size']];grid=np.stack((xx,yy),axis=-1)
    truth=patch_fixture.truth(grid,faces,extras,cam)
    camera_points=(path-cam['eye'])@cam['R'].T
    prescribed=camera_points[:,:2]/camera_points[:,2,None]*cam['focal']+cam['center']
    foot=oracle.analytic_support(grid,prescribed);amb=foot & truth['ambiguous'];error=None
    try:adapter.render_validated(mesh,owners,segments,path,candidate.render,cam,.8,2,2.,.006)
    except ValueError as exc:error=str(exc)
    gaps=abs(truth['owner_faces_depth'][0,amb]-truth['owner_faces_depth'][1,amb])
    m={'attachment':att,'centered_ambiguous_sites':int(amb.sum()),'gap_min':float(gaps.min()) if len(gaps) else None,
       'error':error,'pass':bool(amb.any() and error and 'ambiguous' in error)}
    return m,{'path':path,'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],
              'prescribed_projection':prescribed,'oracle_footprint':foot,'oracle_ambiguous':amb,
              'oracle_depths':truth['owner_faces_depth']}


def historical_replay():
    count=0;records=[]
    for spec in prior.P['cases']:
        m,a=prior.evaluate_case(spec);name=spec['id']
        assert m==json.loads((c.P/'raw'/f'{name}.json').read_text()),name
        old=dict(np.load(c.P/'raw'/f'{name}.npz'));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k],err_msg=f'{name}/{k}');count+=1
        records.append({'case_id':name,'arrays_exact':len(a)})
    m,a=prior.negative_control();assert m==json.loads((c.P/'negative_control.json').read_text())
    old=dict(np.load(c.P/'raw/negative_control.npz'));assert set(old)==set(a)
    for k in a:np.testing.assert_array_equal(a[k],old[k]);count+=1
    older=prior.historical_replay()
    return {'round009_cases':records,'round009_arrays_exact':count,'round009_negative_exact':True,
            'older':older,'all_exact':count==173 and older['all_exact']}


def sensitivity(arrays):
    specs=[('delete_support',0,'candidate_footprint','visible',0.,'unclipped_footprint_exact'),
           ('add_beyond_cap',0,'candidate_footprint','cap',.8,'unclipped_footprint_exact'),
           ('drop_visible_ink',0,'candidate_high','visible',0.,'visible_retained'),
           ('hidden_ink',2,'candidate_high','hidden',.8,'hidden_rejected'),
           ('unsupported_ink',3,'candidate_high','unsupported',.8,'unsupported_rejected'),
           ('final_corruption',0,'candidate_final_uint8','final',1,'final_exact'),
           ('order_difference',0,'reverse_faces_high','visible',0.,'reverse_faces_high')]
    results=[]
    for name,i,key,region,value,target in specs:
        a={k:v.copy() for k,v in arrays[i].items()}
        if region=='cap': y,x=64,81
        elif region=='final':y,x=0,0
        else:y,x=map(int,np.argwhere(a['oracle_support'] & a['oracle_'+region])[0])
        a[key][y,x]=value;gates,_=assess(a,P['cases'][i]['required'])
        results.append({'name':name,'expected_failed_gate':target,'detected':not gates[target],
                        'failed_gates':[k for k,v in gates.items() if not v]})
    return {'baseline_passes':all(all(assess(a,s['required'])[0].values()) for a,s in zip(arrays,P['cases'])),
            'controls':results,'all_detected':all(r['detected'] for r in results)}


def contact(records,arrays):
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    titles=['Centered candidate','Analytic reference','Exposed old stencil','Candidate support error','Visibility controls']
    sheet=Image.new('RGB',(1320,95+len(records)*305),'white');draw=ImageDraw.Draw(sheet)
    draw.text((10,8),'Centered finite butt-cap ribbons | All frozen full views | Analytic GT diagnostic only',font=font(21),fill='black')
    draw.text((10,38),'Blue: surface. Last column: green visible, red hidden, orange unsupported. Closed samples; no area-AA claim.',font=font(15),fill='black')
    for row,(m,a) in enumerate(zip(records,arrays)):
        top=74+row*305;draw.text((10,top),f"{m['case_id']} | GO {m['case_go']} | support {m['footprint_sites']} | old support error {m['legacy_unclipped_support_error_sites']}",font=font(15),fill='black')
        bg=np.full((64,64,3),255.,float)
        domain=np.asarray(Image.fromarray(np.uint8(np.isfinite(a['oracle_scene'])*255)).resize((64,64),Image.Resampling.NEAREST))>0
        bg[domain]=[215,233,245];panels=[]
        for key in ['candidate_final_uint8','reference_final_uint8','legacy_final_uint8']:
            ink=a.get(key,np.zeros((64,64),np.uint8))/255.;panels.append(Image.fromarray(np.uint8(bg*(1-ink[...,None]))))
        error=(a.get('candidate_footprint',np.zeros((128,128)))>0)!=a['oracle_support']
        panels.append(Image.fromarray(np.uint8(255*(1-error.astype(float)))))
        control=np.full((128,128,3),255,np.uint8);control[np.isfinite(a['oracle_scene'])]=[215,233,245]
        for mask,color in [(a['oracle_visible'],[20,130,60]),(a['oracle_hidden'],[210,30,30]),(a['oracle_unsupported'],[230,130,20])]:
            control[mask & a['oracle_support']]=color
        panels.append(Image.fromarray(control))
        for col,panel in enumerate(panels):
            x=8+col*264;draw.text((x,top+25),titles[col],font=font(14),fill='black')
            sheet.paste(panel.resize((256,256),Image.Resampling.NEAREST).convert('RGB'),(x,top+47))
    sheet.save(c.R/'figures/full_view_contact_sheet.png')


def summary(records,negative,regression,mutations):
    gates={'five_new_two_exposed_complete':len(records)==7,'all_case_gates':all(r['case_go'] for r in records),
           'connected_distinct_depth_rejected':negative['pass'],'historical_exact':regression['all_exact'],
           'sensitivity':mutations['baseline_passes'] and mutations['all_detected'],
           'legacy_RED_observed':json.loads((c.R/'RED_LEGACY.json').read_text())['returncode']==1}
    for name in TESTS:gates[name.lower()]=json.loads((c.R/(name+'.json')).read_text())['returncode']==0
    return {'complete':True,'centered_support_go':all(gates.values()),'gates':gates,'cases':records,
            'negative_control':negative,'regression':regression,'sensitivity':mutations,'limits':P['limits']}


def all_specs():
    return [(s,False) for s in P['cases']]+[(s,True) for s in prior.P['cases']]


def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for name in ['raw','figures']:(c.R/name).mkdir(exist_ok=True)
    c.status('evaluating_frozen_centered_support');records=[];arrays=[];start=time.monotonic()
    for spec,tie in all_specs():
        c.resources();m,a=evaluate_case(spec,tie);records.append(m);arrays.append(a)
        c.write(c.R/'raw'/f"{spec['id']}.json",m);np.savez_compressed(c.R/'raw'/f"{spec['id']}.npz",**a)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'cases':records})
        print(json.dumps({'case':spec['id'],'go':m['case_go'],'counts':m['counts'],'failed':[k for k,v in m['gates'].items() if not v]}),flush=True)
    negative,na=negative_control();c.write(c.R/'negative_control.json',negative);np.savez_compressed(c.R/'raw/negative_control.npz',**na)
    mutations=sensitivity(arrays[:5]) if all(r['case_go'] for r in records[:5]) else {'baseline_passes':False,'all_detected':False,'reason':'Frozen acceptance case failed; promotion stopped'}
    c.write(c.R/'SENSITIVITY.json',mutations);regression=historical_replay();c.write(c.R/'REGRESSION.json',regression)
    contact(records,arrays);out=summary(records,negative,regression,mutations)
    out['wall_seconds']=time.monotonic()-start;out['resources']=c.resources();c.write(c.R/'metrics.json',out)
    c.status('evaluated_awaiting_exact_replay',scientific_verdict='CENTERED_SUPPORT_GO_PENDING_REPLAY' if out['centered_support_go'] else 'CENTERED_SUPPORT_NO_GO')
    print(json.dumps({'go':out['centered_support_go'],'gates':out['gates']}),flush=True)


def validate():
    c.verify_lock();c.verify_prior();c.resources();saved=json.loads((c.R/'metrics.json').read_text());records=[];arrays=[];count=0
    for spec,tie in all_specs():
        m,a=evaluate_case(spec,tie);assert m==json.loads((c.R/'raw'/f"{spec['id']}.json").read_text())
        old=dict(np.load(c.R/'raw'/f"{spec['id']}.npz"));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k]);count+=1
        records.append(m);arrays.append(a)
    negative,na=negative_control();assert negative==json.loads((c.R/'negative_control.json').read_text())
    old=dict(np.load(c.R/'raw/negative_control.npz'));assert set(na)==set(old)
    for k in na:np.testing.assert_array_equal(na[k],old[k]);count+=1
    mutations=sensitivity(arrays[:5]) if all(r['case_go'] for r in records[:5]) else saved['sensitivity']
    regression=historical_replay();out=summary(records,negative,regression,mutations)
    for k in out:assert out[k]==saved[k],k
    result={'complete':True,'cases_exact':len(records),'arrays_exact':count,'all_metrics_exact':True,
            'negative_exact':True,'regression':regression,'centered_support_go':out['centered_support_go'],
            'prior_seal':c.verify_prior(),'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',result);c.status('validated_awaiting_report')
    print(json.dumps({'complete':True,'cases_exact':len(records),'arrays_exact':count,'go':out['centered_support_go']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','evaluate','validate'])
    args=parser.parse_args();globals()[args.command]()
