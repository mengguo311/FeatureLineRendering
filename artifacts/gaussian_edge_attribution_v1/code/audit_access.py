"""Scoped successful-open, freeze chronology and protected-input integrity audit.

This does not claim a system-wide access monitor. strace files cover the launched
experiment stages and their traced child processes; untraced agents, shell tools
and unrelated processes are outside that proof boundary.
"""
from __future__ import annotations
import ast
import datetime
import json
from pathlib import Path
import re
import stat
from verify import atomic_json,sha256,verify_seal

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artifacts/gaussian_edge_attribution_v1'
OUT=ROOT/'out/gaussian_edge_attribution_v1'
_QUOTED=re.compile(r'"(?:[^"\\]|\\.)*"')
_FORBIDDEN=re.compile(r'(?i)(?:transforms_(?:test|val)\.json|/(?:test|val)/[^/]+\.(?:png|jpe?g|exr|webp)$|/(?:meshes?|ground_truth_mesh)/|(?:^|/)(?:mesh|gt_mesh)\.(?:ply|obj|off|stl)$)')


def trace_summary(path):
    reads=set();writes=set();devices=set();thread_names=set();unparsed=[];attempted_forbidden=set();successful_forbidden=set();write_lines=[];pending={};reassembled=0
    complete=0;failed=0;unfinished=0
    for line in Path(path).read_text(errors='replace').splitlines():
        pid_match=re.match(r'(?:\[pid\s+)?(\d+)',line)
        pid=pid_match.group(1) if pid_match else None
        resumed=re.search(r'<\.\.\. (open(?:at|at2)?) resumed>',line)
        if resumed:
            key=(pid,resumed.group(1))
            if key not in pending:unparsed.append(line[:500]);continue
            line=pending.pop(key)+line[resumed.end():];reassembled+=1
        syscall=re.search(r'\b(open(?:at|at2)?)\(',line)
        if not syscall:continue
        if '<unfinished ...>' in line:
            pending[(pid,syscall.group(1))]=line.split('<unfinished ...>')[0];continue
        quoted=_QUOTED.findall(line)
        if not quoted:
            unparsed.append(line[:500]);continue
        try:raw_path=ast.literal_eval(quoted[0])
        except (ValueError,SyntaxError):unparsed.append(line[:500]);continue
        if not isinstance(raw_path,str):unparsed.append(line[:500]);continue
        if _FORBIDDEN.search(raw_path):attempted_forbidden.add(raw_path)
        match=re.search(r'\)\s+=\s+(-?\d+)(?:<([^>]+)>)?',line)
        if not match:unparsed.append(line[:500]);continue
        if int(match.group(1))<0:failed+=1;continue
        complete+=1
        resolved=(match.group(2) or raw_path).split('<',1)[0]
        if resolved.endswith(' (deleted)'):resolved=resolved[:-10]
        if not resolved.startswith('/'):
            cwd=re.search(r'AT_FDCWD<([^>]+)>',line)
            if cwd:resolved=str(Path(cwd.group(1))/resolved)
            else:unparsed.append(line[:500]);continue
        if resolved.startswith('/proc/self/') and pid:resolved='/proc/'+pid+resolved[len('/proc/self'):]
        target=Path(resolved)
        if _FORBIDDEN.search(str(target)):successful_forbidden.add(str(target))
        is_write=any(flag in line for flag in ('O_WRONLY','O_RDWR','O_CREAT','O_TRUNC','O_APPEND'))
        if not is_write:reads.add(str(target));continue
        target=target.resolve()
        write_lines.append(line[:1000])
        if pid and re.fullmatch(r'/proc/'+pid+r'/task/\d+/comm',str(target)):
            thread_names.add(str(target));continue
        try:mode=target.stat().st_mode
        except FileNotFoundError:mode=None
        if mode is not None and (stat.S_ISCHR(mode) or stat.S_ISBLK(mode)):
            devices.add(str(target));continue
        writes.add(str(target))
    unfinished=len(pending)
    external=[p for p in sorted(writes) if ROOT!=Path(p) and ROOT not in Path(p).parents]
    return {'path':str(path),'sha256':sha256(path),'successful_open_records':complete,'failed_open_records':failed,
            'unfinished_open_records_not_reconstructed':unfinished,'reassembled_open_records':reassembled,'unparsed_open_records':unparsed,
            'read_paths_count':len(reads),'write_paths':sorted(writes),'device_write_open_paths':sorted(devices),'thread_name_pseudofile_write_opens':sorted(thread_names),
            'external_regular_or_unresolved_file_write_opens':external,'attempted_TEST_VAL_mesh_paths':sorted(attempted_forbidden),
            'successful_TEST_VAL_mesh_paths':sorted(successful_forbidden),
            'ok':not external and not successful_forbidden and not unparsed and not unfinished,
            'scope':'Successful open/openat records. Device descriptors and own-process Linux thread-name /proc comm pseudofiles reported separately; open flags do not prove subsequent write bytes. Unfinished records fail strict completeness.'}


def audit_access():
    frozen=json.loads((ART/'INPUTS_FROZEN.json').read_text());protocol=json.loads((ART/'PROTOCOL_SEAL.json').read_text())
    result={'scope':'Primary stage strace file-open records and explicit read-event/seal logs only. No claim about all untraced agents, interactive shell calls, or unrelated processes. No mesh/TEST ground truth used by the traced stages.',
            'checks':{},'traces':{},'source_files':{},'checkpoints':{},'root_git_controls':{},'scene_chronology':{},'gpu':{}}
    result['engineering_deviations']=[{'stage':'initial independent synthetic unit-test GREEN run','detail':'tempfile default briefly created synthetic seal/panel fixtures under /tmp; context managers removed them. Test fixture root was corrected to workspace out/gaussian_edge_attribution_v1/validation/tmp and all tests rerun. No retained artifact or protected input was written outside workspace.','scope':'This deviation is outside the primary-stage strace proof; no universal workspace-only write claim is made.','known_fixture_path':'/tmp/tmp88mccpp5/panel.png','known_fixture_and_directory_absent_now':not Path('/tmp/tmp88mccpp5/panel.png').exists() and not Path('/tmp/tmp88mccpp5').exists(),'evidence_limit':'The known panel path appeared in initial tool output. Other temporary fixture directory names were not retained; their TemporaryDirectory context managers completed. Current tests use workspace-only fixture roots.'}]
    checks=result['checks']
    for trace in sorted(OUT.glob('*.strace')):
        r=trace_summary(trace);result['traces'][trace.name]=r;checks['trace/'+trace.name]=r['ok']
    source_trace=ROOT/'native_extension/calibration_file_trace.log'
    if source_trace.exists():
        r=trace_summary(source_trace);result['traces']['native_calibration']=r;checks['trace/native_calibration']=r['ok']
    for filename,record in frozen['source_files'].items():
        digest=sha256(filename);ok=digest==record['sha256'];result['source_files'][filename]={'ok':ok,'sha256':digest};checks['source/'+filename]=ok
    for filename,record in frozen.get('root_git_control_snapshot',{}).items():
        digest=sha256(filename);mtime=Path(filename).stat().st_mtime_ns
        ok=digest==record['sha256'] and mtime==record['mtime_ns'];result['root_git_controls'][filename]={'ok':ok,'sha256':digest,'mtime_ns':mtime};checks['protected_root_git/'+filename]=ok
    events=[json.loads(x) for x in (OUT/'READ_EVENTS.jsonl').read_text().splitlines()]
    display=OUT/'mic/DISPLAY_SEAL.json';verify_seal(display);display_created=json.loads(display.read_text())['created_utc']
    checks['all_recorded_pixel_decodes_after_protocol_seal']=all(e['utc']>protocol['created_utc'] for e in events)
    gpu_seconds=0.;launches=0;guards=0;foreign=[]
    for scene,source in frozen['scenes'].items():
        cp=source['checkpoint'];digest=sha256(cp['path']);ok=digest==cp['sha256'];result['checkpoints'][scene]={'sha256':digest,'ok':ok};checks['checkpoint/'+scene]=ok
        base=OUT/scene
        if not (base/'assets/ASSET_SEAL.json').exists():
            result['scene_chronology'][scene]={'state':'not executed','requested_pose_count':49,'actual_pose_count':0};checks[scene+'/all49frames']=False;continue
        asset_seal=base/'assets/ASSET_SEAL.json';verify_seal(asset_seal);asset_sha=sha256(asset_seal);asset_created=json.loads(asset_seal.read_text())['created_utc']
        asset_metadata=json.loads((base/'assets/ASSET.json').read_text())
        runner_candidates=list((ART/'code/history').glob('*.py'))+[ART/'code/run_experiment.py']
        matched_runners=[{'path':str(p),'sha256':sha256(p)} for p in runner_candidates if sha256(p)==asset_metadata['runner_source_sha256']][:1]
        checks[scene+'/exact_fit_runner_source_available']=bool(matched_runners)
        checks[scene+'/same_core_source_available']=sha256(ART/'code/core.py')==asset_metadata['core_source_sha256']
        eval_events=[e for e in events if e['scene']==scene and not e['key'].startswith('F_')]
        f_events=[e for e in events if e['scene']==scene and e['key'].startswith('F_')]
        first_c=min((e['utc'] for e in eval_events),default=None)
        checks[scene+'/C_arc_after_F_asset']=first_c is not None and first_c>asset_created
        checks[scene+'/C_arc_after_MicF_display']=first_c is not None and first_c>display_created
        checks[scene+'/normalization_inherited_Mic_F']=sha256(base/'assets/NORMALIZATION.json')==sha256(OUT/'mic/assets/NORMALIZATION.json')
        checks[scene+'/C_arc_records_same_asset']=bool(eval_events) and all(e.get('asset_seal_sha256')==asset_sha for e in eval_events)
        frame_seals={}
        for p in sorted((base/'frames').glob('*/SEAL.json')):
            s=json.loads(p.read_text());frame_seals[p.parent.name]=s['context']['asset_seal_sha256']
        checks[scene+'/all49frames']=len(frame_seals)==49
        checks[scene+'/all49same_F_asset']=len(frame_seals)==49 and all(v==asset_sha for v in frame_seals.values())
        result['scene_chronology'][scene]={'exact_fit_runner_sources':matched_runners,'core_source_sha256':asset_metadata['core_source_sha256'],'asset_sealed_utc':asset_created,'Mic_F_display_sealed_utc':display_created,'first_C_arc_read_utc':first_c,
            'asset_seal_sha256':asset_sha,'recorded_F_reads':len(f_events),'recorded_C_arc_reads':len(eval_events),'frame_asset_seals':frame_seals,
            'requested_pose_count':49,'actual_pose_count':len(frame_seals)}
        times=base/'native_logs/RENDER_TIMES.jsonl';guardlog=base/'native_logs/GPU_GUARD.jsonl'
        if times.exists():
            rows=[json.loads(x) for x in times.read_text().splitlines()];seconds=sum(r['cuda_synchronized_wall_seconds'] for r in rows);gpu_seconds+=seconds;launches+=len(rows)
        else:rows=[];seconds=0
        if guardlog.exists():
            gs=[json.loads(x) for x in guardlog.read_text().splitlines()];guards+=len(gs)
            bad=[g for g in gs if any(p['pid']!=g['pid'] for p in g['processes'])];foreign.extend(bad)
        else:gs=[];bad=[]
        checks[scene+'/gpu_foreign_guard']=not bad and len(gs)>=len(rows)
        result['gpu'][scene]={'native_launches':len(rows),'guard_records':len(gs),'cuda_synchronized_wall_seconds':seconds,'foreign_guard_records':bad}
    calibration_times=ROOT/'native_extension/calibration_logs/RENDER_TIMES.jsonl'
    calibration_seconds=0.
    if calibration_times.exists():
        cal_rows=[json.loads(x) for x in calibration_times.read_text().splitlines()]
        calibration_seconds=sum(r['cuda_synchronized_wall_seconds'] for r in cal_rows)
        result['gpu']['bounded_top32_calibration']={'launches':len(cal_rows),'cuda_synchronized_wall_seconds':calibration_seconds}
    result['gpu']['total']={'primary_native_launches':launches,'guard_records':guards,'cuda_synchronized_wall_seconds':gpu_seconds,'including_bounded_calibration_seconds':gpu_seconds+calibration_seconds,
                            'scope':'Native-render synchronized wall time, not exclusive device profiler time; compilation/CPU/media excluded. Top32 calibration recorded separately.'}
    result['protocol_sealed_utc']=protocol['created_utc'];result['created_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['wall_seconds_since_protocol_seal']=(datetime.datetime.fromisoformat(result['created_utc'])-datetime.datetime.fromisoformat(protocol['created_utc'])).total_seconds()
    guard_files=[ROOT/'native_extension/calibration_logs/GPU_GUARD.jsonl']+list(OUT.glob('*/native_logs/GPU_GUARD.jsonl'))
    all_guards=[json.loads(line) for path in guard_files if path.exists() for line in path.read_text().splitlines()]
    first_guard=min(g['utc'] for g in all_guards)
    upper_bound=(datetime.datetime.fromisoformat(result['created_utc'])-datetime.datetime.fromisoformat(first_guard)).total_seconds()
    result['gpu']['total']['first_recorded_guard_utc']=first_guard
    result['gpu']['total']['tracked_activity_wall_upper_bound_seconds']=upper_bound
    result['gpu']['total']['budget_basis']='Conservative elapsed wall time from first recorded GPU guard through final completed-stage audit; includes CPU/IO idle time, excludes no recorded GPU launch.'
    checks['tracked_GPU_activity_wall_upper_bound_4h']=0<=upper_bound<4*3600
    checks['wall_budget_6h']=result['wall_seconds_since_protocol_seal']<6*3600
    result['ok']=all(checks.values());result['failed']=[k for k,v in checks.items() if not v]
    atomic_json(ART/'ACCESS_AUDIT.json',result)
    return result

if __name__=='__main__':
    r=audit_access();print(json.dumps({k:r[k] for k in ('ok','failed','wall_seconds_since_protocol_seal')},indent=2))
    if not r['ok']:raise SystemExit(1)
