"""Analytic fixtures. Ground truth is constructed before calling any method."""
import numpy as np

def fixtures(n=128):
    y,x=np.mgrid[:n,:n]; c=n//2
    def step(width,minus,plus):
        a=1/(1+np.exp(np.clip(-(x-c)*4.394449/width,-60,60)))
        return (np.asarray(minus)[None,None,:]*(1-a[...,None])+np.asarray(plus)[None,None,:]*a[...,None]).astype(np.float32)
    def truth(mask): return mask.astype(np.uint8)
    r={}
    r['constant']=(np.full((n,n,3),.55,np.float32),{'truth':np.zeros((n,n),np.uint8)})
    # Equal Rec.709 luminance but a clear red/green color transition.
    r['color_step']=(step(3.,[.15,.55,.35],[.65,.40137025,.35]),{'truth':truth(abs(x-c)<=2),'center':c,'width':3.})
    r['low_contrast']=(step(3.,[.5]*3,[.508]*3),{'truth':truth(abs(x-c)<=2),'center':c,'width':3.})
    stripe=(.3+.35*((x//5)%2)).astype(np.float32)
    r['stripes']=(np.repeat(stripe[...,None],3,axis=2),{'truth':truth((x%5==0)|(x%5==4)),'label':'legitimate visible pattern; geometry/material unknown'})
    corner=(x>=c)&(y>=c)
    r['corner']=(np.repeat((.25+.5*corner)[...,None],3,axis=2).astype(np.float32),{'truth':truth(((abs(x-c)<=1)&(y>=c))|((abs(y-c)<=1)&(x>=c)))})
    junction=.2+.25*(x>=c)+.25*(y>=c)
    r['junction']=(np.repeat(junction[...,None],3,axis=2).astype(np.float32),{'truth':truth((abs(x-c)<=1)|(abs(y-c)<=1))})
    r['width']=(step(6.,[.2,.3,.4],[.7,.65,.6]),{'truth':truth(abs(x-c)<=3),'center':c,'width':6.})
    return r

def moving_sequence(n=128):
    y,x=np.mgrid[:n,:n]; frames=[]
    for k in range(7):
        im=np.full((n,n,3),.7,np.float32)
        if k<6:
            mask=(x>20+8*k)&(x<55+8*k)&(y>25)&(y<102)
            im[mask]=[.25,.35,.5]
            # A new foreground occluder enters independently of the old boundary.
            if k>=3: im[(x>60)&(y>55)]=[.85,.8,.65]
        frames.append(im)
    return frames
