"""Seal only complete verified round_003; never rewrite any previous round."""
import run_round003 as r
import argparse
import datetime
import json
import subprocess


def main(verify):
    if verify:
        m = json.loads((r.R/'SHA256_MANIFEST.json').read_text())
        seal = json.loads((r.R/'SEAL.json').read_text())
        assert r.sha(r.R/'SHA256_MANIFEST.json') == seal['manifest_sha256']
        for f in m['files']:
            path = (r.W if f['root'] == 'worktree' else r.R)/f['path']
            assert r.sha(path) == f['sha256'] and path.stat().st_size == f['bytes'], str(path)
        print(json.dumps({'verified_files': len(m['files']), 'manifest_sha256': seal['manifest_sha256']}))
        return
    assert not (r.R/'SEAL.json').exists()
    lock = r.verify_lock(); r.verify_prior(); r.resource_check()
    validation_lock = json.loads((r.D/'VALIDATION_LOCK.json').read_text())
    for path, digest in validation_lock['sources'].items(): assert r.sha(r.W/path) == digest
    for path, digest in validation_lock['evidence'].items(): assert r.sha(r.R/path) == digest
    assert json.loads((r.R/'VALIDATION.json').read_text())['validation_complete']
    status = json.loads((r.R/'STATUS.json').read_text())
    assert status['execution_state'] == 'complete'
    for name in ['ORBIT_EXECUTION', 'ZOOM_EXECUTION', 'SUMMARY_EXECUTION', 'VALIDATION_EXECUTION']:
        receipt = json.loads((r.R/(name+'.json')).read_text())
        assert receipt['returncode'] == 0 and r.sha(receipt['log']) == receipt['log_sha256']
    paths = [('worktree', r.W/p) for p in lock['source']]
    paths += [('worktree', r.W/p) for p in validation_lock['sources']]
    paths += [('worktree', p) for p in r.D.glob('*') if p.is_file()]
    paths += [('worktree', r.W/'experiments/partwise_sketch_hatching/seal_round003.py')]
    paths += [('round', p) for p in r.R.rglob('*') if p.is_file() and
              p.name not in {'SEAL.json', 'SHA256_MANIFEST.json'} and 'runtime' not in p.relative_to(r.R).parts]
    files = [{'root': root, 'path': str(p.relative_to(r.W if root == 'worktree' else r.R)),
              'bytes': p.stat().st_size, 'sha256': r.sha(p)} for root, p in sorted(set(paths))]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=r.W, text=True).strip()
    m = {'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'source_commit': commit, 'roots': {'round': str(r.R), 'worktree': str(r.W)},
         'files': files, 'exclusions': ['runtime stdout/stderr', 'SHA256_MANIFEST.json', 'SEAL.json']}
    r.write_json(r.R/'SHA256_MANIFEST.json', m)
    seal = {'manifest_sha256': r.sha(r.R/'SHA256_MANIFEST.json'), 'file_count': len(files),
            'total_bytes': sum(f['bytes'] for f in files), 'source_commit': commit,
            'scientific_verdict': status['scientific_verdict']}
    r.write_json(r.R/'SEAL.json', seal); print(json.dumps(seal, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--verify', action='store_true')
    main(p.parse_args().verify)
