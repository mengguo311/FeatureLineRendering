"""Bind the compatibility-only repair before evaluating it."""
from common import *
import subprocess,shutil
from datetime import datetime,timezone
U=OUT.parent/'unit_006'
assert not (U/'ENGINEERING_RECOVERY.json').exists()
old=json.loads((U/'INDEPENDENT_VALIDATION.json').read_text())
assert [k for k,v in old['checks'].items() if not v['passed']]==['official_RaDeGS_camera_reader']
amend=dict(status='FROZEN_BEFORE_ADAPTER_EVALUATION',created_utc=datetime.now(timezone.utc).isoformat(),reason='Exact official reader fails on current Pillow when handed signed np.byte RGB; original rc1 and INVALID retained',original_validation_sha256=sha(U/'INDEPENDENT_VALIDATION.json'),original_execution_sha256=sha(U/'EXECUTION_validate.json'),permitted_change='New local AST adapter replaces the single np.byte dtype with np.uint8, preserving external official source bytes',fixed=['all RGB/camera/oracle artifacts','all camera/split/material/light controls and thresholds','all previous nine fault controls','initial validator and its INVALID verdict/receipt/log'],gates=['all120 local-adapter images equal PNG pixels AND original signed cast underlying unsigned byte view','all120 rotations/translations/focal/projection residual <1e-9','all120 RGB/oracle SHA and camera metadata SHA remain original','empty training transforms_test remains empty; no points3d/training/full loader'],claim='Recover only local-adapter input readiness; unmodified official loader remains NO_GO in current dependency environment; no reconstruction claim')
write_json(U/'ENGINEERING_RECOVERY.json',amend)
write_json(WORK/'docs/partwise_sketch_hatching_v02/RECOVERY_unit006.json',amend)
files=[WORK/'experiments/partwise_sketch_hatching_v02'/x for x in ['radegs_camera_compat.py','recover_validation_unit006.py','freeze_recovery_unit006.py']]+[U/'ENGINEERING_RECOVERY.json',U/'INDEPENDENT_VALIDATION.json',U/'SOURCE_LOCK.json']
rows=[]
for p in files:
 rel=p.relative_to(WORK) if p.is_relative_to(WORK) else Path('unit_inputs')/p.relative_to(U)
 dest=U/'recovery_source_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 rows.append(dict(path=str(p),sha256=sha(p),snapshot=str(dest.relative_to(U))))
write_json(U/'RECOVERY_LOCK.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),files=rows,created_utc=datetime.now(timezone.utc).isoformat()))
print('Compatibility-only recovery frozen; initial failure retained')
