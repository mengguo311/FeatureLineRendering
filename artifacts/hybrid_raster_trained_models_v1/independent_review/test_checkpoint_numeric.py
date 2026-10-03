"""Frozen checkpoint checker must inspect SH fields NPR intentionally ignores."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from plyfile import PlyData,PlyElement
from verify_experiment import OUT,sha
from verify_acquisition import inspect_checkpoint


class CheckpointNumericTests(unittest.TestCase):
    def test_fullsh_finite_and_ignored_nonfinite_rejected(self):
        tmp=OUT/'tmp';tmp.mkdir(parents=True,exist_ok=True)
        names=['x','y','z','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3','f_dc_0','f_dc_1','f_dc_2']+[f'f_rest_{i}' for i in range(45)]
        data=np.zeros(3,dtype=[(n,'f4') for n in names]);data['rot_0']=1
        with tempfile.TemporaryDirectory(dir=tmp) as folder:
            p=Path(folder)/'point_cloud.ply'
            PlyData([PlyElement.describe(data,'vertex')]).write(p)
            self.assertTrue(inspect_checkpoint(p,sha(p))['all_numeric_fields_finite'])
            data['f_rest_44'][1]=np.nan;PlyData([PlyElement.describe(data,'vertex')]).write(p)
            with self.assertRaisesRegex(ValueError,'f_rest_44'):inspect_checkpoint(p,sha(p))
            data['f_rest_44'][1]=0;PlyData([PlyElement.describe(data,'vertex')]).write(p)
            with self.assertRaisesRegex(ValueError,'hash'):inspect_checkpoint(p,'changed')


if __name__=='__main__':unittest.main()
