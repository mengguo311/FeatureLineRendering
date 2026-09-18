import copy,tempfile,unittest
from pathlib import Path
import numpy as np
from test_multiscene import CFG

class ExecutionTests(unittest.TestCase):
    def test_F_primary_exchange_and_LOO_synthetic_straight_line(self):
        from src.corrected_execution import run_inference_arm
        cameras={};fields={};K=np.array([[200.,0,199.5],[0,200.,199.5],[0,0,1]])
        y,x=np.indices((400,400))
        for i,cy in enumerate([0,1,-1,.5,-.5,1.3,-1.3,.8]):
            w=np.eye(4);w[1,3]=-cy;cameras[i]=dict(index=i,K=K.tolist(),w2c=w.tolist())
            edge_y=199.5-200*cy/3;near=np.stack([x,np.full_like(y,edge_y,dtype=float)],axis=2);axis=np.zeros((400,400,2));axis[:,:,0]=1
            fields[i]=dict(dt=abs(y-edge_y),nearest_uv=near,nearest_tangent=axis,domain=np.ones((400,400),bool))
        queries=[dict(query='q',view=0,pixel=[199.5,199.5])];box=[[-1,-1.5,1],[1,1.5,5]]
        with tempfile.TemporaryDirectory() as td:
            base=run_inference_arm(Path(td)/'F',queries,cameras,{k:fields[k] for k in range(4)},None,box,.1,CFG,'no_gs','F')
            exchange=run_inference_arm(Path(td)/'C',queries,cameras,{k:fields[k] for k in range(4,8)},None,box,.1,CFG,'no_gs','C')
            self.assertEqual(len(base['accepted']),1);self.assertEqual(len(exchange['accepted']),1)
            from src.multiscene_probe import match_outputs
            self.assertTrue(match_outputs(base['accepted'],exchange['accepted'],.1,CFG)['passed'])
            loo=run_inference_arm(Path(td)/'LOO',queries,cameras,{k:fields[k] for k in [1,2,3]},None,box,.1,CFG,'loo','F')
            self.assertTrue(match_outputs(base['accepted'],loo['accepted'],.1,CFG)['passed'])
            self.assertTrue((Path(td)/'F/queries.json.sha256').exists())

    def test_route_status_has_per_scene_quality_without_global_blocking(self):
        from src.corrected_execution import scope_decisions
        scenes=[dict(scene='lego',eligible=True,verdict='STOP_B'),dict(scene='chair',eligible=True,verdict='MACHINE_FOUNDATION_GO_MANUAL_PENDING'),dict(scene='drums',eligible=False,verdict='INSUFFICIENT_POSTERIOR_QUALITY'),dict(scene='ficus',eligible=False,verdict='INSUFFICIENT_POSTERIOR_QUALITY')]
        result=scope_decisions(scenes)
        self.assertEqual(result['expanded']['verdict'],'INSUFFICIENT_POSTERIOR_QUALITY')
        self.assertEqual(result['core']['verdict'],'STOP_B')
        self.assertEqual(result['core']['per_scene']['chair'],'MACHINE_FOUNDATION_GO_MANUAL_PENDING')
