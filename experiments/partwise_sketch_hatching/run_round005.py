"""One frozen 20-case plane diagnostic, with full deterministic replay."""
import round005_common as c
import argparse
import datetime
import importlib.metadata
import json
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import coverage_fixture as f

PROTOCOL=json.loads((c.D/'PROTOCOL.json').read_text())
SOURCES=['core.py','temporal_audit.py','stage_attribution.py','coverage_fixture.py',
         'test_coverage_fixture.py','test_stage_attribution.py','test_temporal_audit.py',
         'round005_common.py','round005_receipt.py','run_round005.py','seal_round005.py']


def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    resources=c.resources();prior=c.verify_prior()
    c.write(c.R/'PRIOR_SEAL_VERIFY.json',prior)
    sources=[c.W/'experiments/partwise_sketch_hatching'/n for n in SOURCES]
    sources += [c.D/'PROTOCOL.json',c.D/'REVIEW_CONTRACT_ZH.md',c.W/'docs/partwise_sketch_hatching/experiment_outline_v1.md']
    inputs=[c.P/n for n in ['SEAL.json','SHA256_MANIFEST.json','STATUS.json','NEXT.json','metrics.json','SESSION_FAILURE.json','CONFIRMATION.json']]
    lock={'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),
          'protocol_commit':'d92e2a6a','sources':{str(p.relative_to(c.W)):c.sha(p) for p in sources},
          'inputs':{str(p):c.sha(p) for p in inputs},'prior_seal':prior,'resources':resources,
          'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','Pillow']},
          'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    c.write(c.D/'ASSET_LOCK.json',lock)
    c.status('protocol_and_source_lock_prepared',artifacts=['PRIOR_SEAL_VERIFY.json'])
    print(json.dumps({'source_files':len(sources),'cases':20,'prior':prior}),flush=True)


def case_iter():
    for scene in PROTOCOL['geometry']['scenes']:
        for i,phase in enumerate(PROTOCOL['geometry']['phases_output_px']):
            yield f"{scene['id']}_phase{i}",scene,phase


def _font(size=14):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)


def _surface(owner, ink):
    palette=np.array([[255,255,255],[225,238,247],[238,215,183]],float)
    return np.uint8(np.clip(palette[owner]*(1-ink[...,None]),0,255))


def _difference(a):
    im=_surface(a['oracle_owner'],np.zeros(a['clipped'].shape))
    actual=a['clipped']>0;ref=a['oracle_visible']
    im[actual&ref]=[35,35,35]
    im[ref&~actual]=[220,50,45]
    im[actual&~ref&~a['owner_hidden']]=[35,105,215]
    im[actual&a['owner_hidden']]=[210,25,190]
    return im


def panels(case_id, metrics, a):
    font=_font(14);caption=_font(12)
    pane=256;gap=8;head=54
    sheet=Image.new('RGB',(5*pane+6*gap,pane+head+38),'white');draw=ImageDraw.Draw(sheet)
    draw.text((8,5),f"{case_id} | phase {metrics['phase_output_px']:+.3f} output px | analytic GT",fill='black',font=font)
    panels=[('Accepted point deposits',_surface(a['oracle_owner'],a['accepted_raw'])),
            ('Legacy width / visibility',_surface(a['oracle_owner'],a['clipped'])),
            ('Centered ribbon oracle',_surface(a['oracle_owner'],a['reference_ink'])),
            ('High-sample disagreement',_difference(a)),
            ('Legacy final AA (4x display)',_surface(a['AA_owner'],a['final_uint8']/255.))]
    for j,(name,im) in enumerate(panels):
        x=gap+j*(pane+gap);draw.text((x,30),name,fill='black',font=caption)
        sheet.paste(Image.fromarray(im).resize((pane,pane),Image.Resampling.NEAREST),(x,head))
    draw.text((8,head+pane+8),'Black: retained | Red: missing | Blue: extra visible footprint | Magenta: rear ink on occluder',fill='black',font=caption)
    sheet.save(c.R/'figures'/f'{case_id}.png')


def contact_sheet(records):
    # Every case, ordered by frozen scene then frozen phase. Complete patch views.
    cw,ch=432,188
    sheet=Image.new('RGB',(cw*4,ch*5+34),'white');draw=ImageDraw.Draw(sheet)
    draw.text((8,6),'All frozen plane fixtures | legacy AA / oracle AA / high-sample disagreement',fill='black',font=_font(16))
    for i,m in enumerate(records):
        a=dict(np.load(c.R/'raw'/f"{m['case_id']}.npz"));x=(i%4)*cw;y=(i//4)*ch+34
        draw.text((x+4,y+3),f"{m['scene']} | phase {m['phase_output_px']:+.3f}px",fill='black',font=_font(13))
        ims=[_surface(a['AA_owner'],a['final_uint8']/255.),_surface(a['AA_owner'],a['reference_final_uint8']/255.),_difference(a)]
        for j,im in enumerate(ims):
            sheet.paste(Image.fromarray(im).resize((128,128),Image.Resampling.NEAREST),(x+6+j*142,y+25))
        draw.text((x+6,y+157),f"Retained {m['high']['visible_retained_fraction']:.3f} | hidden ink {m['high']['all_hidden_owner_ink_sites']}",fill='black',font=_font(12))
    sheet.save(c.R/'figures/full_view_contact_sheet.png')


def summarize(records):
    gates={'all20cases':len(records)==20,
           'oracle_all_valid':all(m['checks']['oracle_valid'] for m in records),
           'all_visible_denominators_nonempty':all(m['high']['visible_sites']>0 for m in records),
           'all8_overlap_hidden_and_edge_nonempty':sum(m['scene'].startswith('overlap') for m in records)==8 and all(m['high']['hidden_sites']>0 and m['regions']['occlusion_edge']['hidden_sites']>0 for m in records if m['scene'].startswith('overlap')),
           'known_positive_negative_controls':all(m['controls']['known_control_pass'] for m in records),
           'inherited_adapter_exact':all(m['checks']['adapter_stage_equal'] and m['checks']['adapter_crop_equal'] for m in records)}
    for name in ['TESTS_GREEN','INHERITED_TEMPORAL','INHERITED_STAGE']:
        gates[name.lower()]=json.loads((c.R/(name+'.json')).read_text())['returncode']==0
    summary=[]
    for scene in PROTOCOL['geometry']['scenes']:
        rows=[m for m in records if m['scene']==scene['id']]
        summary.append({'scene':scene['id'],'phase_count':len(rows),
                        'visible_retained_fractions':[m['high']['visible_retained_fraction'] for m in rows],
                        'hidden_ink_sites':[m['high']['all_hidden_owner_ink_sites'] for m in rows],
                        'rejected_rounded_visible_points':[m['points']['rejected_rounded_visible_count'] for m in rows],
                        'exact_visible_rounded_hidden_points':[m['points']['exact_visible_rounded_hidden_count'] for m in rows]})
    return {'evaluation_complete':len(records)==20,'diagnostic_go':all(gates.values()),'gates':gates,
            'scene_summary':summary,'cases':records,
            'scope':'Analytic point-sampled finite ribbons only; unchanged renderer, no lamp render/repair, no temporal or P1 claim',
            'historical_round004':'MATCHED_CONTROL_NO_GO; eight null controls; eleven mixed; original validation child exit UNKNOWN retained'}


def evaluate():
    c.verify_lock();c.resources();c.verify_prior()
    assert not (c.R/'metrics.json').exists()
    for p in ['raw','figures']:(c.R/p).mkdir(exist_ok=True)
    records=[];t=time.monotonic()
    c.status('evaluating_frozen20_plane_cases')
    for case_id,scene,phase in case_iter():
        c.resources();m,a=f.run_case(PROTOCOL,scene,phase);m['case_id']=case_id
        np.savez_compressed(c.R/'raw'/f'{case_id}.npz',**a)
        c.write(c.R/'raw'/f'{case_id}.json',m)
        panels(case_id,m,a);records.append(m)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'cases':records})
        print(json.dumps({'case':case_id,'visible':m['high']['visible_sites'],'retained':m['high']['visible_retained_fraction'],'hidden_ink':m['high']['all_hidden_owner_ink_sites'],'oracle_valid':m['checks']['oracle_valid']}),flush=True)
    contact_sheet(records)
    result=summarize(records);result['wall_seconds']=time.monotonic()-t;result['resources']=c.resources()
    c.write(c.R/'metrics.json',result)
    c.status('evaluation_complete_awaiting_replay',scientific_verdict='DIAGNOSTIC_GO_PENDING_REPLAY' if result['diagnostic_go'] else 'DIAGNOSTIC_NO_GO',artifacts=['metrics.json','raw/','figures/full_view_contact_sheet.png'])
    print(json.dumps({'diagnostic_go':result['diagnostic_go'],'gates':result['gates'],'wall_seconds':result['wall_seconds']}),flush=True)


def validate():
    c.verify_lock();c.resources()
    saved=json.loads((c.R/'metrics.json').read_text());records=[];arrays_checked=0
    for case_id,scene,phase in case_iter():
        c.resources();m,a=f.run_case(PROTOCOL,scene,phase);m['case_id']=case_id
        old=json.loads((c.R/'raw'/f'{case_id}.json').read_text());assert m==old,case_id
        z=dict(np.load(c.R/'raw'/f'{case_id}.npz'));assert set(z)==set(a)
        for k,value in a.items():
            np.testing.assert_array_equal(value,z[k],err_msg=f'{case_id}/{k}');arrays_checked+=1
        records.append(m)
    replay=summarize(records)
    for key in replay:assert replay[key]==saved[key],key
    prior=c.verify_prior()
    result={'complete':True,'cases_recomputed':len(records),'arrays_exact_value_equal':arrays_checked,
            'all_metrics_equal':True,'prior_seal':prior,'diagnostic_go':replay['diagnostic_go'],
            'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',result);c.status('validated_awaiting_report')
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','evaluate','validate']);args=p.parse_args()
    globals()[args.command]()
