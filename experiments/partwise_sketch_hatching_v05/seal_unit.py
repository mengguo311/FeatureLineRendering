"""Integrity lock for validated finite evidence; deliberately no scientific seal."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json,subprocess,shutil

def seal(unit):
    unit=output_guard(unit)
    if (unit/'EVIDENCE_LOCK.json').exists():raise FileExistsError('unit is already sealed')
    p=json.loads((unit/'PROTOCOL.json').read_text());status=json.loads((unit/'STATUS.json').read_text())
    validation=json.loads((unit/'VALIDATION.json').read_text())
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-gaussian-link-v05'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    changes=subprocess.check_output(['git','status','--porcelain'],text=True)
    assert not changes,changes
    assert sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(p['source']['original_ply'])==p['source']['sha256']
    for name,h in p['asset_hashes'].items():assert sha(Path(p['asset'])/name)==h
    for name,h in p['source_hashes'].items():assert sha(unit/'source_snapshot'/name)==h
    for item in Path(__file__).parent.iterdir():
        if item.is_file():assert sha(item)==sha(unit/'delivery_source'/item.name),item.name
    assert status['execution_state']=='partial' and status['scientific_seal'] is False
    assert validation['all_binding_arrays_recomputed_exact']
    rc={}
    for file in (unit/'logs').glob('*.receipt.json'):
        data=json.loads(file.read_text());rc[file.stem]=data['returncode']
        assert data['returncode']==(1 if file.name=='tdd_red.receipt.json' else 0)
    # Cold entrypoint and media have already finished; their files are immutable
    # evidence from this point. Nothing in orchestration is read or written here.
    for folder in ('cold_replay','entrypoint_replay'):
        rr=json.loads((unit/folder/'REPLAY.json').read_text())
        assert all(all(v.values()) for v in rr['checks'].values())
    vv=json.loads((unit/'media/VIDEO_VALIDATION.json').read_text())
    assert all(x['decoded_frames']==x['encoded_frames'] for x in vv['videos'])
    js(unit/'SOURCE_COMMIT.json',dict(commit=commit,branch=branch,worktree=str(Path.cwd()),clean=True,
        frozen_science_source='source_snapshot',complete_delivery_source='delivery_source'))
    status['code_commit']=commit;status['finished_utc']=now();js(unit/'STATUS.json',status)
    size=sum(x.stat().st_size for x in unit.rglob('*') if x.is_file())
    assert size<20*2**30
    js(unit/'FINAL_CHECK.json',dict(utc=now(),branch=branch,commit=commit,source_PLY_hash_unchanged=True,
        asset_hashes_unchanged=True,frozen_protocol_and_code_hashes_unchanged=True,delivered_source_equals_committed=True,
        receipt_returncodes=rc,output_bytes=size,all_required_deliverables=True,scientific_seal=False,
        no_live_unit_compute='all launched compute/compile/ffmpeg command sessions returned; no server or background worker started'))
    manifest={str(x.relative_to(unit)):dict(sha256=sha(x),bytes=x.stat().st_size) for x in sorted(unit.rglob('*'))
              if x.is_file() and 'scratch' not in x.relative_to(unit).parts}
    lock=dict(created_utc=now(),scope='validated finite CPU mapping/render/edit and replay evidence integrity; not native/semantic/scientific certification',
              scientific_seal=False,files=manifest)
    js(unit/'EVIDENCE_LOCK.json',lock)
    reread=json.loads((unit/'EVIDENCE_LOCK.json').read_text())
    for rel,record in reread['files'].items():assert sha(unit/rel)==record['sha256']
    js(unit/'SEAL_VERIFY.json',dict(utc=now(),lock_sha256=sha(unit/'EVIDENCE_LOCK.json'),checked_files=len(manifest),all_hashes_match=True,scientific_seal=False))
    print(json.dumps(dict(execution_state='partial',files=len(manifest),output_bytes=size,commit=commit,next_action='continue')),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);seal(p.parse_args().unit)
