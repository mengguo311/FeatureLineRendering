"""Frozen local cubic seam; no fit, alternate offset, or guard relaxation."""
import overlap_core as oc
from geometry_base import np,arc,clean,project,EPS
def hermite_register(a,b,s):
 old,meta=oc.register(a,b,s)
 meta=dict(meta,representation='HERMITE')
 if old is None:return None,meta
 la=float(arc(a)[-1]);lb=float(arc(b)[-1]);lo=la-min(2.,la);hi=s+min(2.,lb-s)
 p0=oc.at(a,lo);p3=oc.at(b,hi);t0=oc.tangent_at(a,np.asarray(lo));t1=oc.tangent_at(b,np.asarray(hi));D=float(np.linalg.norm(p3-p0))
 meta.update(local_start_a_p=lo,local_end_b_p=hi,old_linear_seam_p=meta['seam_p'],chord_p=D)
 if D<=EPS:meta['status']='hermite_degenerate_chord';return None,meta
 controls=np.array([p0,p0+D*t0/3,p3-D*t1/3,p3]);N=max(1,int(np.ceil(12*np.max(np.linalg.norm(np.diff(controls,axis=0),axis=1)))))
 meta.update(bezier_controls_p=controls.tolist(),sample_segments=N,no_fitting=True)
 if N>128:meta['status']='hermite_sample_cap';return None,meta
 t=np.linspace(0.,1.,N+1)[:,None];z=(1-t)**3*controls[0]+3*(1-t)**2*t*controls[1]+3*(1-t)*t*t*controls[2]+t**3*controls[3]
 z[0]=p0;z[-1]=p3
 q=clean(np.vstack([a[arc(a)<lo],z,b[arc(b)>hi]]));seam=float(project(oc.at(b,s)[None,:],q)[0][0])
 meta.update(seam_p=seam,local_sample_max_spacing_p=float(np.max(np.linalg.norm(np.diff(z,axis=0),axis=1))),fixed_prefix_and_tail=True)
 return q,meta

def library(d,state,sid,side,index,endpoints,representation,guard,max_prefixes=256,max_donors=3):
 import switch_core
 if representation not in ('LINEAR','HERMITE'):raise ValueError(representation)
 return switch_core.candidates(d,state,sid,side,index,endpoints,guard,max_prefixes,max_donors,overlap_register=hermite_register if representation=='HERMITE' else None)
