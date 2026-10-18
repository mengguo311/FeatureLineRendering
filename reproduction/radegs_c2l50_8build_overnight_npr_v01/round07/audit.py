from env import *
from experiment import ARMS,result,rendered,old

def calculate():
 rows=[]
 for s in SCENES:
  for v in views(s):
   b=result(s,v,'full_sh');mask=b['inference_mask'];K=4 if s=='ficus' else 3
   for arm in ARMS:
    a=result(s,v,arm);trans=np.bincount((b['labels'][mask].astype(int)*K+a['labels'][mask]),minlength=K*K).reshape(K,K)
    rows.append(dict(scene=s,view=v,arm=arm,transition_from_full=trans.tolist(),mask_pixels=int(mask.sum()),unknown=int((mask&(a['labels']==0)).sum()),counts=np.bincount(a['labels'][mask],minlength=K).tolist(),changed=int((mask&(a['labels']!=b['labels'])).sum()),known_to_unknown=int((mask&(b['labels']>0)&(a['labels']==0)).sum()),unknown_to_known=int((mask&(b['labels']==0)&(a['labels']>0)).sum()),known_to_different_known=int((mask&(a['labels']>0)&(b['labels']>0)&(a['labels']!=b['labels'])).sum())))
 seed=[]
 for s in SCENES:
  for arm in ARMS:
   m=npz(R/'models'/s/arm/'MODEL.npz');h=m['hist'].reshape(int(m['classes']),-1);overlap=np.minimum(h[:,None,:],h[None,:,:]).sum(2)
   seed.append(dict(scene=s,arm=arm,seed_histogram_overlap=overlap.tolist(),not_semantic_accuracy=True))
 return dict(pixel_transitions=rows,seed_distributions=seed,source_only=True,geometry_all_equal=True)
def main():
 p=R/'mechanism_audit';p.mkdir(exist_ok=True);js(p/'COUNTS.json',calculate());seal(p)
if __name__=='__main__':main()
