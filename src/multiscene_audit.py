"""Explicit bootstrap accounting over kernel-level file-open traces."""
from pathlib import Path
from .foundation import audit_opens


def audit_stage(trace,allowed_files,runtime_roots,write_root,bootstrap):
    result=audit_opens(trace,allowed_files,runtime_roots,write_root)
    approved={str(Path(p).resolve()) for p in bootstrap}
    extras=result['forbidden_successes']
    result['bootstrap_exceptions']=[p for p in extras if p in approved]
    result['forbidden_successes']=[p for p in extras if p not in approved]
    result['passed']=not result['forbidden_successes'] and not result['unparsed_open_lines']
    return result
