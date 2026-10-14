"""Additional fixed analytic contrast sweep, preserving the first fixture."""
import numpy as np
from common import *
from detector import *
from render_boards import board,save_png
write(T/'analytic'/'CONTRAST_PLAN.json',dict(utc=utc(),step_contrasts=[.01,.02,.03,.04],texture_amplitude=.065,thresholds=[.10,.20,.40,.50],selection_role='none; fixed analytic mechanism diagnosis, not scene-preset tuning'))
y,x=np.mgrid[:180,:320];stats=[];items=[];arrays={}
for contrast in [.01,.02,.03,.04]:
    rgb=np.repeat((.35+contrast*(x>=80)+.065*np.sin(x*.8)*(x>=190))[...,None],3,axis=2).astype(np.float32)
    f=analyze_rgb(rgb,'native');rs={t:candidate(f['union'],t) for t in [.10,.20,.40,.50]}
    for t,r in rs.items():stats.append(dict(contrast=contrast,threshold=t,weak_step_candidates=int(r['marked'][15:-15,77:84].sum()),texture_candidates=int(r['marked'][15:-15,200:-15].sum())))
    arrays[str(contrast)+'_rgb']=rgb
    for t,r in rs.items():arrays[f'{contrast}_{t}_marked']=r['marked']
    if contrast in [.01,.02]:
        items.extend([(f'Analytic step contrast={contrast:.2f}\nStep x=80; stronger texture x>=190',rgb),(f'contrast={contrast:.2f} | A10\nStrict T=.10',1-rs[.10]['candidate_darkness']),(f'contrast={contrast:.2f} | A40\nStrict T=.40',1-rs[.40]['candidate_darkness'])])
board(T/'analytic'/'CONTRAST_SWEEP.jpg',items,'Additional analytic contrast sweep | Fixed controls','Known step versus repeated texture; a diagnostic counterexample, not actual-scene SNR')
np.savez_compressed(T/'analytic'/'CONTRAST_SWEEP.npz',**arrays)
write(T/'analytic'/'CONTRAST_RESULTS.json',dict(rows=stats,first_fixture_preserved=True,first_fixture_note='The earlier .04 step remained at all tested thresholds; its structural fit was valid. It did not demonstrate lost weak edges. This additional fixed contrast sweep records both passing and failing cases.'))
print(stats)
