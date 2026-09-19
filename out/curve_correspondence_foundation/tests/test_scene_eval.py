import unittest,numpy as np
from test_matching import CFG,curve,camera,edge
class SceneEvaluation(unittest.TestCase):
 def test_identity_certificate_rejects_missing_margin_and_cycle(self):
  import cc_evaluate
  r=dict(nodes=['1','2','3'],views=[1,2,3],cycle_p90=0,identity_frozen_before_fit=True)
  es=[edge(1,2),edge(1,3),edge(2,3)]
  self.assertTrue(cc_evaluate.identity_certificate([r],es,CFG['matching']))
  es[0]['margin_a']=.001;self.assertFalse(cc_evaluate.identity_certificate([r],es,CFG['matching']))
  self.assertFalse(cc_evaluate.identity_certificate([],[],CFG['matching']))
 def test_failure_buckets_are_explicit_without_semantic_truth(self):
  import cc_evaluate
  cs={'1':curve(1,[[10,10],[20,20]])};annotation=dict(challenges=[dict(view=1,box=[5,5,25,25],category='shadow_highlight')])
  r=cc_evaluate.failure_buckets(cs,[dict(a='1',b='1',reasons=['appearance'])],[],annotation)
  self.assertEqual(set(r['buckets']),{'view_dependent_silhouette','shadows','highlights','repeated_texture','junctions','multilayer_cross_part'})
  self.assertFalse(r['semantic_truth']);self.assertEqual(r['buckets']['shadows']['curves'],1)
 def test_cardinality_and_ink_selection_excludes_empty_denominator(self):
  import cc_evaluate
  c=camera([0,0,0],[[100,0,50],[0,100,50],[0,0,1.]])
  r=[dict(id=str(i),xyz=np.array([[-.2,.01*i,1],[.2,.01*i,1]])) for i in range(5)]
  sets,meta=cc_evaluate.comparison_sets({'a':r,'b':r[:3],'empty':[]},[c],CFG)
  self.assertEqual(meta['cardinality'],3);self.assertEqual(len(sets['cardinality']['empty']),0);self.assertEqual(len(sets['cardinality']['a']),3)
  self.assertEqual(sets['ink']['empty'],[]);self.assertFalse(meta['ink']['empty']['comparable'])
if __name__=='__main__':unittest.main()
