import runtime
from runtime import OUTPUT_ROOT, sha
from pathlib import Path
import json, tempfile, unittest
import numpy as np
from demo import load_asset, edit
from geometry import mesh_data, ray_surface
from screen_selection import visible_faces, pick_region
from region_tools import author_face_selection

UNIT=OUTPUT_ROOT/'units/unit_006'
class ScreenSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads((UNIT/'PROTOCOL.json').read_text())
        cls.asset=Path(cls.p['source_asset'])
        cls.mesh,cls.paths,cls.meta=load_asset(cls.asset)
        cls.s=cls.p['selection']

    def test_real_visible_faces_and_invalid_coordinates(self):
        ids,summary=visible_faces(self.mesh,self.s['camera'],self.s['rectangle'],3)
        _,face,_,_=ray_surface(self.mesh,self.s['camera'],2)
        x0,y0,x1,y1=self.s['rectangle']
        hit=np.unique(face[y0*2:y1*2,x0*2:x1*2]);hit=hit[hit>=0]
        expected=hit[self.mesh['regions'][hit]==3]
        np.testing.assert_array_equal(ids,expected)
        self.assertGreater(len(ids),10)
        self.assertLess(len(ids),int((self.mesh['regions']==3).sum()))
        self.assertEqual(summary['hidden_faces_selected'],0)
        for rect in ([0,0,0,1],[-1,0,10,10],[0,0,513,1],[0,0,float('nan'),10],[0,0,4,4]):
            with self.assertRaises(ValueError):visible_faces(self.mesh,self.s['camera'],rect,3)
        with self.assertRaises(ValueError):pick_region(self.mesh,self.s['camera'],[0,0])

    def test_known_occluded_face_is_not_selected(self):
        vertices=np.array([[-1,-1,2],[1,-1,2],[0,1,2],[-1,-1,3],[1,-1,3],[0,1,3],[8,8,2],[9,8,2],[8,9,2]],float)
        mesh=mesh_data(vertices,np.arange(9).reshape(3,3),np.ones(3,int))
        c=dict(extrinsic=np.eye(4).tolist(),width=32,height=32,fx=20,fy=20,cx=15.5,cy=15.5)
        ids,_=visible_faces(mesh,c,[0,0,32,32],1)
        np.testing.assert_array_equal(ids,[0])
        pick=pick_region(mesh,c,[16,16]);self.assertEqual(pick['face_id'],0)

    def test_real_face_save_edit_reload_preserves_non_target(self):
        ids,_=visible_faces(self.mesh,self.s['camera'],self.s['rectangle'],3)
        root=UNIT/'test_work';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temp:
            a=Path(temp)/'authored';b=Path(temp)/'edited'
            author_face_selection(self.asset,a,ids,3,'Visible patch',dict(operation='manual_visible_rectangle',camera=self.s['camera'],rectangle=self.s['rectangle']))
            mesh,paths,meta=load_asset(a)
            for k in ('vertices','faces'):np.testing.assert_array_equal(mesh[k],self.mesh[k])
            np.testing.assert_array_equal(np.flatnonzero(mesh['regions']==4),ids)
            keep=~np.isin(self.paths[3]['face'],ids)
            for k in self.paths[3]:np.testing.assert_array_equal(paths[3][k],self.paths[3][k][keep])
            for r in (1,2):self.assertEqual(sha(a/f'region_{r}.npz'),sha(self.asset/f'region_{r}.npz'))
            edit(a,b,4,dict(angle=35.));load_asset(b)
            for r in (1,2,3):self.assertEqual(sha(a/f'region_{r}.npz'),sha(b/f'region_{r}.npz'))
            self.assertNotEqual(sha(a/'region_4.npz'),sha(b/'region_4.npz'))
            for bad in ([],[-1],[len(mesh['faces'])],[.5]):
                with self.assertRaises(ValueError):author_face_selection(self.asset,Path(temp)/'bad',bad,3,'Bad',{})

    def test_inherited_world_box_still_saves_the_same_lego_paths(self):
        from region_tools import author_region
        root=UNIT/'test_work';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temp:
            a=Path(temp)/'box'
            author_region(OUTPUT_ROOT/'units/unit_003/assets/baseline',a,
                          [-.70,-1.20,.45,.70,-.35,1.10],3,'Front bucket area')
            load_asset(a)
            for r in (1,2,3,4):
                self.assertEqual(sha(a/f'region_{r}.npz'),sha(OUTPUT_ROOT/f'units/unit_004/assets/baseline/region_{r}.npz'))

if __name__=='__main__':unittest.main(verbosity=2)
