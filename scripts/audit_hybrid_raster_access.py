#!/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
"""Audit only this experiment's saved openat/openat2 strace logs, offline.

No process is attached or inspected. PASS is limited to captured successful
opens and the path-resolution assumptions stated in ACCESS.json. Running or
unparseable traces cannot receive a final PASS.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from src.hybrid_raster_io import atomic_json, hash_file

OUT = ROOT/'out/hybrid_raster_evidence_v2'
ART = ROOT/'artifacts/hybrid_raster_evidence_v2'
IMAGE_EXTENSIONS = {'.png','.jpg','.jpeg','.bmp','.tif','.tiff','.exr','.hdr','.webp','.gif','.ppm','.pgm','.pfm','.npy'}
MESH_EXTENSIONS = {'.obj','.off','.stl','.ply','.glb','.gltf','.fbx','.mesh','.3ds','.dae','.vtk','.vtp'}
PREFIX = re.compile(r'^\s*(?:\[pid\s+(\d+)\]\s+|(\d+)\s+)?(.*)$')
OPEN = re.compile(r'^(openat2?)\(\s*(AT_FDCWD(?:<[^>]*>)?|\d+(?:<[^>]*>)?)\s*,\s*("(?:\\.|[^"\\])*")\s*,(.*)\)\s*=\s*(-?\d+)(?:<[^>]*>)?(?:\s.*)?$')
RESUMED = re.compile(r'^<\.\.\. (openat2?) resumed>(.*)$')
TEST_DEV = re.compile(r'^(?:test|tests|testing|dev|development|validation)(?:[_-].*)?$',re.I)


def decode_c_string(literal):
    """Decode strace C quoting, including octal filename bytes, without eval."""
    text=literal[1:-1]; out=bytearray(); i=0
    escapes={'n':10,'r':13,'t':9,'b':8,'f':12,'v':11,'a':7,'\\':92,'"':34}
    while i<len(text):
        if text[i]!='\\':
            out.extend(text[i].encode('utf-8')); i+=1; continue
        i+=1
        if i==len(text): raise ValueError('trailing C escape')
        char=text[i]
        if char in escapes:
            out.append(escapes[char]); i+=1
        elif char in '01234567':
            j=i
            while j<min(i+3,len(text)) and text[j] in '01234567': j+=1
            out.append(int(text[i:j],8)); i=j
        elif char=='x' and i+2<len(text):
            out.append(int(text[i+1:i+3],16)); i+=3
        else:
            out.extend(('\\'+char).encode('utf-8')); i+=1
    return out.decode('utf-8',errors='backslashreplace')


def _normal(path):
    return os.path.normpath(str(path))


def _resolve_open(path,dirfd,pid,fd_paths,initial_cwd):
    if path.startswith('/'):
        return _normal(path),'absolute'
    match=re.search(r'<([^>]*)>',dirfd)
    if match and match.group(1).startswith('/'):
        return _normal(Path(match.group(1))/path),'strace_dirfd_annotation'
    if dirfd.startswith('AT_FDCWD'):
        return _normal(Path(initial_cwd)/path),'initial_cwd_assumption'
    fd=int(dirfd.split('<')[0])
    if (pid,fd) in fd_paths:
        return _normal(Path(fd_paths[(pid,fd)])/path),'previous_successful_directory_open'
    return None,'unresolved_numeric_dirfd'


def parse_trace_text(text,initial_cwd=ROOT):
    calls=[]; unparsed=[]; pending={}; exits={}; seen=set(); fd_paths={}
    ignored=0; resumed_count=0
    for line_no,line in enumerate(text.splitlines(),1):
        prefix=PREFIX.match(line)
        if not prefix: unparsed.append(dict(line=line_no,text=line,reason='invalid prefix')); continue
        pid=int(prefix.group(1) or prefix.group(2) or 0)
        body=prefix.group(3)
        # Optional strace wall-clock timestamp; this stage currently uses none.
        body=re.sub(r'^\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+','',body)
        if body.startswith('+++ exited with') or body.startswith('+++ killed by'):
            exits[pid]=dict(line=line_no,event=body); ignored+=1; continue
        if body.startswith('--- ') or body.startswith('strace:') or not body.strip():
            ignored+=1; continue
        source_line=line_no
        match=RESUMED.match(body)
        if match:
            if pid not in pending:
                unparsed.append(dict(line=line_no,pid=pid,text=line,reason='resumed without unfinished call')); continue
            previous=pending.pop(pid)
            if previous['syscall']!=match.group(1):
                unparsed.append(dict(line=line_no,pid=pid,text=line,reason='resumed syscall differs')); continue
            body=previous['prefix']+match.group(2); source_line=previous['line']; resumed_count+=1
        elif '<unfinished ...>' in body:
            syscall=re.match(r'^(openat2?)\(',body)
            if not syscall:
                unparsed.append(dict(line=line_no,pid=pid,text=line,reason='unknown unfinished syscall')); continue
            seen.add(pid)
            if pid in pending:
                unparsed.append(dict(line=line_no,pid=pid,text=line,reason='second unfinished call for same PID'))
            pending[pid]=dict(line=line_no,pid=pid,syscall=syscall.group(1),prefix=body.split('<unfinished ...>',1)[0])
            continue
        parsed=OPEN.match(body)
        if not parsed:
            unparsed.append(dict(line=line_no,pid=pid,text=line,reason='unrecognized complete call')); continue
        syscall,dirfd,literal,arguments,returned=parsed.groups(); seen.add(pid)
        try:
            raw_path=decode_c_string(literal)
            path,resolution=_resolve_open(raw_path,dirfd,pid,fd_paths,initial_cwd)
        except (ValueError,OverflowError) as error:
            unparsed.append(dict(line=line_no,pid=pid,text=line,reason='path decode: '+str(error))); continue
        flags_match=re.search(r'flags\s*=\s*([^,}]+)',arguments) if syscall=='openat2' else None
        flags=flags_match.group(1).strip() if flags_match else arguments.split(',',1)[0].strip()
        record=dict(pid=pid,line=source_line,resumed_line=(line_no if source_line!=line_no else None),
                    syscall=syscall,raw_path=raw_path,path=path,path_resolution=resolution,
                    dirfd=dirfd,flags=flags,result=int(returned),successful=int(returned)>=0)
        calls.append(record)
        if record['successful']:
            fd_paths.pop((pid,int(returned)),None)
            if path is not None and ('O_DIRECTORY' in flags or Path(path).is_dir()):
                fd_paths[(pid,int(returned))]=path
    return dict(calls=calls,unparsed=unparsed,pending=list(pending.values()),
                active_pids=sorted(seen-set(exits)),process_exits={str(k):v for k,v in exits.items()},
                call_pids=sorted(seen),resumed_call_count=resumed_count,ignored_event_lines=ignored,
                line_count=len(text.splitlines()))


def _under(path,root):
    try: Path(path).relative_to(root); return True
    except ValueError: return False


def _current_realpath(path):
    # /proc/self depends on the auditor PID and must never be resolved as if it
    # referred to the traced process. Runtime devices are classified lexically.
    if any(_under(path,prefix) for prefix in ('/dev','/proc','/sys')): return path
    try: return str(Path(path).resolve(strict=False))
    except (OSError,RuntimeError): return path


def audit_calls(calls,worktree,allowed_checkpoints):
    worktree=Path(worktree)
    allowed={_normal(path) for path in allowed_checkpoints}
    allowed |= {_current_realpath(path) for path in allowed}
    checkpoints={}; forbidden=[]; meshes=[]; writes=[]; runtime=[]; unresolved=[]
    successful=failed=relative=0
    input_manifest_opens=0
    input_manifest=str(worktree/'artifacts/direct_curve_global_fit_probe/INPUTS.json')
    realpaths={}
    for original in calls:
        if not original['successful']: failed+=1; continue
        successful+=1
        if original['path'] is None:
            unresolved.append(original); continue
        path=original['path']
        if path not in realpaths: realpaths[path]=_current_realpath(path)
        real=realpaths[path]
        record={**original,'current_realpath':real}
        if original['path_resolution']!='absolute': relative+=1
        candidates={path,real}
        if input_manifest in candidates: input_manifest_opens+=1
        if candidates & allowed:
            key=next((p for p in (path,real) if p in allowed),path)
            checkpoints[key]=checkpoints.get(key,0)+1
        else:
            is_stage_output=all(any(_under(candidate,worktree/subdir/'hybrid_raster_evidence_v2') for subdir in ('out','artifacts')) for candidate in candidates)
            if not is_stage_output:
                for candidate in sorted(candidates):
                    p=Path(candidate)
                    if p.suffix.lower() in IMAGE_EXTENSIONS:
                        dataset=re.match(r'^/home/u00134/cglib/data/full/[^/]+/(?:train|test|val|validation)/',candidate,re.I)
                        heldout=any(TEST_DEV.match(part) for part in p.parts[:-1])
                        if dataset or heldout:
                            forbidden.append({**record,'reason':('source_dataset_train_test_val_image' if dataset else 'other_TEST_DEV_image'),'matched_path':candidate})
                            break
                if any(Path(candidate).suffix.lower() in MESH_EXTENSIONS for candidate in candidates):
                    meshes.append({**record,'reason':'mesh_or_nonallowlisted_geometry_asset'})
        is_write=bool(re.search(r'\bO_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND)\b',original['flags']))
        if is_write and not _under(real,worktree):
            is_runtime=any(_under(path,prefix) for prefix in ('/dev','/proc','/sys'))
            mode=None
            try: mode=os.stat(path).st_mode
            except OSError: pass
            if is_runtime or (mode is not None and (stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISSOCK(mode) or stat.S_ISFIFO(mode))):
                runtime.append({**record,'kind':'runtime_device_or_pseudo_filesystem'})
            else:
                writes.append({**record,'kind':('regular_file' if mode is not None and stat.S_ISREG(mode) else 'ordinary_path_or_no_longer_present')})
    return dict(successful_open_count=successful,failed_open_count=failed,
                input_manifest_successful_opens=input_manifest_opens,
                relative_path_resolution_count=relative,checkpoints=checkpoints,
                forbidden_images=forbidden,mesh_assets=meshes,outside_worktree_writes=writes,
                runtime_device_writes=runtime,unresolved_successful_opens=unresolved)


def audit_trace(path,allowed_checkpoints,provisional=False):
    path=Path(path)
    before=path.stat(); blob=path.read_bytes(); after=path.stat()
    parsed=parse_trace_text(blob.decode('utf-8',errors='backslashreplace'),ROOT)
    findings=audit_calls(parsed['calls'],ROOT,allowed_checkpoints)
    snapshot_stable=(before.st_size==after.st_size==len(blob) and before.st_mtime_ns==after.st_mtime_ns)
    violations=findings['forbidden_images']+findings['mesh_assets']+findings['outside_worktree_writes']
    incomplete=(provisional or not snapshot_stable or bool(parsed['active_pids']) or bool(parsed['pending']))
    uncertain=bool(parsed['unparsed'] or findings['unresolved_successful_opens'])
    production_evidence=dict(successful_opens=findings['successful_open_count']>0,
                             completed_traced_processes=bool(parsed['process_exits']) and not parsed['active_pids'],
                             frozen_checkpoint_opened=bool(findings['checkpoints']),
                             input_manifest_opened=findings['input_manifest_successful_opens']>0)
    missing_evidence=[key for key,value in production_evidence.items() if not value]
    return dict(path=str(path),snapshot_sha256=hashlib.sha256(blob).hexdigest(),snapshot_bytes=len(blob),
                snapshot_stable_during_read=snapshot_stable,provisional_requested=provisional,
                trace_processes_complete=not parsed['active_pids'],
                status=('NONCOMPLIANT' if violations else 'UNDETERMINED' if missing_evidence else 'INCOMPLETE' if incomplete else 'UNDETERMINED' if uncertain else 'PASS'),
                passed=not violations and not incomplete and not uncertain and not missing_evidence,
                production_evidence=production_evidence,missing_production_evidence=missing_evidence,
                counts=dict(lines=parsed['line_count'],parsed_open_calls=len(parsed['calls']),
                            successful_opens=findings['successful_open_count'],failed_opens=findings['failed_open_count'],
                            resumed_pairs=parsed['resumed_call_count'],unparsed=len(parsed['unparsed']),
                            pending=len(parsed['pending']),unresolved_successful=len(findings['unresolved_successful_opens'])),
                process_exits=parsed['process_exits'],active_pids=parsed['active_pids'],
                unparsed_calls=parsed['unparsed'],pending_calls=parsed['pending'],**findings)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--traces',nargs='+',type=Path,default=[OUT/'primary_eval_open.trace',OUT/'extra_open.trace'])
    parser.add_argument('--output',type=Path,default=ART/'ACCESS.json')
    parser.add_argument('--allow-running',action='store_true',help='Force a provisional audit; never issue final PASS.')
    args=parser.parse_args()
    if ROOT not in args.output.resolve().parents: parser.error('output must stay in authorized worktree')
    for path in args.traces:
        if ROOT not in path.resolve().parents: parser.error('only this worktree trace files may be audited')
    inputs=json.loads((ROOT/'artifacts/direct_curve_global_fit_probe/INPUTS.json').read_text())
    allowed={value['checkpoint']['path'] for value in inputs['scenes'].values()}
    rows=[]; missing=[]
    for path in args.traces:
        if not path.exists(): missing.append(str(path)); continue
        rows.append(audit_trace(path,allowed,args.allow_running))
    violations=[{'trace':row['path'],'classification':kind,**item} for row in rows
                for kind in ('forbidden_images','mesh_assets','outside_worktree_writes') for item in row[kind]]
    passed=bool(rows) and not missing and all(row['passed'] for row in rows)
    status='PASS' if passed else ('NONCOMPLIANT' if violations else 'INCOMPLETE_OR_UNDETERMINED')
    report=dict(schema='hybrid-raster-access-audit-v1',status=status,passed=passed,
                audited_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),traces=rows,missing_traces=missing,
                noncompliant=violations,allowed_source_checkpoints=sorted(allowed),initial_cwd=str(ROOT),
                script_sha256=hash_file(__file__),
                scope='Only primary C/arc and extra-scene production processes represented by the named strace files. Pilot and primary F had no OS syscall trace.',
                limitations=[
                    'This is not a claim that the entire experiment was syscall-traced.',
                    'openat/openat2 tracing proves path opens, not whether opened bytes were decoded or used; successful forbidden opens are conservatively treated as violations.',
                    'Other mechanisms (inherited descriptors, previously mapped memory, network reads, non-openat syscalls) are not observed by these trace filters.',
                    'Relative AT_FDCWD paths assume the explicitly documented launch cwd; chdir/fork/close/dup are not captured. Numeric dirfds resolve only from strace annotations or same-PID previously observed directory opens; unresolved successful opens block PASS.',
                    'Filesystem symlink resolution is checked at audit time and may differ from execution-time state. Runtime /dev,/proc,/sys paths are classified separately, not treated as ordinary output artifacts.',
                    'The deny policy recognizes source dataset images, TEST/DEV image paths, and common mesh/geometry extensions; extensionless or opaque archive-embedded assets cannot be identified by path alone.',
                    'File snapshots still growing, unmatched unfinished calls, active traced PIDs, missing traces, or unparsed calls cannot support a final PASS.',
                    'A final trace PASS also requires successful opens, complete traced-process exits, and observed opens of an allowlisted frozen checkpoint and INPUTS.json; empty or unrelated traces are UNDETERMINED.',
                    'A PASS is limited to captured calls and these assumptions; it is not a scientific or human visual GO.',
                ])
    atomic_json(args.output,report,replace=True)
    print(json.dumps(dict(status=status,passed=passed,trace_count=len(rows),missing_traces=missing,
                          violation_count=len(violations),summary=[dict(path=r['path'],status=r['status'],counts=r['counts']) for r in rows]),ensure_ascii=False),flush=True)
    return 0 if passed else (1 if violations else 2)


if __name__=='__main__': raise SystemExit(main())
