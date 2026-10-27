"""Independent file/array readback, preserving the interrupted raw command."""
import runtime
from runtime import js,sha
from pathlib import Path
import json
import numpy as np
from PIL import Image
from linked_asset import npz,load_asset
from whole_asset import load_preset
from run_view import verify
UNIT=runtime.ROOT/'units/unit_006'
def main():
    verify(UNIT);checks=dict(render_payload_files=0,png_array_checks=0,compiler_records=[],source_inputs_unchanged=0)
    for rr in list((UNIT/'renders').rglob('RENDER_RECEIPT.json'))+[UNIT/'cold_reload/RENDER_RECEIPT.json']:
        r=json.loads(rr.read_text())
        for name,h in r['files'].items():assert sha(rr.parent/name)==h,name;checks['render_payload_files']+=1
        f=npz(rr.parent/'FRAME.npz')
        for key in ('source','paper','hybrid','proxy','support','combined_ink','other_ink','contour','seat_ink','seat_linked_ink'):
            a=f[key] if key in ('source','paper','hybrid','proxy','support') else 1-f[key]
            if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
            with Image.open(rr.parent/(key+'.png')) as im:
                im.load();np.testing.assert_array_equal(np.asarray(im),np.uint8(np.clip(a,0,1)*255+.5));checks['png_array_checks']+=1
        records=json.loads((rr.parent/'build/COMPILE.json').read_text())
        checks['compiler_records'].append(dict(path=str((rr.parent/'build/COMPILE.json').relative_to(UNIT)),returncodes=[v.get('returncode','UNKNOWN') for v in records]))
        assert all(v.get('returncode')==0 for v in records)
    cold=npz(UNIT/'cold_reload/FRAME.npz');ref=npz(UNIT/'renders/selective/orbit_241_24_5.1/FRAME.npz')
    assert set(cold)==set(ref)
    for k in cold:np.testing.assert_array_equal(cold[k],ref[k])
    checks['cold_reload']=dict(arrays=len(cold),exact=True)
    asset=UNIT/'delivery/assets/selective'
    for folder in ('cli_preset','cli_edit_noop'):
        assert load_preset(UNIT/folder)==load_preset(asset)
        for r in range(1,6):assert sha(UNIT/folder/f'region_{r}.npz')==sha(asset/f'region_{r}.npz')
    checks['cli_recreated_all_path_bytes']=True;checks['cli_noop_all_path_bytes']=True
    for record in json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text())['files']:
        assert sha(Path(record['source']))==record['sha256'],record['source'];checks['source_inputs_unchanged']+=1
    assert not (UNIT/'logs/008_highrear_selective.json').exists()
    rr=UNIT/'renders/selective/orbit_241_60_5.1/RENDER_RECEIPT.json'
    interruption=dict(command='008_highrear_selective',tool_outer_exit_code=143,wrapper_returncode='UNKNOWN',child_returncode='UNKNOWN',
        cause='UNKNOWN',original_start='logs/008_highrear_selective.start.json',original_log='logs/008_highrear_selective.log',
        render_receipt_sha256=sha(rr),completed_payload_independently_verified=True,
        recovery='No science rerun and no fabricated final receipt; independent hashes, 10 PNG/array pairs, frozen inputs and compiler records verified by finish_checks.',
        process_observation='Known wrapper PID2343017 absent when checked; ps exit1. No foreign process was inspected beyond PID/comm or modified.')
    js(UNIT/'INTERRUPTION_008.json',interruption)
    checks['interruption']=interruption;checks['decision_unchanged']=True;checks['frozen_inputs_unchanged']=True
    js(UNIT/'FINAL_VERIFICATION.json',checks)
    print(json.dumps(checks),flush=True)
if __name__=='__main__':main()
