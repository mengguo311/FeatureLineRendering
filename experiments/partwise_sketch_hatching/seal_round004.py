"""Seal complete diagnostic evidence including explicit NO_GO outcomes."""
import run_round004 as r
import argparse,datetime,json,subprocess


def main(verify=False):
    if verify:
        seal=json.loads((r.R/'SEAL.json').read_text());m=json.loads((r.R/'SHA256_MANIFEST.json').read_text())
        assert r.sha(r.R/'SHA256_MANIFEST.json')==seal['manifest_sha256']
        for f in m['files']:
            p=(r.W if f['root']=='worktree' else r.R)/f['path']
            assert r.sha(p)==f['sha256'] and p.stat().st_size==f['bytes'],str(p)
        print(json.dumps({'verified_files':len(m['files']),'manifest_sha256':seal['manifest_sha256']}));return
    assert not (r.R/'SEAL.json').exists();lock=r.verify_lock();r.verify_prior();r.resources()
    status=json.loads((r.R/'STATUS.json').read_text());assert status['execution_state']=='complete'
    assert json.loads((r.R/'VALIDATION.json').read_text())['complete']
    for name in ['TESTS_GREEN_FINAL','INHERITED_TESTS','PREPARE_EXECUTION','EVALUATION_EXECUTION','CONFIRMATION_EXECUTION']:
        receipt=json.loads((r.R/(name+'.json')).read_text())
        assert receipt['returncode']==0 and r.sha(receipt['log'])==receipt['log_sha256']
    assert json.loads((r.R/'TESTS_RED.json').read_text())['returncode']==1
    failure=json.loads((r.R/'SESSION_FAILURE.json').read_text())
    assert failure['outer_tool_returncode']==143 and failure['child_returncode'] is None
    assert not (r.R/'VALIDATION_EXECUTION.json').exists()
    assert json.loads((r.R/'CONFIRMATION.json').read_text())['complete']
    recovery=json.loads((r.D/'RECOVERY_LOCK.json').read_text())
    for p,h in recovery['sources'].items():assert r.sha(r.W/p)==h,p
    for p,h in recovery['evidence'].items():assert r.sha(r.R/p)==h,p
    paths={('worktree',r.W/p) for p in lock['sources']}
    paths|={('worktree',p) for p in r.D.iterdir() if p.is_file()}
    paths.add(('worktree',r.W/'experiments/partwise_sketch_hatching/seal_round004.py'))
    paths|={('worktree',r.W/p) for p in recovery['sources']}
    paths|={('round',p) for p in r.R.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(r.R).parts
            and p.name not in {'SEAL.json','SHA256_MANIFEST.json'}}
    files=[{'root':root,'path':str(p.relative_to(r.W if root=='worktree' else r.R)),
            'bytes':p.stat().st_size,'sha256':r.sha(p)} for root,p in sorted(paths)]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r.W,text=True).strip()
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=r.W)
    m={'source_commit':commit,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'roots':{'worktree':str(r.W),'round':str(r.R)},'files':files,
       'exclusions':['runtime stdout/stderr','SHA256_MANIFEST.json','SEAL.json']}
    r.write(r.R/'SHA256_MANIFEST.json',m)
    seal={'manifest_sha256':r.sha(r.R/'SHA256_MANIFEST.json'),'file_count':len(files),
          'total_bytes':sum(f['bytes'] for f in files),'source_commit':commit,'scientific_verdict':status['scientific_verdict']}
    r.write(r.R/'SEAL.json',seal);print(json.dumps(seal,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();main(a.verify)
