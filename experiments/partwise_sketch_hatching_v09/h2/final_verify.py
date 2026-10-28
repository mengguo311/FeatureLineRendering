"""Final bounded audit of actual receipts, immutable inputs and corrected references."""
import runtime
from runtime import js,sha
import json,datetime,shutil
import numpy as np
from PIL import Image
from run_h2 import UNIT,CODE,VIEWS,ARMS
from linked_asset import npz

def main():
    load=lambda p:json.loads(p.read_text())
    for filename,root in [('INPUT_LOCK.json',UNIT),('SOURCE_LOCK.json',CODE),('DERIVED_LOCK.json',UNIT)]:
        for name,h in load(UNIT/filename).items():assert sha(root/name)==h,(filename,name)
    imports=load(UNIT/'IMPORT.json')
    for r in imports['files']:assert sha(runtime.Path(r['source']))==r['sha256'],r['source']
    assert sha(UNIT/'DECISION.json')==imports['decision_sha256']
    records=[]
    for f in sorted((UNIT/'logs').glob('*.json')):
        if f.name.endswith('.start.json'):continue
        r=load(f);records.append(dict(receipt=f.name,**r))
        assert r['child_returncode']==(1 if f.name=='001_RED.json' else 0),(f,r['child_returncode'])
    records.sort(key=lambda r:r['started_utc']);overlaps=[]
    for a,b in zip(records[:-1],records[1:]):
        if datetime.datetime.fromisoformat(b['started_utc'])<datetime.datetime.fromisoformat(a['finished_utc']):overlaps.append([a['receipt'],b['receipt']])
    assert not overlaps
    compile_records=load(UNIT/'cold_original/build/COMPILE.json');assert len(compile_records)==2 and all(r['returncode']==0 for r in compile_records)
    conventional=[]
    for view in VIEWS:
        old=npz(UNIT/f'inputs/cache/{view}/FRAME.npz')
        for arm in ARMS:
            f=npz(UNIT/f'conventional/{view}/{arm}/FRAME.npz');image=np.array(Image.open(UNIT/f'conventional/{view}/{arm}/image.png'))
            np.testing.assert_array_equal(image,np.repeat(np.uint8(np.clip(f['image'],0,1)*255+.5)[:,:,None],3,axis=2))
            if arm=='U':
                error=float(np.max(np.abs(f['image']-old['proxy'])))
                assert error<=1e-7,(view,error)
                conventional.append(dict(view=view,ungated_U_original_proxy_max_difference=error,scope='1-low(ink) versus low(1-ink) float32 rounding'))
    for sub in ('replay_check','regeneration_check'):
        record=load(UNIT/sub/'REPLAY_CHECK.json');assert len(record['comparisons'])==8
        if sub=='regeneration_check':assert len(record['regenerated_paths_exact'])==5
    size=sum(p.stat().st_size for p in UNIT.rglob('*') if p.is_file());assert size<20*2**30
    root_free=shutil.disk_usage('/').free;hdd_free=shutil.disk_usage(runtime.ROOT).free
    assert root_free>=2**30 and hdd_free>=10*2**30
    status=load(UNIT/'STATUS.json');assert status['execution_state']=='completed' and status['next']=='continue'
    for name in status['artifacts']:assert (UNIT/name).is_file(),name
    result=dict(utc=runtime.now(),decision_input_source_derived_locks_unchanged=True,old_import_sources_unchanged=len(imports['files']),
        completed_receipts=records,expected_RED_preserved=True,no_completed_command_overlap=True,compile_receipts=compile_records,
        corrected_conventional=conventional,corrected_images_checked=20,unit_bytes=size,root_free_bytes=root_free,hdd_free_bytes=hdd_free,
        final_process_cpu_affinity=sorted(runtime.os.sched_getaffinity(0)),parent_verification='pending independent parent read',
        active_final_audit_receipt='This audit process final returncode is authoritative in logs/013_final_verify.json after completion; not synthesized here.')
    js(UNIT/'FINAL_VERIFICATION.json',result)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',{p.name:sha(p) for p in sorted(CODE.iterdir()) if p.suffix in ('.py','.cpp')})
    print(json.dumps(dict(verified=True,unit_bytes=size,old_import_sources_unchanged=len(imports['files']),completed_receipts=len(records),corrected_images=20)))
if __name__=='__main__':main()
