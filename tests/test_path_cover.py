import unittest
import numpy as np
from src.path_cover import PathProblem,proposals,pack,local_greedy
from src.stroke_simplify import simplify,budget_prefix
from src.stroke_relations import draw_paths

OBJ=dict(node_weight=.3,link_weight=.35,path_reward=3.,start_cost=2.,short_cost=1.,short_units=4.,length_scale=8.,turn_penalty=.4,max_turn_deg=110.,witness_fraction=.3,witness_threshold=.6)
SEARCH=dict(seed_cap=40,beam_width=2,max_nodes=36,checkpoints=[3,6,12,24,36])

def line_graph(n=6):
    pairs=np.c_[np.arange(n-1),np.arange(1,n)];e=len(pairs)
    return dict(p=np.c_[np.arange(n),np.zeros((n,2))],pairs=pairs,l=np.full(n,.6),unit=.6,
        physical=np.ones(e,bool),full=np.ones(e,bool),corner=np.zeros(e,bool),support=np.ones((3,e)),
        evaluated=np.ones((3,e),bool),length_px=np.ones((3,e))*8,node_support=np.ones((3,n)),
        node_evaluated=np.ones((3,n),bool),continuation=np.zeros(e),gap=np.full(e,.3),
        tangent_agreement=np.ones(e),id_affinity=np.ones(e),source_weight=np.ones(n),length=np.ones(e))

class CoverTest(unittest.TestCase):
    def test_global_pays_start_cost_for_collectively_good_path(self):
        g=line_graph();p=PathProblem(g,OBJ,'B')
        self.assertTrue(np.all(p.edge_value<0))
        local,_=local_greedy(p);self.assertFalse(local)
        candidates=proposals(p,SEARCH);selected,audit=pack(candidates,p.n)
        self.assertEqual(len(selected),1);self.assertEqual(set(selected[0][0]),set(range(6)))
        self.assertGreater(audit['final_objective'],0)

    def test_corner_protection_and_no_cycles_or_degree_violation(self):
        g=line_graph(5);g['p']=np.array([[0,0,0],[1,0,0],[2,0,0],[2,1,0],[2,2,0.]])
        p=PathProblem(g,OBJ);ok,cost,protected=p.turn(1,2,3,1,2)
        self.assertTrue(ok);self.assertTrue(protected)
        q=PathProblem(g,OBJ,'B');self.assertLess(cost,q.turn(1,2,3,1,2)[1])
        rows,audit=pack(proposals(p,SEARCH),p.n)
        for row in rows:self.assertEqual(len(row[0]),len(set(row[0])))
        self.assertEqual(len([n for row in rows for n in row[0]]),len(set(n for row in rows for n in row[0])))
        self.assertTrue(any(2 in row[0] and 3 in row[0] for row in rows))

    def test_deterministic_and_null_keeps_budget(self):
        g=line_graph();p=PathProblem(g,OBJ,'N',7);q=PathProblem(g,OBJ,'N',7)
        self.assertEqual(int(p.mask.sum()),len(g['pairs']))
        a,_=pack(proposals(p,SEARCH),p.n);b,_=pack(proposals(q,SEARCH),q.n)
        self.assertEqual([r[0] for r in a],[r[0] for r in b])

    def test_greedy_breaks_a_cycle(self):
        g=line_graph(5);g['p']=np.array([[0.,0,0],[1,0,0],[1,1,0],[0,1,0],[3,3,0]])
        g['pairs']=np.array([[0,1],[1,2],[2,3],[0,3]])
        g['continuation'][:]=1.
        rows,audit=local_greedy(PathProblem(g,OBJ))
        self.assertEqual(audit['rejected']['cycle'],1)
        self.assertEqual(len(rows),1);self.assertEqual(len(rows[0][0]),4)

    def test_simplify_protects_corner_and_trust_region(self):
        p=np.array([[0,0,0],[1,0,0],[2,0,0],[2,1,0],[2,2,0.]])
        result,idx=simplify(p,2,.1,35)
        self.assertIn(2,idx);np.testing.assert_array_equal(result,p[idx])
        q=np.array([[0,0,0],[1,.5,0],[2,0,0.]])
        result,idx=simplify(q,2,.05,180)
        self.assertEqual(len(result),3)

    def test_actual_ink_not_candidate_count_controls_budget(self):
        projected=[[np.array([[3.,3.],[25.,3.]])],[np.array([[3.,3.],[25.,3.]])],[np.array([[3.,15.],[25.,15.]])]]
        def measure(ids):
            chosen=np.zeros(3,bool);chosen[ids]=True
            return float((1-draw_paths(projected,chosen,(32,32))[:,:,0]/255.).sum())
        costs=[measure(np.arange(n)) for n in range(4)]
        # AA compositing of duplicate strokes can add darkening; use the actual
        # renderer cost rather than assuming a binary-mask union.
        n,value,info=budget_prefix(np.arange(3),measure,costs[2])
        self.assertEqual(n,2);self.assertEqual(value,costs[2]);self.assertFalse(info['under_capacity'])
        n,value,info=budget_prefix(np.arange(3),measure,2*costs[3])
        self.assertTrue(info['under_capacity'])

if __name__=='__main__':unittest.main()
