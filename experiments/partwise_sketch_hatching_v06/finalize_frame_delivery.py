"""Final metadata/receipt checks after unit010 handoff recovery; no experiment."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT,js,sha,now
from pathlib import Path
import json,shutil
from PIL import Image
from run_frame_unit import protocol

def main():
    p=protocol()
    for path,h in p['inputs'].items():assert sha(path)==h,path
    status=json.loads((UNIT/'STATUS.json').read_text());root=json.loads((OUTPUT_ROOT/'DELIVERY_STATUS.json').read_text())
    assert status['execution_state']=='completed' and root['latest_unit']==str(UNIT)
    assert status['next_action']==root['next_action']=='stop' and not status['default_promoted']
    for path in status['artifacts'].values():assert Path(path).is_file(),path
    decoded=[]
    for name in ('ALL_DEV_VIEWS.png','ALL_DEV_MATCHED.png','ALL_DEV_INK.png','ALL_ARC_FRAMES.png'):
        with Image.open(UNIT/name) as im:im.verify()
        decoded.append(name)
    receipts=[dict(name=f.name,**json.loads(f.read_text())) for f in sorted((UNIT/'logs').glob('*.receipt.json'))]
    actual_failures={r['name']:r['returncode'] for r in receipts if r['returncode']!=0}
    assert actual_failures=={'handoff_001.receipt.json':1,'tdd_red_001.receipt.json':1},actual_failures
    assert json.loads((UNIT/'logs/handoff_002.receipt.json').read_text())['returncode']==0
    assert (UNIT/'interrupted_handoff_001/finish_frame_unit.py').is_file()
    for n,h in json.loads((UNIT/'DELIVERY_PREVIOUS_LOCK.json').read_text())['files'].items():assert sha(UNIT/'delivery_previous'/n)==h
    status['tests_and_actual_commands']=receipts;status['final_metadata_checked_utc']=now()
    js(UNIT/'STATUS.json',status)
    failures=dict(failures=[r for r in receipts if r['returncode']!=0],recovery=json.loads((UNIT/'logs/handoff_002.receipt.json').read_text()),
        scope='Expected TDD RED and post-result handoff import failure; no failed scientific render or parameter revision')
    js(UNIT/'ENGINEERING_FAILURES.json',failures)
    hand=UNIT/'handoff_source';shutil.copy2(Path(__file__),hand/Path(__file__).name)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in hand.iterdir()}))
    js(UNIT/'FINAL_HANDOFF_CHECK.json',dict(utc=now(),protocol_sha256=sha(UNIT/'PROTOCOL.json'),decision_sha256=sha(UNIT/'DECISION.json'),
        input_hashes_checked=len(p['inputs']),receipt_count=len(receipts),actual_failures=actual_failures,handoff_recovery_rc=0,
        root_delivery_points_to_current_unit=True,readable_whole_object_panels=decoded,scientific_outputs_unchanged=True,
        scientific_seal=False,parent_monitor_verification='pending',next_action='stop',stop_reason='no_new_units_deadline'))
    print('FINAL HANDOFF checked; science unchanged; recovery rc0; original failures retained',flush=True)

if __name__=='__main__':main()
