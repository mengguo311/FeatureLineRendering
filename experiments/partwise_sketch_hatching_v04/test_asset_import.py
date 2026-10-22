"""Real saved-model import, isolation and damaged-archive rejection."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse,io,json,unittest,zipfile
import numpy as np
from scene_catalog import SceneCatalog

def repack(files):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    return output.getvalue()

class ImportsTest(unittest.TestCase):
    def test_01_actual_legacy_import_and_independent_edit(self):
        hub=SceneCatalog(CATALOG,OUT/'sessions')
        initial=hub.record;default=hub.asset
        hub.import_archive(PAYLOAD,'saved-lego.zip')
        imported=hub.record;original=hub.asset;identity=imported['example']
        self.assertTrue(identity.startswith('import_'))
        self.assertEqual(imported['styles']['1']['ink_strength'],.6)
        self.assertFalse(imported['can_undo']);self.assertIsNone(imported['draft'])
        self.assertEqual(imported['import_receipt']['integrity'],'legacy_anchor_validation')
        hub.apply(dict(region=1,**(imported['styles']['1']|{'ink_strength':.35}),**imported['camera']))
        edited=hub.asset
        for f in original.iterdir():
            if f.is_file() and f.name!='asset.json':self.assertEqual(sha(f),sha(edited/f.name))
        hub.switch_example('default');self.assertEqual(hub.asset,default);self.assertFalse(hub.record['can_undo'])
        hub.switch_example(identity);self.assertEqual(hub.asset,edited)
        hub.undo();self.assertEqual(hub.asset,original)
        from asset_archive import export_archive
        bundle=export_archive(hub.asset,hub.record['camera'],hub.selected_region,hub.example_metadata)
        hub.import_archive(bundle,'roundtrip.zip')
        self.assertNotEqual(identity,hub.record['example'])
        self.assertEqual(hub.record['import_receipt']['integrity'],'manifest_sha256_and_anchor_validation')
        self.assertEqual(hub.record['styles'],imported['styles'])
        self.assertEqual(hub.record['camera'],imported['camera'])
        self.assertFalse(hub.record['can_undo'])
        js(OUT/'ISOLATION.json',dict(status='PASS',legacy_accepted=True,manifest_roundtrip=True,
            separate_same_model_sessions=True,non_target_bytes_exact=True,camera_styles_exact=True))

    def test_02_invalid_upload_keeps_active_state(self):
        from asset_archive import export_archive
        hub=SceneCatalog(CATALOG,OUT/'rejections')
        before=hub.record;entries=set(hub.examples)
        with zipfile.ZipFile(io.BytesIO(PAYLOAD)) as z:files={n:z.read(n) for n in z.namelist()}
        def changed_meta(**changes):
            return files|{'asset.json':json.dumps(json.loads(files['asset.json'])|changes).encode()}
        damaged=files|{'mesh.npz':b'invalid mesh'}
        cases={'not_zip':b'bad zip','traversal':repack(files|{'../escape.json':b'{}'}),
               'mesh_checksum':repack(damaged),'unknown_model':repack(changed_meta(scene='unlisted')),
               'wrong_model_sha':repack(changed_meta(original={'sha256':'0'*64})),
               'invalid_camera':repack(changed_meta(viewer_camera={'azimuth':0,'elevation':30,'distance':float('nan')})),
               'missing_paths':repack({n:d for n,d in files.items() if n!='region_1.npz'}),
               'metadata_path_escape':repack(changed_meta(region_history=[{'face_ids_file':'../x','face_ids_sha256':'0'*64}]))}
        with np.load(io.BytesIO(files['region_1.npz'])) as z:arrays={k:z[k] for k in z.files}
        for key,modify in [('nonfinite_bary',lambda a:a['bary'].__setitem__((0,0,0),np.nan)),
                           ('bad_face',lambda a:a['face'].__setitem__(0,2**30))]:
            a={k:v.copy() for k,v in arrays.items()};modify(a);buf=io.BytesIO();np.savez_compressed(buf,**a)
            cases[key]=repack(files|{'region_1.npz':buf.getvalue()})
        good=export_archive(hub.asset,hub.record['camera'],hub.selected_region,hub.example_metadata)
        with zipfile.ZipFile(io.BytesIO(good)) as z:f={n:z.read(n) for n in z.namelist()}
        f['region_1.npz']=f['region_1.npz']+b'corrupt'
        cases['path_checksum']=repack(f)
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:
            z.writestr('asset.json',b'{}');z.writestr('asset.json',b'{}')
        cases['duplicate_members']=buf.getvalue()
        for label,payload in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ValueError):hub.import_archive(payload,label+'.zip')
                self.assertEqual(hub.record,before);self.assertEqual(set(hub.examples),entries)
        js(OUT/'REJECTIONS.json',dict(status='PASS',cases=list(cases),active_state_unchanged=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalog',required=True,type=Path);p.add_argument('--legacy-zip',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    CATALOG=a.catalog.resolve();PAYLOAD=a.legacy_zip.read_bytes();OUT=a.output.resolve();OUT.mkdir(parents=True)
    unittest.main(argv=['test_asset_import'],verbosity=2)
