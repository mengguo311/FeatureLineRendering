#!/usr/bin/env python3
"""Independently cross-check completed reports, execution, hashes and media."""
import datetime,json,subprocess,sys
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.corrected_probe import machine_decision
from src.corrected_reporting import sha256,check_markdown,verify_probe_integrity,file_inventory,check_inventory
from src.corrected_audit import stage_record_paths
from src.multiscene import seed_eligibility,controlled_eligibility,independent_eligibility


def read(path):return json.loads(Path(path).read_text())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()


def main():
    root=ROOT/'out/multiscene_foundation_corrected';cfg=read(root/'config.json');result=read(root/'results.json');checks={}
    def require(name,condition):
        checks[name]=bool(condition)
        if not condition:raise ValueError('verification failed: '+name)
    check_markdown(result,(root/'RESULTS.md').read_text());checks['json_markdown_exact']=True
    qualification_text=(root/'QUALIFICATION.md').read_text()
    for s in result['scenes']:
        e=s['eligibility']
        expected=f"| {s['scene']} | {e['posterior_eligible'][0]} | {e['posterior_eligible'][1]} | {e['route_a']} | {e['route_b']} | {len(e['qualified_doses'])}/9 |"
        require('qualification_markdown_'+s['scene'],expected in qualification_text)
    require('branch',git('branch','--show-current')=='multiscene-foundation-corrected')
    prior=read(ROOT/'out/multiscene_foundation/config.json')
    scientific=['budget','controls','detector','eligibility','gates','native','perturbations','probe','queries','scene_order','splits','surface','training','visuals']
    require('all_scientific_settings_unchanged',all(cfg[k]==prior[k] for k in scientific))
    for name in ['config.json','PREREG.md','input_hashes.json']:
        recorded=subprocess.check_output(['git','show','fb4488e:out/multiscene_foundation_corrected/'+name],cwd=ROOT)
        require('prereg_commit_'+name,recorded==(root/name).read_bytes())
    require('old_tracked_files_unchanged',not git('diff',cfg['start_head'],'--','out/point_feature_foundation','out/multiscene_foundation'))
    require('old_sources_and_selectors_unchanged',not git('diff',cfg['start_head'],'--',*[str(p.relative_to(ROOT)) for p in (ROOT/'src').glob('*') if p.is_file() and not p.name.startswith('corrected_')]))
    preserved=read(root/'PRESERVED_INPUT_VERIFICATION.json');require('preserved_archives_inputs_checkpoints',preserved['passed'])
    # Recheck the checkpoint bytes at the end as well as in each stage.
    require('eight_checkpoint_hashes',len(cfg['frozen_posteriors'])==8 and all(sha256(v['path'])==v['sha256'] for v in cfg['frozen_posteriors'].values()))
    require('fixed_parent_recipe_hashes',all(read(root/f'controlled/{s}/measurements/parent_frozen.json')==cfg['frozen_parents'][s] for s in cfg['scene_order']))
    for q in result['quality']:
        measured=seed_eligibility(q['rows'],cfg);calibration=all(c['passed'] for c in q['calibration'])
        require(f"posterior_gate_{q['scene']}_{q['seed']}",measured['groups']==q['eligibility']['groups'] and bool(measured['passed'] and calibration)==q['eligibility']['passed'])
    for d in result['doses']:
        measured=controlled_eligibility(d['rows'],d['coverage'],cfg);calibration=all(c['passed'] for c in d['calibration'])
        require(f"dose_gate_{d['scene']}_{d['name']}",bool(measured['passed'] and calibration)==d['eligibility']['passed'] and measured['rgb_pass']==d['eligibility']['rgb_pass'] and measured['coverage_pass']==d['eligibility']['coverage_pass'])
    for s in result['scenes']:
        e=s['eligibility'];quality=[q for q in result['quality'] if q['scene']==s['scene']]
        pair=independent_eligibility([q['rows'] for q in quality],read(root/f"scenes/{s['scene']}/pair.json")['rows'],cfg)
        route_a=bool(pair['passed'] and all(q['eligibility']['calibration_pass'] for q in quality) and e['valid_parent_geometry'])
        route_b=bool(quality[0]['eligibility']['passed'] and e['valid_parent_geometry'] and e['qualified_doses'])
        require('scene_route_gates_'+s['scene'],e['route_a']==route_a and e['route_b']==route_b and e['eligible']==(route_a or route_b))
    sidecars=[]
    for sidecar in root.rglob('*.sha256'):
        artifact=sidecar.with_suffix('')
        if not artifact.is_file():raise ValueError('missing sidecar target '+str(artifact))
        sidecars.append(dict(path=str(artifact.relative_to(root)),passed=sha256(artifact)==sidecar.read_text().strip()))
    require('all_frozen_sidecars',all(x['passed'] for x in sidecars))
    audit=read(root/'ACCESS_AUDIT.json');require('access_audit',audit['passed'] and audit['forbidden_successes']==0 and audit['unparsed_open_lines']==0)
    audited={r['policy_path'] for r in audit['stages']}
    policies=list(root.rglob('allowlist.json'))
    require('every_attempt_audited',audited=={str(p) for p in policies})
    require('source_provenance',read(root/'SOURCE_PROVENANCE.json')['passed'])
    require('native_build_reproducible',read(root/'setup/build_verification.json')['passed'])
    require('surface_raw_fits_preserved',read(root/'SURFACE_REPAIR_VERIFICATION.json')['passed'])
    for row in read(root/'SOURCE_PROVENANCE.json')['records']:require('source_'+row['sha256'],sha256(root/row['snapshot'])==row['sha256'])
    arms=[];freezes=[];timeline=[]
    for row in result['local_arms']:
        arm=verify_probe_integrity(root/row['path']);arms.append(dict(path=row['path'],**arm))
        require('arm_summary_'+row['path'],all(row[k]==arm[k] for k in ['query_count','mode_count','accepted_count','raw_accepted_count','rejected_count','ambiguous_count']))
    for s in result['scenes']:
        if not s['eligible']:continue
        scene=s['scene'];local=root/f'local/{scene}';elig=read(root/f'scenes/{scene}/eligibility.json')
        expected=['seed_1729']+(['seed_2718'] if elig['route_a'] else [])+(elig['qualified_doses'] if elig['route_b'] else [])
        require('all_eligible_assets_'+scene,read(local/'execution_complete.json')['assets']==expected)
        for asset in expected:
            native=read(local/f'layers/{asset}/complete.json')['calibration']
            require('native_layers_'+scene+'_'+asset,len(native)==16 and all(v['max_alpha_error']<=cfg['native']['calibration_max'] for v in native))
        require('machine_label_'+scene,machine_decision(True,s['machine'],False)==s['verdict'])
        require('C_view_denominators_'+scene,set(s['machine_detail']['C_prediction']['per_view'])=={str(i) for i in cfg['splits']['C']})
        for group in [local/'F',local/'C',*sorted((local/'repeats').glob('*'))]:
            frozen=read(group/'frozen.json')
            for name,digest in frozen['artifacts'].items():
                if sha256(group/name)!=digest:raise ValueError('frozen local output changed '+str(group/name))
            freezes.append(dict(path=str(group.relative_to(root)),artifacts=len(frozen['artifacts'])))
        F=read(root/f'setup/local_{scene}_seed_1729_primary_exit.json')
        if F['exit_code']:
            require('control_completion_preserves_fits_'+scene,read(local/'F/control_completion/complete.json')['existing_artifacts_unchanged'])
            F=read(root/f'setup/local_{scene}_seed_1729_controls_exit.json')
        C=read(root/f'setup/local_{scene}_seed_1729_cross_exit.json');V=read(root/f'setup/evaluation_{scene}_visual_exit.json')
        require('F_before_C_and_DEV_'+scene,F['finished_utc']<=C['started_utc'] and F['finished_utc']<=V['started_utc'])
        timeline.append(dict(scene=scene,F_finished=F['finished_utc'],C_started=C['started_utc'],DEV_started=V['started_utc']))
        vis=root/f'evaluation/{scene}/visual';video=read(vis/'video_status.json');require('video_stage_'+scene,video['reached']==bool(s['machine']['G1'] and s['machine']['G2_machine']))
        key=read(vis/'review_identity_key.json');review=vis/'blinded_review';require('review_is_pending_'+scene,key['independent_reviews_completed']==0 and not (review/'review_identity_key.json').exists())
        for pair in key['pairs']:
            for label,original in pair['identities'].items():require(f"blinded_copy_{scene}_{pair['index']}_{label}",sha256(review/f"{pair['index']:03d}_{label}.png")==sha256(original))
        require('failure_diagnostics_'+scene,all((vis/name).is_file() for name in ['all_modes_diagnostic.png','failure_buckets.png','F__gs_contact.png','F__no_gs_contact.png','pca_contact.png','glyph_metrics.json']))
        require('DEV_view_denominators_'+scene,all(set(v['per_view'])=={str(i) for i in cfg['splits']['DEV']} for v in read(vis/'DEV_detector_prediction.json')['rows'].values()))
    require('local_totals',sum(a['query_count'] for a in arms)==result['totals']['local_queries'] and sum(a['mode_count'] for a in arms)==result['totals']['local_modes'] and sum(a['accepted_count'] for a in arms)==result['totals']['local_accepted'])
    # Decode all new images plus both preserved experiment roots and tracked repo
    # media. This is administrative file validation, after scientific freezing.
    media=set(root.rglob('*.png'))|set(root.rglob('*.mp4'))
    for old in ['point_feature_foundation','multiscene_foundation']:
        media.update((ROOT/'out'/old).rglob('*.png'));media.update((ROOT/'out'/old).rglob('*.mp4'))
    media.update(ROOT/p for p in git('ls-files','*.png','*.mp4').splitlines());decoded=[]
    for p in sorted(media):
        if p.suffix=='.png':
            image=cv2.imread(str(p),cv2.IMREAD_UNCHANGED)
            if image is None:raise ValueError('image decode failed '+str(p))
            decoded.append(dict(path=str(p.relative_to(ROOT)),kind='png',shape=list(image.shape)))
        else:
            cap=cv2.VideoCapture(str(p));count=0;dimensions=set()
            while True:
                ok,frame=cap.read()
                if not ok:break
                count+=1;dimensions.add(tuple(frame.shape[:2]))
            cap.release()
            if count==0:raise ValueError('empty or invalid video '+str(p))
            if root in p.parents and (count!=120 or dimensions!={(400,400)}):raise ValueError('incorrect registered diagnostic video '+str(p))
            decoded.append(dict(path=str(p.relative_to(ROOT)),kind='mp4',decoded_frames=count,dimensions=sorted(dimensions)))
    require('all_media_decode',bool(decoded));freeze_json(root/'MEDIA_VERIFICATION.json',dict(passed=True,records=decoded,png_count=sum(d['kind']=='png' for d in decoded),mp4_count=sum(d['kind']=='mp4' for d in decoded)))
    ledger=[json.loads(line) for line in (root/'tdd/commands.jsonl').read_text().splitlines()]
    end=[next(r for r in reversed(ledger) if r['label'].startswith(prefix)) for prefix in ['final_targeted','final_complete']]
    require('independent_final_suites',len(end)==2 and all(r['exit_code']==0 for r in end) and len({r['start_utc'] for r in end})==2)
    require('observed_red_green',all(any(r['label']==label and r['phase']=='GREEN' and r['exit_code']==0 for r in ledger) for label in {r['label'] for r in ledger if r['phase']=='RED'}))
    verification=dict(passed=all(checks.values()),checks=checks,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),totals=result['totals'],frozen_sidecars=len(sidecars),local_arms=arms,local_freezes=freezes,timeline=timeline,access_audit={k:audit[k] for k in ['passed','trace_count','forbidden_successes','unparsed_open_lines']},preserved_input_files=preserved['files'],media=dict(png_count=sum(d['kind']=='png' for d in decoded),mp4_count=sum(d['kind']=='mp4' for d in decoded),new_png_count=len(list(root.rglob('*.png'))),new_mp4_count=len(list(root.rglob('*.mp4')))),final_suites=end,manual_status='PENDING_INDEPENDENT_REVIEW',git_state_note='Final clean/local/upstream/remote equality is recorded externally after the final commit, avoiding self-reference.')
    freeze_json(root/'VERIFICATION.json',verification)
    exclude=['MANIFEST.json','MANIFEST.json.sha256','FINAL_SEAL.json','FINAL_SEAL.json.sha256']
    inventory=file_inventory(root,exclude=exclude)
    paths=[str(root/row['path']) for row in inventory]
    ignored_process=subprocess.run(['git','check-ignore','--stdin','-z'],cwd=ROOT,input=('\0'.join(paths)+'\0').encode(),stdout=subprocess.PIPE)
    if ignored_process.returncode not in [0,1]:raise RuntimeError('storage classification failed')
    ignored=set(ignored_process.stdout.decode().strip('\0').split('\0'))
    for row,path in zip(inventory,paths):row['storage']='server_only' if path in ignored else 'git'
    freeze_json(root/'MANIFEST.json',dict(root=str(root),files=inventory,file_count=len(inventory),bytes=sum(r['bytes'] for r in inventory),excluded_self_references=exclude,external_dependencies=dict(checkpoints=cfg['frozen_posteriors'],preserved_input_inventory='PRESERVED_INPUT_VERIFICATION.json')))
    check_inventory(root,inventory)
    freeze_json(root/'FINAL_SEAL.json',dict(passed=True,manifest_sha256=sha256(root/'MANIFEST.json'),verification_sha256=sha256(root/'VERIFICATION.json'),results_sha256=sha256(root/'results.json'),markdown_sha256=sha256(root/'RESULTS.md')))
    print(json.dumps(dict(passed=True,totals=result['totals'],media=verification['media'],manifest_files=len(inventory)),indent=2))

if __name__=='__main__':main()
