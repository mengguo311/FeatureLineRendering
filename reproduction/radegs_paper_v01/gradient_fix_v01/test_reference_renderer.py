import ast
import json
from pathlib import Path
import unittest
import torch
from reference_renderer import reference
from paper_losses import median_depth_normal

ROOT=Path(__file__).resolve().parents[1]
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')


def cpu_fixture():
    tree=ast.parse((ROOT/'stage2/gpu_smoke.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fixture')
    values=ast.literal_eval(fn.body[0].value)
    return {k:torch.tensor(v,dtype=torch.double,requires_grad=True) for k,v in values.items()}


def loss(o):
    nd=median_depth_normal(o['median'],16.,12.)
    return (o['alpha']-(o['normal']*nd).sum(0,keepdim=True))[:,11:13,15:17].mean()


class ReferenceTests(unittest.TestCase):
    def test_double_reference_matches_saved_real_native_forward(self):
        old=HDD/'gradient_fix_v01/original_failure'
        baseline=next(old.rglob('baseline.pt'))
        b=torch.load(baseline,map_location='cpu')['outputs']
        p=cpu_fixture();o=reference(p)
        errors={}
        for name,i in [('alpha',4),('median',3),('normal',5)]:
            a=o[name][:,10:14,14:18];native=b[i][:,10:14,14:18].double()
            errors[name]=float((a-native).abs().max())
            torch.testing.assert_close(a,native,rtol=3e-5,atol=2e-6)
        print(json.dumps({'reference_vs_saved_native_max_error':errors}),flush=True)

    def test_double_reference_pipeline_gradcheck(self):
        p=cpu_fixture();keys=('means','scales','rotations','opacity')
        self.assertTrue(torch.autograd.gradcheck(lambda *v:loss(reference(dict(zip(keys,v)))),
                         tuple(p[k] for k in keys),eps=1e-6,atol=1e-7,rtol=1e-5))
        grads=torch.autograd.grad(loss(reference(p)),tuple(p[k] for k in keys))
        print(json.dumps({'double_reference_eq24_gradients':{k:v.tolist() for k,v in zip(keys,grads)}}),flush=True)


if __name__=='__main__':
    torch.set_num_threads(1)
    unittest.main(verbosity=2)
