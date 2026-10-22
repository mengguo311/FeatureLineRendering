"""Real Chair creation snapshot, cold archive restoration and rejection behavior."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil,tempfile,unittest
import numpy as np
from demo import load_asset,edit
from unit022_run import U,ASSET,author,protocol

class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=Path(tempfile.mkdtemp(prefix='restore_',dir=U));self.base=self.temp/'authored';author(self.base)
    def tearDown(self):shutil.rmtree(self.temp)
    def test_creation_saved_exact_original(self):
        meta=json.loads((self.base/'asset.json').read_text())
        self.assertIn('region_origins',meta,'Authoring must persist original strokes and style for later cold restoration')
        entry=meta['region_origins']['4']
        self.assertEqual(sha(self.base/entry['file']),sha(self.base/'region_4.npz'))
        self.assertEqual(entry['style'],meta['styles']['4'])
    def test_cold_archive_restore_is_local_and_exact(self):
        from region_restore import restore_region
        from asset_archive import export_archive,unpack_archive
        edit(self.base,self.temp/'edited',4,dict(angle=65.,width=1.5,cross_enabled=True))
        edit(self.temp/'edited',self.temp/'other',1,dict(ink_strength=.35))
        payload=export_archive(self.temp/'other',protocol()['viewer_camera'],4)
        unpack_archive(payload,self.temp/'imported',{'chair':protocol()['original']['sha256']})
        restore_region(self.temp/'imported',self.temp/'restored',4)
        _,_,meta=load_asset(self.temp/'restored');original=json.loads((self.base/'asset.json').read_text())
        self.assertEqual(meta['styles']['4'],original['styles']['4'])
        self.assertEqual(meta['statistics']['4'],original['statistics']['4'])
        self.assertEqual(sha(self.temp/'restored/region_4.npz'),sha(self.base/'region_4.npz'))
        self.assertEqual(meta['styles']['1']['ink_strength'],.35)
        for f in (self.temp/'imported').iterdir():
            if f.name not in ('asset.json','region_4.npz'):self.assertEqual(sha(f),sha(self.temp/'restored'/f.name))
    def test_missing_stale_corrupt_rejected_without_output(self):
        from region_restore import restore_region,restore_status
        with self.assertRaisesRegex(ValueError,'creation snapshot'):restore_region(ASSET,self.temp/'missing',2)
        self.assertFalse((self.temp/'missing').exists())
        from region_tools import author_face_selection
        stale=self.temp/'stale';_,paths,_=load_asset(self.base)
        faces=np.unique(paths[4]['face'])[::2]
        author_face_selection(self.base,stale,faces,4,'Subregion',{})
        _,_,m=load_asset(stale)
        self.assertFalse(restore_status(m,4)['available'])
        self.assertTrue(restore_status(m,5)['available'])
        with self.assertRaisesRegex(ValueError,'boundaries changed'):restore_region(stale,self.temp/'stale_out',4)
        self.assertFalse((self.temp/'stale_out').exists())
        m=json.loads((self.base/'asset.json').read_text());file=self.base/m['region_origins']['4']['file'];file.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'snapshot checksum'):load_asset(self.base)
        self.assertFalse((self.temp/'corrupt_out').exists())
    def test_snapshot_archive_missing_or_path_escape_rejected(self):
        from asset_archive import export_archive,unpack_archive
        import io,zipfile
        payload=export_archive(self.base,protocol()['viewer_camera'],4)
        result=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(payload)) as old,zipfile.ZipFile(result,'w') as new:
            for name in old.namelist():
                if name not in ('origin_4.npz','ASSET_MANIFEST.json'):new.writestr(name,old.read(name))
        with self.assertRaisesRegex(ValueError,'missing required'):unpack_archive(result.getvalue(),self.temp/'missing_import',{'chair':protocol()['original']['sha256']})
        self.assertFalse((self.temp/'missing_import').exists())
        m=json.loads((self.base/'asset.json').read_text());entry=m['region_origins']['4']
        entry['file']='../region_4.npz';js(self.base/'asset.json',m)
        with self.assertRaises(ValueError):load_asset(self.base)
        payload=export_archive(self.base,protocol()['viewer_camera'],4)
        with self.assertRaises(ValueError):unpack_archive(payload,self.temp/'bad_import',{'chair':protocol()['original']['sha256']})
        self.assertFalse((self.temp/'bad_import').exists())
    def test_restore_original_cross_layers_and_nondefault_style(self):
        from region_restore import restore_region
        from region_tools import author_face_selection
        from hatching import layer_ids
        with np.load(self.base/'selection_4.npz') as z:faces=z['face_ids']
        edit(ASSET,self.temp/'parent_cross',2,dict(cross_enabled=True,width=1.3,ink_strength=.55))
        author_face_selection(self.temp/'parent_cross',self.temp/'cross_origin',faces,2,'Cross patch',{})
        _,before,meta=load_asset(self.temp/'cross_origin')
        self.assertTrue((layer_ids(before[4])==1).any())
        edit(self.temp/'cross_origin',self.temp/'cross_edited',4,dict(angle=65.,cross_enabled=False,spacing=.06))
        restore_region(self.temp/'cross_edited',self.temp/'cross_restored',4)
        _,after,restored=load_asset(self.temp/'cross_restored')
        self.assertEqual(meta['styles']['4'],restored['styles']['4'])
        self.assertEqual(sha(self.temp/'cross_origin/region_4.npz'),sha(self.temp/'cross_restored/region_4.npz'))

if __name__=='__main__':unittest.main()
