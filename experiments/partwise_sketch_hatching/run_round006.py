"""Frozen visibility-only trial:18 independent acceptance +20 exposed regressions."""
import round006_common as c
import argparse
import datetime
import importlib.metadata
import json
import subprocess
import time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import coverage_fixture as old_fixture
import visibility_trial as trial
P=json.loads((c.D/'PROTOCOL.json').read_text())
OLD=json.loads((c.W/'docs/partwise_sketch_hatching/round_005/PROTOCOL.json').read_text())
NEW_SOURCES=['round006_common.py','round006_receipt.py','seal_round006.py','visibility_primitive.py','visibility_trial.py','test_visibility_primitive.py','run_round006.py']
INHERITED=['core.py','temporal_audit.py','stage_attribution.py','coverage_fixture.py','round005_common.py','test_coverage_fixture.py','test_temporal_audit.py','test_stage_attribution.py']

def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    prior=c.verify_prior();c.write(c.R/'PRIOR_SEAL_VERIFY.json',prior)
    paths=[c.W/'experiments/partwise_sketch_hatching'/n for n in NEW_SOURCES+INHERITED]
    paths += [p for p in c.D.iterdir() if p.is_file()]
    paths += [c.W/'docs/partwise_sketch_hatching/experiment_outline_v1.md',c.W/'docs/partwise_sketch_hatching/round_005/PROTOCOL.json']
    inputs=[c.P/n for n in ['SEAL.json','SHA256_MANIFEST.json','STATUS.json','NEXT.json','metrics.json','VALIDATION.json']]
    lock={'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),'protocol_commit':'b586abad',
          'sources':{str(p.relative_to(c.W)):c.sha(p) for p in paths},'inputs':{str(p):c.sha(p) for p in inputs},
          'prior_seal':prior,'resources':c.resources(),'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','Pillow']},
          'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    c.write(c.D/'ASSET_LOCK.json',lock);c.status('sources_locked_awaiting_acceptance',artifacts=['PRIOR_SEAL_VERIFY.json'])
    print(json.dumps({'sources':len(paths),'prior':prior,'acceptance':18,'regression':20}),flush=True)

def cases():
    for spec in P['acceptance']['cases']:yield 'acceptance',spec,None
    for scene in OLD['geometry']['scenes']:
        for i,phase in enumerate(OLD['geometry']['phases_output_px']):
            rear={k:scene[k] for k in ['z0','sx','sy']};rear.update(id=1,bounds=OLD['geometry']['rear_patch_output_bounds_xyxy'])
            front=None
            if scene['occluder']:
                z0,sx,sy=OLD['geometry']['front_plane'];front={'id':2,'z0':z0,'sx':sx,'sy':sy,'bounds':OLD['geometry']['front_patch_output_bounds_xyxy']}
            spec={'id':scene['id']+'_phase'+str(i),'family':scene['id'],'phase_output_px':phase,'rear':rear,'front':front,'endpoints_output':[[32+phase,12+phase],[32+phase,52+phase]]}
            yield 'regression',spec,(scene,phase)

def original_replay(spec,old):
    scene,phase=old;m,a=old_fixture.run_case(OLD,scene,phase);m['case_id']=spec['id']
    saved=json.loads((c.P/'raw'/f"{spec['id']}.json").read_text());assert m==saved,spec['id']
    z=dict(np.load(c.P/'raw'/f"{spec['id']}.npz"));assert set(z)==set(a)
    for k in a:np.testing.assert_array_equal(a[k],z[k],err_msg=f"historical/{spec['id']}/{k}")
    return len(a)

def font(n=13):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
def surface(ids,ink):
    palette=np.array([[255,255,255],[225,238,247],[238,215,183]],float)
    return np.uint8(np.clip(palette[ids]*(1-ink[...,None]),0,255))
def difference(a):
    im=surface(a['oracle_scene_id'],np.zeros(a['candidate_high'].shape));act=a['candidate_high']>0;ref=a['matched_reference']>0
    im[act&ref]=[30,30,30];im[ref&~act]=[220,30,30]
    im[act&a['owner_hidden']]=[210,25,190];im[act&a['owner_unsupported']]=[20,170,90]
    return im

def panels(split,m,a):
    pane=256;gap=8;sheet=Image.new('RGB',(6*pane+7*gap,pane+100),'white');d=ImageDraw.Draw(sheet)
    d.text((8,5),f"{split} | {m['case_id']} | phase {m['phase_output_px']:+.2f}px | analytic diagnostic GT",fill='black',font=font(16))
    ims=[('Legacy final AA',surface(a['AA_scene_id'],a['legacy_final_uint8']/255.)),('Candidate final AA',surface(a['AA_scene_id'],a['candidate_final_uint8']/255.)),('Matched footprint reference',surface(a['AA_scene_id'],a['matched_final_uint8']/255.)),('Centered ribbon (unresolved)',surface(a['AA_scene_id'],a['centered_final_uint8']/255.)),('Candidate high / reference diff',difference(a)),('Raw inherited footprint',surface(a['oracle_scene_id'],a['reference_expanded']))]
    for j,(label,im) in enumerate(ims):
        x=gap+j*(pane+gap);d.text((x,34),label,fill='black',font=font(12));sheet.paste(Image.fromarray(im).resize((pane,pane),Image.Resampling.NEAREST),(x,58))
    d.text((8,324),'Difference: black retained | red missing | magenta hidden ink | green unsupported-owner ink. All views uncropped.',fill='black',font=font(13))
    sheet.save(c.R/'figures'/f"{split}_{m['case_id']}.png")

def contact_sheet(records,split):
    rows=[m for m in records if m['split']==split];cols=3 if split=='acceptance' else 4;cw,ch=540,184
    sheet=Image.new('RGB',(cols*cw,((len(rows)+cols-1)//cols)*ch+40),'white');d=ImageDraw.Draw(sheet)
    d.text((8,5),f"All {len(rows)} {split} cases | Legacy / Candidate / Matched / Centered | full views",fill='black',font=font(17))
    for i,m in enumerate(rows):
        a=dict(np.load(c.R/'raw'/f"{split}_{m['case_id']}.npz"));x=i%cols*cw;y=i//cols*ch+40
        d.text((x+4,y+3),f"{m['case_id']} | phase {m['phase_output_px']:+.2f}px",fill='black',font=font(13))
        for j,key in enumerate(['legacy_final_uint8','candidate_final_uint8','matched_final_uint8','centered_final_uint8']):
            im=surface(a['AA_scene_id'],a[key]/255.);sheet.paste(Image.fromarray(im).resize((128,128),Image.Resampling.NEAREST),(x+5+j*134,y+25))
        d.text((x+5,y+158),f"Recall {m['high']['visible_recall']:.2f} | hidden {m['high']['hidden_ink_sites']} | unsupported {m['high']['unsupported_owner_ink_sites']} | centered {m['centered']['visible_recall']:.2f}",fill='black',font=font(12))
    sheet.save(c.R/'figures'/('full_view_contact_sheet.png' if split=='acceptance' else 'regression_full_view_contact_sheet.png'))

def summarize(records,historical_arrays):
    acc=[r for r in records if r['split']=='acceptance'];reg=[r for r in records if r['split']=='regression']
    gates={'all18_acceptance':len(acc)==18,'all20_regression':len(reg)==20,'all_acceptance_gates':all(r['case_go'] for r in acc),
           'all_regression_gates':all(r['case_go'] for r in reg),'historical860_arrays_exact':historical_arrays==860}
    for n in ['TESTS_GREEN','INHERITED_ORACLE','INHERITED_TEMPORAL','INHERITED_STAGE']:
        gates[n.lower()]=json.loads((c.R/(n+'.json')).read_text())['returncode']==0
    return {'complete':len(records)==38,'plane_primitive_go':all(gates.values()),'gates':gates,'historical_arrays_exact':historical_arrays,'cases':records,
            'limits':['Finite analytic plane diagnostic GT only','Tolerance .006 can accept true gaps below tolerance','Centered footprint mismatch unresolved','No lamp rerender, P1, RaDe-GS or general temporal stability proof','Round004 NO_GO, eight null controls, eleven mixed, original validation child UNKNOWN retained']}

def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for n in ['raw','figures']:(c.R/n).mkdir(exist_ok=True)
    records=[];count=0;t=time.monotonic();c.status('evaluating_frozen18_acceptance_and20_regression')
    for split,spec,old in cases():
        c.resources();m,a=trial.evaluate_case(P,spec,split)
        if old is not None:count+=original_replay(spec,old)
        records.append(m);name=f"{split}_{spec['id']}"
        np.savez_compressed(c.R/'raw'/f'{name}.npz',**a);c.write(c.R/'raw'/f'{name}.json',m);panels(split,m,a)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'historical_arrays_exact':count,'cases':records})
        print(json.dumps({'split':split,'case':spec['id'],'go':m['case_go'],'recall':m['high']['visible_recall'],'hidden':m['high']['hidden_ink_sites'],'unsupported':m['high']['unsupported_owner_ink_sites']}),flush=True)
    for split in ['acceptance','regression']:contact_sheet(records,split)
    result=summarize(records,count);result['wall_seconds']=time.monotonic()-t;result['resources']=c.resources()
    c.write(c.R/'metrics.json',result);c.status('evaluated_awaiting_replay',scientific_verdict='PLANE_PRIMITIVE_GO_PENDING_REPLAY' if result['plane_primitive_go'] else 'PLANE_PRIMITIVE_NO_GO',artifacts=['metrics.json','raw/','figures/full_view_contact_sheet.png','figures/regression_full_view_contact_sheet.png'])
    print(json.dumps({'go':result['plane_primitive_go'],'gates':result['gates'],'wall_seconds':result['wall_seconds']}),flush=True)

def validate():
    c.verify_lock();c.resources();saved=json.loads((c.R/'metrics.json').read_text());records=[];count=0;new_arrays=0
    for split,spec,old in cases():
        c.resources();m,a=trial.evaluate_case(P,spec,split);name=f"{split}_{spec['id']}"
        assert m==json.loads((c.R/'raw'/f'{name}.json').read_text()),name
        z=dict(np.load(c.R/'raw'/f'{name}.npz'));assert set(a)==set(z)
        for k in a:np.testing.assert_array_equal(a[k],z[k],err_msg=f'{name}/{k}');new_arrays+=1
        if old is not None:count+=original_replay(spec,old)
        records.append(m)
    result=summarize(records,count)
    for k in result:assert result[k]==saved[k],k
    validation={'complete':True,'cases':len(records),'new_arrays_exact':new_arrays,'historical_arrays_exact':count,'all_metrics_exact':True,'plane_primitive_go':result['plane_primitive_go'],'prior_seal':c.verify_prior(),'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',validation);c.status('validated_awaiting_report');print(json.dumps(validation),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('command',choices=['prepare','evaluate','validate']);args=a.parse_args();globals()[args.command]()
