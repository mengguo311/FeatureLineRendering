"""Separate handoff: actual fixed before/after controls and portable packaging."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse,json,shutil
import numpy as np
from PIL import Image
from linked_asset import npz,query
from run_motion import MotionRenderer,verify_unit
from motion import load_trajectory
from hybrid import edit_metrics
from finish_outputs import label_panel
UNIT=runtime.ROOT/'units/unit_003';CODE=Path(__file__).parent

def controls():
    verify_unit(UNIT)
    plan=load_trajectory(UNIT/'delivery/TRAJECTORY.json');samples=json.loads((UNIT/'delivery/SAMPLES.json').read_text())
    renderer=MotionRenderer(UNIT/'delivery/assets/whole_baseline',UNIT/'renders/build',samples)
    for i in (0,60):
        row=plan['orbit'][i];reference=UNIT/'inputs/reference'/row['camera']['view']/'whole_baseline/FRAME.npz'
        renderer.frame(row['camera'],UNIT/'controls'/f'{i:03d}',reference,False)
    js(UNIT/'SOURCE_ID_QUERY.json',query(UNIT/'delivery/assets/whole_spacing',[0,1,121080,256689]))
    verify_unit(UNIT)

def compare():
    verify_unit(UNIT);records={};panels=[]
    for i in (0,60):
        before=UNIT/'controls'/f'{i:03d}';after=UNIT/'renders/orbit'/f'{i:03d}'
        receipt=json.loads((before/'RENDER_RECEIPT.json').read_text())
        for name,h in receipt['files'].items():assert sha(before/name)==h
        a=npz(before/'FRAME.npz');b=npz(after/'FRAME.npz')
        prior=npz(UNIT/'inputs/reference'/receipt['camera']['view']/'whole_baseline/FRAME.npz')
        for key in a:np.testing.assert_array_equal(a[key],prior[key])
        invariant={k:bool(np.array_equal(a[k],b[k])) for k in ('source','source_alpha','paper','support','regions','proxy_depth','other_ink','contour','layer_1','layer_2','layer_3','layer_5')}
        assert all(invariant.values())
        records[str(i)]=dict(invariant_layers=invariant,spacing_increment=edit_metrics(a['hybrid'],b['hybrid'],a['regions']))
        panels.append(label_panel([before/'hybrid.png',after/'hybrid.png',after/'proxy.png'],
            [f'Frame {i:03d} | spacing .045',f'Frame {i:03d} | spacing .0675','Conventional proxy .0675']))
    canvas=Image.new('RGB',(panels[0].width,sum(p.height for p in panels)),'white');y=0
    for p in panels:canvas.paste(p,(0,y));y+=p.height
    canvas.save(UNIT/'media/BEFORE_AFTER.png');js(UNIT/'EDIT_CONTROLS.json',records)
    if not (UNIT/'logs/013_controls.json').exists():
        js(UNIT/'INTERRUPTION_013.json',dict(actual_tool_exit_code=143,controller_returncode='UNKNOWN',child_returncode='UNKNOWN',
            controller_final_receipt='missing; never fabricated',reason='UNKNOWN',
            completed_payloads=['controls/000','controls/060','SOURCE_ID_QUERY.json'],
            independent_control_array_comparisons=38,all_equal=True,recovery='Both completed controls independently audited; no rerender'))
    print(json.dumps(records),flush=True)

def package():
    verify_unit(UNIT);d=UNIT/'delivery';e=d/'evidence';e.mkdir(exist_ok=True)
    for name in ('REPORT_ZH.md','STATUS.json','NEXT.json','PROTOCOL.json','PROTOCOL_LOCK.json','SOURCE_LOCK.json','INPUT_COPY_RECEIPT.json',
                 'TEMPORAL.json','FRAME_INDEX.json','MEDIA_AUDIT.json','EDIT_CONTROLS.json','SOURCE_ID_QUERY.json','INTERRUPTION_007.json','INTERRUPTION_013.json','SAVED_SUMMARY.json','GIT_FINAL.json'):
        shutil.copy2(UNIT/name,e/name)
    for name in ('orbit.png','zoom.png','orbit_CONTACT.png','zoom_CONTACT.png','WHOLE_LAYERS.png','BEFORE_AFTER.png'):
        shutil.copy2(UNIT/'media'/name,e/name)
    for sequence in ('orbit','zoom'):
        shutil.copytree(UNIT/'media'/(sequence+'_frames'),e/(sequence+'_frames'),dirs_exist_ok=True)
    shutil.copytree(UNIT/'logs',e/'logs',dirs_exist_ok=True)
    shutil.copy2(CODE/'handoff.py',d/'code/handoff.py')
    (d/'handoff_source').mkdir(exist_ok=True)
    for source in CODE.iterdir():
        if source.is_file():shutil.copy2(source,d/'handoff_source'/source.name)
    records={}
    for path in sorted((UNIT/'logs').glob('*.json')):
        if path.name.endswith('.start.json'):continue
        row=json.loads(path.read_text())
        if 'child_returncode' in row:records[path.stem]=row
    records['encoder_discovery']=dict(argv='command -v ffmpeg; command -v ffprobe',actual_tool_exit_code=1,
        outcome='Neither executable found; existing Pillow lossless APNG used; no install or download')
    records['007_interrupted']=json.loads((UNIT/'INTERRUPTION_007.json').read_text())
    records['013_interrupted']=json.loads((UNIT/'INTERRUPTION_013.json').read_text())
    records['observational_source_diff']=dict(actual_tool_exit_code=1,command='git diff --no-index whole_chair/render.py chair_motion/render.py',
        outcome='Expected differences: selected stroke observation masks only; original compositor/visibility arithmetic retained')
    records['renderer_compile']=json.loads((UNIT/'renders/build/COMPILE.json').read_text())
    js(UNIT/'EXECUTION_RECORDS.json',records);shutil.copy2(UNIT/'EXECUTION_RECORDS.json',e/'EXECUTION_RECORDS.json')
    sources={p.name:sha(p) for p in CODE.iterdir() if p.is_file()}
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files=sources));shutil.copy2(UNIT/'HANDOFF_SOURCE_LOCK.json',e/'HANDOFF_SOURCE_LOCK.json')
    files={str(p.relative_to(d)):sha(p) for p in sorted(d.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
    js(d/'MANIFEST.json',dict(files=files,scope='Chair only; relative data/assets/code; motion samples belong to saved whole_spacing; original rows and proxy paths, not per-path source ownership'))
    # Re-read both the portable contents and all original frozen inputs.
    for rel,h in files.items():assert sha(d/rel)==h
    verify_unit(UNIT)
    size=sum(p.stat().st_size for p in UNIT.rglob('*') if p.is_file())
    assert size<20*2**30
    js(UNIT/'FINAL_VERIFICATION.json',dict(package_files=len(files),package_manifest_sha256=sha(d/'MANIFEST.json'),
        unit_bytes=size,source_and_inputs_unchanged=True,decision_sha256=sha(UNIT/'DECISION.json'),
        media_all_frame_decode='MEDIA_AUDIT.json',remote_copy_verification='not performed',last_engine_exit_code='UNKNOWN'))
    print(json.dumps(dict(package_files=len(files),unit_bytes=size,manifest_sha256=sha(d/'MANIFEST.json'))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['controls','compare','package']);a=p.parse_args()
    {'controls':controls,'compare':compare,'package':package}[a.stage]()
