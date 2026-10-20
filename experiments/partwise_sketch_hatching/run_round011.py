"""Frozen pixel-square area diagnostic; no acceptance-driven tuning."""
import round011_common as c
import argparse
import importlib.metadata
import json
import subprocess
import time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import core
import mesh_attachment as adapter
import visibility_primitive as visibility
import centered_coverage as baseline
import area_coverage as candidate
import round011_oracle as oracle
import round010_fixture as fixture
import coverage_fixture
import patch_fixture
import run_round010 as prior
P=json.loads((c.D/'PROTOCOL.json').read_text())
TESTS=['INHERITED_ATTACHMENT','INHERITED_PATCH','INHERITED_CANDIDATE','INHERITED_ORACLE','INHERITED_TEMPORAL','INHERITED_STAGE','INHERITED_CENTERED','GREEN_AREA']
NEW=['round011_common.py','round011_receipt.py','build_round011_protocol.py','area_coverage.py','round011_oracle.py','test_area_coverage.py','run_round011.py','seal_round011.py']

def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    verification=c.verify_prior();c.write(c.R/'PRIOR_SEAL_VERIFY.json',verification)
    old=json.loads((c.W/'docs/partwise_sketch_hatching/round_010/ASSET_LOCK.json').read_text())
    for path,h in old['sources'].items():assert c.sha(c.W/path)==h,path
    for name,key in [('visibility_primitive.py','candidate_source_sha256'),('mesh_attachment.py','adapter_source_sha256')]:assert c.sha(c.W/'experiments/partwise_sketch_hatching'/name)==P[key]
    paths={c.W/p for p in old['sources']}|{c.W/'experiments/partwise_sketch_hatching'/n for n in NEW}|{p for p in c.D.iterdir() if p.is_file()}
    paths|={c.W/'docs/partwise_sketch_hatching/round_010'/n for n in ['ASSET_LOCK.json','REPORT_ZH.md','REPRODUCE.md']}
    inputs=[c.P/n for n in ['STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json','metrics.json','REGRESSION.json','VALIDATION.json']]
    c.write(c.D/'ASSET_LOCK.json',{'protocol_commit':'8054de7f','implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),'sources':{str(p.relative_to(c.W)):c.sha(p) for p in sorted(paths)},'inputs':{str(p):c.sha(p) for p in inputs},'prior_seal':verification,'resources':c.resources(),'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','Pillow']}})
    c.status('source_locked_awaiting_acceptance');print(json.dumps({'frozen_new_cases':len(P['cases']),'prior':verification}),flush=True)

def max_error(a,b):return float(np.max(np.abs(a-b)))

def assess(a,required):
    area=a['oracle_area'];foot=area>0;visible=foot&a['oracle_visible'];hidden=foot&a['oracle_hidden'];unsupported=foot&a['oracle_unsupported']
    parts={'visible':visible,'hidden':hidden,'unsupported_background':unsupported&~np.isfinite(a['oracle_scene']),'unsupported_foreground':unsupported&np.isfinite(a['oracle_scene']),'samepart_unsupported':unsupported&(a['oracle_part']==1)}
    gates={'full_area_fraction':max_error(a['candidate_coverage'],area)<=1e-10,
           'unclipped_area_sum':abs(float(a['candidate_coverage'].sum()-area.sum()))<=1e-8,
           'analytic_rectangle_mass':abs(float(a['candidate_coverage'].sum())-float(a['analytic_rectangle_area']))<=1e-8,
           'oracle_rectangle_mass':abs(float(a['oracle_area_raw'].sum())-float(a['analytic_rectangle_area']))<=1e-8,
           'footprint_ink':max_error(a['candidate_footprint'],area*.8)<=1e-10,
           'positive_support_exact':bool(np.array_equal(a['candidate_coverage']>0,foot)),
           'high_fraction':max_error(a['candidate_high'],a['reference_high'])<=1e-10,
           'high_ink_sum':abs(float(a['candidate_high'].sum()-a['reference_high'].sum()))<=1e-8,
           'quantized_exact':bool(np.array_equal(a['candidate_quantized_uint8'],a['reference_quantized_uint8'])),
           'final_exact':bool(np.array_equal(a['candidate_final_uint8'],a['reference_final_uint8'])),
           'nonempty_visible':bool(visible.any()),'visible_retained':max_error(a['candidate_high'][visible],a['reference_high'][visible])<=1e-10 if visible.any() else False,
           'hidden_rejected':bool(np.all(a['candidate_high'][hidden]==0)),
           'unsupported_rejected':bool(np.all(a['candidate_high'][unsupported]==0)),
           'gate_exact':bool(np.array_equal(a['candidate_gate'],visible)),
           'scene_depth':prior.depth_ok(a['candidate_scene_depth'],a['oracle_scene'])[1],
           'owner_depth':prior.depth_ok(a['candidate_owner_depth'][foot],a['oracle_owner'][foot])[1],
           'scene_parts':bool(np.array_equal(a['candidate_scene_owner'],a['oracle_part']))}
    for name in required:gates['nonempty_'+name]=bool(parts[name].any())
    for variant in P['controls']['variants']:
        for key in P['controls']['physical_arrays']:gates[variant+'_'+key]=bool(np.array_equal(a[variant+'_'+key],a['candidate_'+key]))
    return gates,{k:{'sites':int(v.sum()),'area':float(area[v].sum())} for k,v in parts.items()}

def evaluate_case(spec,tie=False):
    if tie:
        g=prior.prior.P['geometry'];cam=coverage_fixture.camera(prior.prior.P)
        mesh=core.finalize_mesh(g['vertices'],g['faces'],g['parts']);path=np.asarray(spec['path'],float)
        owners=list(g['owners']);segments=list(spec['segment_faces']);yy,xx=np.mgrid[:cam['size'],:cam['size']];grid=np.stack((xx,yy),axis=-1)
        truth=patch_fixture.truth(grid,g['analytic_faces'],[],cam)
        prescribed=np.array([[64.+64.*x/z,64.+64.*y/z] for x,y,z in spec['path']]);required=['visible']
    else:
        mesh,cam,path,owners,segments,grid,truth=fixture.fixture(P,spec)
        prescribed=np.asarray(spec['projected_path'],float);required=spec['required']
    fingerprint=prior.prior.prior.fingerprint((mesh,owners,segments,path));att=adapter.validate_attachment(mesh,owners,segments,path)['diagnostics']
    area,raw=oracle.area_reference(prescribed,cam['size'],2.);ref=area*truth['visible']*.8
    a={**{'oracle_'+k:v for k,v in truth.items()},'oracle_area':area,'oracle_area_raw':raw,
       'analytic_rectangle_area':np.array(2*np.linalg.norm(prescribed[-1]-prescribed[0])),
       'prescribed_projected_path':prescribed,'reference_high':ref,'reference_quantized_uint8':np.uint8(ref*255),'reference_final_uint8':coverage_fixture.down(ref,2),
       'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],'mesh_parts':mesh['parts'],'path':path,'owners':np.array(owners),'segment_faces':np.array(segments)}
    errors={};immutable={}
    for name in ['candidate']+P['controls']['variants']:
        reverse_faces=name in ['reverse_faces','reverse_both'];reverse_owners=name in ['reverse_owners','reverse_both']
        m=core.finalize_mesh(mesh['vertices'],mesh['faces'][::-1],mesh['parts'][::-1]) if reverse_faces else mesh
        n=len(mesh['faces']);o=[n-1-i for i in owners] if reverse_faces else owners.copy();s=[n-1-i for i in segments] if reverse_faces else segments.copy();q=path
        if reverse_owners:o=o[::-1]
        if name=='reverse_path':q=path[::-1];s=s[::-1]
        before=prior.prior.prior.fingerprint((m,o,s,q))
        try:
            result=adapter.render_validated(m,o,s,q,candidate.render,cam,.8,2,2.,.006);a.update({name+'_'+k:v for k,v in result.items()})
        except Exception as exc:errors[name]=type(exc).__name__+': '+str(exc)
        immutable[name]=before==prior.prior.prior.fingerprint((m,o,s,q))
    old=adapter.render_validated(mesh,owners,segments,path,baseline.render,cam,.8,2,2.,.006);a.update({'point_'+k:v for k,v in old.items()})
    gates,counts=assess(a,required) if not errors else ({'no_candidate_errors':False},{})
    gates['no_candidate_errors']=not errors;gates['input_immutable']=all(immutable.values()) and fingerprint==prior.prior.prior.fingerprint((mesh,owners,segments,path))
    gates['projection_matches_prescribed']=bool('candidate_projected_path' in a and max_error(a['candidate_projected_path'],prescribed)<=1e-12)
    tie_metrics=None
    if tie:
        expected=np.zeros(area.shape,bool);expected[64,32:97]=True;both=np.isfinite(truth['owner_faces_depth']).all(axis=0);uv=grid[expected]
        singles=np.stack([visibility.owner_depth(mesh,[fi],cam,uv)[0] for fi in owners]);joint=visibility.owner_depth(mesh,owners,cam,uv)[0]
        a.update(expected_tie_mask=expected,single_face_tie_depths=singles,joint_tie_depth=joint);tied=expected&(area>0)
        gates.update(exact_tie_mask=bool(np.array_equal(both,expected)),exact_analytic_tie_depths=bool(np.array_equal(truth['owner_faces_depth'][:,expected],np.full((2,65),4.))),exact_single_and_joint=bool(np.array_equal(singles,np.full((2,65),4.)) and np.array_equal(joint,np.full(65,4.))),nonempty_area_ties=bool(tied.any()),retain_area_ties=bool(not errors and max_error(a['candidate_high'][tied],ref[tied])<=1e-10))
        tie_metrics={'global_ties':int(both.sum()),'area_footprint_ties':int(tied.sum()),'tie_area':float(area[tied].sum())}
    m={'case_id':spec['id'],'exposed_tie_control':tie,'attachment':att,'counts':counts,'errors':errors,'gates':gates,'case_go':all(gates.values()),'input_fingerprint':fingerprint,'tie_metrics':tie_metrics,
       'reference_area':float(area.sum()),'analytic_rectangle_area':float(a['analytic_rectangle_area']),'point_area':float((old['footprint']/.8).sum()),'reference_ink':float(ref.sum()),'point_ink':float(old['high'].sum()),
       'candidate_area':float(a['candidate_coverage'].sum()) if not errors else None,'candidate_ink':float(a['candidate_high'].sum()) if not errors else None,
       'max_area_error':max_error(a['candidate_coverage'],area) if not errors else None,'max_high_error':max_error(a['candidate_high'],ref) if not errors else None,
       'quantized_mismatch_pixels':int(np.count_nonzero(a['candidate_quantized_uint8']!=a['reference_quantized_uint8'])) if not errors else None,
       'final_mismatch_pixels':int(np.count_nonzero(a['candidate_final_uint8']!=a['reference_final_uint8'])) if not errors else None,
       'point_final_L1':float(abs(old['final_uint8'].astype(float)-a['reference_final_uint8']).sum()/255),
       'candidate_final_L1':float(abs(a['candidate_final_uint8'].astype(float)-a['reference_final_uint8']).sum()/255) if not errors else None}
    return m,a

def negative_control():
    old=prior.prior.prior.prior.P;spec=old['negative_controls']['multidepth_connected']
    cam,faces,extras,mesh,path=patch_fixture.fixture(old,spec,negative=True);owners=old['geometry']['owner_faces'];segments=spec['segment_owner_faces']
    att=adapter.validate_attachment(mesh,owners,segments,path)['diagnostics'];segment=path[:2]
    yy,xx=np.mgrid[:cam['size'],:cam['size']];grid=np.stack((xx,yy),axis=-1);truth=patch_fixture.truth(grid,faces,extras,cam)
    camera_points=(segment-cam['eye'])@cam['R'].T;prescribed=camera_points[:,:2]/camera_points[:,2,None]*cam['focal']+cam['center']
    area,raw=oracle.area_reference(prescribed,cam['size']);amb=(area>0)&truth['ambiguous'];error=None
    try:adapter.render_validated(mesh,owners,segments[:1],segment,candidate.render,cam,.8,2,2.,.006)
    except ValueError as exc:error=str(exc)
    gaps=abs(truth['owner_faces_depth'][0,amb]-truth['owner_faces_depth'][1,amb])
    m={'full_bent_attachment':att,'tested_segment':0,'area_ambiguous_sites':int(amb.sum()),'ambiguous_area':float(area[amb].sum()),'gap_min':float(gaps.min()) if len(gaps) else None,'error':error,'pass':bool(amb.any() and error and 'ambiguous' in error)}
    return m,{'path':path,'tested_segment':segment,'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],'prescribed_projection':prescribed,'oracle_area':area,'oracle_area_raw':raw,'oracle_ambiguous':amb,'oracle_depths':truth['owner_faces_depth']}

def historical_replay():
    count=0;records=[]
    for spec,tie in prior.all_specs():
        m,a=prior.evaluate_case(spec,tie);name=spec['id'];assert m==json.loads((c.P/'raw'/f'{name}.json').read_text()),name
        old=dict(np.load(c.P/'raw'/f'{name}.npz'));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k],err_msg=f'{name}/{k}');count+=1
        records.append({'case_id':name,'arrays_exact':len(a)})
    m,a=prior.negative_control();assert m==json.loads((c.P/'negative_control.json').read_text());old=dict(np.load(c.P/'raw/negative_control.npz'));assert set(a)==set(old)
    for k in a:np.testing.assert_array_equal(a[k],old[k]);count+=1
    older=prior.historical_replay()
    return {'round010_cases':records,'round010_arrays_exact':count,'round010_negative_exact':True,'older':older,'all_exact':count==586 and older['all_exact']}

def sensitivity(arrays):
    specs=[('delete_area',0,'candidate_coverage','visible',0.,'full_area_fraction'),('add_outside_area',0,'candidate_coverage','outside',1.,'full_area_fraction'),('drop_visible_ink',0,'candidate_high','visible',0.,'visible_retained'),('hidden_ink',2,'candidate_high','hidden',.8,'hidden_rejected'),('unsupported_ink',3,'candidate_high','unsupported',.8,'unsupported_rejected'),('final_corruption',0,'candidate_final_uint8','final',1,'final_exact'),('order_difference',0,'reverse_faces_high','visible',0.,'reverse_faces_high')]
    records=[]
    for name,i,key,region,value,target in specs:
        a={k:v.copy() for k,v in arrays[i].items()}
        if region in ['outside','final']:y,x=0,0
        else:y,x=map(int,np.argwhere((a['oracle_area']>0)&a['oracle_'+region])[0])
        a[key][y,x]=value;gates,_=assess(a,P['cases'][i]['required'])
        records.append({'name':name,'expected_failed_gate':target,'detected':not gates[target],'failed_gates':[k for k,v in gates.items() if not v]})
    return {'baseline_passes':all(all(assess(a,s['required'])[0].values()) for a,s in zip(arrays,P['cases'])),'controls':records,'all_detected':all(r['detected'] for r in records)}

def contact(records,arrays):
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    titles=['Area candidate','Independent area reference','Exposed point baseline','Area error x16','Center-site controls']
    sheet=Image.new('RGB',(1320,95+len(records)*305),'white');draw=ImageDraw.Draw(sheet)
    draw.text((10,8),'Pixel-square area coverage | All frozen full views | Analytic GT diagnostic only',font=font(21),fill='black')
    draw.text((10,38),'Blue: surface. Green: visible. Red: hidden. Orange: unsupported. Within-pixel visibility remains unmeasured.',font=font(15),fill='black')
    for row,(m,a) in enumerate(zip(records,arrays)):
        top=74+row*305;draw.text((10,top),f"{m['case_id']} | GO {m['case_go']} | area {m['reference_area']:.6f} | point {m['point_area']:.1f}",font=font(15),fill='black')
        bg=np.full((64,64,3),255.);domain=np.asarray(Image.fromarray(np.uint8(np.isfinite(a['oracle_scene'])*255)).resize((64,64),Image.Resampling.NEAREST))>0;bg[domain]=[215,233,245];panels=[]
        for key in ['candidate_final_uint8','reference_final_uint8','point_final_uint8']:
            ink=a.get(key,np.zeros((64,64),np.uint8))/255.;panels.append(Image.fromarray(np.uint8(bg*(1-ink[...,None]))))
        error=abs(a.get('candidate_coverage',np.zeros((128,128)))-a['oracle_area']);panels.append(Image.fromarray(np.uint8(255*(1-np.minimum(1,error*16)))))
        control=np.full((128,128,3),255,np.uint8);control[np.isfinite(a['oracle_scene'])]=[215,233,245]
        for mask,color in [(a['oracle_visible'],[20,130,60]),(a['oracle_hidden'],[210,30,30]),(a['oracle_unsupported'],[230,130,20])]:control[mask&(a['oracle_area']>0)]=color
        panels.append(Image.fromarray(control))
        for col,panel in enumerate(panels):
            x=8+col*264;draw.text((x,top+25),titles[col],font=font(14),fill='black');sheet.paste(panel.resize((256,256),Image.Resampling.NEAREST).convert('RGB'),(x,top+47))
    sheet.save(c.R/'figures/full_view_contact_sheet.png')

def summary(records,negative,regression,mutations):
    gates={'five_new_two_exposed_complete':len(records)==7,'all_case_gates':all(r['case_go'] for r in records),'connected_distinct_depth_rejected':negative['pass'],'historical_exact':regression['all_exact'],'sensitivity':mutations['baseline_passes'] and mutations['all_detected'],'point_RED_observed':json.loads((c.R/'RED_POINT.json').read_text())['returncode']==1}
    for name in TESTS:gates[name.lower()]=json.loads((c.R/(name+'.json')).read_text())['returncode']==0
    return {'complete':True,'area_coverage_go':all(gates.values()),'gates':gates,'cases':records,'negative_control':negative,'regression':regression,'sensitivity':mutations,'limits':P['limits']}

def all_specs():return [(s,False) for s in P['cases']]+[(s,True) for s in prior.prior.P['cases']]

def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for name in ['raw','figures']:(c.R/name).mkdir(exist_ok=True)
    c.status('evaluating_frozen_area_coverage');records=[];arrays=[];start=time.monotonic()
    for spec,tie in all_specs():
        c.resources();m,a=evaluate_case(spec,tie);records.append(m);arrays.append(a);c.write(c.R/'raw'/f"{spec['id']}.json",m);np.savez_compressed(c.R/'raw'/f"{spec['id']}.npz",**a)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'cases':records});print(json.dumps({'case':spec['id'],'go':m['case_go'],'counts':m['counts'],'failed':[k for k,v in m['gates'].items() if not v]}),flush=True)
    negative,na=negative_control();c.write(c.R/'negative_control.json',negative);np.savez_compressed(c.R/'raw/negative_control.npz',**na)
    mutations=sensitivity(arrays[:5]);c.write(c.R/'SENSITIVITY.json',mutations);regression=historical_replay();c.write(c.R/'REGRESSION.json',regression)
    contact(records,arrays);out=summary(records,negative,regression,mutations);out['wall_seconds']=time.monotonic()-start;out['resources']=c.resources();c.write(c.R/'metrics.json',out)
    c.status('evaluated_awaiting_exact_replay',scientific_verdict='AREA_COVERAGE_GO_PENDING_REPLAY' if out['area_coverage_go'] else 'AREA_COVERAGE_NO_GO');print(json.dumps({'go':out['area_coverage_go'],'gates':out['gates']}),flush=True)

def validate():
    c.verify_lock();c.verify_prior();c.resources();saved=json.loads((c.R/'metrics.json').read_text());records=[];arrays=[];count=0
    for spec,tie in all_specs():
        m,a=evaluate_case(spec,tie);assert m==json.loads((c.R/'raw'/f"{spec['id']}.json").read_text());old=dict(np.load(c.R/'raw'/f"{spec['id']}.npz"));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k]);count+=1
        records.append(m);arrays.append(a)
    negative,na=negative_control();assert negative==json.loads((c.R/'negative_control.json').read_text());old=dict(np.load(c.R/'raw/negative_control.npz'));assert set(na)==set(old)
    for k in na:np.testing.assert_array_equal(na[k],old[k]);count+=1
    mutations=sensitivity(arrays[:5]);regression=historical_replay();out=summary(records,negative,regression,mutations)
    for k in out:assert out[k]==saved[k],k
    result={'complete':True,'cases_exact':len(records),'arrays_exact':count,'all_metrics_exact':True,'negative_exact':True,'regression':regression,'area_coverage_go':out['area_coverage_go'],'prior_seal':c.verify_prior(),'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',result);c.status('validated_awaiting_report');print(json.dumps({'complete':True,'cases_exact':len(records),'arrays_exact':count,'go':out['area_coverage_go']}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','evaluate','validate']);args=p.parse_args();globals()[args.command]()
