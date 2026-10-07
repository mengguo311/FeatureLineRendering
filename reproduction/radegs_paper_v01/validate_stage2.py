"""Read-only stage2 document/source/config checks; never initializes CUDA."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote,urlparse

ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'artifacts/radegs_paper_reproduction_v01'
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
sys.path.insert(0,str(Path(__file__).parent/'stage2'))
from safety import sha256,atomic_json


def git(*args,cwd=ROOT):
    return subprocess.run(['git',*args],cwd=cwd,capture_output=True,text=True)


def main():
    errors=[];links=[];json_count=0
    for p in ART.rglob('*.json'):
        try:json.loads(p.read_text(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)));json_count+=1
        except Exception as e:errors.append(f'{p}: {e}')
    for p in (ROOT/'reproduction/radegs_paper_v01').rglob('*.py'):
        try:ast.parse(p.read_text())
        except Exception as e:errors.append(f'{p}: {e}')
    for document in [ART/'STAGE1_AUDIT_ZH.md',ART/'stage1_frozen/STAGE1_AUDIT_ZH.md',
                     ART/'STAGE2_IMPLEMENTATION_ZH.md',ART/'PAPER_TEXT_DEVIATIONS_ZH.md']:
        for target in re.findall(r'\]\(([^)]+)\)',document.read_text()):
            parsed=urlparse(target)
            if parsed.scheme:continue
            exists=(document.parent/unquote(parsed.path)).exists()
            links.append({'document':str(document.relative_to(ROOT)),'target':target,'exists':exists})
            if not exists:errors.append('missing link: '+target)
    for item in json.loads((ART/'stage1_frozen/SEAL.json').read_text())['files']:
        if sha256(ART/'stage1_frozen'/item['path'])!=item['sha256']:errors.append('stage1 seal changed')
    original=HDD/'sources/RaDe-GS'
    if git('rev-parse','HEAD',cwd=original).stdout.strip()!='2d4bc087f1b4bd62c96054fbe89d273490526b81':errors.append('C24 head')
    if git('status','--porcelain',cwd=original).stdout:errors.append('C24 not clean')
    patch=git('apply','--check',str(ART/'SOURCE_PATCH.diff'),cwd=original)
    if patch.returncode:errors.append('patch cannot apply: '+patch.stderr)
    config_path=HDD/'stage2/state/runner_config.json'
    config=json.loads(config_path.read_text());state=json.loads((HDD/'stage2/state/runner_state.json').read_text())
    if sha256(config_path)!=state['config_sha256']:errors.append('live config changed')
    mismatches=[path for path,digest in config['immutable_files'].items() if sha256(path)!=digest]
    errors.extend(mismatches)
    status=git('status','--porcelain','--untracked-files=all')
    for row in status.stdout.splitlines():
        if not row[3:].startswith(('artifacts/radegs_paper_reproduction_v01/','reproduction/radegs_paper_v01/')):
            errors.append('outside allowed changes: '+row)
    diff=git('diff','--cached','--check','--','artifacts/radegs_paper_reproduction_v01/','reproduction/radegs_paper_v01/')
    if diff.returncode or diff.stdout or diff.stderr:errors.append('staged whitespace: '+diff.stdout+diff.stderr)
    if git('branch','--show-current').stdout.strip()!='gaer-rade-depth-lift-v01':errors.append('wrong branch')
    report={'passed':not errors,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'json_files':json_count,'relative_links':links,'immutable_files_verified':len(config['immutable_files']),
            'source_patch_apply_check':patch.returncode,'staged_diff_check':diff.returncode,
            'branch':git('branch','--show-current').stdout.strip(),'head_at_check':git('rev-parse','HEAD').stdout.strip(),
            'live_runner_status':state['status'],'runner_pid':state['runner_pid'],'errors':errors,
            'GPU_numeric_checks':'not executed by this validator'}
    atomic_json(ART/'stage2_evidence/document_validation.json',report)
    print(json.dumps({k:report[k] for k in ['passed','json_files','immutable_files_verified','source_patch_apply_check','staged_diff_check','errors']},indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
