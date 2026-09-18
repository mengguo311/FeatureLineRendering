#!/usr/bin/env python3
"""Resolve every observed stage source hash to exact versioned bytes."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.corrected_reporting import sha256
parser=argparse.ArgumentParser();parser.add_argument('--snapshot-only',action='store_true');args=parser.parse_args()
root=ROOT/'out/multiscene_foundation_corrected';wanted={}
preserved={r['path']:r['observed_sha256'] for r in json.loads((root/'PRESERVED_INPUT_VERIFICATION.json').read_text())['records'] if r['passed']}
vendor=json.loads((ROOT/'out/multiscene_foundation/setup/training_source.json').read_text())
for policy in sorted(root.rglob('allowlist.json')):
    item=json.loads(policy.read_text())
    for path,digest in dict(item.get('source_hashes',{}),**item.get('upstream_source_hashes',{})).items():
        wanted.setdefault((path,digest),[]).append(str(policy.relative_to(root)))
destination=root/'setup/source_versions';destination.mkdir(exist_ok=True);records=[];versions={}
for (path,digest),stages in sorted(wanted.items()):
    relative=str(Path(path).relative_to(ROOT))
    if Path(path).suffix=='.so' or '/vendor/' in path:
        if sha256(path)!=digest:raise ValueError('native/vendor dependency changed '+path)
        if not str(Path(path)).startswith(str(root)) and preserved.get(path)!=digest:raise ValueError('unverified prior dependency '+path)
        snapshot=destination/(digest+Path(path).suffix)
        if snapshot.exists():
            if sha256(snapshot)!=digest:raise ValueError('snapshot collision')
        else:snapshot.write_bytes(Path(path).read_bytes())
        records.append(dict(path=relative,sha256=digest,snapshot=str(snapshot.relative_to(root)),stages=stages,equals_final_worktree=True,provenance='native binary: exact rebuild or preserved archive' if Path(path).suffix=='.so' else 'preserved pinned vendor source',vendor_source_commit=vendor['source_commit'] if '/vendor/' in path else None,vendor_diff_sha256=vendor['diff_sha256'] if '/vendor/' in path else None))
        continue
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
if not args.snapshot_only:freeze_json(root/'SOURCE_PROVENANCE.json',dict(passed=True,records=records,source_variants=len(records),scope='Every observed repository Python source version is retained and resolved to Git. Native binaries match independent rebuilds or preserved archives; vendor source matches the preserved pinned source inventory. Later administrative/resource-only changes do not pretend to have existed in earlier processes.'))
print('source variants',len(records))
