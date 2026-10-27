import runtime
import tempfile,unittest,json
from pathlib import Path
import numpy as np
from motion import trajectory,save_trajectory,load_trajectory,classify_visibility,transition_counts,select_samples
from geometry import mesh_data,orbit_camera,project

class MotionTests(unittest.TestCase):
    def test_saved_camera_path_and_dolly(self):
        plan=trajectory();o=plan['orbit'];z=plan['zoom']
        self.assertEqual((len(o),len(z)),(61,21))
        self.assertEqual([o[i]['azimuth'] for i in (0,30,60)],[61.,151.,241.])
        self.assertEqual([z[i]['distance'] for i in (0,10,20)],[5.1,4.5,5.1])
        self.assertEqual(o[-1]['camera'],z[0]['camera']);self.assertEqual(z[0]['camera'],z[-1]['camera'])
        point=np.array([[.1,.1,.1]])
        uv1,_=project(point,z[0]['camera']);uv2,_=project(point,z[10]['camera'])
        self.assertGreater(np.linalg.norm(uv2-191.5),np.linalg.norm(uv1-191.5))
        with tempfile.TemporaryDirectory(dir=runtime.ROOT/'units/unit_003/tests') as d:
            p=Path(d)/'trajectory.json';save_trajectory(p,plan);self.assertEqual(load_trajectory(p),plan)
            broken=json.loads(p.read_text());broken['orbit'][20]['camera']['extrinsic'][0][3]+=.1
            p.write_text(json.dumps(broken))
            with self.assertRaises(ValueError):load_trajectory(p)

    def test_visibility_and_actual_ink_transitions(self):
        status=classify_visibility(np.array([True,True,True,True,False,True]),
            np.array([1.,1.,1.,1.,1.,.1]),np.array([1.,.5,np.inf,1.,1.,.1]),
            np.array([4,4,0,5,4,4]),np.array([16]*6,dtype=np.uint64))
        self.assertEqual(status.tolist(),['visible','depth_rejected','no_proxy_hit','label_rejected','offscreen','behind'])
        a=np.array(['visible','visible','depth_rejected','visible']);b=np.array(['visible','visible','visible','depth_rejected'])
        r=transition_counts(a,b,np.array([.3,.3,0,.3]),np.array([0,.3,.3,0]))
        self.assertEqual(r['joint_visible'],2);self.assertEqual(r['visible_ink_dropouts'],1)
        self.assertEqual(r['occlusion_entries'],1);self.assertEqual(r['occlusion_exits'],1)

    def test_arclength_sampling_does_not_bridge_a_gap(self):
        # Two segments share an ID but a gap is not sampled as surface support.
        vertices=np.array([[0.,0,0],[1,0,0],[0,1,0],[3,0,0],[4,0,0],[3,1,0]])
        mesh=mesh_data(vertices,np.array([[0,1,2],[3,4,5]]),np.array([4,4]))
        paths={4:dict(points=vertices[[[0,1],[3,4]]],face=np.array([0,1]),
            bary=np.array([[[1.,0,0],[0,1,0]]]*2),stroke_id=np.array([77,77]),visibility_mask=np.array([16,16],np.uint64))}
        sample=select_samples(mesh,paths,counts={4:1})
        self.assertEqual(len(sample['anchors']),3)
        for a in sample['anchors']:
            self.assertFalse(1<a['point'][0]<3)
            np.testing.assert_allclose(np.array(a['bary'])@mesh['tri'][a['face']],a['point'])

    def test_observer_does_not_change_raster_or_borrow_other_strokes(self):
        from render import _coverage
        v=np.array([[-1.,-1,0],[1,-1,0],[0,1,0]])
        mesh=mesh_data(v,np.array([[0,1,2]]),np.array([4]))
        points=np.array([[[-.4,-.3,0],[.4,-.3,0]],[[-.3,.3,0],[.3,.3,0]]])
        paths={4:dict(points=points,face=np.array([0,0]),stroke_id=np.array([11,22]))}
        camera=dict(width=32,height=32,fx=32.,fy=32.,cx=15.5,cy=15.5,extrinsic=[[1,0,0,0],[0,1,0,0],[0,0,1,2],[0,0,0,1]])
        styles={'4':dict(angle=0.,spacing=.1,length=.2,width=1.)}
        plain=_coverage(mesh,paths,styles,camera,2)
        watched=_coverage(mesh,paths,styles,camera,2,('4:11',))
        np.testing.assert_array_equal(plain['coverage'][4][0],watched['coverage'][4][0])
        self.assertTrue(watched['tracked']['4:11'].any())
        self.assertTrue((watched['coverage'][4][0]&~watched['tracked']['4:11']).any())

if __name__=='__main__':
    (runtime.ROOT/'units/unit_003/tests').mkdir(exist_ok=True)
    unittest.main()
