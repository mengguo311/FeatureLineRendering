"""Seal validated finite outputs; retain interrupted history as history."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import argparse,json,datetime,shutil,subprocess


def seal(unit):
    if (unit/'EVIDENCE_LOCK.json').exists():raise FileExistsError('already sealed')
    status=json.loads((unit/'STATUS.json').read_text());p=json.loads((unit/'PROTOCOL.json').read_text())
    assert status['execution_state']=='partial' and status['scientific_seal'] is False
    assert sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256']
    for scene in ('chair','lego'):
        v=json.loads((unit/'results'/scene/'VALIDATION.json').read_text());assert v['all_scheduled_views_validated']
    for name,h in p['source_hashes'].items():
        assert sha(unit/'source_snapshot'/name)==h and sha(unit/'delivery_source'/name)==h
    previous={}
    for number in (1,2,3):
        old=OUTPUT_ROOT/f'units/unit_{number:03d}';lock=json.loads((old/'EVIDENCE_LOCK.json').read_text())
        errors=[name for name,v in lock['files'].items() if sha(old/name)!=v['sha256']]
        assert not errors,errors
        previous[old.name]=dict(members=len(lock['files']),mismatches=errors,lock_sha256=sha(old/'EVIDENCE_LOCK.json'))
    js(unit/'PREVIOUS_SEALS_FINAL_AUDIT.json',dict(utc=now(),units=previous))
    receipts={};interruptions={};pids=[]
    for start in (unit/'logs').glob('*.start.json'):
        name=start.name.removesuffix('.start.json');record=json.loads(start.read_text());pids.append(record['pid'])
        receipt=unit/'logs'/(name+'.receipt.json');interruption=unit/'logs'/(name+'.interruption.json')
        if receipt.exists():receipts[name]=json.loads(receipt.read_text())['returncode']
        else:
            assert interruption.exists(),start
            interruptions[name]=json.loads(interruption.read_text())
    assert set(k for k,v in receipts.items() if v!=0)=={'transfer_tdd_red'}
    alive=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid=,comm='],text=True,capture_output=True)
    assert not alive.stdout.strip(),alive.stdout
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-gaussian-link-v05'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert commit==status['code_commit']
    end=datetime.datetime.now(datetime.timezone.utc);elapsed=(end-datetime.datetime.fromisoformat(p['started_jst'])).total_seconds()/60
    assert elapsed<=55,elapsed
    status.update(finished_utc=end.isoformat(),elapsed_minutes=elapsed,finished_before_55min=True,
        evidence_seal=dict(file='EVIDENCE_LOCK.json',scientific_seal=False,
            scope='Validated finite engineering arrays/renders/tests; negative scientific gates and interrupted history explicitly preserved'))
    js(unit/'STATUS.json',status)
    interrupted={str(f.relative_to(unit/'interrupted_lego_view_0')):dict(sha256=sha(f),bytes=f.stat().st_size)
        for f in (unit/'interrupted_lego_view_0').rglob('*') if f.is_file()}
    js(unit/'INTERRUPTED_OUTPUT_LOCK.json',dict(utc=now(),directory='interrupted_lego_view_0',files=interrupted,
        scope='Original bytes from interrupted batch; no runner success receipt; not counted as a successful experiment'))
    runtime.output_guard(unit)
    js(unit/'FINAL_CHECK.json',dict(utc=now(),branch=branch,commit=commit,receipts=receipts,interruptions=interruptions,
        all_started_commands_accounted_for=True,no_logged_children_still_present=True,elapsed_minutes=elapsed,
        root_free=shutil.disk_usage('/').free,HDD_free=shutil.disk_usage(OUTPUT_ROOT).free,
        unit_bytes=sum(f.stat().st_size for f in unit.rglob('*') if f.is_file()),scientific_seal=False))
    exclude={'EVIDENCE_LOCK.json','SEAL_VERIFY.json'}
    members={str(f.relative_to(unit)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in sorted(unit.rglob('*'))
        if f.is_file() and f.name not in exclude and 'scratch' not in f.relative_to(unit).parts}
    js(unit/'EVIDENCE_LOCK.json',dict(utc=now(),scientific_seal=False,
        scope='Validated finite engineering evidence, negative transfer results, and explicitly labeled original failure/interruption history. No semantic/native/physical seal.',files=members))
    errors=[name for name,v in members.items() if sha(unit/name)!=v['sha256']];assert not errors
    result=dict(utc=now(),members=len(members),mismatches=errors,lock_sha256=sha(unit/'EVIDENCE_LOCK.json'),scientific_seal=False,elapsed_minutes=elapsed)
    js(unit/'SEAL_VERIFY.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);seal(ap.parse_args().unit)
