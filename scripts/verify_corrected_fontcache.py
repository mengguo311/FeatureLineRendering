#!/usr/bin/env python3
"""Inventory exact system-font metadata observed before visual confinement."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.corrected_audit import bootstrap_reads_before_policy

root=ROOT/'out/multiscene_foundation_corrected'
audit=json.loads((root/'setup/access_audit_before_runtime_accounting.json').read_text())
stages=[s for s in audit['stages'] if s['forbidden_successes']]
assert all(s['label'] in ['evaluation_lego_visual','evaluation_chair_visual'] for s in stages)
paths=sorted({p for s in stages for p in s['forbidden_successes']});records=[]
earliest=min(datetime.datetime.fromisoformat(s['execution_status']['started_utc']).timestamp() for s in stages)
for path in paths:
    p=Path(path);stat=p.stat();decoded=subprocess.run(['fc-cat','-v',path],capture_output=True,text=True,check=True)
    directory=decoded.stdout.splitlines()[0]
    assert p.parent==Path('/var/cache/fontconfig') and not p.is_symlink()
    font_dir=Path(directory.removeprefix('Directory: '))
    assert stat.st_uid==0 and stat.st_mtime<earliest and any(font_dir==r or r in font_dir.parents for r in [Path('/usr/share/fonts'),Path('/usr/local/share/fonts')])
    records.append(dict(path=path,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=stat.st_size,uid=stat.st_uid,mtime=stat.st_mtime,font_directory=directory[len('Directory: '):],fc_cat_exit=0,decoded_output_sha256=hashlib.sha256(decoded.stdout.encode()).hexdigest()))
checks=[]
for stage in stages:
    trace=Path(stage['trace']).read_text();passed=bootstrap_reads_before_policy(trace,stage['policy_path'],paths)
    assert passed
    checks.append(dict(stage=stage['label'],trace_sha256=stage['trace_sha256'],all_reads_before_policy_creation=passed))
freeze_json(root/'setup/font_cache_bootstrap.json',dict(passed=True,files=records,stage_checks=checks,scope='Exact root-owned fontconfig metadata, decoded by fc-cat, references system font directories and predates execution. Only visual interpreter startup reads before policy creation are exempted. No scientific file or frozen allowlist is changed.'))
print(json.dumps(dict(passed=True,files=len(records),stages=len(checks))))
