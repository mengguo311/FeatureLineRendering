"""Fail-closed native-open accounting and exact artifact inventories."""
import hashlib,os,pathlib
from src.corrected_audit import audit_policy,bootstrap_reads_before_policy,normalize_open_trace
from cc_io import sha

def audit_one(trace,policy,output,bootstrap):
    output=pathlib.Path(output);record=audit_policy(trace,policy,output,bootstrap)
    exceptions=record.get('bootstrap_exceptions',[])
    record['bootstrap_precedes_policy']=bootstrap_reads_before_policy(trace,output/'allowlist.json',exceptions)
    record['passed']=record['passed'] and record['bootstrap_precedes_policy']
    return record

def inventory(root,exclude=()):
    root=pathlib.Path(root);result=[]
    for p in sorted(root.rglob('*')):
        relative=str(p.relative_to(root))
        if relative in exclude:continue
        if p.is_symlink():
            target=os.readlink(p);result.append(dict(path=relative,kind='symlink',target=target,bytes=len(target.encode()),sha256=hashlib.sha256(target.encode()).hexdigest()))
        elif p.is_file():result.append(dict(path=relative,kind='file',bytes=p.stat().st_size,sha256=sha(p)))
    return result

def verify_inventory(root,records,exclude=()):
    return inventory(root,exclude)==records
