"""Snapshot current inputs/code, preserve previous failures, then lock before rendering."""
from common import *
import subprocess,shutil
from datetime import datetime,timezone
U=OUT.parent/'unit_006';prev=U.parent/'unit_005'
assert not (U/'SOURCE_LOCK.json').exists()
paths=[WORK/'experiments/partwise_sketch_hatching_v02'/s for s in ['prepare_unit006.py','refine_protocol_unit006.py','receipt_unit006.py','run_unit006.py','lock_unit006.py','audit_unit006.py','validate_unit006.py','reconstruction_dataset.py','common.py']]
paths += [WORK/'experiments/partwise_sketch_hatching'/s for s in ['core.py','core_walk_v2.py']]
paths += [U/'PROTOCOL.json',U/'RECONSTRUCTION_INVENTORY.json',U/'oracle_only/lamp_mesh.npz']
official=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/RaDe-GS')
paths += [official/s for s in ['scene/dataset_readers.py','utils/graphics_utils.py','submodules/diff-gaussian-rasterization/cuda_rasterizer/auxiliary.h']]
rows=[]
for path in paths:
 assert path.is_file(),path
 if path.is_relative_to(WORK):rel=path.relative_to(WORK)
 elif path.is_relative_to(U):rel=Path('unit_inputs')/path.relative_to(U)
 else:rel=Path('external_sources')/path.relative_to(official)
 dest=U/'source_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
 rows.append(dict(path=str(path),sha256=sha(path),snapshot=str(dest.relative_to(U))))
write_json(U/'SOURCE_LOCK.json',dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),initial_protocol_commit='e6a54645',frozen_utc=datetime.now(timezone.utc).isoformat(),files=rows))
failure_sources=[prev/'previous_snapshot/unit004_diagnostic_preview/FROZEN_GATE_FAILURES.json',prev/'inherited_failures/failure_orbit_019.png']
for path in failure_sources:
 dest=U/'inherited_failures'/path.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(path,dest)
write_json(U/'INPUT_PROVENANCE.json',dict(origin='Original authored procedural lamp; no third-party mesh/photograph/download',license_scope='Project-authored fixture; no new external licensing dependency; no blanket legal license assertion',mesh_sha256=sha(U/'oracle_only/lamp_mesh.npz'),prior_units_read_only=True,RGB='New synthetic local-Lambert surface renders, no NPR strokes burned into images',test_exposure='All RGB inspected only for integrity and coverage, frozen recipe never tuned against test',oracle='Sibling isolated oracle_only; GT not used as reconstructed main surface',inherited_failure_files=[dict(source=str(x),sha256=sha(x)) for x in failure_sources]))
print('source/input lock created before rendering')
