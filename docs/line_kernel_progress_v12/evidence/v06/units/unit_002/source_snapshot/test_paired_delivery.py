"""Small checkpoint, crop and frozen-core regressions; synthetic images only."""
from runtime_io import *
from paired_delivery import save_pair,restore_pair,crop_pair,diagnostic_cases
from port_paths import Edge,Leaf,PathOracle,greedy,joint,paths
import unittest,importlib.util,sys
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_002/tests')
OLD=U.parent.parent/'unit_001'

class PairedTests(unittest.TestCase):
    def test_complete_pair_resume_and_later_failure(self):
        out=U/('pair_'+str(time.time_ns()));choices={'greedy':[2],'joint':[3,4]};recs={'greedy':{'status':'greedy_complete'},'joint':{'status':'optimal'}}
        save_pair(out,'bound',7,choices,recs)
        try:raise RuntimeError('diagnostic failure after durable paired checkpoint')
        except RuntimeError:pass
        self.assertEqual(restore_pair(out,'bound',7),(choices,recs))
        with self.assertRaises(AssertionError):restore_pair(out,'other',7)
        with self.assertRaises(AssertionError):restore_pair(out,'bound',8)
        with (out/'LINKS.npz').open('ab') as f:f.write(b'changed')
        with self.assertRaises(RuntimeError):restore_pair(out,'bound',7)
    def test_union_crop_same_bbox_and_empty(self):
        root=U/('crop_'+str(time.time_ns()));root.mkdir()
        a=np.ones((80,100,3));b=a.copy();a[30,35]=0;b[40,55]=.5
        pp=[root/'a.png',root/'b.png'];oo=[root/'ac.png',root/'bc.png']
        for p,x in zip(pp,[a,b]):save_image(p,x)
        receipt=crop_pair(pp,oo);self.assertEqual(receipt['bbox'],[19,14,72,57])
        for out in oo:
            with Image.open(out) as image:self.assertEqual(image.size,(212,172))
        for p in [root/'w1.png',root/'w2.png']:save_image(p,np.ones((10,10,3)))
        empty=crop_pair([root/'w1.png',root/'w2.png'],[root/'e1.png',root/'e2.png']);self.assertTrue(empty['empty']);self.assertFalse((root/'e1.png').exists())
    def test_scientific_core_byte_identical_to_snapshot(self):
        frozen=json.loads((OLD/'PARENT_RUN_FROZEN.json').read_text())
        for name in ['port_paths.py','geometry_base.py']:
            current=Path(__file__).parent/name;source=OLD/'source_snapshot'/name
            self.assertEqual(sha(current),sha(source));self.assertEqual(sha(source),frozen['source_files'][str(current)])
    def test_bounded_real_knots_against_pinned_oracle(self):
        # Only four already saved real carrier knot sequences; no full source asset.
        spec=importlib.util.spec_from_file_location('pinned_port_paths',OLD/'source_snapshot/port_paths.py');pinned=importlib.util.module_from_spec(spec);sys.modules[spec.name]=pinned;spec.loader.exec_module(pinned)
        with np.load(U/'REAL_LEAVES.npz') as z:
            leaves={}
            for j,cid in enumerate(z['ids']):
                lo,hi=z['offsets'][j:j+2];q=z['knots'][lo:hi];length=np.linalg.norm(np.diff(q,axis=0),axis=1).sum()
                leaves[int(cid)]=Leaf(int(cid),int(z['versions'][j]),np.arange(j*6,j*6+6),np.arange(j*3,j*3+3),q,True,False,np.array([[0.,length]]))
        self.assertLessEqual(sum(len(x.reps) for x in leaves.values()),128)
        es=[];ids=sorted(leaves)
        for i,(a,b) in enumerate(zip(ids,ids[1:])):
            pa,pb=pinned.endpoint_ports(leaves[a],leaves[b]);es.append(Edge(i,a,pa,b,pb,.4))
        for algorithm in ['greedy','joint']:
            got,receipt=getattr(sys.modules['port_paths'],algorithm)(es,PathOracle(leaves))
            ref,reference=getattr(pinned,algorithm)(es,pinned.PathOracle(leaves))
            self.assertEqual(got,ref);self.assertEqual(receipt['status'],reference['status']);self.assertEqual(receipt['benefit'],reference['benefit'])
        for cid in leaves:self.assertEqual(PathOracle(leaves)([(cid,False)]),pinned.PathOracle(leaves)([(cid,False)]))

if __name__=='__main__':unittest.main(verbosity=2)
