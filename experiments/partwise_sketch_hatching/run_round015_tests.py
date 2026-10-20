"""Serial test receipts, with an intentional broken-metric RED control."""
import round015_common as c
import json,subprocess,sys
S='experiments/partwise_sketch_hatching/'
jobs=[('RED_METRICS',[S+'test_planar_temporal_metrics.py','--broken'],1),('GREEN_METRICS',[S+'test_planar_temporal_metrics.py'],0)]
for name in ['test_mesh_attachment','test_patch_attachment','test_visibility_primitive','test_coverage_fixture','test_temporal_audit','test_stage_attribution','test_centered_coverage','test_area_coverage','test_physical_area_reference','test_planar_fragments','test_exact_triangle_set']:
    jobs.append((name.upper(),[S+name+'.py'],0))
jobs.append(('CANDIDATE_FRAGMENTS',['-c',"import sys;sys.path.insert(0,'experiments/partwise_sketch_hatching');import round015_common;import test_planar_fragments as t;import planar_fragments_exact as n;import unittest;t.new=n;unittest.main(module=t,verbosity=2)"],0))
records=[]
for name,args,expected in jobs:
    c.resources();rc=subprocess.run([sys.executable,S+'round015_receipt.py',name]+args).returncode
    records.append({'name':name,'returncode':rc,'expected':expected,'passed':rc==expected})
    c.write(c.R/'TESTS.json',{'complete':len(records)==len(jobs),'passed':all(r['passed'] for r in records),'executions':records})
    assert rc==expected,name
print(json.dumps({'complete':True,'groups':len(jobs)}))
