"""Width from linear RGB profiles, not binary instance argmax. Units: pixels."""
import numpy as np

def linear_to_srgb(x):
    x=np.clip(x,0,1)
    return np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0)**(1/2.4)-.055)

def lab(rgb):
    # Linear sRGB primaries, CIE XYZ, D65 reference white and 2-degree observer.
    xyz=np.asarray(rgb)@np.array([[.4124564,.2126729,.0193339],
                                  [.3575761,.7151522,.1191920],
                                  [.1804375,.0721750,.9503041]])
    v=xyz/np.array([.95047,1,1.08883]); delta=6/29
    f=np.where(v>delta**3,np.cbrt(v),v/(3*delta**2)+4/29)
    return np.stack([116*f[...,1]-16,500*(f[...,0]-f[...,1]),200*(f[...,1]-f[...,2])],axis=-1)

def measure(t, rgb, visible=True, contrast_min=.02, residual_max=.08, reversal_max=.12):
    t=np.asarray(t); rgb=np.asarray(rgb)
    out={'width_px':None,'center_px':None,'contrast_linear':None,
         'deltaE76_D65_2deg':None,'deltaL':None,'confidence':0.,'reason':None,
         'overshoot':None}
    if not visible:
        out['reason']='hidden';return out
    if len(t)<10 or not np.isfinite(rgb).all() or np.any(np.diff(t)<=0):
        out['reason']='invalid_samples';return out
    n=max(2,len(t)//8)
    a=np.median(rgb[:n],axis=0);b=np.median(rgb[-n:],axis=0);d=b-a
    D=float(np.linalg.norm(d));la,lb=lab(a),lab(b)
    out.update(contrast_linear=D,deltaE76_D65_2deg=float(np.linalg.norm(lb-la)),deltaL=float(lb[0]-la[0]))
    if D<contrast_min:
        out['reason']='low_contrast';return out
    f=(rgb-a)@d/(D*D)
    residual=float(np.sqrt(np.mean((rgb-(a+f[:,None]*d))**2))/D)
    reversal=float(np.maximum(-np.diff(f),0).sum())
    out['overshoot']=float(max(0,-f.min(),f.max()-1))
    if residual>residual_max or reversal>reversal_max:
        out['reason']='complex_profile';return out
    def crossing(q):
        ids=np.flatnonzero((f[:-1]<=q)&(f[1:]>q))
        if not len(ids):return None
        j=ids[np.argmin(np.abs(t[ids]))]
        return float(t[j]+(q-f[j])/(f[j+1]-f[j])*(t[j+1]-t[j]))
    lo,hi,center=crossing(.1),crossing(.9),crossing(.5)
    if lo is None or hi is None or hi<=lo:
        out['reason']='crossing_missing';return out
    out.update(width_px=hi-lo,center_px=center,confidence=float(max(0,1-residual-reversal)))
    return out
