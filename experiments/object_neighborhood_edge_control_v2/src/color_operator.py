"""Matrix-free native effective-color A and A^T, same fixed alpha/sort/termination."""
import numpy as np,torch
from renderer_adapter import rgb
from contracts import ls_certificate
C0=.28209479177387814

def effective(m):return (m._features_dc[:,0,:].detach()*C0+.5).clamp_min(0)
class ColorOperator:
    def __init__(self,m,views,mask):
        self.m=m;self.views=views;self.mask=mask;self.original=effective(m);self.k=int(mask.sum());self.M=sum(int(v['band'].sum())*3 for v in views)
        self.factors=[np.sqrt(self.M/(len(views)*int(v['band'].sum())*3)) for v in views]
        self.fixed=[];self.b=[];self.interval=[]
        zero=self.original.clone();zero[mask]=0
        one=zero.clone();one[mask]=1
        with torch.no_grad():
            for v,w in zip(views,self.factors):
                r=rgb(m,v['camera'],zero).detach();hi=rgb(m,v['camera'],one).detach();b=(v['target'][:,v['band']]-r[:,v['band']])*w
                self.fixed.append(r);self.b.append(b)
                miss=(r[:,v['band']]-v['target'][:,v['band']]).clamp_min(0)+(v['target'][:,v['band']]-hi[:,v['band']]).clamp_min(0)
                self.interval.append(float(miss.double().square().mean()))
    def colors(self,c):
        z=torch.zeros_like(self.original);z[self.mask]=c;return z
    def forward(self,c):
        colors=self.colors(c)
        with torch.no_grad():return [rgb(self.m,v['camera'],colors)[:,v['band']]*w for v,w in zip(self.views,self.factors)]
    def adjoint(self,ys):
        g=torch.zeros((self.k,3),device='cuda',dtype=torch.float64)
        for v,w,y in zip(self.views,self.factors,ys):
            c=torch.zeros_like(self.original,requires_grad=True);im=rgb(self.m,v['camera'],c)
            g+=torch.autograd.grad((im[:,v['band']]*y*w).sum(),c)[0][self.mask].double()
        return g
    def objective_gradient(self,c):
        g=torch.zeros((self.k,3),device='cuda',dtype=torch.float64);res=[]
        for v,w,b in zip(self.views,self.factors,self.b):
            color=self.colors(c).detach().requires_grad_();im=rgb(self.m,v['camera'],color);r=im[:,v['band']]*w-b
            g+=torch.autograd.grad(.5*r.square().sum(),color)[0][self.mask].double();res.append(r.detach())
        return res,g
    def certificate(self,c,margin_mse):
        res,g=self.objective_gradient(c)
        P=sum(.5*r.double().square().sum() for r in res).item();by=sum((b.double()*r.double()).sum() for b,r in zip(self.b,res)).item()
        D=-P-by+torch.minimum(g,torch.zeros_like(g)).sum().item();margin=self.M*margin_mse/2
        return {'P':P,'D_raw':D,'D':D-margin,'gap':P-D+margin,'numerical_margin':margin,'scalar_observations':self.M,'mse_upper':2*P/self.M,'mse_lower':2*(D-margin)/self.M},g
    def validate(self):
        c=self.original[self.mask];a=self.forward(c)
        err=max((z+self.fixed[i][:,v['band']]*self.factors[i]-rgb(self.m,v['camera'])[:,v['band']]*self.factors[i]).abs().max().item() for i,(z,v) in enumerate(zip(a,self.views)))
        generator=torch.Generator(device='cuda');generator.manual_seed(81)
        x=torch.rand((self.k,3),device='cuda',generator=generator);ys=[torch.randn_like(b) for b in self.b]
        ax=self.forward(x);aty=self.adjoint(ys);left=sum((z.double()*y.double()).sum() for z,y in zip(ax,ys)).item();right=(x.double()*aty).sum().item()
        rel=abs(left-right)/max(abs(left),abs(right),1.)
        assert err<2e-5 and rel<2e-5,(err,rel)
        return {'reconstruction_max_abs':err,'adjoint_relative_error':rel,'dot_Ax_y':left,'dot_x_ATy':right,'selected_count':self.k,'scalar_observations':self.M,'interval_necessary_mse_lower':float(np.mean(self.interval)),'noncandidate_color_max':float(self.original[~self.mask].max()) if (~self.mask).any() else None,'storage':'O(N+views*band_pixels), no dense N*H*W','normalization':'each view equal weight; A rows weighted sqrt(M/(V*3*band_pixels)); MSE=2P/M'}
    def lipschitz(self):
        x=torch.ones((self.k,3),device='cuda');x/=torch.linalg.norm(x);lam=0.
        for _ in range(14):
            z=self.adjoint(self.forward(x)).float();lam=float((z*x).sum());x=z/torch.linalg.norm(z).clamp_min(1e-20)
        return max(lam*1.1,1e-6)
    def install(self,c):
        with torch.no_grad():self.m._features_dc[self.mask,0,:]=(c-.5)/C0
