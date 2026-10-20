"""Measure frozen center-site renderer against independent visible footprint area."""
import round012_common as c
import argparse,importlib.metadata,json,subprocess,time,traceback
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import area_coverage as candidate
import mesh_attachment as adapter
import physical_area_reference as oracle
import round010_fixture as fixture
import coverage_fixture
import run_round011 as prior
P=json.loads((c.D/'PROTOCOL.json').read_text())
TESTS=['INHERITED_ATTACHMENT','INHERITED_PATCH','INHERITED_CANDIDATE','INHERITED_ORACLE','INHERITED_TEMPORAL','INHERITED_STAGE','INHERITED_CENTERED','INHERITED_AREA','GREEN_REFERENCE']
NEW=['round012_common.py','round012_receipt.py','build_round012_protocol.py','physical_area_reference.py','test_physical_area_reference.py','run_round012.py','seal_round012.py']

def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    old=json.loads((c.W/'docs/partwise_sketch_hatching/round_011/ASSET_LOCK.json').read_text())
    for path,h in old['sources'].items():assert c.sha(c.W/path)==h,path
    for name,h in P['candidate_sources'].items():assert c.sha(c.W/'experiments/partwise_sketch_hatching'/name)==h,name
    paths={c.W/p for p in old['sources']}|{c.W/'experiments/partwise_sketch_hatching'/n for n in NEW}|{p for p in c.D.iterdir() if p.is_file()}
    paths|={c.W/'docs/partwise_sketch_hatching/round_011'/n for n in ['ASSET_LOCK.json','REPORT_ZH.md','REPRODUCE.md']}
    inputs=[c.P/n for n in ['STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json','metrics.json','REGRESSION.json','VALIDATION.json']]
    c.write(c.D/'ASSET_LOCK.json',{'protocol_commit':'be600922','implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),'sources':{str(p.relative_to(c.W)):c.sha(p) for p in sorted(paths)},'inputs':{str(p):c.sha(p) for p in inputs},'prior_seal':c.verify_prior(),'resources':c.resources(),'dependencies':{n:importlib.metadata.version(n) for n in ['numpy','scipy','Pillow']}})
    c.status('sources_locked_awaiting_evaluation');print(json.dumps({'frozen_cases':len(P['cases']),'prior_seal':c.verify_prior()}))

def maxerr(a,b):return float(np.max(abs(a-b)))

def error_stats(actual,expected,mask=None):
    delta=np.asarray(actual,float)-np.asarray(expected,float)
    if mask is not None:delta=delta[mask]
    if delta.size==0:return {'sites':0,'over':0.,'under':0.,'signed':0.,'L1':0.,'max_abs':0.,'mismatch_sites':0}
    return {'sites':int(delta.size),'over':float(np.maximum(delta,0).sum()),'under':float(np.maximum(-delta,0).sum()),'signed':float(delta.sum()),'L1':float(abs(delta).sum()),'max_abs':float(abs(delta).max()),'mismatch_sites':int((abs(delta)>1e-10).sum())}

def known_masses(spec):
    a,b=np.asarray(spec['projected_path'],float)[[0,-1]];length=float(np.linalg.norm(b-a));r=2*length
    if a[1]==b[1]:owned=length;hidden=0.
    else:
        owned=r
        hidden=0. if 'extra' not in spec else (spec['extra']['bounds_high_xyxy'][2]-spec['extra']['bounds_high_xyxy'][0])*2*length/abs(b[0]-a[0])
    return {'ribbon':r,'owned':owned,'occluded':hidden,'visible':owned-hidden,'unsupported':r-owned}

def reference_gates(a,spec):
    raw={k:a['raw_'+k] for k in ['ribbon','owned','occluded','visible','unsupported']}
    r,o,h,v,u=[raw[k] for k in ['ribbon','owned','occluded','visible','unsupported']]
    gates={'raw_finite':all(np.isfinite(x).all() for x in raw.values()),'raw_range':bool((r>=-1e-10).all() and (r<=1+1e-10).all() and (o>=-1e-10).all() and (o<=r+1e-10).all() and (h>=-1e-10).all() and (h<=o+1e-10).all()),'raw_partition':maxerr(r,v+h+u)<=1e-10}
    expected=known_masses(spec)
    for k in raw:
        gates['global_integral_'+k]=abs(float(raw[k].sum())-float(a['global_'+k]))<=1e-8
        gates['closed_form_'+k]=abs(float(raw[k].sum())-expected[k])<=1e-8
    names=['physical_boundary','visible_interior','hidden_interior','unsupported_interior','outside_ribbon']
    gates['disjoint_complete_subsets']=bool(np.array_equal(sum(a['subset_'+n].astype(int) for n in names),np.ones(r.shape,int)))
    gates['nonempty_visible_interior']=bool(a['subset_visible_interior'].any())
    if spec['id']=='area_oblique_visible':gates['all_visible_no_boundary']=not bool(a['subset_physical_boundary'].any())
    else:gates['nonempty_physical_boundary']=bool(a['subset_physical_boundary'].any())
    if spec['id']=='area_oblique_partial_hidden':gates['nonempty_hidden_interior']=bool(a['subset_hidden_interior'].any())
    if 'owner_edge' in spec['id']:gates['nonempty_unsupported_interior']=bool(a['subset_unsupported_interior'].any())
    return {k:bool(v) for k,v in gates.items()}

def promotion_gates(a):
    if 'candidate_high' not in a:return {'candidate_completed':False}
    return {'full_physical_area':maxerr(a['candidate_visible_area'],a['reference_visible'])<=1e-10,
            'area_mass':abs(float(a['candidate_visible_area'].sum()-a['reference_visible'].sum()))<=1e-8,
            'high_ink':maxerr(a['candidate_high'],a['reference_high'])<=1e-10,
            'ink_mass':abs(float(a['candidate_high'].sum()-a['reference_high'].sum()))<=1e-8,
            'quantized_exact':bool(np.array_equal(a['candidate_quantized_uint8'],a['reference_quantized_uint8'])),
            'final_exact':bool(np.array_equal(a['candidate_final_uint8'],a['reference_final_uint8']))}

def evaluate_case(spec):
    mesh,cam,path,owners,segments,grid,center_truth=fixture.fixture(P,spec)
    prescribed=np.asarray(spec['projected_path'],float)
    clean,raw,glob=oracle.reference(prescribed,128,2.,P['geometry']['analytic_owner']['bounds_high_xyxy'],4.,spec.get('extra'))
    a={**{'reference_'+k:v for k,v in clean.items()},**{'raw_'+k:v for k,v in raw.items()},**{'global_'+k:np.array(v) for k,v in glob.items()},**{'subset_'+k:v for k,v in oracle.subsets(clean).items()},'prescribed_projected_path':prescribed,
       'reference_high':clean['visible']*.8,'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],'mesh_parts':mesh['parts'],'path':path,'owners':np.array(owners),'segment_faces':np.array(segments)}
    a['reference_quantized_uint8']=np.uint8(np.clip(a['reference_high'],0,1)*255)
    a['reference_final_uint8']=coverage_fixture.down(a['reference_high'],2)
    before=prior.prior.prior.prior.fingerprint((mesh,owners,segments,path));error=None
    try:
        result=adapter.render_validated(mesh,owners,segments,path,candidate.render,cam,.8,2,2.,.006)
        a.update({'candidate_'+k:v for k,v in result.items()})
        a['candidate_visible_area']=result['coverage']*result['gate']
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    immutable=before==prior.prior.prior.prior.fingerprint((mesh,owners,segments,path))
    gates=reference_gates(a,spec);gates['candidate_no_error']=error is None;gates['input_immutable']=immutable
    if error is None:
        gates['prescribed_projection']=maxerr(a['candidate_projected_path'],prescribed)<=1e-12
        gates['ribbon_unchanged']=maxerr(a['candidate_coverage'],a['reference_ribbon'])<=1e-10
    promote=promotion_gates(a);sub={}
    for name,mask in oracle.subsets(clean).items():
        sub[name]={'sites':int(mask.sum()),'ribbon_area':float(clean['ribbon'][mask].sum()),'physical_visible_area':float(clean['visible'][mask].sum()),'ribbon_fraction':float(clean['ribbon'][mask].sum()/clean['ribbon'].sum())}
        if error is None:sub[name].update(candidate_visible_area=float(a['candidate_visible_area'][mask].sum()),area_error=error_stats(a['candidate_visible_area'],clean['visible'],mask),ink_error=error_stats(a['candidate_high'],a['reference_high'],mask))
    stats={} if error else {'area':error_stats(a['candidate_visible_area'],clean['visible']),'high_ink':error_stats(a['candidate_high'],a['reference_high']),'quantized_ink':error_stats(a['candidate_quantized_uint8']/255.,a['reference_quantized_uint8']/255.),'final_ink':error_stats(a['candidate_final_uint8']/255.,a['reference_final_uint8']/255.)}
    m={'case_id':spec['id'],'exposed_fixture':True,'measurement_valid':all(gates.values()),'physical_promotion':all(promote.values()),'validity_gates':gates,'promotion_gates':promote,'candidate_error':error,'raw_masses':{k:float(v.sum()) for k,v in raw.items()},'global_integrals':glob,'closed_form_masses':known_masses(spec),'subsets':sub,'errors':stats,'input_fingerprint':before}
    return m,a

def historical_replay():
    count=0;records=[]
    for spec,tie in prior.all_specs():
        m,a=prior.evaluate_case(spec,tie);name=spec['id'];assert m==json.loads((c.P/'raw'/f'{name}.json').read_text()),name
        old=dict(np.load(c.P/'raw'/f'{name}.npz'));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k],err_msg=f'{name}/{k}');count+=1
        records.append({'case_id':name,'arrays_exact':len(a),'prior_go_preserved':m['case_go']})
    m,a=prior.negative_control();assert m==json.loads((c.P/'negative_control.json').read_text());old=dict(np.load(c.P/'raw/negative_control.npz'));assert set(a)==set(old)
    for k in a:np.testing.assert_array_equal(a[k],old[k]);count+=1
    older=prior.historical_replay()
    return {'round011_cases':records,'round011_arrays_exact':count,'round011_negative_exact':True,'older':older,'all_exact':count==609 and older['all_exact']}

def sensitivity(arrays):
    if not arrays or 'candidate_high' not in arrays[0]:return {'complete':False,'all_detected':False,'reason':'missing candidate array; retain incomplete evidence'}
    a=arrays[0];records=[];y,x=map(int,np.argwhere(a['reference_visible']>.5)[0])
    for label,mode in [('reference_delete','delete'),('reference_outside','outside')]:
        b={k:v.copy() for k,v in a.items()}
        if mode=='delete':b['raw_visible'][y,x]=0.
        else:b['raw_visible'][0,0]=.5
        gates=reference_gates(b,P['cases'][0]);records.append({'name':label,'detected':not gates['raw_partition'] and not gates['closed_form_visible'],'failed':[k for k,v in gates.items() if not v]})
    truth=a['reference_high'];ideal=truth.copy();ideal[y,x]-=.2
    stats=error_stats(ideal,truth);records.append({'name':'ideal_delete','detected':stats['under']>.19 and stats['over']==0,'metrics':stats})
    ideal=truth.copy();ideal[0,0]=.2;stats=error_stats(ideal,truth);records.append({'name':'ideal_add','detected':stats['over']>.19 and stats['under']==0,'metrics':stats})
    ideal=truth.copy();ideal[y,x]-=.2;ideal[0,0]=.2;stats=error_stats(ideal,truth);records.append({'name':'equal_mass_relocation','detected':abs(stats['signed'])<1e-10 and stats['L1']>.39,'metrics':stats})
    b={k:v.copy() for k,v in a.items()};b['candidate_final_uint8']=b['reference_final_uint8'].copy();b['candidate_final_uint8'][0,0]=1
    records.append({'name':'final_corruption','detected':not promotion_gates(b)['final_exact']})
    return {'complete':True,'controls':records,'all_detected':all(r['detected'] for r in records)}

def contact(records,arrays):
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    titles=['Frozen center-gated output','Physical area reference','High area: red over / blue under','Visibility domains']
    sheet=Image.new('RGB',(1320,110+len(records)*365),'white');draw=ImageDraw.Draw(sheet)
    draw.text((12,8),'Within-pixel visibility audit | All exposed full views | Analytic GT only',font=font(23),fill='black')
    draw.text((12,40),'Green: visible interior. Red: occluded interior. Orange: unsupported. Purple: mixed physical visibility.',font=font(16),fill='black')
    draw.text((12,67),'Error color intensity = absolute area error (linear 0 to 1); no spatial crop. Background surface is illustrative.',font=font(15),fill='black')
    for row,(m,a) in enumerate(zip(records,arrays)):
        top=100+row*365
        draw.text((12,top),f"{m['case_id']} | valid {m['measurement_valid']} | physical GO {m['physical_promotion']}",font=font(17),fill='black')
        bg=np.full((64,64,3),255.);panels=[]
        scene=np.isfinite(a.get('candidate_scene_depth',np.full((128,128),np.inf)))
        domain=np.asarray(Image.fromarray(np.uint8(scene)*255).resize((64,64),Image.Resampling.NEAREST))>0;bg[domain]=[215,233,245]
        for key in ['candidate_final_uint8','reference_final_uint8']:
            ink=a.get(key,np.zeros((64,64),np.uint8))/255.;panels.append(Image.fromarray(np.uint8(bg*(1-ink[...,None]))))
        delta=a.get('candidate_visible_area',np.zeros((128,128)))-a['reference_visible'];err=np.ones((128,128,3))*255
        over=np.maximum(delta,0).clip(0,1);under=np.maximum(-delta,0).clip(0,1);err[...,1]*=(1-over)*(1-under);err[...,2]*=1-over;err[...,0]*=1-under
        panels.append(Image.fromarray(np.uint8(err)))
        domains=np.full((128,128,3),255,np.uint8)
        for name,color in [('visible_interior',[20,140,60]),('hidden_interior',[200,30,30]),('unsupported_interior',[235,145,20]),('physical_boundary',[145,50,180])]:domains[a['subset_'+name]]=color
        panels.append(Image.fromarray(domains))
        for col,panel in enumerate(panels):
            xx=12+col*330;draw.text((xx,top+28),titles[col],font=font(14),fill='black');sheet.paste(panel.resize((300,300),Image.Resampling.NEAREST).convert('RGB'),(xx,top+52))
    sheet.save(c.R/'figures/full_view_contact_sheet.png')

def summary(records,regression,mutations):
    gates={'four_exposed_cases':len(records)==4,'all_reference_controls':all(r['measurement_valid'] for r in records),'historical_exact':regression['all_exact'],'sensitivity':mutations['all_detected'],'center_reference_RED':json.loads((c.R/'RED_CENTER_REFERENCE.json').read_text())['returncode']==1}
    for n in TESTS:gates[n.lower()]=json.loads((c.R/(n+'.json')).read_text())['returncode']==0
    valid=all(gates.values());promote=valid and all(r['physical_promotion'] for r in records)
    return {'complete':True,'measurement_valid':valid,'physical_promotion':promote,'verdict':'PHYSICAL_VISIBILITY_GO' if promote else ('MEASUREMENT_VALID_PHYSICAL_VISIBILITY_NO_GO' if valid else 'ENGINEERING_INVALID'),'gates':gates,'cases':records,'regression':regression,'sensitivity':mutations,'limits':P['limits']}

def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for name in ['raw','figures']:(c.R/name).mkdir(exist_ok=True)
    c.status('evaluating_frozen_physical_reference');records=[];arrays=[];start=time.monotonic()
    for spec in P['cases']:
        c.resources();m,a=evaluate_case(spec);records.append(m);arrays.append(a)
        c.write(c.R/'raw'/f"{spec['id']}.json",m);np.savez_compressed(c.R/'raw'/f"{spec['id']}.npz",**a)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'cases':records})
        print(json.dumps({'case':spec['id'],'valid':m['measurement_valid'],'physical_go':m['physical_promotion'],'errors':m['errors']}),flush=True)
    mutations=sensitivity(arrays);c.write(c.R/'SENSITIVITY.json',mutations)
    regression=historical_replay();c.write(c.R/'REGRESSION.json',regression)
    contact(records,arrays);out=summary(records,regression,mutations);out['wall_seconds']=time.monotonic()-start;out['resources']=c.resources();c.write(c.R/'metrics.json',out)
    c.status('evaluated_awaiting_exact_replay',scientific_verdict=out['verdict']);print(json.dumps({'verdict':out['verdict'],'gates':out['gates']}),flush=True)

def validate():
    c.verify_lock();c.verify_prior();c.resources();saved=json.loads((c.R/'metrics.json').read_text());records=[];arrays=[];count=0
    for spec in P['cases']:
        m,a=evaluate_case(spec);assert m==json.loads((c.R/'raw'/f"{spec['id']}.json").read_text());old=dict(np.load(c.R/'raw'/f"{spec['id']}.npz"));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k]);count+=1
        records.append(m);arrays.append(a)
    mutations=sensitivity(arrays);regression=historical_replay();out=summary(records,regression,mutations)
    for k in out:assert out[k]==saved[k],k
    result={'complete':True,'cases_exact':len(records),'arrays_exact':count,'all_metrics_exact':True,'regression':regression,'measurement_valid':out['measurement_valid'],'physical_promotion':out['physical_promotion'],'prior_seal':c.verify_prior(),'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',result);c.status('validated_awaiting_report');print(json.dumps({'complete':True,'cases_exact':len(records),'arrays_exact':count,'measurement_valid':out['measurement_valid'],'physical_go':out['physical_promotion']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','evaluate','validate']);args=p.parse_args()
    try:globals()[args.command]()
    except Exception as exc:
        c.status('interrupted_or_engineering_failure',execution_state='incomplete',scientific_verdict='ENGINEERING_INVALID',blockers=[type(exc).__name__+': '+str(exc)])
        n=json.loads((c.R/'NEXT.json').read_text());n.update(action='stop',priority='recover_failed_round012',recommended_next_step='Inspect retained receipt, log, and partial arrays. No physical promotion or renderer changes. Resolve engineering validity before any new science.',blockers=[type(exc).__name__+': '+str(exc)]);c.write(c.R/'NEXT.json',n)
        raise
