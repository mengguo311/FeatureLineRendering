"""Preserve raw interruption, certify completed payloads, move incomplete output aside."""
import runtime
from runtime import js,sha
from PIL import Image
UNIT=runtime.ROOT/'units/unit_003'
def main():
    assert not (UNIT/'logs/007_orbit_30_50.json').exists()
    checked={}
    for i in range(30,45):
        p=UNIT/'renders/orbit'/f'{i:03d}';receipt=runtime.json.loads((p/'RENDER_RECEIPT.json').read_text())
        for name,h in receipt['files'].items():
            assert sha(p/name)==h
            if name.endswith('.png'):
                with Image.open(p/name) as im:im.load()
        checked[str(i)]=sha(p/'RENDER_RECEIPT.json')
    p=UNIT/'renders/orbit/045';files=[str(f.relative_to(p)) for f in p.rglob('*') if f.is_file()]
    assert not files,files
    destination=UNIT/'failed_attempts/orbit_045_interrupted';destination.parent.mkdir(exist_ok=True)
    p.rename(destination)
    js(UNIT/'INTERRUPTION_007.json',dict(actual_tool_exit_code=143,controller_returncode='UNKNOWN',render_batch_child_returncode='UNKNOWN',
        controller_final_receipt='missing; never fabricated',controller_pid=2332409,
        process_observation='controller and its children absent; only unrelated python3 PID2324005 observed and untouched',
        completed_frames_checked=checked,incomplete_frame=45,incomplete_files=files,preserved_directory=str(destination),
        recovery='Resume45 onward under new receipts; completed30..44 never rerun',reason='UNKNOWN'))
    print('Verified15 completed frames; preserved empty interrupted frame45; resume45',flush=True)
if __name__=='__main__':main()
