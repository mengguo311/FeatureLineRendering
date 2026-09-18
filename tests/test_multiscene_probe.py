"""Local evidence, native visibility and gate falsification fixtures."""
import copy
import json
from pathlib import Path
import unittest
import numpy as np

from src.foundation import project_jacobian,native_render
from test_multiscene import CFG,asset_fixture


class ProbeTests(unittest.TestCase):
    def test_full_box_search_retains_separated_modes_and_plateaus(self):
        from src.multiscene_probe import ray_profile
        camera=dict(K=[[100,7,20],[0,90,30],[0,0,1]],w2c=np.eye(4).tolist())
        box=[[-1,-1,1],[1,1,5]]
        def evaluate(points):return np.minimum((points[:,2]-2)**2,(points[:,2]-4)**2)
        result=ray_profile(camera,[20,30],box,.02,evaluate,CFG)
        depths=np.array([m['depth'] for m in result['modes']])
        self.assertTrue(np.any(abs(depths-2)<.01));self.assertTrue(np.any(abs(depths-4)<.01))
        self.assertLessEqual(result['depths'][0],1);self.assertGreaterEqual(result['depths'][-1],5)
        self.assertTrue(result['resolution_ok'])
        plateau=ray_profile(camera,[20,30],box,.02,lambda p:np.zeros(len(p)),CFG)
        self.assertEqual(len(plateau['modes']),1)
        self.assertGreater(plateau['modes'][0]['plateau'][1]-plateau['modes'][0]['plateau'][0],3.9)
        coarse=ray_profile(camera,[20,30],box,.0001,evaluate,CFG)
        self.assertFalse(coarse['resolution_ok'])

    def test_image_hessian_is_axial_and_full_K_covariant(self):
        from src.multiscene_probe import image_hessian,axial_angle
        p=np.array([[.2,.1,3.]])
        cameras=[]
        for shift in [[0,0,0],[1,0,0],[0,1,0]]:
            w=np.eye(4);w[:3,3]=shift;cameras.append(w)
        K=np.array([[120.,9,29],[0,80,31],[0,0,1]])
        t=np.array([1.,2.,.3]);t/=np.linalg.norm(t)
        J=np.stack([project_jacobian(p,K,w)[2][0] for w in cameras])
        tangent=J@t;normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1)
        normal/=np.linalg.norm(normal,axis=1,keepdims=True)
        H,eigenvalues,axis=image_hessian(J,normal)
        self.assertLess(axial_angle(axis,t),1e-5)
        H2,_,axis2=image_hessian(J,-normal);np.testing.assert_allclose(H,H2)
        self.assertLess(axial_angle(axis2,-t),1e-5)
        angle=.7;Q=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
        H3,_,axis3=image_hessian(J@Q.T,normal)
        np.testing.assert_allclose(H3,Q@H@Q.T,atol=1e-10)
        self.assertLess(axial_angle(axis3,Q@t),1e-5)
        self.assertGreater(eigenvalues[1],0)

    def test_canny_tangents_queries_and_shift_control_are_frozen(self):
        from src.multiscene_probe import edge_field,sample_queries,shift_field
        rgb=np.ones((400,400,3));rgb[:,200:]=0
        field=edge_field(rgb,CFG);self.assertGreater(field['edge'].sum(),300)
        y,x=np.nonzero(field['edge']);axes=field['tangent'][y,x]
        self.assertGreater(np.nanmedian(abs(axes[:,1])),.99)
        q=sample_queries(field,1,CFG);q2=sample_queries(field,1,CFG)
        self.assertEqual(q,q2);self.assertLessEqual(len(q),64)
        self.assertEqual(len({(p['pixel'][0]//8,p['pixel'][1]//8) for p in q}),len(q))
        shifted=shift_field(field,0,CFG)
        self.assertEqual(shifted['edge'].sum(),field['edge'].sum())
        self.assertFalse(shifted['domain'][:32].any());self.assertFalse(shifted['domain'][:,:32].any())
        self.assertFalse(np.array_equal(shifted['edge'],field['edge']))

    def test_native_depth_layers_preserve_transmittance_and_disjoint_support(self):
        from src.multiscene_probe import NativeLayers
        a=asset_fixture();a['mu'][:]=[[0,0,2],[0,0,2.1],[0,0,4],[0,0,4.1]]
        a['opacity'][:]=.6;a['scale'][:]=[.2,.2,.1]
        K=np.array([[50.,0,31.5],[0,50.,31.5],[0,0,1]])
        state=native_render(a,K,np.eye(4),64,64,1)
        layers=NativeLayers(state,64,64)
        full=layers.events(32,32)
        self.assertEqual(len(full['depth']),4)
        self.assertLess(abs(full['transmittance'][-1]-state['final_T'][32,32]),1e-6)
        front,support=layers.query(np.array([[32,32]]*4),np.array([1.,2.,3.,5.]),.02)
        self.assertAlmostEqual(front[0],1.)
        self.assertTrue(support[1]);self.assertFalse(support[2]);self.assertFalse(support[3])
        self.assertLess(front[-1],.1)

    def test_matching_is_bidirectional_sign_invariant_and_empty_is_not_success(self):
        from src.multiscene_probe import match_outputs
        base=[dict(query=i,point=[i*3.,0,0],axis=[1,0,0]) for i in range(10)]
        other=[dict(query=i,point=[i*3.+.2,0,0],axis=[-1,0,0]) for i in reversed(range(10))]
        result=match_outputs(base,other,1.,CFG)
        self.assertTrue(result['passed']);self.assertAlmostEqual(result['median_distance_delta'],.2)
        self.assertFalse(match_outputs(base,other[:5],1.,CFG)['passed'])
        self.assertFalse(match_outputs([],[],1.,CFG)['passed'])
        other[0]['query']=999
        self.assertEqual(match_outputs(base,other,1.,CFG)['matches'],9)

    def test_inference_rejects_global_multimodality_despite_local_hessian(self):
        from src.multiscene_probe import infer_queries
        cameras={};fields={};K=np.array([[200.,0,200],[0,200,200],[0,0,1]])
        y,x=np.indices((400,400))
        for i,cy in enumerate([0.,1.,-1.,.5]):
            w=np.eye(4);w[1,3]=-cy;cameras[i]=dict(index=i,K=K.tolist(),w2c=w.tolist())
            edge_y=200-200*cy/3
            nearest=np.stack([x,np.full_like(y,edge_y,dtype=float)],axis=2)
            tangent=np.zeros((400,400,2));tangent[:,:,0]=1
            fields[i]=dict(dt=abs(y-edge_y),nearest_uv=nearest,nearest_tangent=tangent,domain=np.ones((400,400),bool))
        queries=[dict(query='common-ray',view=0,pixel=[200,200])]
        result=infer_queries(queries,cameras,fields,None,[[-1,-1.5,1],[1,1.5,5]],.1,CFG)
        self.assertEqual(len(result['accepted']),1)
        self.assertLess(np.linalg.norm(np.array(result['accepted'][0]['point'])-[0,0,3]),.02)
        for i,cy in enumerate([0.,1.,-1.,.5]):
            first,second=200-200*cy/2,200-200*cy/4
            nearest_y=np.where(abs(y-first)<=abs(y-second),first,second)
            fields[i]['dt']=abs(y-nearest_y)
            fields[i]['nearest_uv']=np.stack([x,nearest_y],axis=2)
        ambiguous=infer_queries(queries,cameras,fields,None,[[-1,-1.5,1],[1,1.5,5]],.1,CFG)
        self.assertEqual(ambiguous['accepted'],[])
        self.assertTrue(any('multimodal' in r['reasons'] for r in ambiguous['modes']))


if __name__=='__main__':unittest.main()
