"""Extra deadline contract and pinned real finite-geometry regression; no full assets."""
from runtime_io import *
from port_paths import Leaf
from geometry_base import sample,project
from overlap_model import select_joint
import unittest,importlib.util,sys
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_004/tests')
PREV=U.parent.parent/'unit_003'
class Contracts(unittest.TestCase):
    def test_no_solver_after_zero_budget(self):
        bank=[dict(hid=0,anchor=0,leaves=[0,1],benefit=1.)]
        selected,receipt=select_joint(bank,0,lambda:None)
        self.assertEqual(selected,[]);self.assertEqual(receipt['status'],'partial');self.assertEqual(receipt['reason'],'NO_SOLVER_BUDGET')
    def test_real_successful_cost_schema_and_rejected_cost_exclusion(self):
        from overlap_model import successful_overlaps
        from types import SimpleNamespace
        a=dict(np.load(U/'REAL_OVERLAP_RECORDS.npz',allow_pickle=False));pairs=list(zip(a['a'].tolist(),a['b'].tolist()));leaves={i:SimpleNamespace(valid=True) for pair in pairs for i in pair}
        d=dict(candidates=a,pairs=pairs,leaves=leaves);out=successful_overlaps(d)
        self.assertEqual(len(out),6)
        a['cost']=a['cost'].copy();a['cost'][out[0]['record_id']]+=.01
        with self.assertRaises(AssertionError):successful_overlaps(d)
    def test_pinned_real_geometry_and_exact_rows(self):
        # Previously saved bounded fixture only: nine real carriers /35 seedlets.
        a=dict(np.load(PREV/'tests/REAL_COMPONENT.npz',allow_pickle=False));p=float(a['p'])
        self.assertEqual(len(a['carrier_id']),9);self.assertLessEqual(len(a['seedlets']),128)
        spec=importlib.util.spec_from_file_location('pinned_unit003_geometry',PREV/'source_snapshot/geometry_base.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        qq=[a['knots'][a['knot_offsets'][i]:a['knot_offsets'][i+1]]/p for i in range(len(a['carrier_id']))]
        for donor in qq:
            x=sample(donor)
            for anchor in qq:
                new=project(x,anchor);ref=old.project(x,anchor)
                for aa,bb in zip(new,ref):np.testing.assert_array_equal(aa,bb)
        print('REAL_GEOMETRY_REGRESSION:9 original carriers,35 seedlets; projections identical to unit003 snapshot. No raw-asset loading, refit or science result.')
if __name__=='__main__':unittest.main(verbosity=2)
