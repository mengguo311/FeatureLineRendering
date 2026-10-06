"""Independent tiny original-ID truth for mandatory assignment and raw voting."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from assignment import assign, sample_sparse, aggregate, rank_ids

class Contract(unittest.TestCase):
    def fixture(self):
        ids=np.full((5,7,2),-1,np.int32); w=np.zeros(ids.shape,np.float32)
        # Center has two original rows; row 4 has the larger side difference.
        ids[2,3]=[2,4]; w[2,3]=[.6,.3]
        ids[2,1]=[4,2]; w[2,1]=[.7,.2]
        ids[2,5]=[2,4]; w[2,5]=[.2,.1]
        line=np.zeros((5,7),bool); line[2,3]=True
        normal=np.zeros((5,7,2),np.float32);normal[...,0]=1
        conf=np.ones((5,7),np.float32)
        return ids,w,w.sum(2),line,normal,conf
    def test_known_normal_and_multiple_attributes(self):
        a=assign(*self.fixture(),count=7)
        self.assertEqual(a['winner_map'][2,3],4)
        self.assertAlmostEqual(a['selected_D'][0],.6,places=6)
        self.assertEqual(a['fallback_map'][2,3],0)
        self.assertEqual(int(a['counts'].sum()),1)
    def test_zero_difference_falls_back_to_center(self):
        ids,w,full,line,n,c=self.fixture();w[2,1]=w[2,5]=0;full=w.sum(2)
        a=assign(ids,w,full,line,n,c,count=7)
        self.assertEqual(a['winner_map'][2,3],2)
        self.assertEqual(a['fallback_map'][2,3],2)
    def test_background_stays_marked_and_is_counted(self):
        ids,w,full,line,n,c=self.fixture();line[0,0]=True
        a=assign(ids,w,full,line,n,c,count=7)
        self.assertTrue(line[0,0]);self.assertEqual(a['winner_map'][0,0],-1)
        self.assertEqual(a['fallback_map'][0,0],5)
        self.assertEqual(a['unassignable'],1)
        self.assertEqual(int(a['counts'].sum()),int(line.sum())-1)
    def test_bilinear_unions_original_ids_not_slots(self):
        ids=np.array([[[5,2],[2,5]],[[2,5],[5,2]]],np.int32)
        w=np.array([[[.7,.1],[.3,.5]],[[.2,.6],[.8,.0]]],np.float32)
        m,res=sample_sparse(ids,w,np.array([[.5,.5]]),w.sum(2),8)
        self.assertAlmostEqual(m[0,5],.65,places=6)
        self.assertAlmostEqual(m[0,2],.15,places=6)
        self.assertLess(abs(res[0]),1e-7)
    def test_endpoint_only_cannot_receive_center_vote(self):
        ids,w,full,line,n,c=self.fixture();ids[2,1]=[6,2];w[2,1]=[.9,.1]
        ids[2,5]=[2,4];w[2,5]=[.1,.1]
        a=assign(ids,w,w.sum(2),line,n,c,count=7)
        self.assertEqual(a['endpoint_best_id'][0],6)
        self.assertNotEqual(a['winner_map'][2,3],6)
    def test_stable_original_id_ties(self):
        ids,w,full,line,n,c=self.fixture();ids[2,3]=[4,2];w[2,3]=[.5,.5]
        w[2,1]=w[2,5]=0
        a=assign(ids,w,w.sum(2),line,n,c,count=7)
        self.assertEqual(a['winner_map'][2,3],2)
        self.assertEqual(rank_ids(np.array([0,5,5]),np.array([0,1,2])).tolist(),[2,1])
    def test_undefined_normal_and_large_unknown_still_assign(self):
        ids,w,full,line,n,c=self.fixture();n[2,3]=np.nan
        a=assign(ids,w,full,line,n,c,count=7)
        self.assertEqual(a['winner_map'][2,3],2);self.assertEqual(a['fallback_map'][2,3],1)
        ids,w,full,line,n,c=self.fixture();full[2,1]=full[2,5]=1
        w[2,1]*=.01;w[2,5]*=.01
        a=assign(ids,w,full,line,n,c,count=7)
        self.assertEqual(a['winner_map'][2,3],2);self.assertEqual(a['fallback_map'][2,3],3)
    def test_raw_full_N_presence_once_and_duplicate_camera_rejected(self):
        c=np.array([0,100,0,1,0],np.int64);d=np.array([0,2,0,0,0],np.int64)
        a=aggregate([('a',c,101),('b',d,2)],5)
        self.assertEqual(a['raw_frequency'].tolist(),[0,102,0,1,0])
        self.assertEqual(a['view_count'].tolist(),[0,2,0,1,0])
        self.assertAlmostEqual(a['view_normalized'][1],100/101+1)
        with self.assertRaises(ValueError):aggregate([('a',c,101),('a',d,2)],5)
    def test_every_valid_pixel_exactly_one_vote(self):
        rng=np.random.default_rng(9);ids=np.broadcast_to(np.array([8,3]),(8,8,2)).copy()
        w=rng.uniform(.01,.3,ids.shape).astype(np.float32);line=np.ones((8,8),bool)
        n=np.zeros((8,8,2),np.float32);n[...,0]=1
        a=assign(ids,w,w.sum(2),line,n,np.ones((8,8)),count=10)
        self.assertTrue(np.all(a['winner_map']>=0));self.assertEqual(int(a['counts'].sum()),64)

if __name__=='__main__':unittest.main(verbosity=2)
