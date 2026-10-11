import unittest
from pathlib import Path
from native_patch import patched_files

H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
C24=H/'sources/RaDe-GS/submodules/diff-gaussian-rasterization/cuda_rasterizer'

class NativePatchTests(unittest.TestCase):
    def test_official_distortion_forward_body_preserved(self):
        p=patched_files();old=(C24/'forward.cu').read_text();new=p['forward.cu']
        self.assertEqual(new.split('template <uint32_t CHANNELS>')[1:],old.split('template <uint32_t CHANNELS>')[1:])
        self.assertIn('depth_distortion += error * aT;',new)
        self.assertNotIn('paper_distortion',new)
    def test_official_distortion_backward_body_preserved(self):
        p=patched_files();old=(C24/'backward.cu').read_text();new=p['backward.cu']
        self.assertEqual(new.split('template <uint32_t C>')[1:],old.split('template <uint32_t C>')[1:])
        self.assertIn('dmax_t_dd',new)
    def test_fixes_identified_and_no_loss_or_train_in_patch(self):
        p=patched_files();self.assertEqual(set(p),{'forward.cu','backward.cu','rasterizer_impl.cu','paper_geometry_precision.cuh'})
        self.assertIn('geomState.conic_opacity,\n\t\tdL_dopacity), debug)',p['rasterizer_impl.cu'])
        self.assertIn('const float l3 = l * l * l;',p['backward.cu'])
        self.assertIn('const double denom2inv = 1.0 / (denom * denom);',p['backward.cu'])

if __name__=='__main__':unittest.main()
