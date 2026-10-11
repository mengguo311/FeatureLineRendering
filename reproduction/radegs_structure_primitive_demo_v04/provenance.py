from common import *
from primitive import curve_eval,basis
import sys

def primitive_arc(points,g):
    x=np.asarray(points,float);cp=np.asarray(g['control'])
    if g['type']=='point':return np.full(len(x),.5)
    if g['type']=='line':
        d=cp[3]-cp[0];return np.clip((x-cp[0])@d/max(1e-30,d@d),0,1)
    tt=np.linspace(0,1,65);q=curve_eval(cp,'bezier',tt);t=tt[np.linalg.norm(x[:,None]-q[None],axis=2).argmin(1)]
    for _ in range(6):
        q=curve_eval(cp,'bezier',t);d=basis(t,'bezier',True)@cp;dd=6*(1-t[:,None])*(cp[2]-2*cp[1]+cp[0])+6*t[:,None]*(cp[3]-2*cp[2]+cp[1]);den=(d*d+(q-x)*dd).sum(1);num=((q-x)*d).sum(1);t=np.clip(t-num/np.where(abs(den)>1e-20,den,1),0,1)
    return t

def refine(name):
    src=T/'results'/name;dst=T/'provenance_refined'/name;dst.mkdir(parents=True,exist_ok=True);a=dict(np.load(src/'observations.npz'));graph=json.loads((src/'optimized_graph.json').read_text())['primitives'];params=dict(np.load(src/'optimized_primitives.npz'));scene=name.split('_')[0];cs=demo.cameras(scene)
    x=np.full((len(a['depth']),3),np.nan)
    for vi,v in enumerate(BUILD):
        ok=(a['source_view']==vi)&np.isfinite(a['depth'])&(a['depth']>0);x[ok]=core.backproject(a['uv'][ok],a['depth'][ok],cs[v])
    arc=np.full(len(x),-1.,np.float32);res=np.full(len(x),-1.,np.float32)
    order=np.argsort(a['primitive_id'],kind='stable');ids=a['primitive_id'][order];bounds=np.r_[0,np.flatnonzero(np.diff(ids))+1,len(ids)]
    for l,r in zip(bounds[:-1],bounds[1:]):
        pid=int(ids[l])
        if pid<0:continue
        ix=order[l:r];g={'control':params['control'][pid],'type':str(params['type'][pid])};t=primitive_arc(x[ix],g);arc[ix]=t;res[ix]=np.linalg.norm(curve_eval(g['control'],g['type'],t)-x[ix],axis=1)/params['pixel'][pid]
    np.savez_compressed(dst/'source_to_optimized_primitive.npz',source_row=np.arange(len(x),dtype=np.int32),primitive_id=a['primitive_id'],source_chain_arc=a['arc'],optimized_primitive_arc=arc,raw_to_curve_residual_pixel=res,source_view=a['source_view'],uv=a['uv'],reason=a['reason'])
    js(dst/'README.json',{'source_ledger':str(src/'observations.npz'),'source_ledger_sha256':sha(src/'observations.npz'),'primitive_parameters_sha256':sha(src/'optimized_primitives.npz'),'rows':len(x),'assigned':int((arc>=0).sum()),'arc_definition':'nearest bounded object-space parameter on optimized fixed primitive; not proof of cross-view curve identity','original_arc_field':'source-chain parameter, retained verbatim; cannot be equated with merged-primitive arc','optimization_influenced_by_this_postprocessing':False});seal(dst);print('PROVENANCE_REFINED',name,len(x),int((arc>=0).sum()),flush=True)

if __name__=='__main__':refine(sys.argv[1])
