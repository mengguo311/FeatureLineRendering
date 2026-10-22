"""One bounded serial replay after an explicitly recorded scheduling mistake."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import datetime,json,os,subprocess,sys,time
from validate_replays import compare

unit=OUTPUT_ROOT/'units/unit_011';here=Path(__file__).resolve().parent
start=time.monotonic();receipts={}
for name in ('static_chair','motion'):
    receipts[name]=json.loads((unit/f'logs/{name}.receipt.json').read_text())
    group=json.loads((unit/f'logs/{name}.start.json').read_text())['own_process_group']
    try:os.killpg(group,0)
    except ProcessLookupError:pass
    else:raise RuntimeError('original owned group still exists; do not overlap recovery')
out=unit/'attempt_schedule_overlap';out.mkdir()
for name in ('chair','orbit','zoom'):
    source=unit/'renders'/name
    if source.exists():source.rename(out/name)
commands=[]
for name,args in [('static_chair_recovery',['static','--scene','chair']),('motion_recovery',['motion'])]:
    cmd=[sys.executable,str(here/'run_logged.py'),'--unit',str(unit),'--name',name,'--',sys.executable,str(here/'contour_trial.py'),*args]
    r=subprocess.run(cmd,timeout=220);commands.append(dict(command=cmd,returncode=r.returncode));r.check_returncode()
exact=[]
for record in out.rglob('frame_*.json'):
    relative=record.relative_to(out);new=unit/'renders'/relative
    for suffix in ('image.png','hatch.png','contour.png','proxy.png','region_rgb.png','arrays.npz'):
        old_file=record.with_name(record.stem+'_'+suffix);new_file=new.with_name(new.stem+'_'+suffix)
        exact.append(compare(old_file,new_file))
parse=datetime.datetime.fromisoformat
overlap=(min(parse(r['end_utc']) for r in receipts.values())-max(parse(r['start_utc']) for r in receipts.values())).total_seconds()
js(unit/'EXECUTION_AMENDMENT.json',dict(utc=now(),reason='Parent started motion before static_chair terminal receipt; serial schedule violated.',
    original_receipts=receipts,overlap_seconds=max(0,overlap),motion_deliberately_stopped_by_parent=True,
    shell_motion_returncode=241,child_motion_returncode=-15,original_outputs_retained=str(out),
    cpu_limit='Both inherited affinity [0,1], numeric threads1; no GPU. Serial rule violated despite total CPU<=2.',
    recovery_commands=commands,recovery_seconds=time.monotonic()-start,all_complete_original_frames_exact=exact,
    protocol_or_parameters_changed=False,scientific_retry=False,scope='Scheduling recovery only; final evidence uses sequential reruns. Original affected outputs are not primary evidence.'))
