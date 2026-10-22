"""Real-model example identity and session isolation, without old output writes."""
import runtime
from runtime import OUTPUT_ROOT,sha,js
from pathlib import Path
import argparse,json,unittest
from scene_catalog import SceneCatalog

class ExamplesTest(unittest.TestCase):
    def test_saved_real_examples_are_independent(self):
        hub=SceneCatalog(CATALOG,OUT/'sessions')
        default=hub.asset
        self.assertEqual(hub.record['example'],'default')
        hub.switch_example('lego_platform_ink')
        original=hub.asset;original_record=hub.record
        self.assertEqual(hub.record['styles']['1']['ink_strength'],.4)
        style=hub.record['styles']['1']|{'ink_strength':.6}
        hub.apply(dict(region=1,**style,**hub.record['camera']))
        edited=hub.asset;image=hub.record['images']['image']
        self.assertNotEqual(original,edited)
        self.assertTrue(hub.record['can_undo'])
        for f in original.iterdir():
            if f.is_file() and f.name!='asset.json':self.assertEqual(sha(f),sha(edited/f.name))
        for key in ('2','3','4'):self.assertEqual(original_record['styles'][key],hub.record['styles'][key])
        hub.switch_example('lego_bucket_cross')
        self.assertFalse(hub.record['can_undo'])
        self.assertEqual(hub.record['styles']['1'].get('ink_strength',.8),.8)
        with self.assertRaisesRegex(ValueError,'example changed'):
            hub.check_scene(dict(scene='lego',example='lego_platform_ink'))
        with self.assertRaises(ValueError):hub.switch_example('../lego')
        hub.switch_example('lego_platform_ink')
        self.assertEqual(hub.asset,edited);self.assertEqual(hub.record['images']['image'],image)
        hub.switch('chair')
        with self.assertRaises(ValueError):hub.switch_example('lego_platform_ink')
        hub.switch('lego');self.assertEqual(hub.asset,edited)
        hub.undo();self.assertEqual(hub.asset,original)
        hub.switch_example('default');self.assertEqual(hub.asset,default)
        self.assertFalse(hub.record['can_undo'])
        js(OUT/'ISOLATION.json',dict(status='PASS',real_scene='lego',all_binary_files_exact=True,
            cross_example_stale_rejected=True,independent_undo=True,model_return_restores_example=True))

    def test_legacy_catalog_default_and_invalid_scene(self):
        cat=json.loads(CATALOG.read_text());cat.pop('examples')
        for entry in cat['scenes'].values():entry['asset']=str(CATALOG.parent/entry['asset'])
        legacy=OUT/'legacy.json';js(legacy,cat)
        hub=SceneCatalog(legacy,OUT/'legacy_session')
        hub.check_scene(dict(scene='lego'))
        self.assertEqual(hub.record['example'],'default')
        with self.assertRaises(ValueError):hub.switch_example('lego_platform_ink')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalog',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    CATALOG=a.catalog.resolve();OUT=a.output.resolve();OUT.mkdir(parents=True)
    unittest.main(argv=['test_example_catalog'],verbosity=2)
