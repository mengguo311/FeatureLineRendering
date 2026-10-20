"""Seal the completed single frozen temporal audit, preserving prior rounds."""
import round016_common as c
import argparse,datetime,json,subprocess

def main(verify=False):
    if verify:
        seal=json.loads((c.R/'SEAL.json').read_text());manifest=json.loads((c.R/'SHA256_MANIFEST.json').read_text())
        assert c.sha(c.R/'SHA256_MANIFEST.json')==seal['manifest_sha256']
        for f in manifest['files']:
            p=(c.W if f['root']=='worktree' else c.R)/f['path'];assert c.sha(p)==f['sha256'] and p.stat().st_size==f['bytes'],str(p)
        print(json.dumps({'verified_files':len(manifest['files']),'manifest_sha256':seal['manifest_sha256']}));return
    assert not (c.R/'SEAL.json').exists();lock=c.verify_lock();c.verify_prior();c.resources()
    status=json.loads((c.R/'STATUS.json').read_text());assert status['execution_state']=='complete'
    assert json.loads((c.R/'VALIDATION.json').read_text())['complete']
    tests=json.loads((c.R/'TESTS.json').read_text());assert tests['complete'] and tests['passed']
    expected={r['name']:r['expected'] for r in tests['executions']}
    expected.update(PREPARE_EXECUTION=0,EVALUATION_EXECUTION=0,VALIDATION_EXECUTION=0)
    for name,rc in expected.items():
        receipt=json.loads((c.R/(name+'.json')).read_text());assert receipt['returncode']==rc and c.sha(receipt['log'])==receipt['log_sha256']
    paths={('worktree',c.W/p) for p in lock['sources']}
    paths|={('worktree',p) for p in c.D.iterdir() if p.is_file()}
    paths|={('round',p) for p in c.R.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(c.R).parts and p.name not in {'SEAL.json','SHA256_MANIFEST.json'}}
    files=[{'root':root,'path':str(p.relative_to(c.W if root=='worktree' else c.R)),'bytes':p.stat().st_size,'sha256':c.sha(p)} for root,p in sorted(paths)]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.W,text=True).strip();assert not subprocess.check_output(['git','status','--porcelain'],cwd=c.W)
    c.write(c.R/'SHA256_MANIFEST.json',{'source_commit':commit,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'roots':{'worktree':str(c.W),'round':str(c.R)},'files':files,'exclusions':['runtime stdout/stderr, bound by receipts','SEAL.json','SHA256_MANIFEST.json']})
    result={'manifest_sha256':c.sha(c.R/'SHA256_MANIFEST.json'),'file_count':len(files),'total_bytes':sum(f['bytes'] for f in files),'source_commit':commit,'scientific_verdict':status['scientific_verdict']};c.write(c.R/'SEAL.json',result);print(json.dumps(result))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');main(p.parse_args().verify)
