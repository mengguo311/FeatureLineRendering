"""Real model multi-region authoring, cold restoration and stale-support rejection."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil,tempfile,unittest
import numpy as np
from demo import load_asset,edit
from unit023_run import U,PREV,author,second,protocol

class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp=Path(tempfile.mkdtemp(prefix='dependencies_',dir=U));self.base=self.temp/'seat';author(self.base)
    def tearDown(self):shutil.rmtree(self.temp)
    def test_independent_creation_cold_restore(self):
        from region_restore import restore_region
        from asset_archive import export_archive,unpack_archive
        second(self.base,self.temp/'two')
        edit(self.temp/'two',self.temp/'back_edit',5,dict(ink_strength=.45))
        edit(self.temp/'back_edit',self.temp/'edited',4,dict(angle=65.,cross_enabled=True,width=1.5))
        payload=export_archive(self.temp/'edited',protocol()['viewer_camera'],4)
        unpack_archive(payload,self.temp/'imported',{'chair':protocol()['original']['sha256']})
        restore_region(self.temp/'imported',self.temp/'restored',4)
        _,_,meta=load_asset(self.temp/'restored')
        self.assertEqual(sha(self.base/'region_4.npz'),sha(self.temp/'restored/region_4.npz'))
        self.assertEqual(meta['styles']['5']['ink_strength'],.45)
        for f in (self.temp/'imported').iterdir():
            if f.name not in ('asset.json','region_4.npz'):self.assertEqual(sha(f),sha(self.temp/'restored'/f.name))
        # Restoration also works in the other direction, without undoing the
        # already restored seat. This is separate from session-wide Undo.
        restore_region(self.temp/'restored',self.temp/'back_restored',5)
        _,_,both=load_asset(self.temp/'back_restored')
        original=json.loads((self.temp/'two/asset.json').read_text())
        self.assertEqual(both['styles']['5'],original['styles']['5'])
        self.assertEqual(both['styles']['4'],meta['styles']['4'])
        self.assertEqual(sha(self.temp/'back_restored/region_4.npz'),sha(self.temp/'restored/region_4.npz'))
        self.assertEqual(sha(self.temp/'back_restored/region_5.npz'),sha(self.temp/'two/region_5.npz'))
    def test_shared_support_and_owner_split_rejected(self):
        from region_restore import restore_region,restore_status
        from region_tools import author_face_selection
        mesh,paths,_=load_asset(self.base)
        for source in (2,4):
            folder=self.temp/f'split{source}'
            faces=np.unique(paths[source]['face'])[::2]
            author_face_selection(self.base,folder,faces,source,'Shared support split',{})
            m,_,meta=load_asset(folder)
            self.assertFalse(restore_status(meta,4,m)['available'])
            self.assertTrue(restore_status(meta,5,m)['available'])
            with self.assertRaisesRegex(ValueError,'boundaries changed'):restore_region(folder,self.temp/f'refused{source}',4)
            self.assertFalse((self.temp/f'refused{source}').exists())
    def test_changed_support_geometry_rejected_even_with_valid_current_paths(self):
        from region_restore import restore_region,restore_status
        mesh,paths,meta=load_asset(self.base)
        vertex=int(mesh['faces'][paths[4]['face'][0]][0]);mesh['vertices'][vertex,0]+=1e-4
        np.savez_compressed(self.base/'mesh.npz',vertices=mesh['vertices'],faces=mesh['faces'],face_regions=mesh['regions'])
        for r,data in paths.items():
            data['points']=np.einsum('nij,njk->nik',data['bary'],mesh['vertices'][mesh['faces']][data['face']])
            np.savez_compressed(self.base/f'region_{r}.npz',**data)
        meta['mesh_sha256']=sha(self.base/'mesh.npz');js(self.base/'asset.json',meta)
        m,_,a=load_asset(self.base);self.assertFalse(restore_status(a,4,m)['available'])
        with self.assertRaises(ValueError):restore_region(self.base,self.temp/'refused',4)
        self.assertFalse((self.temp/'refused').exists())
    def test_legacy_snapshots_remain_conservative(self):
        from region_restore import restore_region,restore_status
        old=PREV/'assets/edited';restore_region(old,self.temp/'legacy',4)
        self.assertEqual(sha(self.temp/'legacy/region_4.npz'),sha(PREV/'assets/authored/region_4.npz'))
        second(old,self.temp/'legacy_split');m,_,a=load_asset(self.temp/'legacy_split')
        self.assertFalse(restore_status(a,4,m)['available'])
        with self.assertRaises(ValueError):restore_region(self.temp/'legacy_split',self.temp/'refused',4)
    def test_dependency_metadata_corruption_rejected(self):
        meta=json.loads((self.base/'asset.json').read_text())
        meta['region_origins']['4']['dependency']['masks']=[1<<3]
        js(self.base/'asset.json',meta)
        with self.assertRaisesRegex(ValueError,'snapshot support'):load_asset(self.base)

if __name__=='__main__':unittest.main()
