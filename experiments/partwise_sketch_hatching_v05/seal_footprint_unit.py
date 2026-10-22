"""Seal completed finite engineering artifacts, never a scientific GO."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,datetime,shutil,subprocess

def seal(unit):
    if (unit/'EVIDENCE_LOCK.json').exists():raise FileExistsError('already sealed')
    status=json.loads((unit/'STATUS.json').read_text());assert status['execution_state']=='partial'
    assert status['scientific_seal'] is False
    for scene in ('chair','lego'):
        v=json.loads((unit/'results'/scene/'VALIDATION.json').read_text())
        assert v['all_footprint_rows_and_UNKNOWN_recomputed'] and v['no_prior_UNKNOWN_promoted']
    pending=[];receipts={}
    for start in (unit/'logs').glob('*.start.json'):
        receipt=start.with_name(start.name.replace('.start.json','.receipt.json'))
        if not receipt.exists():pending.append(start.name)
        else:receipts[receipt.name]=json.loads(receipt.read_text())['returncode']
    assert not pending,pending
    interrupted=json.loads((unit/'INTERRUPTED_EVALUATION_LOCK.json').read_text())
    for name,v in interrupted['files'].items():assert sha(Path(interrupted['directory'])/name)==v['sha256']
    proto=json.loads((unit/'PROTOCOL.json').read_text())
    for name,h in proto['source_hashes'].items():
        assert sha(unit/'source_snapshot'/name)==h
        assert sha(unit/'delivery_source'/name)==h
    start=datetime.datetime.fromisoformat('2026-10-22T18:00:46.369335+09:00')
    end=datetime.datetime.now(datetime.timezone.utc);elapsed=(end-start).total_seconds()/60
    status.update(finished_utc=end.isoformat(),elapsed_minutes=elapsed,finished_before_55min=elapsed<=55,
        evidence_seal=dict(file='EVIDENCE_LOCK.json',scientific_seal=False,scope='Validated finite engineering results plus preserved failure receipts; no native/physical/semantic seal'))
    js(unit/'STATUS.json',status)
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-gaussian-link-v05'
    check=dict(utc=now(),branch=branch,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        protocol_core_source_unchanged=True,all_started_commands_have_receipts=True,receipt_returncodes=receipts,
        elapsed_minutes=elapsed,under_55_minutes=elapsed<=55,root_free=shutil.disk_usage('/').free,
        HDD_free=shutil.disk_usage(runtime.OUTPUT_ROOT).free,unit_bytes=sum(f.stat().st_size for f in unit.rglob('*') if f.is_file()),
        scientific_seal=False)
    assert check['root_free']>=2**30 and check['HDD_free']>=10*2**30
    js(unit/'FINAL_CHECK.json',check)
    excluded={'EVIDENCE_LOCK.json','SEAL_VERIFY.json'}
    members={str(f.relative_to(unit)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(unit.rglob('*'))
        if f.is_file() and f.name not in excluded and 'scratch' not in f.relative_to(unit).parts}
    js(unit/'EVIDENCE_LOCK.json',dict(utc=now(),scientific_seal=False,
        scope='Validated finite source-kernel engineering evidence; failed test/command receipts are preserved historical records, not successful experiments',files=members))
    errors=[name for name,v in members.items() if sha(unit/name)!=v['sha256']]
    assert not errors,errors
    result=dict(utc=now(),members=len(members),mismatches=errors,lock_sha256=sha(unit/'EVIDENCE_LOCK.json'),scientific_seal=False)
    js(unit/'SEAL_VERIFY.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);seal(ap.parse_args().unit)
