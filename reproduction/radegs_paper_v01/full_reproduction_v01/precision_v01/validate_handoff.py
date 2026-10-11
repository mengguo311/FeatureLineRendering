"""Read-only evidence/code validation and atomic progress receipts; no CUDA."""
import ast
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal


def noindex_check(path):
    r=subprocess.run(['git','diff','--no-index','--check','/dev/null',str(path)],capture_output=True,text=True)
    # --no-index implies --exit-code: 1 with no diagnostic means an ordinary
    # new file difference, not a whitespace error. Preserve actual diagnostics.
    return None if r.returncode in (0,1) and not (r.stdout or r.stderr) else {
        'new_file_diff_check':str(path),'returncode':r.returncode,'detail':r.stdout+r.stderr}


def main():
    hdd=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
    full=hdd/'full_reproduction_v01';prec=full/'precision_v01'
    art=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01'
    part=art/'precision_v01';code=Path(__file__).resolve().parent
    old=json.loads((hdd/'gradient_fix_v01/pilot/state/runner_config.json').read_text())
    current_path=prec/'red_gpu_actual_free_v02/state/runner_config.json'
    current=json.loads(current_path.read_text())
    checks={};errors=[]
    for label,cfg in [('original_inputs',old),('actual_free_RED_inputs',current)]:
        bad=[p for p,d in cfg['immutable_files'].items() if sha256(p)!=d]
        if bad:errors.append({label:bad})
        checks[label]=len(cfg['immutable_files'])
    checks['original_seals']={stage:verify_seal(hdd/f'gradient_fix_v01/pilot/state/{stage}.seal.json',stage,old['inputs'])
                              for stage in ['smoke','train','export']}
    if not all(checks['original_seals'].values()):errors.append('old seal changed')
    diag_path=full/'checkpoint_diagnostic/state/runner_config.json'
    diag=json.loads(diag_path.read_text())
    checks['checkpoint_diagnostic_seal']=verify_seal(diag_path.parent/'checkpoint_diagnostic.seal.json',
                                                    'checkpoint_diagnostic',diag['inputs'])
    if not checks['checkpoint_diagnostic_seal']:errors.append('checkpoint diagnostic seal changed')
    # Previously published static manifests must still verify. New files are
    # added below; old digests are never silently replaced after a mismatch.
    for filename in [art/'EVIDENCE_MANIFEST.json',part/'MANIFEST.json']:
        manifest=json.loads(filename.read_text())
        for row in manifest['files']:
            if sha256(row['path'])!=row['sha256']:errors.append({'manifest_changed':row['path']})
        for p,digest in manifest.get('code',{}).items():
            if sha256(p)!=digest:errors.append({'code_changed':p})
    protocol=json.loads((art/'FULL_SUITE_PROTOCOL.json').read_text())
    expected={row['id'] for row in protocol['entries']}
    paths=list((art/'experiments').glob('*/STATUS.json'))
    actual={json.loads(p.read_text())['id'] for p in paths}
    checks['suite_rows']=len(expected);checks['suite_status_files']=len(paths)
    if actual!=expected or len(paths)!=len(expected):errors.append('suite IDs/count mismatch')
    checks['JSON_files']=0
    for path in art.rglob('*.json'):
        json.loads(path.read_text());checks['JSON_files']+=1
    checks['Python_AST_files']=0
    for path in code.parent.rglob('*.py'):
        ast.parse(path.read_text());checks['Python_AST_files']+=1
    for path in art.rglob('*.md'):
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',path.read_text()):
            if target.startswith(('http://','https://','#')):continue
            target=target.strip('<>').split('#')[0]
            if target and not (path.parent/target).exists():errors.append({'broken_link':str(path),'target':target})
    changes=subprocess.check_output(['git','status','--porcelain','-z','--untracked-files=all'],cwd=ROOT).decode().split('\0')
    allowed=('reproduction/radegs_paper_v01/','artifacts/radegs_paper_reproduction_v01/')
    for row in filter(None,changes):
        if not row[3:].startswith(allowed):errors.append({'unexpected_git_change':row})
    checks['HEAD']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if checks['HEAD']!='00bb67c4ae39157906bcda6abc8760cc37679414':errors.append('HEAD changed')
    diff=subprocess.run(['git','diff','--check','--',*allowed],cwd=ROOT,capture_output=True,text=True)
    if diff.returncode:errors.append({'diff_check':diff.stdout+diff.stderr})
    # Git's ordinary diff ignores newly-created documents; explicitly check them.
    controls=prec/'validation_controls';controls.mkdir(exist_ok=True)
    (controls/'clean.txt').write_text('clean\n')
    (controls/'trailing_space.txt').write_text('deliberate trailing whitespace \n')
    clean_result=noindex_check(controls/'clean.txt')
    negative_result=noindex_check(controls/'trailing_space.txt')
    checks['noindex_controls']={'clean_accepted':clean_result is None,
                               'trailing_space_rejected':negative_result is not None}
    if clean_result is not None or negative_result is None:errors.append('diff-check control failure')
    for base in [art,code.parent]:
        for p in base.rglob('*'):
            if p.is_file() and p.suffix in ('.py','.md','.json','.csv','.diff','.gitignore'):
                error=noindex_check(p)
                if error:errors.append(error)
    state_path=current_path.parent/'runner_state.json';state=json.loads(state_path.read_text())
    checks['runner_state']={key:state.get(key) for key in ['status','runner_pid','child_pid','selected_gpu_uuid','config_sha256']}
    checks['runner_live']=Path('/proc',str(state['runner_pid'])).exists()
    if state['config_sha256']!=sha256(current_path):errors.append('config hash mismatch')
    checks['policy_CPU_tests']=15
    checks['policy_CPU_log_sha256']=sha256(prec/'admission_fix_v01/CPU_POLICY_INTEGRATION_GREEN.log')
    checks['no_GPU_GREEN_claim']=True
    result={'passed':not errors,'errors':errors,'checks':checks,'scientificdone':False,
            'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    atomic_json(part/'VALIDATION.json',result)
    print(json.dumps(result,indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
