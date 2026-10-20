"""Frozen mesh-only attachment acceptance and exact historical replay."""
import round008_common as c
import argparse
import copy
import datetime
import hashlib
import importlib.metadata
import json
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import mesh_attachment as adapter
import patch_fixture as analytic
import run_round007 as prior

P = json.loads((c.D/'PROTOCOL.json').read_text())
F = json.loads((c.D/'FIXTURES.json').read_text())
NEW = ['round008_common.py','round008_receipt.py','mesh_attachment.py',
       'test_mesh_attachment.py','run_round008.py','seal_round008.py']
TESTS = ['TESTS_GREEN','TESTS_GREEN_FINAL','INHERITED_PATCH','INHERITED_CANDIDATE','INHERITED_ORACLE',
         'INHERITED_TEMPORAL','INHERITED_STAGE']


def prepare():
    assert not (c.D/'ASSET_LOCK.json').exists()
    verification = c.verify_prior()
    c.write(c.R/'PRIOR_SEAL_VERIFY.json', verification)
    old = json.loads((c.W/'docs/partwise_sketch_hatching/round_007/ASSET_LOCK.json').read_text())
    for path, h in old['sources'].items():
        assert c.sha(c.W/path) == h, path
    assert c.sha(c.D/'FIXTURES.json') == P['fixtures_sha256']
    assert c.sha(c.W/'experiments/partwise_sketch_hatching/visibility_primitive.py') == P['candidate_source_sha256']
    paths = {c.W/p for p in old['sources']}
    paths |= {c.W/'experiments/partwise_sketch_hatching'/n for n in NEW}
    paths |= {p for p in c.D.iterdir() if p.is_file()}
    paths.add(c.W/'docs/partwise_sketch_hatching/round_007/ASSET_LOCK.json')
    inputs = [c.P/n for n in ['STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json',
                             'metrics.json','negative_controls.json','VALIDATION.json']]
    lock = {'protocol_commit':'28b2343b',
            'implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip(),
            'sources':{str(p.relative_to(c.W)):c.sha(p) for p in sorted(paths)},
            'inputs':{str(p):c.sha(p) for p in inputs},'prior_seal':verification,
            'resources':c.resources(),
            'dependencies':{k:importlib.metadata.version(k) for k in ['numpy','scipy','Pillow']}}
    c.write(c.D/'ASSET_LOCK.json',lock)
    c.status('source_locked_awaiting_acceptance')
    print(json.dumps({'frozen_cases':len(F['cases']),'prior':verification}),flush=True)


def fixture(spec):
    mesh = {'vertices':np.array(spec['vertices'],dtype=float),
            'faces':np.array(spec['faces']), 'parts':np.array(spec['parts'])}
    if 'cached_triangle_delta' in spec:
        mesh['tri'] = mesh['vertices'][mesh['faces']].copy()
        mesh['tri'][0,0,0] += spec['cached_triangle_delta']
    return mesh, list(spec['owner_faces']), list(spec['segment_faces']), np.array(spec['path'],dtype=float)


def fingerprint(value):
    h = hashlib.sha256()
    def update(x):
        if isinstance(x,np.ndarray):
            h.update(str((x.dtype.str,x.shape)).encode());h.update(x.tobytes())
        elif isinstance(x,dict):
            for k in sorted(x):h.update(k.encode());update(x[k])
        elif isinstance(x,(list,tuple)):
            h.update(type(x).__name__.encode())
            for item in x:update(item)
        else:h.update(repr(x).encode())
    update(value)
    return h.hexdigest()


GEOMETRIC_INVALID = {'invalid_chord_face0','invalid_chord_face1_rotated',
    'invalid_off_plane','invalid_outside_triangle','invalid_wrong_segment_face',
    'invalid_waypoint_off_shared_edge','invalid_waypoint_past_edge'}


def independent_check(spec, path):
    """Old analytic validator never reads adapter barycentrics or mesh caches."""
    if not spec['expected_valid'] and spec['id'] not in GEOMETRIC_INVALID:
        return {'kind':'frozen_input_or_topology_construction',
                'expected_error':spec['expected_error'],
                'analytic_geometry_test':'NOT_APPLICABLE_TO_THIS_CONTRACT_VIOLATION'}
    canonical = path.copy()
    if spec['transform']=='vertical_y90':
        canonical = (canonical-np.array(F['translation']))@np.array(F['rotation'])
    try:
        result=analytic.validate_attachment(canonical,spec['segment_faces'],
                                             F['analytic_faces'],F['shared_edge'])
        accepted=True;error=None
    except ValueError as exc:
        result=None;accepted=False;error=str(exc)
    return {'kind':'independent_canonical_analytic_plane_and_halfspaces',
            'valid':accepted,'expected_valid':spec['expected_valid'],
            'agrees':accepted==spec['expected_valid'],'diagnostics':result,'error':error}


def evaluate_case(spec):
    mesh,owners,segments,path=fixture(spec)
    original=(mesh,owners,segments,path);before=fingerprint(original)
    calls=[];diagnostics=None;error=None;unexpected=None;identity=False
    def spy(m,o,p):
        calls.append((m,o,p))
        return 'callback_completed'
    try:
        result=adapter.validate_attachment(mesh,owners,segments,path)
        diagnostics=result['diagnostics']
        identity=all(result[key] is value for key,value in zip(
            ['mesh','owner_faces','segment_faces','path'],original))
        value=adapter.render_validated(mesh,owners,segments,path,spy)
        accepted=True
        identity &= value=='callback_completed' and calls[0][0] is mesh and calls[0][1] is owners and calls[0][2] is path
    except adapter.AttachmentError as exc:
        accepted=False;error=exc.code
        # Exercise the wrapper independently: invalid input must not call spy.
        try:adapter.render_validated(mesh,owners,segments,path,spy)
        except adapter.AttachmentError as second:
            if second.code!=error:unexpected='validator/wrapper error mismatch'
        else:unexpected='wrapper accepted rejected input'
    except Exception as exc:
        accepted=False;unexpected=type(exc).__name__+': '+str(exc)
    unchanged=before==fingerprint(original)
    truth=independent_check(spec,path)
    gates={'expected_decision':accepted==spec['expected_valid'],
           'intended_error':error==spec['expected_error'],
           'no_mutation':unchanged,'original_references':identity if accepted else True,
           'callback_count':len(calls)==(1 if spec['expected_valid'] else 0),
           'independent_geometry_agrees':truth.get('agrees',True),
           'no_unexpected_exception':unexpected is None}
    m={'case_id':spec['id'],'expected_valid':spec['expected_valid'],'accepted':accepted,
       'error_code':error,'unexpected_exception':unexpected,'callback_calls':len(calls),
       'input_sha256_before':before,'input_sha256_after':fingerprint(original),
       'diagnostics':diagnostics,'independent_truth':truth,'gates':gates,'case_go':all(gates.values())}
    raw={'vertices':mesh['vertices'],'faces':mesh['faces'],'parts':mesh['parts'],
         'path':path,'owner_faces':np.asarray(owners),'segment_faces':np.asarray(segments)}
    if 'tri' in mesh:raw['cached_tri']=mesh['tri']
    return m,raw


def historical_replay(save=False):
    records=[];count=0;adapter_count=0
    for spec in prior.P['acceptance']['cases']:
        name=spec['id'];m,a=analytic.evaluate_case(prior.P,spec)
        assert m==json.loads((c.P/'raw'/f'{name}.json').read_text()),name
        old=dict(np.load(c.P/'raw'/f'{name}.npz'))
        assert set(old)==set(a)
        for k in a:np.testing.assert_array_equal(a[k],old[k],err_msg=f'{name}/{k}');count+=1
        cam,faces,extras,mesh,path=analytic.fixture(prior.P,spec)
        owners=prior.P['geometry']['owner_faces'];segments=spec['segment_owner_faces']
        before=fingerprint((mesh,owners,segments,path))
        pp=prior.P['primitive']
        rendered=adapter.render_validated(mesh,owners,segments,path,analytic.candidate.render,
            cam,pp['ink'],prior.P['camera']['supersample'],pp['high_width_filter_size'],
            pp['dense_step_high_px'],pp['depth_tolerance_world'])
        assert before==fingerprint((mesh,owners,segments,path))
        for k in rendered:
            np.testing.assert_array_equal(rendered[k],old['candidate_'+k],err_msg=f'adapter/{name}/{k}')
            adapter_count+=1
        if save:
            np.savez_compressed(c.R/'regression_raw'/f'{name}.npz',**a)
            c.write(c.R/'regression_raw'/f'{name}.json',m)
        records.append({'case_id':name,'all_arrays_exact':len(a),'adapter_render_arrays_exact':len(rendered)})
    neg,na=analytic.negative_controls(prior.P)
    assert neg==json.loads((c.P/'negative_controls.json').read_text())
    old=dict(np.load(c.P/'raw/negative_controls.npz'));assert set(na)==set(old)
    for k in na:np.testing.assert_array_equal(na[k],old[k]);count+=1
    if save:
        np.savez_compressed(c.R/'regression_raw/negative_controls.npz',**na)
        c.write(c.R/'regression_raw/negative_controls.json',neg)
    planes=prior.plane_regression()
    return {'cases':records,'round007_arrays_exact':count,'adapter_candidate_arrays_exact':adapter_count,
            'round006_arrays_exact':planes['round006_arrays_exact'],
            'round005_arrays_exact':planes['round005_arrays_exact'],
            'all_metrics_exact':True,'negative_controls_exact':True,
            'all_exact':count==559 and adapter_count==180 and planes['all_exact']}


def font(n):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)


def contact(records):
    # Three fixed orthographic views expose the full 3D input, including vertical faces.
    cw,ch=510,230
    sheet=Image.new('RGB',(3*cw,10*ch+70),'white');draw=ImageDraw.Draw(sheet)
    draw.text((8,5),'All 30 frozen attachment inputs | XY / XZ / YZ full orthographic views',fill='black',font=font(20))
    draw.text((8,32),'Blue: owner topology; gray: scene-only faces; black/red: valid/invalid supplied path. Geometry diagnostics only.',fill='black',font=font(14))
    for i,(spec,result) in enumerate(zip(F['cases'],records)):
        x=i%3*cw;y=i//3*ch+70
        draw.text((x+5,y+3),spec['id'],fill='black',font=font(13))
        mesh,owners,segments,path=fixture(spec);v=mesh['vertices'];f=mesh['faces']
        finite=np.concatenate((v[np.isfinite(v).all(axis=1)],path[np.isfinite(path).all(axis=1)]))
        for j,(axes,label) in enumerate([((0,1),'XY'),((0,2),'XZ'),((1,2),'YZ')]):
            left=x+6+j*166;top=y+42;area=156
            q=finite[:,axes];lo=q.min(axis=0);hi=q.max(axis=0);extent=max(float((hi-lo).max()),.1)
            center=(hi+lo)/2
            def project(points):
                z=(points[:,axes]-center)/extent*(area-20)
                return [(left+area/2+a,top+area/2-b) for a,b in z]
            draw.text((left+4,y+22),label,fill='#555555',font=font(12))
            for fi,face in enumerate(f):
                if np.any(face<0) or np.any(face>=len(v)):continue
                tri=v[face]
                if not np.isfinite(tri).all():continue
                pts=project(tri);draw.polygon(pts,fill='#d9ebf7' if fi in owners else '#eeeeee',outline='#6192b0')
            for a,b in zip(path[:-1],path[1:]):
                if np.isfinite([a,b]).all():
                    draw.line(project(np.array([a,b])),fill='black' if spec['expected_valid'] else '#bb2233',width=2)
            for point in path:
                if np.isfinite(point).all():
                    u,w=project(point[None])[0];draw.ellipse((u-2,w-2,u+2,w+2),fill='black')
        label=('ACCEPT' if result['accepted'] else 'REJECT '+str(result['error_code']))
        draw.text((x+6,y+204),label+' | gate '+str(result['case_go']),fill='darkgreen' if result['case_go'] else 'red',font=font(12))
    sheet.save(c.R/'figures/full_view_contact_sheet.png')
    # Keep all old views visible as exact regression, with explicit inherited label.
    old=Image.open(c.P/'figures/full_view_contact_sheet.png').convert('RGB')
    joined=Image.new('RGB',(old.width,old.height+38),'white')
    d=ImageDraw.Draw(joined);d.text((8,7),'EXPOSED ROUND007 REGRESSION: all candidate arrays exact after mesh attachment adapter',fill='black',font=font(18))
    joined.paste(old,(0,38));joined.save(c.R/'figures/prior12_full_view_regression.png')


def summary(records,regression):
    gates={'all30_cases':len(records)==30,'all_case_gates':all(m['case_go'] for m in records),
           'all8_valid':sum(m['accepted'] for m in records)==8,
           'all22_invalid_before_callback':sum(not m['accepted'] and m['callback_calls']==0 for m in records)==22,
           'all_regressions_exact':regression['all_exact']}
    for name in TESTS:gates[name.lower()]=json.loads((c.R/(name+'.json')).read_text())['returncode']==0
    return {'complete':len(records)==30,'attachment_contract_go':all(gates.values()),
            'gates':gates,'cases':records,'regression':regression,
            'limits':['Mesh attachment input contract only; no new visibility accuracy claim',
                      'All prior renders exposed; no centered-footprint/AA repair',
                      'No reconstruction accuracy, lamp/P1, automatic owner discovery or temporal stability evidence',
                      'Global manifold topology and cached renderer fields other than tri not certified']}


def evaluate():
    c.verify_lock();c.verify_prior();c.resources();assert not (c.R/'metrics.json').exists()
    for name in ['raw','regression_raw','figures']:(c.R/name).mkdir(exist_ok=True)
    c.status('evaluating_frozen_mesh_attachment_contract');records=[];start=time.monotonic()
    for spec in F['cases']:
        c.resources();m,a=evaluate_case(spec);records.append(m)
        c.write(c.R/'raw'/f"{spec['id']}.json",m)
        np.savez_compressed(c.R/'raw'/f"{spec['id']}.npz",**a)
        c.write(c.R/'PARTIAL_METRICS.json',{'completed_cases':len(records),'cases':records})
        print(json.dumps({'case':spec['id'],'go':m['case_go'],'error':m['error_code']}),flush=True)
    regression=historical_replay(save=True);c.write(c.R/'REGRESSION.json',regression)
    contact(records);result=summary(records,regression)
    result['wall_seconds']=time.monotonic()-start;result['resources']=c.resources()
    c.write(c.R/'metrics.json',result)
    c.status('evaluated_awaiting_replay',scientific_verdict='ATTACHMENT_GO_PENDING_REPLAY' if result['attachment_contract_go'] else 'ATTACHMENT_NO_GO')
    print(json.dumps({'go':result['attachment_contract_go'],'gates':result['gates']}),flush=True)


def validate():
    c.verify_lock();c.verify_prior();c.resources();saved=json.loads((c.R/'metrics.json').read_text())
    records=[];arrays=0
    for spec in F['cases']:
        m,a=evaluate_case(spec);assert m==json.loads((c.R/'raw'/f"{spec['id']}.json").read_text())
        old=dict(np.load(c.R/'raw'/f"{spec['id']}.npz"));assert set(a)==set(old)
        for k in a:np.testing.assert_array_equal(a[k],old[k]);arrays+=1
        records.append(m)
    regression=historical_replay();result=summary(records,regression)
    for k in result:assert result[k]==saved[k],k
    out={'complete':True,'cases_exact':len(records),'new_arrays_exact':arrays,
         'all_metrics_exact':True,'regression':regression,
         'attachment_contract_go':result['attachment_contract_go'],
         'prior_seal':c.verify_prior(),'resources':c.resources()}
    c.write(c.R/'VALIDATION.json',out);c.status('validated_awaiting_report')
    print(json.dumps(out),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','evaluate','validate'])
    args=parser.parse_args();globals()[args.command]()
