import unittest,sys
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from experiments import probe_color_projection
class ProbeTests(unittest.TestCase):
    def test_known_recoverable_probe_keeps_native_initial_color_feasible(self):
        initial=torch.tensor([[1.22,.25,.0],[.7,.1,.4]])
        self.assertTrue(torch.equal(probe_color_projection(initial,initial),initial))
    def test_probe_bounds_derived_only_from_perturbed_native_colors(self):
        initial=torch.tensor([[1.22,.25,.0]])
        got=probe_color_projection(torch.tensor([[1.9,-.2,2.]]),initial)
        self.assertTrue(torch.allclose(got,torch.tensor([[1.22,0.,1.]])))
if __name__=='__main__':unittest.main()
