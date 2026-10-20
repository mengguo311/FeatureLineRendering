"""Prefrozen finite planar visible-fragment experiment, serial CPU only."""
import round013_common as c
import argparse,copy,importlib.metadata,json,subprocess,time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import core,mesh_attachment as adapter
import planar_fragments as candidate
import physical_area_reference as oracle
import round010_fixture as fixture
import coverage_fixture
import run_round012 as prior
P=json.loads((c.D/'PROTOCOL.json').read_text())
NEW=['round013_common.py','round013_receipt.py','build_round013_protocol.py','planar_fragments.py','test_planar_fragments.py','run_round013.py','seal_round013.py']
TESTS=['INHERITED_ATTACHMENT','INHERITED_PATCH','INHERITED_CANDIDATE','INHERITED_ORACLE','INHERITED_TEMPORAL','INHERITED_STAGE','INHERITED_CENTERED','INHERITED_AREA','INHERITED_REFERENCE','GREEN_FRAGMENTS_VALID']
NAMES=['ribbon','owned','occluded','visible','unsupported']

def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    old=json.loads((c.W/'docs/partwise_sketch_hatching/round_012/ASSET_LOCK.json').read_text())
    for path,h in old['sources'].items():assert c.sha(c.W/path)==h,path
    for name,h in P['candidate_sources_preserved'].items():assert c.sha(c.W/'experiments/partwise_sketch_hatching'/name)==h,name
    paths={c.W/p for p in old['sources']}|{c.W/'experiments/partwise_sketch_hatching'/n for n in NEW}|{p for p in c.D.iterdir() if p.is_file()}
    paths|={c.W/'docs/partwise_sketch_hatching/round_012'/n for n in ['ASSET_LOCK.json','REPORT_ZH.md','REPRODUCE.md']}
    inputs=[c.P/n for n in ['STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json','metrics.json','REGRESSION.json','VALIDATION.json']]
    c.write(c.D/'ASSET_LOCK.json',{'protocol_commit':'f3e2ee1b','implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),'sources':{str(p.relative_to(c.W)):c.sha(p) for p in sorted(paths)},'inputs':{str(p):c.sha(p) for p in inputs},'prior_seal':c.verify_prior(),'resources':c.resources(),'dependencies':{n:importlib.metadata.version(n) for n in ['numpy','scipy','Pillow']}})
    c.status('sources_locked_awaiting_evaluation');print(json.dumps({'cases':len(P['cases']),'prior':c.verify_prior()}))

def fixture_for(spec):
    protocol={**P,'geometry':spec.get('geometry',P['geometry'])}
    return fixture.fixture(protocol,spec)

def masses(spec):
    a,b=np.asarray(spec['projected_path'])[[0,-1]];length=float(np.linalg.norm(b-a));r=length*2
    owned=r/2 if spec['mass_kind']=='half' else r
    if spec['mass_kind']=='hidden':hidden=owned
    elif spec['mass_kind']=='strip':hidden=(spec['extra']['bounds_high_xyxy'][2]-spec['extra']['bounds_high_xyxy'][0])*2*length/abs(b[0]-a[0])
    else:hidden=0.
    return {'ribbon':r,'owned':owned,'occluded':hidden,'visible':owned-hidden,'unsupported':r-owned}

def reference_gates(a,spec):
    raw={k:a['reference_raw_'+k] for k in NAMES};r,o,h,v,u=[raw[k] for k in NAMES]
    gates={'raw_finite':all(np.isfinite(x).all() for x in raw.values()),
           'raw_range':bool((r>=-1e-10).all() and (r<=1+1e-10).all() and (o>=-1e-10).all() and (o<=r+1e-10).all() and (h>=-1e-10).all() and (h<=o+1e-10).all()),
           'raw_partition':prior.maxerr(r,v+h+u)<=1e-10}
    expected=masses(spec)
    for k in NAMES:
        gates['global_'+k]=abs(float(raw[k].sum()-a['reference_global_'+k]))<=1e-8
        gates['closed_form_'+k]=abs(float(raw[k].sum())-expected[k])<=1e-8
    subsets=['physical_boundary','visible_interior','hidden_interior','unsupported_interior','outside_ribbon']
    gates['disjoint_complete_subsets']=bool(np.array_equal(sum(a['subset_'+n].astype(int) for n in subsets),np.ones(r.shape,int)))
    for n in spec['required_subsets']:gates['nonempty_'+n]=bool(a['subset_'+n].any())
    if spec['mass_kind']=='hidden':gates['fully_hidden_visible_zero']=bool(not np.any(a['reference_visible']) and a['reference_occluded'].sum()>0)
    return {k:bool(v) for k,v in gates.items()}

def promotion_gates(a):
    if 'candidate_visible' not in a:return {'candidate_completed':False}
    r,o,h,v,u=[a['candidate_raw_'+k] for k in NAMES]
    gates={'candidate_raw_finite':all(np.isfinite(a['candidate_raw_'+k]).all() for k in NAMES),
           'candidate_raw_range':bool((r>=-1e-10).all() and (r<=1+1e-10).all() and (o>=-1e-10).all() and (o<=r+1e-10).all() and (v>=-1e-10).all() and (v<=o+1e-10).all()),
           'candidate_raw_partition':prior.maxerr(r,v+h+u)<=1e-10}
    for name in NAMES:
        gates['raw_'+name]=prior.maxerr(a['candidate_raw_'+name],a['reference_raw_'+name])<=1e-10
        gates['clean_'+name]=prior.maxerr(a['candidate_'+name],a['reference_'+name])<=1e-10
        gates['mass_'+name]=abs(float(a['candidate_raw_'+name].sum()-a['reference_raw_'+name].sum()))<=1e-8
    gates.update(high_ink=prior.maxerr(a['candidate_high'],a['reference_high'])<=1e-10,
                 ink_mass=abs(float(a['candidate_high'].sum()-a['reference_high'].sum()))<=1e-8,
                 quantized_exact=bool(np.array_equal(a['candidate_quantized_uint8'],a['reference_quantized_uint8'])),
                 final_exact=bool(np.array_equal(a['candidate_final_uint8'],a['reference_final_uint8'])))
    return gates

def variant_results(mesh,owners,segments,path,cam):
    def call(m,o,s,p):return adapter.render_validated(m,o,s,p,candidate.render,cam,.8,2,2.,.006)
    yield 'owner_order',call(mesh,owners[::-1],segments,path)
    yield 'path_reverse',call(mesh,owners,segments[::-1],path[::-1])
    f=mesh['faces'];v=mesh['vertices'];parts=mesh['parts'];order=np.arange(len(f))[::-1];inv=np.argsort(order)
    m=core.finalize_mesh(v,f[order][:,::-1],parts[order])
    yield 'face_order_winding',call(m,inv[owners].tolist(),inv[segments].tolist(),path)
    m=core.finalize_mesh(v,np.concatenate([f,f[owners]]),np.concatenate([parts,parts[owners]]))
    yield 'duplicate_owners',call(m,owners+list(range(len(f),len(f)+len(owners))),segments,path)
    extra=[i for i in range(len(f)) if i not in owners]
    if extra:
        m=core.finalize_mesh(v,np.concatenate([f,f[extra]]),np.concatenate([parts,parts[extra]]))
        yield 'duplicate_occluders',call(m,owners,segments,path)

def evaluate_case(spec):
    mesh,cam,path,owners,segments,_,_=fixture_for(spec)
    g=spec.get('geometry',P['geometry']);clean,raw,glob=oracle.reference(spec['projected_path'],128,2.,g['analytic_owner']['bounds_high_xyxy'],4.,spec.get('extra'))
    a={**{'reference_'+k:v for k,v in clean.items()},**{'reference_raw_'+k:v for k,v in raw.items()},**{'reference_global_'+k:np.array(v) for k,v in glob.items()},**{'subset_'+k:v for k,v in oracle.subsets(clean).items()},
       'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],'mesh_parts':mesh['parts'],'path':path,'owners':np.array(owners),'segment_faces':np.array(segments),'prescribed_projected_path':np.array(spec['projected_path'])}
    a['reference_high']=clean['visible']*.8;a['reference_quantized_uint8']=np.uint8(np.clip(a['reference_high'],0,1)*255);a['reference_final_uint8']=coverage_fixture.down(a['reference_high'],2)
    fingerprint=prior.prior.prior.prior.prior.fingerprint
    before=fingerprint((mesh,owners,segments,path));error=None;variants={}
    try:
        result=adapter.render_validated(mesh,owners,segments,path,candidate.render,cam,.8,2,2.,.006)
        a.update({'candidate_'+k:v for k,v in result.items()})
        for name,result2 in variant_results(mesh,owners,segments,path,cam):
            vg={}
            for k in NAMES+['high','quantized_uint8','final_uint8']:
                a['variant_'+name+'_'+k]=result2[k];vg[k]=bool(np.array_equal(result[k],result2[k]))
            for k in NAMES:
                a['variant_'+name+'_raw_'+k]=result2['raw_'+k];vg['raw_'+k]=prior.maxerr(result['raw_'+k],result2['raw_'+k])<=1e-10
            variants[name]=vg
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    valid=reference_gates(a,spec);valid['candidate_completed']=error is None;valid['input_immutable']=before==fingerprint((mesh,owners,segments,path))
    promotion=promotion_gates(a)
    if error is None:
        valid['projection']=prior.maxerr(a['candidate_projected_path'],a['prescribed_projected_path'])<=1e-12
        promotion['order_invariants']=all(all(v.values()) for v in variants.values())
        if spec['id']=='area_oblique_partial_hidden':
            promotion['exposed_visible_sliver_60_60']=bool(abs(a['candidate_visible'][60,60]-a['reference_visible'][60,60])<=1e-10 and a['candidate_visible'][60,60]>0)
    subsets={}
    for name,mask in oracle.subsets(clean).items():
        subsets[name]={'sites':int(mask.sum()),'ribbon_area':float(clean['ribbon'][mask].sum()),'visible_area':float(clean['visible'][mask].sum())}
        if error is None:subsets[name]['area_error']=prior.error_stats(a['candidate_visible'],clean['visible'],mask)
    errors={} if error else {'raw_area':prior.error_stats(a['candidate_raw_visible'],a['reference_raw_visible']), 'area':prior.error_stats(a['candidate_visible'],a['reference_visible']), 'high_ink':prior.error_stats(a['candidate_high'],a['reference_high']), 'quantized_ink':prior.error_stats(a['candidate_quantized_uint8']/255.,a['reference_quantized_uint8']/255.),'final_ink':prior.error_stats(a['candidate_final_uint8']/255.,a['reference_final_uint8']/255.)}
    m={'case_id':spec['id'],'exposed':spec['exposed'],'measurement_valid':all(valid.values()),'candidate_go':all(promotion.values()),'validity_gates':valid,'promotion_gates':promotion,'ordering_gates':variants,'candidate_error':error,'reference_raw_masses':{k:float(v.sum()) for k,v in raw.items()},'closed_form_masses':masses(spec),'candidate_raw_masses':{} if error else {k:float(a['candidate_raw_'+k].sum()) for k in NAMES},'subsets':subsets,'errors':errors,'input_fingerprint':before}
    return m,a

def rejections():
    spec=P['cases'][0];base,cam,path,owners,segments,_,_=fixture_for(spec);records=[]
    for label in P['rejection_controls']:
        m=copy.deepcopy(base);o=owners.copy();s=segments.copy();p=path.copy()
        if label=='non-frontoparallel scene':
            ss=copy.deepcopy(spec);ss['extra']={'z':3.,'bounds_high_xyxy':[59.25,40.25,70.25,88.25],'part_id':2};m=fixture_for(ss)[0];m['vertices'][4,2]+=.1;code='nonfrontoparallel_triangle'
        elif label=='noncoplanar owners':
            v=np.concatenate([m['vertices'],m['vertices'][:3]+[0,0,1.]])
            m=core.finalize_mesh(v,np.concatenate([m['faces'],[[4,5,6]]]),np.r_[m['parts'],1]);o.append(2);code='noncoplanar_owners'
        elif label in ['co-depth nonowner','near-depth nonowner','nonpositive scene depth']:
            z={'co-depth nonowner':4.,'near-depth nonowner':4.003,'nonpositive scene depth':-1.}[label]
            ss=copy.deepcopy(spec);ss['extra']={'z':z,'bounds_high_xyxy':[59.25,40.25,70.25,88.25],'part_id':2};m=fixture_for(ss)[0];code='nonpositive_scene_depth' if z<0 else 'ambiguous_nonowner_depth'
        elif label=='bent path':
            _,_,p,o,s,_,_=fixture_for(P['cases'][5]);p=np.array([p[0],(p[0]+p[-1])/2+[0,-.1,0],p[-1]]);s=[0,0];code='only straight projected paths supported'
        elif label=='detached path':p[0,2]+=.1;code='off_plane'
        m['tri']=m['vertices'][m['faces']]
        try:adapter.render_validated(m,o,s,p,candidate.render,cam,.8,2,2.,.006);error=None
        except Exception as exc:error=str(exc)
        records.append({'case':label,'expected_error':code,'observed_error':error,'passed':error is not None and code in error})
    return {'controls':records,'all_rejected':all(r['passed'] for r in records)}

def historical_replay():
    count=0;records=[]
    for spec in prior.P['cases']:
        m,a=prior.evaluate_case(spec);name=spec['id'];assert m==json.loads((c.P/'raw'/f'{name}.json').read_text()),name
        old=dict(np.load(c.P/'raw'/f'{name}.npz'));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k],err_msg=f'{name}/{k}');count+=1
        records.append({'case_id':name,'arrays_exact':len(a),'prior_NO_GO_preserved':not m['physical_promotion']})
    older=prior.historical_replay()
    return {'round012_cases':records,'round012_arrays_exact':count,'older':older,'all_exact':count==172 and older['all_exact']}

def sensitivity(a):
    records=[];y,x=map(int,np.argwhere(a['reference_visible']>.5)[0])
    for mode in ['delete','outside']:
        b={k:v.copy() for k,v in a.items()}
        if mode=='delete':b['reference_raw_visible'][y,x]=0.
        else:b['reference_raw_visible'][0,0]=.5
        g=reference_gates(b,P['cases'][0]);records.append({'name':'reference_'+mode,'detected':not g['raw_partition'] and not g['closed_form_visible']})
    truth=a['reference_high']
    for mode in ['delete','add','relocate']:
        b=truth.copy()
        if mode in ['delete','relocate']:b[y,x]-=.2
        if mode in ['add','relocate']:b[0,0]+=.2
        stats=prior.error_stats(b,truth);detected=stats['L1']>.19
        if mode=='relocate':detected=abs(stats['signed'])<1e-10 and stats['L1']>.39
        records.append({'name':'ideal_'+mode,'detected':detected,'metrics':stats})
    b={k:v.copy() for k,v in a.items()};b['candidate_final_uint8']=b['reference_final_uint8'].copy();b['candidate_final_uint8'][0,0]=1
    records.append({'name':'final_corruption','detected':not promotion_gates(b)['final_exact']})
    return {'controls':records,'all_detected':all(r['detected'] for r in records)}

def contact(records,arrays):
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    sheet=Image.new('RGB',(1160,85+len(records)*290),'white');d=ImageDraw.Draw(sheet)
    d.text((12,8),'Planar visible fragments | All full views | Analytic GT only',font=font(23),fill='black')
    d.text((12,40),'Fixed 64x64 output, 2x area grid. Error: red over / blue under (linear 0 to 1).',font=font(17),fill='black')
    for i,(m,a) in enumerate(zip(records,arrays)):
        top=80+i*290;d.text((12,top),f"{m['case_id']} | {'exposed' if m['exposed'] else 'new'} | GO {m['candidate_go']}",font=font(15),fill='black')
        panels=[]
        for k in ['candidate_final_uint8','reference_final_uint8']:
            panels.append(Image.fromarray(255-a.get(k,np.zeros((64,64),np.uint8))))
        delta=a.get('candidate_visible',np.zeros((128,128)))-a['reference_visible'];err=np.ones((128,128,3))*255
        over=np.maximum(delta,0).clip(0,1);under=np.maximum(-delta,0).clip(0,1);err[...,1]*=(1-over)*(1-under);err[...,2]*=1-over;err[...,0]*=1-under;panels.append(Image.fromarray(np.uint8(err)))
        domain=np.full((128,128,3),255,np.uint8)
        for name,col in [('visible_interior',[20,140,60]),('hidden_interior',[200,30,30]),('unsupported_interior',[235,145,20]),('physical_boundary',[145,50,180])]:domain[a['subset_'+name]]=col
        panels.append(Image.fromarray(domain))
        for j,(panel,title) in enumerate(zip(panels,['Mesh fragment output','Independent area reference','Area difference','Visibility subsets'])):
            x=12+j*290;d.text((x,top+22),title,font=font(14),fill='black');sheet.paste(panel.resize((240,240),Image.Resampling.NEAREST).convert('RGB'),(x,top+44))
    sheet.save(c.R/'figures/full_view_contact_sheet.png')

def summary(records,regression,reject,mutations):
    gates={'ten_frozen_cases':len(records)==10,'reference_controls':all(r['measurement_valid'] for r in records),'historical_exact':regression['all_exact'],'rejection_controls':reject['all_rejected'],'sensitivity':mutations['all_detected'],'actual_old_RED':json.loads((c.R/'RED_OLD_RENDERER_VALID.json').read_text())['returncode']==1}
    for n in TESTS:gates[n.lower()]=json.loads((c.R/(n+'.json')).read_text())['returncode']==0
    valid=all(gates.values());go=valid and all(r['candidate_go'] for r in records)
    return {'complete':True,'measurement_valid':valid,'candidate_go':go,'verdict':'FINITE_PLANAR_FRAGMENT_GO' if go else ('MEASUREMENT_VALID_FRAGMENT_NO_GO' if valid else 'ENGINEERING_INVALID'),'gates':gates,'cases':records,'regression':regression,'rejections':reject,'sensitivity':mutations,'limits':P['limits']}

def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for n in ['raw','figures']:(c.R/n).mkdir(exist_ok=True)
    c.status('evaluating_frozen_fragment_mechanism');records=[];arrays=[];start=time.monotonic()
    for spec in P['cases']:
        c.resources();m,a=evaluate_case(spec);records.append(m);arrays.append(a)
        c.write(c.R/'raw'/f"{spec['id']}.json",m);np.savez_compressed(c.R/'raw'/f"{spec['id']}.npz",**a);c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'cases':records})
        print(json.dumps({'case':spec['id'],'valid':m['measurement_valid'],'go':m['candidate_go'],'error':m['candidate_error'],'failed':[k for k,v in m['promotion_gates'].items() if not v]}),flush=True)
    reject=rejections();c.write(c.R/'REJECTIONS.json',reject);mutations=sensitivity(arrays[0]);c.write(c.R/'SENSITIVITY.json',mutations)
    regression=historical_replay();c.write(c.R/'REGRESSION.json',regression);contact(records,arrays)
    out=summary(records,regression,reject,mutations);out['wall_seconds']=time.monotonic()-start;out['resources']=c.resources();c.write(c.R/'metrics.json',out);c.status('evaluated_awaiting_replay',scientific_verdict=out['verdict']);print(json.dumps({'verdict':out['verdict'],'gates':out['gates']}))

def validate():
    c.verify_lock();c.verify_prior();c.resources();saved=json.loads((c.R/'metrics.json').read_text());records=[];arrays=[];count=0
    for spec in P['cases']:
        m,a=evaluate_case(spec);assert m==json.loads((c.R/'raw'/f"{spec['id']}.json").read_text());old=dict(np.load(c.R/'raw'/f"{spec['id']}.npz"));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k]);count+=1
        records.append(m);arrays.append(a)
    regression=historical_replay();out=summary(records,regression,rejections(),sensitivity(arrays[0]))
    for k in out:assert out[k]==saved[k],k
    result={'complete':True,'cases_exact':len(records),'arrays_exact':count,'all_metrics_exact':True,'regression':regression,'measurement_valid':out['measurement_valid'],'candidate_go':out['candidate_go'],'prior_seal':c.verify_prior(),'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',result);c.status('validated_awaiting_report');print(json.dumps({'cases_exact':len(records),'arrays_exact':count,'verdict':out['verdict']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','evaluate','validate']);args=parser.parse_args()
    try:globals()[args.command]()
    except Exception as exc:
        c.status('interrupted_or_engineering_failure',execution_state='incomplete',scientific_verdict='ENGINEERING_INVALID',blockers=[type(exc).__name__+': '+str(exc)])
        n=json.loads((c.R/'NEXT.json').read_text());n.update(action='stop',priority='recover_round013',recommended_next_step='Recover retained round013 logs and partial arrays. No promotion or new science before validity is resolved.',blockers=[type(exc).__name__+': '+str(exc)]);c.write(c.R/'NEXT.json',n);raise
