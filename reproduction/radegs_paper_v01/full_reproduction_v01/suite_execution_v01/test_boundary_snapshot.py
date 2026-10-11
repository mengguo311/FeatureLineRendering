import tempfile,unittest
from pathlib import Path
from boundary_snapshot import preserve,sha256
class BoundarySnapshot(unittest.TestCase):
 def test_verified_copy_and_immutable_repeat(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);src=root/'restart.json.generation-example';src.write_bytes(b'complete-model-optimizer-appearance-RNG');out=root/'evidence';d={'completed_iteration':15000,'path':str(src),'sha256':sha256(src),'provenance':{'source':'sealed'}}
   receipt=preserve(d,out,{'source':'sealed'});self.assertEqual(sha256(out/'checkpoint_15000.pt'),d['sha256']);self.assertEqual(receipt['completed_iteration'],15000)
   self.assertEqual(preserve(d,out,{'source':'sealed'}),receipt)
 def test_corrupt_checkpoint_cannot_be_sealed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);src=root/'restart.json.generation-example';src.write_bytes(b'corrupt');d={'completed_iteration':15000,'path':str(src),'sha256':'0'*64,'provenance':{'source':'sealed'}}
   with self.assertRaises(ValueError):preserve(d,root/'out',{'source':'sealed'})
   self.assertFalse((root/'out/checkpoint_15000.seal.json').exists())
 def test_wrong_iteration_or_provenance_rejected(self):
  for value,provenance in [(14500,{'source':'sealed'}),(15000,{'source':'other'})]:
   with tempfile.TemporaryDirectory() as td:
    with self.assertRaises(ValueError):preserve({'completed_iteration':value,'provenance':provenance},Path(td)/'out',{'source':'sealed'})
if __name__=='__main__':unittest.main(verbosity=2)
