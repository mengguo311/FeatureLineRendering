"""Independent screen-space visible footprint area; never imports renderer.

Input is the prescribed projected endpoints and analytic rectangular domains.
Area units are high-resolution pixel squares, not world surface area.
"""
import round012_common
import numpy as np

def intersect_box(a,b):
    return (max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3]))

def ribbon_constraints(a,b,width):
    d=b-a;length=float(np.linalg.norm(d))
    if length<=0 or width<=0:raise ValueError('positive length and width required')
    base=float(d@a);cross=-d[1]*a[0]+d[0]*a[1]
    return [(d[0],d[1],base+length*length),(-d[0],-d[1],-base),
            (-d[1],d[0],cross+width*length/2),(d[1],-d[0],-cross+width*length/2)]

def cross_section_integral(a,b,width,box):
    """Exact piecewise-linear 1D integral, unrelated to polygon clipping."""
    x0,y0,x1,y1=map(float,box)
    if x1<=x0 or y1<=y0:return 0.
    # Local coordinates limit cancellation for pixel-scale boxes.
    cx=(x0+x1)/2;cy=(y0+y1)/2;left=x0-cx;right=x1-cx
    lower=[(0.,y0-cy)];upper=[(0.,y1-cy)]
    for A,B,C in ribbon_constraints(a,b,width):
        C=C-A*cx-B*cy
        if B>0:upper.append((-A/B,C/B))
        elif B<0:lower.append((-A/B,C/B))
        elif A>0:right=min(right,C/A)
        elif A<0:left=max(left,C/A)
        elif C<0:return 0.
    if right<=left:return 0.
    lines=lower+upper;cuts=[left,right]
    for i,(m,q) in enumerate(lines):
        for n,r in lines[i+1:]:
            if m!=n:
                crossing=(r-q)/(m-n)
                if left<crossing<right:cuts.append(crossing)
    cuts=sorted(set(cuts));area=0.
    for left,right in zip(cuts[:-1],cuts[1:]):
        mid=(left+right)/2
        thickness=min(m*mid+q for m,q in upper)-max(m*mid+q for m,q in lower)
        area+=(right-left)*max(0.,thickness)
    return float(area)

def area_in_box(a,b,width,box,force_cross=False):
    a=np.asarray(a,float);b=np.asarray(b,float)
    if np.linalg.norm(b-a)<=0 or width<=0:raise ValueError('positive length and width required')
    if not force_cross and (a[0]==b[0] or a[1]==b[1]):
        lo=np.minimum(a,b).copy();hi=np.maximum(a,b).copy()
        axis=1 if a[1]==b[1] else 0
        lo[axis]-=width/2;hi[axis]+=width/2
        return float(max(0.,min(hi[0],box[2])-max(lo[0],box[0]))*max(0.,min(hi[1],box[3])-max(lo[1],box[1])))
    return cross_section_integral(a,b,width,box)

def area_map(path,size,width,domain=None,force_cross=False):
    a=np.asarray(path[0],float);b=np.asarray(path[-1],float)
    domain=(-.5,-.5,size-.5,size-.5) if domain is None else domain
    out=np.zeros((size,size))
    # Endpoint ranges plus width safely enclose any orientation of the ribbon.
    lo=np.maximum(0,np.ceil(np.minimum(a,b)-width/2-.5).astype(int))
    hi=np.minimum(size-1,np.floor(np.maximum(a,b)+width/2+.5).astype(int))
    for y in range(lo[1],hi[1]+1):
        for x in range(lo[0],hi[0]+1):
            box=intersect_box((x-.5,y-.5,x+.5,y+.5),domain)
            out[y,x]=area_in_box(a,b,width,box,force_cross)
    return out

def reference(path,size,width,owner_bounds,owner_z,extra=None):
    ribbon=area_map(path,size,width)
    owned=area_map(path,size,width,owner_bounds)
    hidden=np.zeros_like(ribbon)
    nearer=extra is not None and extra['z']<owner_z
    overlap=intersect_box(owner_bounds,extra['bounds_high_xyxy']) if nearer else None
    if overlap is not None:hidden=area_map(path,size,width,overlap)
    visible=owned-hidden;unsupported=ribbon-owned
    raw={'ribbon':ribbon,'owned':owned,'occluded':hidden,'visible':visible,'unsupported':unsupported}
    cleaned={}
    for k,v in raw.items():
        v=v.copy();v[v<=1e-12]=0.;v[v>=1-1e-12]=1.;cleaned[k]=v
    box=(-.5,-.5,size-.5,size-.5);a=path[0];b=path[-1]
    glob_r=area_in_box(a,b,width,box);glob_a=area_in_box(a,b,width,intersect_box(box,owner_bounds))
    glob_h=0. if overlap is None else area_in_box(a,b,width,intersect_box(box,overlap))
    global_integrals={'ribbon':glob_r,'owned':glob_a,'occluded':glob_h,'visible':glob_a-glob_h,'unsupported':glob_r-glob_a}
    return cleaned,raw,global_integrals

def subsets(ref):
    r=ref['ribbon'];v=ref['visible'];a=ref['owned'];support=r>0
    boundary=support&(v>1e-10)&(v<r-1e-10)
    visible=support&(abs(v-r)<=1e-10)
    hidden=support&(v<=1e-10)&(a>1e-10)
    unsupported=support&(a<=1e-10)
    return {'physical_boundary':boundary,'visible_interior':visible,'hidden_interior':hidden,
            'unsupported_interior':unsupported,'outside_ribbon':~support,
            'ribbon_edge':support&(r<1)}
