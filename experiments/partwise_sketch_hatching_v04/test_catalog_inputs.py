"""Catalog errors must fail before an output or a rendered scene is created."""
import runtime
from runtime import OUTPUT_ROOT,js
from pathlib import Path
import unittest,json
from scene_catalog import SceneCatalog

class CatalogInputs(unittest.TestCase):
 def test_missing_and_mislabeled_model(self):
  u=OUTPUT_ROOT/'units/unit_008';folder=u/'tests/invalid_catalogs';folder.mkdir(parents=True,exist_ok=True)
  cases=[dict(schema='partwise_scene_catalog_v1',scenes={'lego':dict(asset='missing')}),
         dict(schema='partwise_scene_catalog_v1',scenes={'chair':dict(asset=str(u/'catalog_assets/lego'))}),
         dict(schema='partwise_scene_catalog_v1',scenes={'../lego':dict(asset=str(u/'catalog_assets/lego'))})]
  for i,data in enumerate(cases):
   path=folder/f'case{i}.json';out=folder/f'output{i}';js(path,data)
   with self.assertRaises(ValueError):SceneCatalog(path,out)
   self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
