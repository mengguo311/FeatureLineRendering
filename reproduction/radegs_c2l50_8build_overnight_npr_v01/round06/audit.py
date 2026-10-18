from env import *
from experiment import ARMS,result,shape,old

def calculate():
 rows=[]
 for v in views('ficus'):
  a=shape('ficus',v);m=a['candidate'];b=result('ficus',v,'rgb');row=dict(view=v,mask_pixels=int(m.sum()),shape_reliable=int(a['eligible'].sum()),feature_qualification_by_rgb_proxy={str(k):dict(total=int((b['labels']==k).sum()),shape_reliable=int(((b['labels']==k)&a['eligible']).sum())) for k in range(1,4)},arms={})
  for arm in ARMS:
   n=result('ficus',v,arm);before=b['labels'][m];after=n['labels'][m];row['arms'][arm]=dict(transitions=np.bincount((before*4+after).astype(int),minlength=16).reshape(4,4).tolist(),unknown=int((after==0).sum()),known_to_unknown=int(((before>0)&(after==0)).sum()),unknown_to_known=int(((before==0)&(after>0)).sum()),different_known=int(((before>0)&(after>0)&(before!=after)).sum()))
  rows.append(row)
 return rows

def main():
 p=R/'mechanism_audit'
 if (p/'SEAL.json').exists():checkseal(p);return
 p.mkdir();rows=calculate();js(p/'COUNTS.json',rows);overlap={}
 for arm in ARMS:
  m=npz(R/'models'/arm/'MODEL.npz');h=m['shape_hist'].reshape(3,-1);overlap[arm]=dict(shape_bhattacharyya=np.sqrt(h)@np.sqrt(h).T,threshold=m['shape_threshold'])
 js(p/'MODEL_OVERLAP.json',{arm:{k:v.tolist() for k,v in vals.items()} for arm,vals in overlap.items()})
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(1,2,figsize=(12,5))
 for i,v in enumerate(fit_views_local()):
  a=npz(R/'models/rgb_morph'/(v+'_SEEDS.npz'));f=a['feature'];e=a['eligible'];y=a['labels']
  for k,label,col in [(1,'pot proxy','#44a5dc'),(2,'wood proxy','#e77f39'),(3,'crown proxy','#76ac31')]:
   q=np.flatnonzero(e&(y==k))[::5];ax[i].scatter(f[q,0],f[q,2],s=7,alpha=.4,c=col,label=label)
  ax[i].set(xlabel='Normalized distance to negative space',ylabel='Large-scale occupancy',title=v+' | original seed labels, not GT',xlim=(0,1),ylim=(0,1))
 ax[0].legend();fig.tight_layout();fig.savefig(p/'FEATURE_OVERLAP.jpg',dpi=150);plt.close(fig);seal(p)
def fit_views_local():return [DEV['ficus'],AUX['ficus']]
if __name__=='__main__':main()
