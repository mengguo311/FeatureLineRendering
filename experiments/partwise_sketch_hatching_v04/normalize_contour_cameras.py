"""Apply the already frozen 512px contract; preserve mismatched-size attempt."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import json,subprocess,sys,time
from geometry import resize_camera

unit=OUTPUT_ROOT/'units/unit_011';here=Path(__file__).resolve().parent
p=json.loads((unit/'PROTOCOL.json').read_text());out=unit/'attempt_camera_sizes';out.mkdir()
facts={}
for scene in ('ficus','chair'):
    facts[scene]=[json.loads((unit/f'renders/{scene}/baseline/frame_{i:03d}.json').read_text())['camera']['width'] for i in range(4)]
    for root in ('source_model','renders'):
        destination=out/root;destination.mkdir(exist_ok=True);(unit/root/scene).rename(destination/scene)
(unit/'metrics/COMPARISON.json').rename(out/'COMPARISON.json')
for f in unit.joinpath('media').glob('*_*.png'):
    if f.name.startswith(('ficus_','chair_')):f.rename(out/f.name)
(unit/'VISUAL_REVIEW.json').rename(out/'VISUAL_REVIEW.json')
js(unit/'CAMERA_NORMALIZATION.json',dict(utc=now(),detected_by='Actual relocated CLI PNG replay assertion rc1; default four-model replay already exact',
    inherited_widths=facts,declared_protocol_size=512,reason='Trial passed inherited camera sizes directly; CLI resizes to512. Inconsistent protocol implementation.',
    effective_cameras={s:[resize_camera(c,512) for c in e['cameras']] for s,e in p['scenes'].items()},
    unchanged='Camera poses/FOV, geometry, paths, labels, styles, two contour arms; no parameter selection or visual tuning',
    original_attempt=str(out),original_failure='logs/package_replay.receipt.json',protocol_sha256=sha(unit/'PROTOCOL.json'),source_sha256=sha(here/'contour_trial.py')))
commands=[];start=time.monotonic()
for phase,scene in [('source','ficus'),('source','chair'),('static','ficus'),('static','chair'),('metrics',None)]:
    name='normalized_'+phase+('_'+scene if scene else '')
    cmd=[sys.executable,str(here/'run_logged.py'),'--unit',str(unit),'--name',name,'--',sys.executable,str(here/'contour_trial.py'),phase]
    if scene:cmd+=['--scene',scene]
    result=subprocess.run(cmd,timeout=150);commands.append(dict(command=cmd,returncode=result.returncode));result.check_returncode()
js(unit/'metrics/CAMERA_NORMALIZATION_REPLAY.json',dict(status='PASS',seconds=time.monotonic()-start,commands=commands,
    original_outputs_retained=True,science_parameters_unchanged=True))
