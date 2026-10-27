import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil
from geometry import orbit_camera
UNIT=runtime.ROOT/'units/unit_007';CODE=Path(__file__).parent
def main():
    cams=[]
    for az,el,role in [(151,36,'author_BUILD_exposed'),(61,24,'exposed_front_hiding_check'),(241,24,'exposed_weak_rear'),(241,60,'exposed_high_rear'),(196,36,'new_output_reserved_not_GS_unseen')]:
        c=orbit_camera(az,el,5.1,384);c['role']=role;cams.append(c);js(UNIT/'delivery/cameras'/(c['view']+'.json'),c)
    js(UNIT/'PROTOCOL.json',dict(unit='unit_007',utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='Does one saved authored rear inner-rim detail make the fixed whole-Chair preset more readable across cameras?',
        scope='SYSTEM/STYLE capability; adds structure content/ink, not equal-budget superiority, automatic edge recovery, H2/H3 or Gaussian path certification',
        author= json.loads((UNIT/'AUTHOR.json').read_text()),cameras=cams,arms=['off','on'],
        curve=dict(id=240807000001,width=1.,strength=.85,color=.03,aa=2,depth_tolerance=.004,author_interpolation='piecewise linear; no smoothing, closure or image fitting',
            projection='projected-triangle interval clipping; exact inverse-z frontmost envelope; perspective-correct barycentric endpoints',
            missing='retain uncovered intervals and world discontinuities; no joining segment',visibility='fixed proxy first hit, no region or source-S clipping'),
        frozen='Original PLY/order/256690 rows, geometry/covariance/opacity/fullSH, mesh and labels, UNKNOWN170281, 27873-row seat S, .95 global paper, all five region path files/styles, original contours',
        evaluation='Full natural source/paper/contour/structure/ink/hybrid/proxy; added ink budget disclosed; visual source agreement on new rear, correct front hiding; old holes retained',
        old_negatives='v05 far8.044%/31px/4.49%; v07 eleven no-whole-winner/H collapse/zero_step_cycle; v08 actual143/UNKNOWN, temporal drops, empty supports and 077 rear near-vanishing',
        no_per_eval_repairs=True,no_new_video=True,deadlines='12:25 no new units / 12:45 wrap / 13:00 hardstop JST',resources='serial CPU affinity2, threads1, CUDA empty'))
    inputs={}
    for folder in (UNIT/'delivery/data',UNIT/'delivery/assets/base',UNIT/'delivery/cameras',UNIT/'inputs'):
        for p in sorted(folder.rglob('*')):
            if p.is_file():inputs[str(p.relative_to(UNIT))]=sha(p)
    inputs['AUTHOR.json']=sha(UNIT/'AUTHOR.json');js(UNIT/'INPUT_LOCK.json',inputs)
    sources={p.name:sha(p) for p in sorted(CODE.iterdir()) if p.suffix in ('.py','.cpp')}
    for name,h in sources.items():
        dst=UNIT/'source_snapshot'/name;dst.parent.mkdir(exist_ok=True);shutil.copy2(CODE/name,dst);assert sha(dst)==h
    js(UNIT/'SOURCE_LOCK.json',sources)
    js(UNIT/'PROTOCOL_LOCK.json',dict(decision=sha(UNIT/'DECISION.json'),protocol=sha(UNIT/'PROTOCOL.json'),source=sha(UNIT/'SOURCE_LOCK.json'),inputs=sha(UNIT/'INPUT_LOCK.json'),utc=runtime.now()))
    print('Frozen',len(inputs),'inputs',len(sources),'sources',len(cams),'cameras')
if __name__=='__main__':main()
