import unittest,json,tempfile,hashlib,sys
from pathlib import Path
from pipeline_scope import validate_scope
from native_provenance import provenance_for
class TestRevision(unittest.TestCase):
 def test_prior_native_cannot_enter_new_route(self):
  c=json.loads(Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01/scan55/state/runner_config.json').read_text())
  with self.assertRaises(ValueError):validate_scope(c)
 def test_current_native_and_provenance_required(self):
  c=json.loads(Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01/scan55/state/runner_config.json').read_text());c['numerical_revision']='scan55_eigen_fallback_v01';c['inputs']['native']='5f98bba44b97881767bba81dab21d9bcf83565410dce8f7052a0a059e7d5fce1';c['native_build_manifest']='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01/scan55_failure_v01/repair_v01/build/MANIFEST.json';validate_scope(c)
  info=provenance_for(c);self.assertEqual(info['native_sha256'],c['inputs']['native']);self.assertEqual(info['source_manifest_path'],c['native_build_manifest'])
  c['inputs']['native']='incorrect'
  with self.assertRaises(ValueError):provenance_for(c)
if __name__=='__main__':unittest.main()
