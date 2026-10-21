"""Preserve a scheduling deviation; rerun SAME frozen stages serially, no tuning."""
from runtime import *
import subprocess
import time

def main():
    zoom=json.loads((ROOT/'runtime/render_zoom.started.json').read_text())
    zr=json.loads((ROOT/'runtime/render_zoom.json').read_text())
    iso=json.loads((ROOT/'runtime/render_isolated.started.json').read_text())
    ir=json.loads((ROOT/'runtime/render_isolated.json').read_text())
    overlap=max(0.,min(zoom['start_unix']+zr['wall_seconds'],iso['start_unix']+ir['wall_seconds'])-max(zoom['start_unix'],iso['start_unix']))
    assert overlap>0 and zr['returncode']==ir['returncode']==0
    evidence=ROOT/'attempt_schedule_overlap'
    if evidence.exists(): raise FileExistsError(evidence)
    evidence.mkdir()
    amendment=dict(kind='EXECUTION_ONLY_INFRASTRUCTURE_RECOVERY',overlap_seconds=overlap,
        reason='Main orchestration launched isolated scoring render before confirming zoom completion. Both numeric processes1thread, affinity[0,1], CPU total<=2; frozen serial scheduling was violated.',
        preserved_original_returncodes=[zr['returncode'],ir['returncode']],
        correction='Move original two output sets into evidence, rerun identical commands serially; assert every PNG and NPZ hash exact. No scientific parameter, input, threshold or arm change.',
        protocol_sha256=sha(ROOT/'PROTOCOL.json'),status='PRESERVED_BEFORE_REPLAY')
    write_json(ROOT/'EXECUTION_AMENDMENT.json',amendment)
    (ROOT/'renders/zoom').rename(evidence/'zoom')
    (ROOT/'isolated').rename(evidence/'isolated')
    update_status('SERIAL_SCHEDULING_RECOVERY',execution_state='RUNNING')
    receipts=[]
    for sequence in ('zoom','isolated'):
        cmd=[PYTHON,'-B',str(CODE/'execute.py'),f'render_{sequence}_serial',str(CODE/'run_comparison.py'),sequence]
        result=subprocess.run(cmd,timeout=590)
        receipts.append(dict(command=cmd,returncode=result.returncode))
        write_json(evidence/'RECOVERY_COMMANDS.json',receipts)
        result.check_returncode()
    checked=[]
    for sequence,folder in [('zoom',ROOT/'renders/zoom'),('isolated',ROOT/'isolated')]:
        before=evidence/sequence
        for path in sorted(before.rglob('*')):
            if path.suffix not in ('.png','.npz'): continue
            current=folder/path.relative_to(before)
            assert sha(path)==sha(current),current
            checked.append(dict(before=str(path),after=str(current),sha256=sha(path)))
    r0=json.loads((ROOT/'runtime/render_zoom_serial.started.json').read_text())
    r1=json.loads((ROOT/'runtime/render_zoom_serial.json').read_text())
    r2=json.loads((ROOT/'runtime/render_isolated_serial.started.json').read_text())
    assert r2['start_unix']>=r0['start_unix']+r1['wall_seconds']
    amendment.update(status='SERIAL_REPLAY_VALIDATED',bitwise_scientific_files=len(checked),
                     all_png_npz_exact=True,corrected_stages_serial=True,unchanged_protocol_sha256=sha(ROOT/'PROTOCOL.json'))
    write_json(ROOT/'EXECUTION_AMENDMENT.json',amendment)
    write_json(evidence/'REPLAY_EQUIVALENCE.json',dict(checked=checked,all_exact=True))
    print(json.dumps(dict(overlap_seconds=overlap,replay_files=len(checked),all_exact=True)))

if __name__=='__main__': main()
