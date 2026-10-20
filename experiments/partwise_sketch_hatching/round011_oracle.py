"""Independent scalar cross-section integrals; never imports candidate coverage."""
import round011_common
import numpy as np

def axial_area(a,b,size,width):
    low=np.minimum(a,b);high=np.maximum(a,b)
    if a[1]==b[1]:low[1]-=width/2;high[1]+=width/2
    else:low[0]-=width/2;high[0]+=width/2
    x=np.arange(size,dtype=float);y=np.arange(size,dtype=float)
    wx=np.maximum(0,np.minimum(x+.5,high[0])-np.maximum(x-.5,low[0]))
    wy=np.maximum(0,np.minimum(y+.5,high[1])-np.maximum(y-.5,low[1]))
    return wy[:,None]*wx[None,:]

def cross_section_area(a,b,size,width):
    d=b-a;length=np.sqrt(float(d@d));base=float(d@a);crossbase=-d[1]*a[0]+d[0]*a[1]
    # A*x+B*y<=C, derived solely from along/cross distances.
    constraints=[(d[0],d[1],base+length*length),(-d[0],-d[1],-base),
                 (-d[1],d[0],width*length/2+crossbase),(d[1],-d[0],width*length/2-crossbase)]
    out=np.zeros((size,size))
    for y in range(size):
        for x in range(size):
            lower=[(0.,-.5)];upper=[(0.,.5)];left=-.5;right=.5
            for A,B,C in constraints:
                local=C-A*x-B*y
                if B>0:upper.append((-A/B,local/B))
                elif B<0:lower.append((-A/B,local/B))
                elif A>0:right=min(right,local/A)
                elif A<0:left=max(left,local/A)
            if right<=left:continue
            lines=lower+upper;cuts=[left,right]
            for i,(m,b0) in enumerate(lines):
                for m2,b2 in lines[i+1:]:
                    if m!=m2:
                        q=(b2-b0)/(m-m2)
                        if left<q<right:cuts.append(q)
            cuts=sorted(set(cuts));area=0.
            for l,r in zip(cuts[:-1],cuts[1:]):
                mid=(l+r)/2
                low=max(m*mid+b0 for m,b0 in lower);high=min(m*mid+b0 for m,b0 in upper)
                area+=(r-l)*max(0.,high-low)
            out[y,x]=area
    return out

def area_reference(prescribed_path,size,width=2.):
    p=np.asarray(prescribed_path,float);a=p[0];b=p[-1]
    raw=axial_area(a,b,size,width) if a[0]==b[0] or a[1]==b[1] else cross_section_area(a,b,size,width)
    area=raw.copy();area[area<=1e-12]=0.;area[area>=1-1e-12]=1.
    return area,raw
