"""Real saved-model sessions must preserve edits and drafts across scene switches."""
import runtime
from runtime import OUTPUT_ROOT,sha
import unittest,json,shutil
import numpy as np
from scene_catalog import SceneCatalog
from screen_selection import visible_faces
from geometry import orbit_camera

class CatalogTest(unittest.TestCase):
 def test_real_scenes_draft_edit_and_stale_request(self):
  u=OUTPUT_ROOT/'units/unit_008';out=u/'tests/catalog'
  if out.exists():shutil.rmtree(out)
  hub=SceneCatalog(u/'CATALOG.json',out)
  self.assertEqual(hub.record['scene'],'lego')
  original=hub.asset; hashes={p.name:sha(p) for p in original.iterdir() if p.is_file()}
  request=dict(revision=hub.record['revision'],source_region=3,mode='visible',rectangle=[240,80,380,180],operation='replace')
  hub.preview_selection(request)
  ids=hub.active.draft.face_ids.copy();self.assertGreater(len(ids),0)
  token=hub.active.pending['token'];old_record=hub.record.copy()
  hub.switch('chair');self.assertEqual(hub.record['scene'],'chair')
  with self.assertRaisesRegex(ValueError,'scene changed'):hub.check_scene({'scene':'lego'})
  with self.assertRaises(ValueError):hub.switch('../lego')
  with self.assertRaises(ValueError):hub.switch('ficus')
  hub.switch('lego');np.testing.assert_array_equal(ids,hub.active.draft.face_ids)
  self.assertEqual(hub.active.pending['token'],token)
  self.assertEqual(hub.asset,original)
  hub.draft_action(dict(revision=hub.record['revision'],action='clear'))
  meta=json.loads((original/'asset.json').read_text());style=meta['styles']['2']|{'width':1.7}
  hub.apply(dict(region=2,**style,**hub.record['camera']))
  edited=hub.asset;self.assertNotEqual(edited,original)
  for s in ('drums','chair','lego'):hub.switch(s)
  self.assertEqual(hub.asset,edited);self.assertEqual(hub.record['styles']['2']['width'],1.7)
  self.assertEqual(hub.record['images']['image'].split('/')[2],'lego')
  self.assertEqual(hashes,{p.name:sha(p) for p in original.iterdir() if p.is_file()})
  hub.undo();self.assertEqual(hub.asset,original)

if __name__=='__main__':unittest.main()
