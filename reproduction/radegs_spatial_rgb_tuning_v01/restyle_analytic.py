import numpy as np
from common import T
from detector import analyze_rgb,candidate
from render_boards import board
# Presentation-only replay. Input/plan/measurement files are untouched.
a=dict(np.load(T/'analytic'/'CONTRAST_SWEEP.npz'));items=[]
for c in [.01,.02]:
    rgb=a[str(c)+'_rgb'];f=analyze_rgb(rgb,'native')
    r={t:candidate(f['union'],t) for t in [.1,.4]}
    for t in r:np.testing.assert_array_equal(r[t]['marked'],a[f'{c}_{t}_marked'])
    items.extend([(f'Step contrast={c:.2f}\nStep x=80; texture x>=190',rgb),(f'contrast={c:.2f} | A10\nStrict T=.10',1-r[.1]['candidate_darkness']),(f'contrast={c:.2f} | A40\nStrict T=.40',1-r[.4]['candidate_darkness'])])
board(T/'analytic'/'CONTRAST_SWEEP.jpg',items,'Analytic control | Weak step versus strong texture','Synthetic counterexample, not real-scene SNR')
from detector import mix_fields
a=dict(np.load(T/'analytic'/'maps.npz'));items=[('Analytic input | contrast=.04\nStep x=80; texture x>=190',a['rgb'])]
for id,lam,t in [('A20',1,.2),('A40',1,.4),('B50',.5,.2),('B00',0,.2),('A50',1,.5)]:
    r=candidate(mix_fields(a,lam),t);np.testing.assert_array_equal(r['marked'],a[id+'_marked'])
    items.append((f'{id} | T={t:.2f}\ndetail={lam:.2f}',1-r['candidate_darkness']))
board(T/'analytic'/'WEAK_EDGE_STRONG_TEXTURE.jpg',items,'First analytic control | The step survives all thresholds','Preserved initial fixture: not evidence that this particular step was deleted')
