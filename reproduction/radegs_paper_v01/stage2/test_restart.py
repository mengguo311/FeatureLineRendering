"""CPU Adam/RNG/buffer restart parity; test precedes implementation."""
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np
import torch
import checkpointing as cp


class FakeGaussian:
    def __init__(self):
        for key in cp.PARAMETERS:
            setattr(self, key, torch.nn.Parameter(torch.tensor([.2,.7],dtype=torch.double)))
        for i,key in enumerate(cp.BUFFERS):
            setattr(self,key,torch.tensor([i+.4],dtype=torch.double))
        self.appearance_network = torch.nn.Linear(2,2).double()
        self.active_sh_degree = 2
        self.spatial_lr_scale = 1.2
        self.training_setup(None)

    def training_setup(self, _):
        self.optimizer = torch.optim.Adam([getattr(self,k) for k in cp.PARAMETERS]
                                         +list(self.appearance_network.parameters()), lr=.01)
        # C24 overwrites these accumulators in training_setup.
        self.xyz_gradient_accum = torch.zeros(1,dtype=torch.double)

    def step(self):
        r = random.random() + np.random.rand() + torch.rand((),dtype=torch.double)
        loss = sum((getattr(self,k)*r).square().sum() for k in cp.PARAMETERS)
        loss += self.appearance_network(torch.tensor([.3,.1],dtype=torch.double)).square().sum()
        loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad(set_to_none=True)
        self.xyz_gradient_accum += .25


class RestartTests(unittest.TestCase):
    def test_resume_matches_uninterrupted_parameters_rng_optimizer_buffers(self):
        random.seed(0);np.random.seed(0);torch.manual_seed(0)
        a = FakeGaussian()
        a.step();a.step()
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/'checkpoint.pt'
            cp.save_checkpoint(file,a,2,['camera4','camera1'],{'source':'test'},cuda=False)
            a.step()
            expected_next = (random.random(),np.random.rand(),torch.rand(()))
            b = FakeGaussian()
            iteration,stack = cp.restore_checkpoint(file,b,None,{'source':'test'},cuda=False)
            self.assertEqual(iteration,2)
            self.assertEqual(stack,['camera4','camera1'])
            b.step()
            self.assertEqual(expected_next,(random.random(),np.random.rand(),torch.rand(())))
            for key in cp.PARAMETERS+cp.BUFFERS:
                self.assertTrue(torch.equal(getattr(a,key),getattr(b,key)),key)
            for x,y in zip(a.appearance_network.parameters(),b.appearance_network.parameters()):
                self.assertTrue(torch.equal(x,y))
            for key in a.optimizer.state_dict()['state']:
                for field,x in a.optimizer.state_dict()['state'][key].items():
                    self.assertTrue(torch.equal(x,b.optimizer.state_dict()['state'][key][field]))

    def test_wrong_provenance_and_unsealed_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/'checkpoint.pt'
            cp.save_checkpoint(file,FakeGaussian(),2,[],{'source':'test'},cuda=False)
            with self.assertRaises(ValueError):
                cp.restore_checkpoint(file,FakeGaussian(),None,{'source':'wrong'},cuda=False)
            file.write_bytes(b'truncated')
            with self.assertRaises(ValueError):
                cp.restore_checkpoint(file,FakeGaussian(),None,{'source':'test'},cuda=False)


if __name__=='__main__':
    unittest.main(verbosity=2)
