"""Nine real finite carriers / 35 seedlets; geometry-only bounded regression."""
from runtime_io import *
from adapter import validate_candidates
from port_paths import Leaf,PathOracle,greedy,joint,check_selection
from ambiguity_policy import certify_component,validate_successful_records
import unittest,importlib.util,sys
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_003/tests')
PREV=U.parent.parent/'unit_002'
class RealAmbiguityTests(unittest.TestCase):
    def test_real_prefix_metrics_ports_and_pinned_guard_results(self):
        a=dict(np.load(U/'REAL_COMPONENT.npz',allow_pickle=False));p=float(a['p']);ls={}
        for i,cid in enumerate(a['carrier_id']):
            part=lambda key,off:a[key][a[off][i]:a[off][i+1]]
            ls[int(cid)]=Leaf(int(cid),int(a['version'][i]),part('rows','row_offsets'),part('seedlets','seed_offsets'),part('knots','knot_offsets')/p,bool(a['valid'][i]),bool(a['baseline'][i]),part('supported_intervals','interval_offsets')/p)
        self.assertLessEqual(sum(len(x.reps) for x in ls.values()),128)
        z={k[len('candidate_'):]:v for k,v in a.items() if k.startswith('candidate_') and k!='candidate_record_index'};z['metric_names']=a['metric_names'];pairs=set(zip(z['a'].tolist(),z['b'].tolist()))
        self.assertEqual(validate_successful_records(dict(candidates=z,leaves=ls)),dict(candidate_records=len(z['a']),successful_overlap=0))
        masked,edges,_=validate_candidates(ls,z,dict(a=z['a'],b=z['b']),pairs);self.assertEqual(masked,[]);self.assertGreater(len(edges),0)
        spec=importlib.util.spec_from_file_location('unit002_pinned_port_paths',PREV/'source_snapshot/port_paths.py');old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
        before={cid:(x.q.copy(),x.rows.copy(),x.reps.copy(),x.version) for cid,x in ls.items()}
        for e in edges:self.assertEqual((e.pa,e.pb),old.endpoint_ports(ls[e.a],ls[e.b]))
        for name in ['greedy','joint']:
            x,r=globals()[name](edges,PathOracle(ls));xx,rr=getattr(old,name)(edges,old.PathOracle(ls))
            self.assertEqual(x,xx);self.assertEqual(r['status'],rr['status']);self.assertEqual(r['benefit'],rr['benefit'])
            self.assertEqual(r.get('records'),rr.get('records'));self.assertEqual(r.get('cuts'),rr.get('cuts'))
        out,rec=certify_component(edges,PathOracle(ls),dict(greedy=[],joint=[]),10)
        self.assertEqual(rec['status'],'certified_complete')
        for arm in out:self.assertTrue(check_selection(edges,out[arm],PathOracle(ls))[0])
        for cert in rec['certificates']:
            if cert['certified']:self.assertGreater(cert['delta'],cert['threshold'])
        for cid,x in ls.items():
            q,rows,reps,version=before[cid];np.testing.assert_array_equal(x.q,q);np.testing.assert_array_equal(x.rows,rows);np.testing.assert_array_equal(x.reps,reps);self.assertEqual(x.version,version)
        print('BOUNDED_REAL_REGRESSION nine original carriers, 35 seedlets; unchanged pair metrics, ports, raw solver results and arrays; no fitting/full scene.')
if __name__=='__main__':unittest.main(verbosity=2)
