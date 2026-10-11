import unittest
import numpy as np
import torch
from common import core
from primitive import fit_segment, sample_graph, sampling_layout
from differentiable import derive, render_sparse, class_loss,project_torch,candidate_pairs
torch.set_num_threads(2)

class Renderer(unittest.TestCase):
    def setup_scene(self):
        c={'width':31,'height':27,'fx':45.,'fy':43.,'extrinsic':np.eye(4).tolist()}
        p=np.array([[-.25,.013,2.1],[.25,.013,2.1]])
        g=fit_segment(p,.05);g.update(normal=[0,0,1],views=[0],members=[0]);layout=sampling_layout([g])
        return c,g,layout
    def test_roundtrip(self):
        c,g,_=self.setup_scene();u=np.array([[0,0],[15,13],[30,26]],float);z=np.array([1,2,3.]);v,d=core.project(core.backproject(u,z,c),c)
        np.testing.assert_allclose(v,u,atol=1e-8);np.testing.assert_allclose(d,z,atol=1e-8)
    def test_native_regression_reload(self):
        c,g,l=self.setup_scene();cp=torch.tensor(np.array([g['control']]),dtype=torch.float64);w=torch.tensor([.45],dtype=torch.float64);o=torch.tensor([.6],dtype=torch.float64)
        a=derive(cp,w,o,[g],l);x=render_sparse(a,c)
        expected=1-core.render(sample_graph([g],l),c)[...,0]
        np.testing.assert_allclose(x.detach().numpy(),expected,atol=2e-6,rtol=0)
    def test_geometry_width_opacity_FD(self):
        c,g,l=self.setup_scene();cp=torch.tensor(np.array([g['control']]),dtype=torch.float64,requires_grad=True);w=torch.tensor([.45],dtype=torch.float64,requires_grad=True);o=torch.tensor([.6],dtype=torch.float64,requires_grad=True)
        weight=torch.tensor(np.random.RandomState(7).rand(27,31),dtype=torch.float64)
        def fn():return (render_sparse(derive(cp,w,o,[g],l),c)*weight).sum()
        val=fn();grad=torch.autograd.grad(val,[cp,w,o]);pairs=[(cp,(0,0,1),grad[0][0,0,1]),(cp,(0,3,2),grad[0][0,3,2]),(w,(0,),grad[1][0]),(o,(0,),grad[2][0])]
        for arr,idx,an in pairs:
            old=arr[idx].item();eps=1e-6
            with torch.no_grad():arr[idx]=old+eps
            plus=fn().item()
            with torch.no_grad():arr[idx]=old-eps
            minus=fn().item()
            with torch.no_grad():arr[idx]=old
            fd=(plus-minus)/(2*eps)
            np.testing.assert_allclose(float(an),fd,rtol=1e-4,atol=1e-6)
            print('Gaussian FD',idx,'analytic',float(an),'FD',fd,'abs_error',abs(float(an)-fd))
    def test_positive_offline_and_hidden_controls(self):
        c,g,l=self.setup_scene();cp=torch.tensor(np.array([g['control']]),dtype=torch.float64);w=torch.tensor([.45],dtype=torch.float64);o=torch.tensor([.6],dtype=torch.float64)
        a=derive(cp,w,o,[g],l);target=render_sparse(a,c).detach();known=torch.ones_like(target,dtype=torch.bool)
        perfect=class_loss(target,target,known)
        self.assertGreater(float(class_loss(torch.zeros_like(target),target,known)),float(perfect)+.01)
        self.assertGreater(float(class_loss(torch.ones_like(target)*.9,target,known)),float(perfect)+.1)
        hid=render_sparse(a,c,np.ones((27,31)),np.ones((27,31)))
        self.assertEqual(float(hid.max()),0.)
        unknown=torch.zeros_like(known)
        self.assertEqual(float(class_loss(torch.ones_like(target),torch.zeros_like(target),unknown)),0.)
    def test_depth_order_color_native(self):
        c,g,l=self.setup_scene();a={'means':np.array([[0,0,2.],[0,0,3.]]),'covariance':np.repeat(np.eye(3)[None]*.01,2,axis=0),'opacity':np.array([.5,.5]),'colors':np.array([[1,0,0],[0,0,1]])}
        r=core.render(a,c);np.testing.assert_allclose(r[13,15],[.75,.25,.5],atol=1e-6)
    def test_bezier_control_FD(self):
        c,g,_=self.setup_scene();t=np.linspace(0,1,17);p=np.stack([.5*(t-.5),.14*np.sin(np.pi*t)+.013,2.1+0*t],1);g=fit_segment(p,.025);g.update(normal=[0,0,1]);self.assertEqual(g['type'],'bezier');l=sampling_layout([g])
        cp=torch.tensor(np.array([g['control']]),dtype=torch.float64,requires_grad=True);w=torch.tensor([.45],dtype=torch.float64);o=torch.tensor([.6],dtype=torch.float64);weights=torch.arange(31*27,dtype=torch.float64).reshape(27,31)/(31*27)
        def fn():return (render_sparse(derive(cp,w,o,[g],l),c)*weights).sum()
        analytic=torch.autograd.grad(fn(),cp)[0][0,1,1].item();old=cp[0,1,1].item();eps=1e-6
        with torch.no_grad():cp[0,1,1]=old+eps
        plus=fn().item()
        with torch.no_grad():cp[0,1,1]=old-eps
        minus=fn().item()
        with torch.no_grad():cp[0,1,1]=old
        fd=(plus-minus)/(2*eps);np.testing.assert_allclose(analytic,fd,rtol=1e-4,atol=1e-6)
        print('Bezier control analytic',analytic,'FD',fd,'abs_error',abs(fd-analytic))
    def test_geometry_active_not_opacity_only(self):
        c,g,l=self.setup_scene();cp=torch.tensor(np.array([g['control']]),dtype=torch.float64);w=torch.tensor([.45],dtype=torch.float64);o=torch.tensor([.6],dtype=torch.float64);target=render_sparse(derive(cp,w,o,[g],l),c).detach();shift=torch.tensor(.02,dtype=torch.float64,requires_grad=True);opt=torch.optim.Adam([shift],lr=.002);known=torch.ones_like(target,dtype=torch.bool);values=[]
        for it in range(20):
            opt.zero_grad();offset=torch.stack([shift*0,shift,shift*0]);pred=render_sparse(derive(cp+offset,w,o,[g],l),c);loss=class_loss(pred,target,known);values.append(float(loss));loss.backward();opt.step()
        self.assertLess(values[-1],values[0]*.3);self.assertLess(abs(float(shift)),.02)
        print('Geometry active control',values[0],values[-1],float(shift))
    def test_sparse_candidates_exclude_zero_support(self):
        c,g,l=self.setup_scene();cp=torch.tensor(np.array([g['control']]),dtype=torch.float64);w=torch.tensor([.45],dtype=torch.float64);o=torch.tensor([.6],dtype=torch.float64);a=derive(cp,w,o,[g],l);uv,z,S=project_torch(a,c);ids,x,y=candidate_pairs(uv,z,S,c);u=uv.numpy();s=S.numpy();d=np.stack([x,y],1)-u[ids];q=np.einsum('ni,nij,nj->n',d,np.linalg.inv(s[ids]),d)
        self.assertTrue((q<=9.0011).all(),float(q.max()))

if __name__=='__main__':unittest.main(verbosity=2)
