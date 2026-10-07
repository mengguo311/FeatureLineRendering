"""Static integration gates run before importing any CUDA-dependent C24 module."""
import ast
from pathlib import Path
import unittest

ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/paper_text_variant')


class TrainContractTests(unittest.TestCase):
    def test_loss_schedule_and_resume_are_wired(self):
        source=(ROOT/'train.py').read_text()
        ast.parse(source)
        self.assertIn('if geometry_active(iteration):',source)
        self.assertIn('geometry_losses(render_pkg, viewpoint_cam)',source)
        self.assertNotIn('distortion_map = depth_distortion[0] * edge',source)
        self.assertNotIn('depth_ratio = 0.6',source)
        self.assertIn('pilot.restore(gaussians, opt, trainCameras)',source)
        self.assertIn('pilot.completed_step(iteration, gaussians, viewpoint_stack',source)
        self.assertNotIn('if iteration < opt.iterations:\n                gaussians.optimizer.step()',source)

    def test_explicit_text_parameters_are_guarded(self):
        source=(ROOT/'train.py').read_text()
        self.assertIn('validate_pilot_arguments(args)',source)
        self.assertIn('pilot_config=args.pilot_config',source)

    def test_evaluator_propagates_subprocess_failure(self):
        source=(ROOT/'evaluate_dtu_mesh.py').read_text()
        self.assertNotIn('os.system(cmd)',source)
        self.assertIn('check=True',source)

    def test_native_kernel_uses_paper_recurrence_without_live_ndc_declaration(self):
        base=ROOT/'submodules/diff-gaussian-rasterization/cuda_rasterizer'
        forward=(base/'forward.cu').read_text();backward=(base/'backward.cu').read_text()
        self.assertIn('paper_distortion_increment(depth, aT, A, dist1, dist2)',forward)
        self.assertIn('paper_distortion_gradient(depth, dchannel_dcolor, w_final, wd_final)',backward)
        self.assertNotIn('const float dmax_t_dd =',backward)


if __name__=='__main__':
    unittest.main(verbosity=2)
