"""Read back every new payload, immutable input and cold recovery result."""
import runtime
from runtime import sha,js
from pathlib import Path
import json
import numpy as np
from PIL import Image
from linked_asset import npz
UNIT=runtime.ROOT/'units/unit_007';CODE=Path(__file__).parent
def main():
    lock=json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())
    for f,k in [('DECISION.json','decision'),('PROTOCOL.json','protocol'),('SOURCE_LOCK.json','source'),('INPUT_LOCK.json','inputs')]:assert sha(UNIT/f)==lock[k]
    inp=json.loads((UNIT/'INPUT_LOCK.json').read_text())
    for p,h in inp.items():assert sha(UNIT/p)==h,p
    for p,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text()).items():assert sha(CODE/p)==sha(UNIT/'source_snapshot'/p)==h,p
    for p,h in json.loads((UNIT/'DERIVED_LOCK.json').read_text()).items():assert sha(UNIT/p)==h,p
    for p,h in json.loads((UNIT/'PACKAGE_SOURCE_CHECK.json').read_text()).items():assert sha(UNIT/'delivery/code'/p)==h,p
    recovered={};png_count=0;compile_records=[];payloads={}
    roots=list((UNIT/'renders').glob('*/*'))+[UNIT/'cold_reload',UNIT/'serial_recovery/high_rear_on',UNIT/'serial_recovery/reserved_off']
    for out in roots:
        r=json.loads((out/'RENDER_RECEIPT.json').read_text());a=npz(out/'FRAME.npz')
        for f,h in r['files'].items():assert sha(out/f)==h;payloads[str((out/f).relative_to(UNIT))]=h
        for p in out.glob('*.png'):
            im=Image.open(p);im.load();x=a[p.stem]
            if p.stem in ('combined_ink','other_ink','contour','seat_ink','seat_linked_ink','structure','structure_available'):x=1-x
            if x.ndim==2:x=np.repeat(x[:,:,None],3,2)
            np.testing.assert_array_equal(np.asarray(im),np.uint8(np.clip(x,0,1)*255+.5));png_count+=1
        commands=json.loads((out/'build/COMPILE.json').read_text())
        assert all(c['returncode']==0 for c in commands)
        compile_records.append(dict(path=str((out/'build/COMPILE.json').relative_to(UNIT)),returncodes=[c['returncode'] for c in commands]))
    pairs=[('serial_recovery/high_rear_on','renders/on/orbit_241_60_5.1'),('serial_recovery/reserved_off','renders/off/orbit_196_36_5.1'),('cold_reload','renders/on/orbit_241_24_5.1')]
    for new,old in pairs:
        a=npz(UNIT/new/'FRAME.npz');b=npz(UNIT/old/'FRAME.npz');assert set(a)==set(b)
        for k in a:np.testing.assert_array_equal(a[k],b[k])
        recovered[new]=dict(arrays=len(a),exact=True)
    for p in ('structure.npz','mesh.npz','SOURCE_LINK.npz',*[f'region_{i}.npz' for i in range(1,6)]):assert sha(UNIT/'cli_toggle_off'/p)==sha(UNIT/'delivery/assets/off'/p)
    assert json.loads((UNIT/'cli_toggle_off/STRUCTURE.json').read_text())==json.loads((UNIT/'delivery/assets/off/STRUCTURE.json').read_text())
    r1=json.loads((UNIT/'logs/012_serial_high_rear.json').read_text());r2=json.loads((UNIT/'logs/013_serial_reserved.json').read_text())
    assert r1['finished_utc']<r2['started_utc'];assert r1['child_returncode']==r2['child_returncode']==0
    recovery=dict(utc=runtime.now(),original_violation='SCHEDULING_DEVIATION.json',overlap_seconds=json.loads((UNIT/'SCHEDULING_DEVIATION.json').read_text())['overlap_seconds'],
        serial_recovery_complete=True,actual_returncodes=[r1['child_returncode'],r2['child_returncode']],exact_arrays=recovered,
        scope='Affected data exactly recovered by subsequent serial cold renders. The initial serial-scheduling violation remains a protocol deviation; no blanket serial-only execution claim.')
    js(UNIT/'SCHEDULING_RECOVERY.json',recovery)
    js(UNIT/'FINAL_VERIFICATION.json',dict(source_inputs_unchanged=len(inp),decision_unchanged=True,scientific_source_unchanged=True,
        png_array_checks=png_count,compiler_records=compile_records,recovery=recovered,package_toggle_exact=True,
        render_payloads=payloads,protocol_deviation=recovery,local_only=True,no_remote_certification=True))
    print('Verified',png_count,'PNG/array pairs;',recovered)
if __name__=='__main__':main()
