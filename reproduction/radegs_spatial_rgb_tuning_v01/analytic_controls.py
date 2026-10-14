import numpy as np
from common import *
from detector import *
from render_boards import board,save_png
# A known weak genuine step and high-contrast repeated texture. This is a
# constructed counterexample to "larger response necessarily means useful".
y,x=np.mgrid[:180,:320]
a=.35+.04*(x>=80)+.065*np.sin(x*.8)*(x>=190)
rgb=np.repeat(a[...,None],3,axis=2).astype(np.float32)
f=analyze_rgb(rgb,'native');save_png(T/'analytic'/'INPUT.png',rgb)
items=[('Analytic input\nWeak step at x=80; texture at x>=190',rgb)]
stats={};allmaps={}
for id,lam,t in [('A20',1,.2),('A40',1,.4),('B50',.5,.2),('B00',0,.2),('A50',1,.5)]:
    r=candidate(mix_fields(f,lam),t);allmaps[id]=r
    stats[id]=dict(weak_step_candidates=int(r['marked'][15:-15,77:84].sum()),texture_candidates=int(r['marked'][15:-15,200:-15].sum()))
    items.append((f'{id} | T={t:.2f} detail={lam:.2f}',1-r['candidate_darkness']))
board(T/'analytic'/'WEAK_EDGE_STRONG_TEXTURE.jpg',items,'Analytic negative control | Response is not semantic importance','Synthetic mechanism test, not a scene result or measured real-image SNR')
write(T/'analytic'/'RESULTS.json',dict(stats=stats,interpretation='A threshold ranks response, not importance; strong texture can survive after a weak genuine edge is removed.',source='deterministic analytic grayscale fixture'))
np.savez_compressed(T/'analytic'/'maps.npz',rgb=rgb,detail=f['detail'],structural=f['structural'],**{id+'_marked':r['marked'] for id,r in allmaps.items()})
print(stats)
