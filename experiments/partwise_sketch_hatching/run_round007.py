"""One frozen noncoplanar patch diagnostic; no changes to visibility primitive."""
import round007_common as c
import argparse
import datetime
import importlib.metadata
import json
import subprocess
import time
import traceback
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import patch_fixture as trial
import run_round006 as prior_runner
import visibility_trial as prior_trial
P=json.loads((c.D/'PROTOCOL.json').read_text())
NEW=['round007_common.py','round007_receipt.py','patch_fixture.py','test_patch_attachment.py','run_round007.py','seal_round007.py']
RECEIPTS=['TESTS_GREEN_REPAIRED','INHERITED_CANDIDATE','INHERITED_ORACLE','INHERITED_TEMPORAL','INHERITED_STAGE']


def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists();prior=c.verify_prior();c.write(c.R/'PRIOR_SEAL_VERIFY.json',prior)
    old=json.loads((c.W/'docs/partwise_sketch_hatching/round_006/ASSET_LOCK.json').read_text())
    for p,h in old['sources'].items():assert c.sha(c.W/p)==h,p
    assert c.sha(c.W/'experiments/partwise_sketch_hatching/visibility_primitive.py')==P['candidate_source_sha256']
    paths={c.W/p for p in old['sources']}|{c.W/'experiments/partwise_sketch_hatching'/n for n in NEW}|{p for p in c.D.iterdir() if p.is_file()}
    paths.add(c.W/'docs/partwise_sketch_hatching/round_006/ASSET_LOCK.json')
    inputs=[c.P/n for n in ['SEAL.json','SHA256_MANIFEST.json','STATUS.json','NEXT.json','metrics.json','VALIDATION.json']]
    lock={'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),'protocol_commit':'1f1ff148','sources':{str(p.relative_to(c.W)):c.sha(p) for p in sorted(paths)},'inputs':{str(p):c.sha(p) for p in inputs},'prior_seal':prior,'resources':c.resources(),'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','Pillow']},'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    c.write(c.D/'ASSET_LOCK.json',lock);c.status('source_locked_awaiting_acceptance',artifacts=['PRIOR_SEAL_VERIFY.json'])
    print(json.dumps({'sources':len(paths),'prior':prior,'new_cases':12}),flush=True)


def safe_case(spec):
    try:return trial.evaluate_case(P,spec)
    except Exception as exc:
        cam,faces,extras,mesh,path=trial.fixture(P,spec)
        yy,xx=np.mgrid[:cam['size'],:cam['size']];grid=np.stack((xx,yy),axis=-1)
        truth=trial.truth(grid,faces,extras,cam)
        return {'case_id':spec['id'],'case_go':False,'engineering_invalid':True,'exception':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}, {'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],'stroke_path':path,**{'oracle_'+k:v for k,v in truth.items()}}


def plane_regression():
    arrays=0;historical=0;cases=[]
    for split,spec,old in prior_runner.cases():
        m,a=prior_trial.evaluate_case(prior_runner.P,spec,split);name=f"{split}_{spec['id']}"
        assert m==json.loads((c.P/'raw'/f'{name}.json').read_text()),name
        saved=dict(np.load(c.P/'raw'/f'{name}.npz'));assert set(a)==set(saved)
        for key in a:np.testing.assert_array_equal(a[key],saved[key],err_msg=f'{name}/{key}');arrays+=1
        if old is not None:historical+=prior_runner.original_replay(spec,old)
        cases.append({'case_id':name,'case_metrics_exact':True,'array_count':len(a),'original_round005_replayed':old is not None})
    return {'cases':cases,'cases_exact':len(cases),'round006_arrays_exact':arrays,'round005_arrays_exact':historical,'all_exact':len(cases)==38 and arrays==1634 and historical==860}


def font(n):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
def surface(ids,ink):
    palette=np.array([[255,255,255],[217,235,247],[192,212,233],[237,207,168],[222,203,236]],float)
    return np.uint8(np.clip(palette[ids]*(1-ink[...,None]),0,255))
def panels(m,a):
    pane=240;sheet=Image.new('RGB',(6*pane+56,pane+120),'white');d=ImageDraw.Draw(sheet)
    d.text((8,5),f"{m['case_id']} | analytic finite noncoplanar diagnostic GT | GO={m['case_go']}",fill='black',font=font(16))
    if 'engineering_invalid' in m:
        d.text((8,45),m['message'],fill='red',font=font(14));sheet.save(c.R/'figures'/f"{m['case_id']}.png");return
    diff=surface(a['oracle_component'],np.zeros(a['candidate_high'].shape));act=a['candidate_high']>0;ref=a['matched_reference']>0
    diff[act&ref]=[20,20,20];diff[ref&~act]=[220,30,30];diff[act&a['oracle_hidden']]=[210,25,190];diff[act&a['oracle_unsupported']]=[20,170,90]
    ims=[('Legacy final AA',surface(a['AA_component'],a['legacy_final_uint8']/255.)),('Candidate final AA',surface(a['AA_component'],a['candidate_final_uint8']/255.)),('Matched reference',surface(a['AA_component'],a['matched_final_uint8']/255.)),('Centered piecewise ribbon',surface(a['AA_component'],a['centered_final_uint8']/255.)),('High image difference',diff),('Raw pre-z expanded footprint',surface(a['oracle_component'],a['reference_expanded']))]
    for j,(label,im) in enumerate(ims):
        x=8+j*(pane+8);d.text((x,34),label,fill='black',font=font(12));sheet.paste(Image.fromarray(im).resize((pane,pane),Image.Resampling.NEAREST),(x,58))
    d.text((8,306),'Blue shades: two owner faces | Tan: front occluder | Purple: disconnected same-part sheet (not owner)',fill='black',font=font(14))
    d.text((8,328),'Diff: black retained | red missing | magenta hidden ink | green unsupported. All views uncropped.',fill='black',font=font(14))
    sheet.save(c.R/'figures'/f"{m['case_id']}.png")


def contact(records):
    cw,ch=540,182;sheet=Image.new('RGB',(3*cw,4*ch+62),'white');d=ImageDraw.Draw(sheet)
    d.text((8,5),'All 12 noncoplanar cases | Legacy / Candidate / Matched / Centered | full views',fill='black',font=font(17))
    d.text((8,28),'Analytic GT only. Blue: owner faces; tan: occluder; purple: disconnected same-part sheet.',fill='black',font=font(15))
    for i,m in enumerate(records):
        a=dict(np.load(c.R/'raw'/f"{m['case_id']}.npz"));x=i%3*cw;y=i//3*ch+62
        d.text((x+5,y+3),m['case_id'],fill='black',font=font(13))
        if 'engineering_invalid' in m:d.text((x+5,y+35),'ENGINEERING INVALID: '+m['message'],fill='red',font=font(12));continue
        for j,key in enumerate(['legacy_final_uint8','candidate_final_uint8','matched_final_uint8','centered_final_uint8']):
            im=surface(a['AA_component'],a[key]/255.);sheet.paste(Image.fromarray(im).resize((128,128),Image.Resampling.NEAREST),(x+5+j*134,y+24))
        d.text((x+5,y+157),f"GO {m['case_go']} | recall {m['high']['visible_recall']:.2f} | hidden {m['high']['hidden_ink_sites']} | unsupported {m['high']['unsupported_owner_ink_sites']}",fill='black',font=font(12))
    sheet.save(c.R/'figures/full_view_contact_sheet.png')


def summary(records,negative,regression):
    gates={'all12_ordinary':len(records)==12,'all_ordinary_gates':all(m['case_go'] for m in records),'all_negative_controls':negative['all_pass'],'exposed_plane_regressions_exact':regression['all_exact']}
    for name in RECEIPTS:gates[name.lower()]=json.loads((c.R/(name+'.json')).read_text())['returncode']==0
    return {'complete':len(records)==12,'patch_primitive_go':all(gates.values()),'gates':gates,'cases':records,'negative_controls':negative,'regression':regression,'limits':['Finite explicit two-face diagnostic GT only; no automatic owner discovery','Noncoplanar shared-edge exact integer query not directly covered by these fractional phases','Centered piecewise ribbon and AA tails remain diagnostics','Tolerance .006 and caller attachment preconditions unchanged','No lamp P1, RaDe-GS reconstruction or temporal stability evidence','Historical round004 NO_GO and null/mixed/UNKNOWN evidence unchanged']}


def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for n in ['raw','figures']:(c.R/n).mkdir(exist_ok=True)
    c.status('evaluating_frozen_non_coplanar_patch_suite');t=time.monotonic();records=[]
    for spec in P['acceptance']['cases']:
        c.resources();m,a=safe_case(spec);records.append(m);name=spec['id']
        np.savez_compressed(c.R/'raw'/f'{name}.npz',**a);c.write(c.R/'raw'/f'{name}.json',m);panels(m,a)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'cases':records})
        print(json.dumps({'case':name,'go':m['case_go'],'failed_gates':[k for k,v in m.get('gates',{}).items() if not v],'exception':m.get('message')}),flush=True)
    negative,na=trial.negative_controls(P);c.write(c.R/'negative_controls.json',negative);np.savez_compressed(c.R/'raw/negative_controls.npz',**na)
    regression=plane_regression();c.write(c.R/'PLANE_REGRESSION.json',regression);contact(records)
    result=summary(records,negative,regression);result['wall_seconds']=time.monotonic()-t;result['resources']=c.resources()
    c.write(c.R/'metrics.json',result);c.status('evaluated_awaiting_replay',scientific_verdict='PATCH_GO_PENDING_REPLAY' if result['patch_primitive_go'] else 'PATCH_NO_GO',artifacts=['metrics.json','negative_controls.json','PLANE_REGRESSION.json','raw/','figures/full_view_contact_sheet.png'])
    print(json.dumps({'go':result['patch_primitive_go'],'gates':result['gates'],'wall_seconds':result['wall_seconds']}),flush=True)


def validate():
    c.verify_lock();c.resources();saved=json.loads((c.R/'metrics.json').read_text());records=[];count=0
    for spec in P['acceptance']['cases']:
        m,a=safe_case(spec);name=spec['id'];assert m==json.loads((c.R/'raw'/f'{name}.json').read_text()),name
        old=dict(np.load(c.R/'raw'/f'{name}.npz'));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k],err_msg=f'{name}/{k}');count+=1
        records.append(m)
    neg,na=trial.negative_controls(P);assert neg==json.loads((c.R/'negative_controls.json').read_text());old=dict(np.load(c.R/'raw/negative_controls.npz'))
    for k in na:np.testing.assert_array_equal(na[k],old[k]);count+=1
    reg=plane_regression();result=summary(records,neg,reg)
    for key in result:assert result[key]==saved[key],key
    out={'complete':True,'cases_exact':len(records),'new_arrays_exact':count,'all_metrics_exact':True,'negative_controls_exact':True,'round006_arrays_exact':reg['round006_arrays_exact'],'round005_arrays_exact':reg['round005_arrays_exact'],'patch_primitive_go':result['patch_primitive_go'],'prior_seal':c.verify_prior(),'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',out);c.status('validated_awaiting_report');print(json.dumps(out),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','evaluate','validate']);args=p.parse_args();globals()[args.command]()
