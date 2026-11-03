from runtime_io import *
from types import SimpleNamespace
import unittest
from coverage_policy import select_scope,diagnostics
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_007/tests')
class CoveragePolicy(unittest.TestCase):
 def test_all_components_beyond_eight_keep_incident_evidence(self):
  pairs=[(2*i,2*i+1) for i in range(10)];d=dict(overlaps=[dict(a=a,b=b,record_id=k) for k,(a,b) in enumerate(pairs)],pairs=pairs+[(1,20)],leaves={i:SimpleNamespace(intervals=np.array([[0.,1.]])) for i in range(21)},arrays=dict(carrier_id=np.arange(21),kind=np.array(['line']*21)))
  c=dict(max_components=8,decision_carrier_cap=128,overlap_priority_ids=[])
  contexts,audit=select_scope(c,d)
  self.assertEqual(len(contexts),10);self.assertEqual(contexts[0]['evidence_carriers'],[0,1,20]);self.assertEqual(sum(len(x['overlap_record_ids']) for x in contexts),10)
 def test_member_change_not_crowded_out_by_model_replacement(self):
  root=U/('selector_'+str(time.time_ns()));root.mkdir(parents=True)
  def group(k,ids,s,model):return dict(edge_id=k,anchor=k,leaves=[dict(carrier_id=i) for i in ids],supported_length_p=s,model_kind='line',model_key=[1,k,model])
  old=[group(i,[i,i+1],100-i,99) for i in (0,2,4)];current=[group(i,[i,i+1],100-i,98) for i in (0,2,4)]+[group(6,[6,7],2,7)]
  c=dict(previous_arms={},negative_pairs=[],fixed_member_ids=[])
  for a in ('greedy','joint'):
   p=root/a;js(p/'GROUPS.json',dict(groups=old));c['previous_arms'][a]=str(p)
  contexts=[dict(context_id=0,carriers=list(range(8)),evidence_carriers=list(range(8)),incident_record_ids=[])]
  result=diagnostics(c,dict(pairs=[],leaves={}),{a:({},current) for a in ('greedy','joint')},contexts)
  self.assertIn([6,7],[x['core_carriers'] for x in result['cases']])
if __name__=='__main__':unittest.main(verbosity=2)
