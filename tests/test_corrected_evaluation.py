import unittest
from test_multiscene import CFG

class EvaluationTests(unittest.TestCase):
    def test_gate_failure_is_determinate_and_keeps_manual_pending(self):
        from src.corrected_evaluation import compute_machine_gates
        base=dict(accepted_count=64,query_count=256,resolution_ok=True)
        pred=dict(passed=True,coverage=1.,joint_fraction=1.)
        repeats={'C':dict(passed=True),'LOO':dict(passed=True),'seed':dict(passed=True),'dose':dict(passed=True)}
        angles={'gs':[5.]*10,'random':[50.]*10}
        r=compute_machine_gates(base,pred,repeats,dict(accepted_count=10,query_count=256),angles,True,CFG)
        self.assertTrue(all(r['machine'].values()));self.assertEqual(r['manual']['G2'],'PENDING_INDEPENDENT_REVIEW')
        base['accepted_count']=0
        r=compute_machine_gates(base,pred,repeats,dict(accepted_count=0,query_count=256),angles,True,CFG)
        self.assertFalse(r['machine']['G1']);self.assertFalse(r['machine']['G4_machine'])
        base['accepted_count']=64;repeats['dose']['passed']=False
        self.assertFalse(compute_machine_gates(base,pred,repeats,dict(accepted_count=10,query_count=256),angles,True,CFG)['machine']['G3'])
