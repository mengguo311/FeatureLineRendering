"""Native-open audits with explicit, narrow startup exceptions."""
from pathlib import Path
from .multiscene_audit import audit_stage,bytecode_status


def audit_policy(trace,policy,output,bootstrap=()):
    readonly=[Path(p) for p in policy['readonly']]
    files=[str(p) for p in readonly if p.is_file()]
    roots=[str(p) for p in readonly if p.is_dir()]+[p for p in policy.get('writable',[]) if p!=str(output)]
    return audit_stage(trace,files,roots,output,[str(p) for p in bootstrap])
