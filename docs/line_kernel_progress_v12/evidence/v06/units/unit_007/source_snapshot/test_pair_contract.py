"""Read-only pinned geometry checks plus model lineage/UNKNOWN contracts."""
from runtime_io import *
import unittest,importlib.util
from test_overlap_model import fixture
from test_pair_model import recoverable,CORE
from pair_model import fit_engine,fit_pair,build_extra_bank,map_support,model_group_guard
from pair_delivery import membership_for,enrich,diagnostics
from geometry_base import project
class Contracts(unittest.TestCase):
    def test_original_geometry_preserved_and_aux_model_serialized(self):
        d=recoverable();before={i:(x.q.copy(),x.rows.copy()) for i,x in d['leaves'].items()};means=d['asset']['means'].copy();e=fit_engine(CORE,d);m=fit_pair(e,d,0,1,0,None);hs,_=build_extra_bank(d,dict(carriers=[0,1]),[m]);out,gs,lin=membership_for(d,[hs[0]],hs)
        np.testing.assert_array_equal(means,d['asset']['means'])
        for i,(q,rows) in before.items():np.testing.assert_array_equal(q,d['leaves'][i].q);np.testing.assert_array_equal(rows,d['leaves'][i].rows)
        self.assertEqual(lin[0]['model_seed_pair'],[0,1]);self.assertEqual(gs[0]['model_key'],[1,0,1]);self.assertEqual(enrich(d,gs)[0]['model_q'],m['q'])
    def test_original_unknown_gate_and_aux_survive(self):
        d=fixture(2,length=2.);d['membership']['aux_ids']=np.full((12,2),-7,np.int64);m=fit_pair(fit_engine(CORE,d),d,0,1,0,None);hs,_=build_extra_bank(d,dict(carriers=[0,1]),[m]);out,gs,_=membership_for(d,[hs[0]],hs)
        self.assertTrue(np.all(out['edge_id'][6:]<0));np.testing.assert_array_equal(out['aux_ids'],d['membership']['aux_ids'])
    def test_guard_regression_on_small_fixed_models(self):
        from overlap_model import group_guard
        for n,length in [(2,2.),(3,6.),(4,8.)]:
            d=fixture(n,length);old=group_guard(d,0,list(d['leaves']));new=model_group_guard(d,d['leaves'][0].q,list(d['leaves']));self.assertEqual(old,new)
    def test_pinned_real_support_mapping(self):
        # Only saved nine-carrier/35-seedlet bounded fixture, no original full NPZ loaded.
        p=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_003/tests/REAL_COMPONENT.npz')
        a=dict(np.load(p,allow_pickle=False));self.assertEqual(len(a['carrier_id']),9);self.assertLessEqual(len(a['seedlets']),128)
        spec=importlib.util.spec_from_file_location('pinned_geometry',p.parents[1]/'source_snapshot/geometry_base.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        for i in range(9):
            q=a['knots'][a['knot_offsets'][i]:a['knot_offsets'][i+1]]/float(a['p']);x=old.sample(q)
            for aa,bb in zip(project(x,q),old.project(x,q)):np.testing.assert_array_equal(aa,bb)
        print('REAL_REGRESSION:9 frozen carriers/35 seedlets; no full asset loading or fitting.')
if __name__=='__main__':unittest.main(verbosity=2)
