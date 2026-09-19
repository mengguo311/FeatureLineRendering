import copy,tempfile,unittest
from pathlib import Path
import numpy as np
from test_multiscene import CFG

class ExecutionTests(unittest.TestCase):
    def test_control_completion_never_changes_existing_fits(self):
        from src.corrected_execution import finish_primary_controls
        import json,hashlib
        class Evidence:
            def observations(self,points):return [dict(visible=np.ones(len(points),bool),dt=np.zeros(len(points))) for _ in range(4)]
        x,y=np.meshgrid(np.linspace(-.2,.2,12),np.linspace(-.2,.2,12));mu=np.c_[x.ravel(),y.ravel(),np.ones(x.size)];asset=dict(mu=mu,scale=np.full_like(mu,.03))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for arm in ['gs','no_gs']:
                (root/arm).mkdir()
                for name,value in [('summary.json',dict(accepted_count=0)),('accepted.json',[]),('modes.json',[])]:
                    (root/arm/name).write_text(json.dumps(value))
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            report=finish_primary_controls(root,asset,Evidence(),CFG)
            self.assertTrue(report['existing_artifacts_unchanged'])
            self.assertGreater(len(json.loads((root/'pca.json').read_text())['accepted']),0)
            self.assertTrue(all(Path(p).read_bytes()==data for p,data in before.items()))
            with self.assertRaises(FileExistsError):finish_primary_controls(root,asset,Evidence(),CFG)

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

    def test_parallel_arms_are_array_identical_to_serial_execution(self):
        from src.corrected_execution import run_parallel_arms,run_inference_arm
        from src.corrected_probe import load_probe
        cameras={};fields={};K=np.array([[100.,0,99.5],[0,100.,99.5],[0,0,1]])
        y,x=np.indices((200,200))
        for i,cy in enumerate([0.,1.,-1.,.5]):
            w=np.eye(4);w[1,3]=-cy;cameras[i]=dict(K=K,w2c=w)
            ey=99.5-100*cy/3;t=np.zeros((200,200,2));t[:,:,0]=1
            fields[i]=dict(dt=abs(y-ey),nearest_uv=np.stack([x,np.full_like(y,ey,dtype=float)],axis=2),nearest_tangent=t,domain=np.ones((200,200),bool))
        queries=[dict(query='q',view=0,pixel=[99.5,99.5])];box=[[-1,-1.5,1],[1,1.5,5]]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run_inference_arm(root/'serial',queries,cameras,fields,None,box,.1,CFG,'serial','F')
            names=['arm_'+str(i) for i in range(8)]
            jobs=[dict(name=name,queries=queries,fields=fields,layers=None) for name in names]
            run_parallel_arms(root/'parallel',jobs,cameras,box,.1,CFG,'F',workers=8)
            for name in names:
                a=load_probe(root/'serial');b=load_probe(root/'parallel'/name)
                self.assertEqual(a['accepted'],b['accepted']);self.assertEqual(a['modes'],b['modes'])
                with np.load(root/'serial/profiles.npz') as x,np.load(root/'parallel'/name/'profiles.npz') as y:
                    for k in x.files:np.testing.assert_array_equal(x[k],y[k])
