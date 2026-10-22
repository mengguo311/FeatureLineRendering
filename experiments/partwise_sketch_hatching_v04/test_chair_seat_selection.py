"""Real Chair recipe, exact non-target preservation and cold editing contracts."""
import runtime
from runtime import js,sha,now
import json,unittest
import numpy as np
from unit020_run import U,ASSET
from demo import load_asset
from selection_draft import replay_recipe
from screen_selection import visible_faces

class ChairSeatTests(unittest.TestCase):
    def test_saved_real_selection_and_unselected_paths(self):
        m,s,meta=load_asset(ASSET);a,p,am=load_asset(U/'assets/authored')
        recipe=json.loads((U/'SELECTION_RECIPE.json').read_text());d=replay_recipe(m,meta['mesh_sha256'],recipe)
        hits=[visible_faces(m,x['camera'],x['rectangle'],2)[0] for x in recipe['steps']]
        np.testing.assert_array_equal(d.face_ids,np.union1d(*hits))
        self.assertGreater(len(np.setdiff1d(hits[1],hits[0])),0)
        np.testing.assert_array_equal(m['vertices'],a['vertices']);np.testing.assert_array_equal(m['faces'],a['faces'])
        np.testing.assert_array_equal(np.flatnonzero(a['regions']==4),d.face_ids)
        keep=~np.isin(s[2]['face'],d.face_ids)
        for k in s[2]:np.testing.assert_array_equal(p[2][k],s[2][k][keep])
        for r in (1,3):self.assertEqual(sha(ASSET/f'region_{r}.npz'),sha(U/f'assets/authored/region_{r}.npz'))
        self.assertEqual(am['styles']['4']['angle'],95.)
        self.assertEqual(am['styles']['4']['plane'],'xy')
        self.assertGreater(len(p[4]['points']),0)
        with self.assertRaises(ValueError):replay_recipe(m,meta['mesh_sha256'],dict(recipe,mesh_sha256='wrong'))

    def test_cold_loaded_target_only_angle_revision(self):
        a,p,am=load_asset(U/'assets/authored');b,q,bm=load_asset(U/'assets/edited')
        self.assertEqual(sha(U/'assets/authored/mesh.npz'),sha(U/'assets/edited/mesh.npz'))
        for r in (1,2,3):
            self.assertEqual(sha(U/f'assets/authored/region_{r}.npz'),sha(U/f'assets/edited/region_{r}.npz'))
            self.assertEqual(am['styles'][str(r)],bm['styles'][str(r)])
        self.assertEqual(bm['styles']['4'],dict(am['styles']['4'],angle=65.))
        self.assertNotEqual(sha(U/'assets/authored/region_4.npz'),sha(U/'assets/edited/region_4.npz'))
        for r,paths in q.items():
            self.assertTrue((b['regions'][paths['face']]==r).all())
            xyz=np.einsum('nij,njk->nik',paths['bary'],b['tri'][paths['face']])
            self.assertLess(float(np.max(np.abs(xyz-paths['points']))),1e-9)
        result=dict(utc=now(),tests=2,real_old_model='chair',geometry_exact=True,selected_faces=int((b['regions']==4).sum()),
            non_target_paths_and_styles_exact=True,unselected_original_source_segments_exact=True,
            target_path_stats={arm:dict(segments=len(z[4]['points']),paths=len(np.unique(z[4]['stroke_id'])),length_world=float(np.linalg.norm(np.diff(z[4]['points'],axis=1),axis=2).sum())) for arm,z in [('authored',p),('edited',q)]},
            scope='Cold asset/recipe implementation contracts, not independent surface truth')
        js(U/'metrics/REAL_ASSET_TEST.json',result)

if __name__=='__main__':unittest.main(verbosity=2)
