import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='2'
import unittest
import numpy as np
from grouping import run_arrays

def fixture(paths):
    means=[]; controls=[]; ci=[]; pieces=[]; truth=[]
    for label, path in enumerate(paths):
        for start in range(0,len(path),4):
            pts=path[start:start+4]
            if len(pts)<2: continue
            k=len(controls); controls.extend([pts[0],pts[-1]])
            means.extend(pts); ci.extend([[k,k+1]]*len(pts)); pieces.extend([k//2]*len(pts)); truth.extend([label]*len(pts))
    means=np.asarray(means); n=len(means)
    a=dict(means=means,covariance=np.tile(np.eye(3)*.1,(n,1,1)),opacity=np.full(n,.2),colors=np.zeros((n,3)),primitive_id=np.asarray(pieces,dtype=np.int32),internal_piece_id=np.asarray(pieces,dtype=np.int32),arc_t=np.arange(n,dtype=float))
    s=dict(control=np.asarray(controls),control_index=np.asarray(ci),derivative_basis=np.tile([-1.,1.],(n,1)),pixel=np.ones(n))
    return a,s,np.asarray(truth)

class GroupingTests(unittest.TestCase):
    def check_case(self, paths, minimum=16):
        a,s,truth=fixture(paths); before={k:v.tobytes() for k,v in a.items()}
        result=run_arrays(a,s)
        for method in ('baseline','hough'):
            ids=result[method]['edge_id']; self.assertEqual(len(ids),len(truth)); self.assertGreaterEqual(int((ids>=0).sum()),minimum)
            for e in np.unique(ids[ids>=0]): self.assertEqual(len(np.unique(truth[ids==e])),1)
            self.assertLessEqual(result[method]['max_degree'],2)
            self.assertLessEqual(result[method]['max_gap_over_p'],1.5+1e-10)
        for k,v in a.items(): self.assertEqual(before[k],v.tobytes())
        return a,s,result
    def test_fragmented_cross_parent_and_parent_permutation(self):
        x=np.arange(96)*.35; path=np.c_[x,np.zeros((len(x),2))]
        a,s,r=self.check_case([path],80)
        self.assertGreaterEqual(max(np.bincount(r['hough']['edge_id'][r['hough']['edge_id']>=0])),80)
        self.assertGreater(r['hough_family_count'],0)
        a['primitive_id']=10000-a['primitive_id']*7
        b=run_arrays(a,s)
        for m in ('baseline','hough'): np.testing.assert_array_equal(r[m]['edge_id'],b[m]['edge_id'])
    def test_gradually_curved_fragments(self):
        t=np.arange(80)*.025; path=np.c_[15*np.cos(t),15*np.sin(t),np.zeros(len(t))]
        self.check_case([path],60)
    def test_parallel_edges(self):
        x=np.arange(80)*.35; self.check_case([np.c_[x,np.zeros(len(x)),np.zeros(len(x))],np.c_[x+.1,np.full(len(x),1.2),np.zeros(len(x))]],100)
    def test_x_and_t_crossings(self):
        x=(np.arange(80)-39.5)*.35; h=np.c_[x,np.zeros((len(x),2))]; v=np.c_[np.zeros(len(x)),x,np.zeros(len(x))]
        self.check_case([h,v],100); self.check_case([h,v[40:]],70)

if __name__=='__main__': unittest.main()
