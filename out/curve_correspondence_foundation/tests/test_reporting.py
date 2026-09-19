import unittest,copy,json
from test_matching import CFG
class Reporting(unittest.TestCase):
 def test_scene_gates_cannot_be_rescued_by_other_scene_or_empty(self):
  import cc_report
  passing=dict(yield_pass=True,fit_pass=True,C_pass=True,DEV_pass=True,C_coverage=.9,DEV_coverage=.7,repeat_pass=True,certificate=True,C_null=True,DEV_null=True)
  a=cc_report.arm_gates(passing,CFG['gates']);self.assertTrue(all(a.values()))
  bad=dict(passing,yield_pass=False);self.assertFalse(cc_report.arm_gates(bad,CFG['gates'])['G1'])
  result=cc_report.core_verdict({'lego':'CURVE_CORRESPONDENCE_GO_MANUAL_PENDING','chair':'STOP_CORRESPONDENCE'});self.assertEqual(result,'STOP_CORRESPONDENCE')
 def test_report_json_roundtrip_totals_and_manual_honesty(self):
  import cc_report
  result=dict(core_verdict='STOP_CORRESPONDENCE',scenes=[dict(scene='lego',verdict='STOP_CORRESPONDENCE',qualifier='CONTROLLED_ONLY',segments=100,candidates=70,pairs=10,identities=2,image_tracks=1,gs_tracks=0,arms=37)],totals=dict(segments=100,candidates=70,pairs=10,identities=2,image_tracks=1,gs_tracks=0,arms=37),manual=dict(independent_review_count=0,status='PENDING_INDEPENDENT_REVIEW'))
  text=cc_report.markdown(json.loads(json.dumps(result,sort_keys=True)));self.assertTrue(cc_report.verify_markdown(result,text));self.assertFalse(cc_report.verify_markdown(result,text.replace('| segments | 100 |','| segments | 101 |')))
  self.assertIn('Zero independent',text)
if __name__=='__main__':unittest.main()
