import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import guard
from optimization import Editor,coverage_loss
from adapter import load_model,make_camera,render,alpha,support,permission_audit,snapshot

class Native(unittest.TestCase):
    def test_real_fullsh_permission_and_coverage_gradient(self):
        import torch, json, numpy as np
        guard('native-integration-test')
        from runtime import ART
        v=json.loads((ART/'DATA_FREEZE.json').read_text())['scenes']['chair']
        m=load_model(v['model'],3);c=make_camera(v['roles']['edit-train'][0]['camera'])
        baseline=render(m,c);python=render(m,c,python_sh=True)
        self.assertLess((baseline-python).abs().max().item(),5e-5)
        self.assertEqual(m.get_features.shape[1],16)
        with torch.no_grad(): a=alpha(m,c)
        before=snapshot(m); ids=list(range(100))
        e=Editor(m,ids,True);me=e.model()
        l=coverage_loss(alpha(me,c),torch.ones_like(a),torch.ones_like(a))
        g=torch.autograd.grad(l,e.scale_delta,retain_graph=True)[0]
        self.assertTrue(torch.isfinite(g).all());self.assertGreater(g.abs().sum().item(),0)
        with torch.no_grad():e.dc_delta.add_(.001);e.scale_delta.add_(.005);e.project()
        self.assertTrue(permission_audit(before,snapshot(e.model()),ids,True)['pass'])
        maps=[np.ones(a.shape,np.float32)]*3
        mass=support(m,c,maps)
        self.assertLess(abs(mass[:,0].sum().item()-a.sum().item())/a.sum().item(),2e-6)
        # Parallel CUDA atomic sums need a finite precision tolerance per channel.
        self.assertTrue(torch.allclose(mass[:,0],mass[:,1],atol=2e-5,rtol=2e-6))
        # Real zero-step display-DC projection is a separately named diagnostic.
        self.assertEqual(m.active_sh_degree,3)

if __name__=='__main__':unittest.main()
