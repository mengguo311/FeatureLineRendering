import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from test_multiscene import CFG
from src.multiscene_probe import edge_field,shift_field as old_shift,ImageEvidence,infer_queries
try:
    from src.corrected_probe import shift_field
except ImportError:
    shift_field=old_shift

class CorrectedProbeTests(unittest.TestCase):
    def test_shifted_association_moves_nearest_edge_coordinates_with_maps(self):
        im=np.ones((400,400,3));im[:,200:]=0
        field=edge_field(im,CFG);shifted=shift_field(field,0,CFG)
        # View0 shifts x by -32; an observed point on the shifted edge has zero residual.
        ys,xs=np.nonzero(shifted['edge']&shifted['domain'])
        index=len(xs)//2;x,y=xs[index],ys[index]
        np.testing.assert_allclose(shifted['nearest_uv'][y,x],[x,y])

    def test_prediction_denominators_and_empty_controls_do_not_pass(self):
        from src.corrected_probe import prediction_summary,machine_decision
        rows=[dict(query=i,views=[dict(view=v,direction_evaluable=True,dt=.5,angle=3.) for v in range(3)]) for i in range(10)]
        good=prediction_summary(rows,CFG);self.assertTrue(good['passed']);self.assertEqual(good['denominator'],10)
        for r in rows[:3]:r['views']=[]
        self.assertFalse(prediction_summary(rows,CFG)['passed'])
        self.assertFalse(prediction_summary([],CFG)['passed'])
        self.assertEqual(machine_decision(True,dict(G0=True,G1=False,G2_machine=False,G3=False,G4_machine=False),False),'STOP_B')
        self.assertEqual(machine_decision(False,{},False),'INSUFFICIENT_POSTERIOR_QUALITY')
        self.assertEqual(machine_decision(True,dict(G0=True,G1=True,G2_machine=True,G3=True,G4_machine=True),False),'MACHINE_FOUNDATION_GO_MANUAL_PENDING')

    def test_saved_profile_retains_all_queries_modes_and_nonfinite_masks(self):
        from src.corrected_probe import save_probe,load_probe
        result=dict(accepted=[],modes=[dict(query='q',accepted=False,reasons=['multimodal'],rms=None)],profiles=[dict(query='q',depths=np.array([1.,2,3]),cost=np.array([np.inf,.5,np.inf]),origin=np.zeros(3),direction=np.array([0.,0,1]),modes=[dict(depth=2.,cost=.5,plateau=[2,2],bracket=[1,3])],resolution_ok=True)],query_count=1,resolution_ok=True)
        with tempfile.TemporaryDirectory() as td:
            save_probe(Path(td),result);loaded=load_probe(Path(td))
            self.assertEqual(loaded['modes'],result['modes'])
            with np.load(Path(td)/'profiles.npz') as data:
                np.testing.assert_array_equal(data['cost'],[np.inf,.5,np.inf])
                np.testing.assert_array_equal(data['offsets'],[0,3])
            self.assertEqual(loaded['query_count'],1)

    def test_pca_null_stays_at_original_centers_and_uses_F_views(self):
        from src.corrected_probe import pca_control,random_control,glyph_coverage
        n=120;mu=np.stack([np.linspace(-1,1,n),np.zeros(n),np.full(n,3)],axis=1)
        asset=dict(mu=mu,scale=np.full((n,3),.08))
        class Evidence:
            def observations(self,points):return [dict(visible=np.ones(len(points),bool),dt=np.zeros(len(points))) for _ in range(4)]
        result=pca_control(asset,Evidence(),CFG)
        self.assertEqual(result['selected_count'],36)
        self.assertGreater(len(result['accepted']),20)
        for row in result['accepted']:
            self.assertTrue(np.any(np.all(mu==row['point'],axis=1)))
            self.assertGreater(abs(row['axis'][0]),.999)
        rand=random_control(result['accepted'],CFG)
        self.assertEqual([r['point'] for r in rand],[r['point'] for r in result['accepted']])
        self.assertEqual(rand,random_control(result['accepted'],CFG))
        cov=glyph_coverage(result['accepted'],result['accepted'],.01,CFG)
        self.assertEqual(cov['forward'],1.);self.assertEqual(cov['backward'],1.)
