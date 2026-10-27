"""Freeze the one declared style and four cameras before any image evaluation."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil
from geometry import orbit_camera
from style_asset import create_style,CHANGES
from whole_asset import STYLE_PRESET
UNIT=runtime.ROOT/'units/unit_006';CODE=Path(__file__).parent
def main():
    if (UNIT/'PROTOCOL.json').exists():raise FileExistsError('already frozen')
    cameras=[orbit_camera(a,e,5.1,384) for a,e in ((61,24),(241,24),(241,60),(151,36))]
    protocol=dict(unit='unit_006',utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),cameras=cameras,
        task='One declared whole-object STYLE/SYSTEM capability test; outline plus two authored regions of long sparse hatching',
        preset=STYLE_PRESET,changes=CHANGES,reference='unit005 angle; exposed functional reference, not a quality winner',
        source=dict(rows=256690,unknown=170281,seat_weight_rows=27873,upper_back_ink='proxy-only',original_arrays='all fixed',new_path_certificate=False),
        fixed='Original mesh/labels/PLY/fullSH/opacity/order; region1-3 path bytes; paper .95; AA2; width1; visibility .004; contour rule and strength; gap .035 and original slicing phase',
        camera_scope='0 BUILD exposed;1/2 exposed weak rear/high rear;3 newly reserved for this unit before viewing, no GS-training-unseen claim',
        match=dict(build_index=0,rule='One scalar per arm=min(BUILD effect)/arm effect. Effect is whole-frame raw RGB L1 of natural hybrid minus same fixed paper+contour image. Apply to this incremental residual after natural union, not to contour or paper.',
            scope='Additional display normalization only; natural style remains primary; no causal mechanism superiority or per-DEV fitting'),
        authoring=dict(frozen_choices='Decision-prescribed display mask and two parameter tuples; original manual regions and directions reused',new_clicks=0,new_face_edits=0,output_driven_parameter_revisions=0),
        falsification=json.loads((UNIT/'DECISION.json').read_text())['falsification'],
        resources=dict(cpu_affinity_max=2,numeric_threads=1,serial=True,cuda='disabled'))
    js(UNIT/'PROTOCOL.json',protocol)
    for i,c in enumerate(cameras):js(UNIT/'delivery/cameras'/f'{i}.json',c)
    sources={}
    for f in sorted(CODE.iterdir()):
        if f.is_file():
            sources[f.name]=sha(f)
            for dst in (UNIT/'source_snapshot',UNIT/'delivery/code'):
                dst.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst/f.name)
    js(UNIT/'SOURCE_LOCK.json',sources)
    js(UNIT/'PROTOCOL_LOCK.json',dict(decision=sha(UNIT/'DECISION.json'),protocol=sha(UNIT/'PROTOCOL.json'),source=sha(UNIT/'SOURCE_LOCK.json')))
    create_style(UNIT/'delivery/assets/reference',UNIT/'delivery/assets/selective')
    inputs={}
    for sub in ('inputs','delivery/data','delivery/assets','delivery/controls','delivery/cameras'):
        for f in sorted((UNIT/sub).rglob('*')):
            if f.is_file():inputs[str(f.relative_to(UNIT))]=sha(f)
    js(UNIT/'INPUT_LOCK.json',inputs)
    js(UNIT/'INPUT_SEAL.json',dict(inputs=sha(UNIT/'INPUT_LOCK.json'),protocol_lock=sha(UNIT/'PROTOCOL_LOCK.json'),utc=runtime.now()))
    print('Frozen protocol, source and',len(inputs),'inputs',flush=True)
if __name__=='__main__':main()
