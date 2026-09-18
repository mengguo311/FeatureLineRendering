#!/usr/bin/env python3
"""Resolve every observed stage source hash to exact versioned bytes."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.corrected_reporting import sha256
root=ROOT/'out/multiscene_foundation_corrected';wanted={}
for policy in sorted(root.rglob('allowlist.json')):
    for path,digest in json.loads(policy.read_text()).get('source_hashes',{}).items():
        wanted.setdefault((path,digest),[]).append(str(policy.relative_to(root)))
destination=root/'setup/source_versions';destination.mkdir(exist_ok=True);records=[];versions={}
for (path,digest),stages in sorted(wanted.items()):
    relative=str(Path(path).relative_to(ROOT))
    if relative not in versions:
        versions[relative]={}
        commits=subprocess.check_output(['git','log','--all','--format=%H','--',relative],cwd=ROOT,text=True).splitlines()
        for commit in commits:
            attempt=subprocess.run(['git','show',commit+':'+relative],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            if attempt.returncode:continue
            content=attempt.stdout;key=hashlib.sha256(content).hexdigest()
            versions[relative].setdefault(key,(content,commit))
    if digest not in versions[relative]:raise ValueError('unversioned observed source '+relative+' '+digest)
    content,commit=versions[relative][digest];snapshot=destination/(digest+Path(path).suffix)
    if snapshot.exists():
        if sha256(snapshot)!=digest:raise ValueError('snapshot collision')
    else:snapshot.write_bytes(content)
    records.append(dict(path=relative,sha256=digest,git_commit=commit,snapshot=str(snapshot.relative_to(root)),stages=stages,equals_final_worktree=sha256(path)==digest))
freeze_json(root/'SOURCE_PROVENANCE.json',dict(passed=True,records=records,source_variants=len(records),scope='Every allowlisted stage source version is retained and resolved to Git. Later administrative/resource-only changes do not pretend to have existed in earlier processes.'))
print('source variants',len(records))
