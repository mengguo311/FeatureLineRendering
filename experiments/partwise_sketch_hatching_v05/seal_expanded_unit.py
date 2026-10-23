"""Integrity seal for verified finite engineering evidence, never scientific GO."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import argparse,json,subprocess,os
import numpy as np


def seal(unit):
    if (unit/'EVIDENCE_LOCK.json').exists():raise FileExistsError('existing seal must not be overwritten')
    p=json.loads((unit/'PROTOCOL.json').read_text());status=json.loads((unit/'STATUS.json').read_text())
    assert status['execution_state']=='partial' and status['frozen_experiment_execution_complete'] and not status['scientific_seal']
    assert json.loads((unit/'NEXT.json').read_text())['action']=='stop'
    parent=OUTPUT_ROOT/'orchestration/continuation_001'
    preserved={}
    for filename in ('UNIT005_FILES_BEFORE.json','PROTECTED_FILES_BEFORE.json'):
        manifest=json.loads((parent/filename).read_text())
        errors=[path for path,h in manifest.items() if sha(path)!=h]
        assert not errors,errors
        preserved[filename]=dict(members=len(manifest),mismatches=errors,manifest_sha256=sha(parent/filename))
    # Old unit evidence remains read-only; verify referenced locks without reruns.
    for name,h in p['input_hashes'].items():assert sha(name)==h,name
    for name,h in p['source_hashes'].items():assert sha(unit/'source_snapshot'/name)==h,name
    for scene in p['scenes']:
        validation=json.loads((unit/f'VALIDATION_{scene}.json').read_text())
        assert len(validation['checks'])==4 and validation['actual_scaled_matching_valid']
        root=unit/'results'/scene
        for name,h in json.loads((root/'BINDING_LOCK.json').read_text())['files'].items():assert sha(root/name)==h
        query=unit/'continuation_001'/('query_'+scene);receipt=json.loads((query/'RECEIPT.json').read_text())
        with (query/'path_original_ID_support.csv').open() as f:assert sum(1 for _ in f)-1==receipt['rows']
        with np.load(query/'ALL_ANCHORS.npz') as z:
            assert len(z['segment_index'])==receipt['anchors']
            assert int(z['unknown'].sum())==receipt['unknown_anchors']
        for operation in ('tint','opacity'):
            replay=json.loads((unit/'continuation_001'/f'replay_{scene}_{operation}'/'RECEIPT.json').read_text())
            assert all(replay['all_arrays_exact'].values())
    pack=unit/'continuation_001/delivery';pm=json.loads((pack/'PACKAGE_FILES.json').read_text())
    for name,v in pm['files'].items():assert sha(pack/name)==v['sha256'],name
    js(unit/'continuation_001/PRESERVATION_FINAL_AUDIT.json',dict(utc=now(),protected=preserved,all_protocol_inputs_unchanged=True,
        frozen_protocol_sha256=sha(unit/'PROTOCOL.json'),package_members=len(pm['files']),package_exact=True))
    partial_files=[f for dirname in ('interrupted_chair_view_1','continuation_001/interrupted_lego_view_3') for f in (unit/dirname).rglob('*') if f.is_file()]
    js(unit/'INTERRUPTED_OUTPUT_LOCK.json',dict(utc=now(),scope='Integrity of interrupted raw files ONLY; excluded from validated scientific evidence.',
        original_child_returncodes={'chair_view1':-15,'continuation_lego_view3':-15},files={str(f.relative_to(unit)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in partial_files}))
    # Own completed child processes must be absent. PID reuse is not attributed.
    owned=[]
    for f in (unit/'logs').glob('resume_*.start.json'):
        d=json.loads(f.read_text());receipt=f.with_name(f.name.replace('.start.json','.receipt.json'))
        assert receipt.exists()
        rc=json.loads(receipt.read_text())['returncode'];assert rc==0 or (receipt.name=='resume_lego_eval3_c001.receipt.json' and rc==-15)
        pid=d['pid'];owned.append(dict(pid=pid,present=Path(f'/proc/{pid}').exists(),returncode=rc))
    assert not any(x['present'] for x in owned),'completed child PID still present; inspect PID/comm before attributing'
    js(unit/'continuation_001/PROCESS_AUDIT.json',dict(utc=now(),own_recorded_children=owned,all_absent=True))
    files=[]
    for dirname in ('results','source_snapshot','logs','media','continuation_001'):
        for f in (unit/dirname).rglob('*'):
            if f.is_file() and 'build' not in f.relative_to(unit).parts and '__pycache__' not in f.parts and 'interrupted_lego_view_3' not in f.parts:
                files.append(f)
    for name in ('PROTOCOL.json','PROTOCOL_LOCK.json','PREVIOUS_SEAL_AUDIT.json','STATUS.json','NEXT.json','REPORT_ZH.md','SUMMARY.json',
                 'VALIDATION_chair.json','VALIDATION_lego.json','INTERRUPTED_OUTPUT_LOCK.json','SOURCE_COMMIT.json'):
        file=unit/name;assert file.is_file(),name;files.append(file)
    manifest={str(f.relative_to(unit)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(set(files))}
    js(unit/'EVIDENCE_LOCK.json',dict(utc=now(),scientific_seal=False,
        scope='Validated finite original-ID CPU mappings, matched source edits, replay/query/media and explicitly labeled historical failures. Interrupted raw outputs have only a separate integrity lock.',files=manifest))
    errors=[name for name,v in manifest.items() if sha(unit/name)!=v['sha256']];assert not errors
    js(unit/'SEAL_VERIFY.json',dict(utc=now(),members=len(manifest),mismatches=errors,scientific_seal=False,
        evidence_lock_sha256=sha(unit/'EVIDENCE_LOCK.json')))
    print(json.dumps(dict(sealed_engineering_files=len(manifest),scientific_seal=False,all_old_files_unchanged=True)),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);seal(ap.parse_args().unit)
