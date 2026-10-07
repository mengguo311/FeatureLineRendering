"""Validate stage-1 documents, file links and source identity; no scientific tests."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/radegs_paper_reproduction_v01'
CODE = ROOT / 'reproduction/radegs_paper_v01'
REPO = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/RaDe-GS')
EXPECTED_HEAD = '2d4bc087f1b4bd62c96054fbe89d273490526b81'


def git(*args, cwd=ROOT):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    return {'args': list(args), 'cwd': str(cwd), 'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}


def main():
    errors = []
    json_files = sorted(OUT.rglob('*.json'))
    for p in json_files:
        try:
            json.loads(p.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except Exception as exc:
            errors.append(f'JSON: {p}: {exc}')
    for p in CODE.glob('*.py'):
        try:
            ast.parse(p.read_text(), filename=str(p))
        except Exception as exc:
            errors.append(f'Python syntax: {p}: {exc}')
    document = OUT / 'STAGE1_AUDIT_ZH.md'
    links = []
    for target in re.findall(r'\]\(([^)]+)\)', document.read_text()):
        parsed = urlparse(target)
        if parsed.scheme in ('http', 'https', 'mailto'):
            continue
        target_file = document.parent / unquote(parsed.path)
        exists = target_file.is_file()
        links.append({'target': target, 'exists': exists})
        if not exists:
            errors.append(f'Missing relative link: {target}')
    authored = [OUT / n for n in ['STAGE1_AUDIT_ZH.md', 'SOURCE_MANIFEST.json', 'DATA_INVENTORY.json', 'REPRODUCTION_PROTOCOL_DRAFT.json', 'STATUS.json']] + sorted(CODE.glob('*.py'))
    whitespace = []
    for p in authored:
        r = git('diff', '--no-index', '--check', '--', '/dev/null', str(p))
        whitespace.append(r)
        # --no-index implies --exit-code: an added, clean file can return 1.
        # Whitespace diagnostics are emitted to stdout; tool failures exceed 1.
        if r['exit_code'] not in (0, 1) or r['stdout'] or r['stderr']:
            errors.append(f'Whitespace check: {p}')
    root_head = git('rev-parse', 'HEAD')
    root_branch = git('branch', '--show-current')
    changes = git('status', '--porcelain', '--untracked-files=all')
    if root_head['stdout'].strip() != '52a409b806fd5d326ccce0d5657e25336beb68d5':
        errors.append('workspace HEAD changed')
    if root_branch['stdout'].strip() != 'gaer-rade-depth-lift-v01':
        errors.append('workspace branch changed')
    for line in changes['stdout'].splitlines():
        path = line[3:]
        if not path.startswith(('artifacts/radegs_paper_reproduction_v01/', 'reproduction/radegs_paper_v01/')):
            errors.append('change outside allowed paths: ' + path)
    source_head = git('rev-parse', 'HEAD', cwd=REPO)
    source_status = git('status', '--porcelain', '--untracked-files=all', cwd=REPO)
    submodules = git('submodule', 'status', cwd=REPO)
    if source_head['stdout'].strip() != EXPECTED_HEAD or source_status['stdout']:
        errors.append('source HEAD/cleanliness mismatch')
    for line in submodules['stdout'].splitlines():
        if not line.startswith(' '):
            errors.append('submodule not at gitlink: ' + line)
    manifest = json.loads((OUT / 'SOURCE_MANIFEST.json').read_text())
    for record in manifest['C24_critical_files']:
        if hashlib.sha256(Path(record['absolute_path']).read_bytes()).hexdigest() != record['sha256_exact_working_file_bytes']:
            errors.append('source file digest changed: ' + record['path'])
    reference_checks = []
    for key, url in manifest['references'].items():
        match = re.search(r'/RaDe-GS/blob/([0-9a-f]{40})/(.+)#L(\d+)(?:-L(\d+))?$', url)
        if not match:
            continue
        sha, path, first, last = match.groups()
        if sha == EXPECTED_HEAD:
            p = REPO / path
        else:
            version = next(k for k in ['C25', 'C26'] if manifest['versions'][k]['sha'] == sha)
            p = REPO.parent / 'version_evidence' / version / path
        lines = len(p.read_text().splitlines()) if p.exists() else 0
        ok = lines >= int(last or first) >= int(first) > 0
        reference_checks.append({'id': key, 'local_source': str(p), 'line_count': lines, 'range_exists': ok})
        if not ok:
            errors.append('source citation range: ' + key)
    report = {'validated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scope': 'documentation_JSON_links_identity_only_no_numerical_or_GPU_checks', 'json_file_count': len(json_files), 'json_files': [str(p.relative_to(ROOT)) for p in json_files], 'relative_links': links, 'whitespace_checks': whitespace, 'root_head': root_head, 'root_branch': root_branch, 'workspace_changes': changes, 'source_head': source_head, 'source_status': source_status, 'submodule_status': submodules, 'immutable_source_citation_ranges': reference_checks, 'errors': errors, 'passed': not errors}
    (OUT / 'evidence/document_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': not errors, 'json_files': len(json_files), 'relative_links': len(links), 'immutable_source_ranges': len(reference_checks), 'errors': errors}, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
