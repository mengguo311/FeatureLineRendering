import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil
from linked_asset import npz
from structure_motion import verify_unit
UNIT=runtime.ROOT/'units/unit_008'
def main():
    verify_unit(UNIT);records=[]
    for i in range(16,27):
        root=UNIT/'renders'/f'{i:03d}';receipt=json.loads((root/'RENDER_RECEIPT.json').read_text())
        for name,h in receipt['files'].items():assert sha(root/name)==h
        for arm in ('off','on'):assert len(npz(root/arm/'FRAME.npz'))==24
        records.append(dict(index=i,receipt_sha256=sha(root/'RENDER_RECEIPT.json'),payload_verified=True))
    partial=UNIT/'renders/027';archive=UNIT/'failed_attempts/007_frame027'
    assert not (partial/'RENDER_RECEIPT.json').exists()
    archive.parent.mkdir(exist_ok=True);shutil.move(str(partial),archive)
    js(UNIT/'INTERRUPTION_007.json',dict(utc=runtime.now(),actual_tool_exit_code=143,wrapper_returncode='UNKNOWN',child_returncode='UNKNOWN',
        reason='UNKNOWN; final receipt absent. No fabricated success or diagnosis.',completed_frames=records,partial_preserved=str(archive.relative_to(UNIT)),
        own_wrapper_pid=2349640,own_wrapper_ps_returncode=1,own_matching_renderer_pgrep_returncode=1,
        recovery='Resume unchanged frozen trajectory at27; no recomputation of completed verified frames16..26',extension_invoked=False))
    print('Verified completed16..26; preserved incomplete27; resume27',flush=True)
if __name__=='__main__':main()
