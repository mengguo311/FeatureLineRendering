"""Native-open audits with explicit, narrow startup exceptions."""
from pathlib import Path
import re
from .multiscene_audit import audit_stage,bytecode_status


def normalize_open_trace(trace):
    """Join strace's interleaved calls by PID/syscall; keep incomplete calls fatal."""
    pending={};lines=[];unparsed=[];joined=0
    prefix=r'^\s*(?:\[pid\s+(\d+)\]|(\d+))?\s*'
    for line in trace.splitlines():
        resumed=re.match(prefix+r'<\.\.\. (open|openat|openat2|creat) resumed>(.*)$',line)
        if resumed:
            key=(resumed[1] or resumed[2] or '',resumed[3])
            if key not in pending:unparsed.append(line);continue
            line=pending.pop(key)+resumed[4];joined+=1
        else:
            unfinished=re.match(prefix+r'(open|openat|openat2|creat)\(.*<unfinished \.\.\.>$',line)
            if unfinished:
                key=(unfinished[1] or unfinished[2] or '',unfinished[3])
                if key in pending:unparsed.append(pending[key]+'<unfinished ...>')
                pending[key]=line[:-len('<unfinished ...>')];continue
        # -yy adds character/block device identity inside the resolved fd path.
        line=re.sub(r'(= \d+<[^<>]+)<(?:char|block) \d+:\d+>>',r'\1>',line)
        lines.append(line)
    unparsed.extend(value+'<unfinished ...>' for value in pending.values())
    return '\n'.join(lines),unparsed,joined


def bootstrap_reads_before_policy(trace,policy_path,paths):
    normalized,unparsed,_=normalize_open_trace(trace)
    if unparsed:return False
    lines=normalized.splitlines()
    boundary=next((i for i,line in enumerate(lines) if '"'+str(policy_path)+'"' in line and 'O_CREAT' in line and '= -1' not in line),None)
    if boundary is None:return False
    return all(i<boundary for i,line in enumerate(lines) if any('"'+str(p)+'"' in line for p in paths) and '= -1' not in line)


def stage_record_paths(root,policy_path,key):
    root=Path(root);parts=Path(policy_path).relative_to(root).parts
    attempts=[p for p in parts if p.startswith('attempt_')]
    if len(attempts)>1:raise ValueError('ambiguous archived attempt')
    directory=root/'setup'
    if attempts:directory=directory/attempts[0]
    return directory/(key+'.strace'),directory/(key+'_exit.json')


def audit_policy(trace,policy,output,bootstrap=()):
    readonly=[Path(p) for p in policy['readonly']]
    files=[str(p) for p in readonly if p.is_file()]
    roots=[str(p) for p in readonly if p.is_dir()]+[p for p in policy.get('writable',[]) if p!=str(output)]
    normalized,unparsed,joined=normalize_open_trace(trace)
    result=audit_stage(normalized,files,roots,output,[str(p) for p in bootstrap])
    result['unparsed_open_lines'].extend(unparsed)
    result['resumed_open_count']=joined
    result['passed']=not result['forbidden_successes'] and not result['unparsed_open_lines']
    return result


def verified_source_exception(path,expected_sha256):
    import hashlib
    path=Path(path).resolve()
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha256:
        raise ValueError('bootstrap source differs from pinned inventory')
    return str(path)
