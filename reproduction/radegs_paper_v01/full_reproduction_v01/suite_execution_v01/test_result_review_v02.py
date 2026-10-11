import json,tempfile,unittest
from pathlib import Path
from result_review_v02 import validate_review
class Review(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'status.json';self.p.write_text(json.dumps({'status':'NEGATIVE_GEOMETRY_EMPTY_AFTER_AUTHOR_MASK_CONFIRMED','scene':'scan63','GPU_original_cull_verified':True,'verified_stages':['smoke','train','export','tsdf'],'official_metric':None}));import hashlib
  self.review={'decision':'CONTINUE_SAME_FROZEN_METHOD_TO_NEXT_EXPLICIT_SCENE','direct_failure_explained':True,'failure_stage':'eval','confirmed_negative_result':str(self.p),'result_sha256':hashlib.sha256(self.p.read_bytes()).hexdigest()}
 def tearDown(self):self.tmp.cleanup()
 def test_gpu_confirmed_empty_cull_allows_next_same_method(self):self.assertEqual(validate_review(self.review,'scan63')['scene'],'scan63')
 def test_scene_mismatch_rejected(self):
  with self.assertRaises(ValueError):validate_review(self.review,'scan55')
 def test_unexplained_failure_rejected(self):
  self.review['direct_failure_explained']=False
  with self.assertRaises(ValueError):validate_review(self.review,'scan63')
 def test_wrong_failure_stage_rejected(self):
  self.review['failure_stage']='tsdf'
  with self.assertRaises(ValueError):validate_review(self.review,'scan63')
 def test_mutated_status_rejected(self):
  self.p.write_text('{}')
  with self.assertRaises(ValueError):validate_review(self.review,'scan63')
if __name__=='__main__':unittest.main(verbosity=2)
