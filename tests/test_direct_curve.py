import unittest
import numpy as np
import torch

class DirectCurveTests(unittest.TestCase):
    def test_fixed_cubic_projection_and_native_centers(self):
        from src.direct_curve import bezier,project
        p=torch.tensor([[[-.3,0,2],[-.1,0,2],[.1,0,2],[.3,0,2]]],dtype=torch.float64,requires_grad=True)
        original=p.detach().clone();x=bezier(p,7)
        torch.testing.assert_close(x[0,:,0],torch.linspace(-.3,.3,7,dtype=p.dtype))
        K=torch.tensor([[100.,0,399.5],[0,100,399.5],[0,0,1]],dtype=p.dtype);w=torch.eye(4,dtype=p.dtype)
        uv,z=project(x,K,w)
        torch.testing.assert_close(uv[0,3],torch.tensor([399.5,399.5],dtype=p.dtype))
        w[0,3]=.2;uv2,_=project(x,K,w);torch.testing.assert_close(uv2-uv,torch.tensor([10.,0.],dtype=p.dtype).expand_as(uv))
        uv2.sum().backward();self.assertTrue(torch.isfinite(p.grad).all());torch.testing.assert_close(p.detach(),original)

    def test_union_saturates_reassigns_and_unknown_cannot_hide(self):
        from src.direct_curve import association
        target=torch.tensor([[0.,0.],[10.,0.]])
        tangent=torch.tensor([[1.,0.],[1.,0.]])
        p=torch.tensor([[0.,0.]],requires_grad=True);t=tangent[:1]
        kw=dict(sigma=2.,active=torch.ones(1),visible=torch.ones(1),known=torch.ones(1,dtype=torch.bool))
        a=association(p,t,target,tangent,**kw)
        b=association(p.repeat(2,1),t.repeat(2,1),target,tangent,sigma=2.,active=torch.ones(2),visible=torch.ones(2),known=torch.ones(2,dtype=torch.bool))
        torch.testing.assert_close(a['coverage'],b['coverage'])
        self.assertEqual(a['nearest'].item(),0)
        c=association(p+10,t,target,tangent,**kw);self.assertEqual(c['nearest'].item(),1)
        u=association(p,t,target,tangent,**dict(kw,known=torch.zeros(1,dtype=torch.bool)))
        self.assertEqual(u['coverage'].sum().item(),0);self.assertEqual(u['unsupported'].item(),1)
        h=association(p,t,target,tangent,**dict(kw,visible=torch.zeros(1)))
        self.assertEqual(h['coverage'].sum().item(),0);self.assertEqual(h['unsupported'].item(),0)
        wrong=association(p,torch.tensor([[0.,1.]]),target,tangent,**kw)
        self.assertLess(wrong['coverage'].sum(),a['coverage'].sum())
        move=association(p+1,t,target,tangent,**kw);move['coverage'].sum().backward();self.assertGreater(abs(p.grad).sum().item(),0)
        # Appearance side order is immaterial, changed colors are not.
        sides=torch.tensor([[[0.,0.,0.],[1.,1.,1.]]]);ts=sides.repeat(2,1,1)
        e=association(p,t,target,tangent,**kw,sides=sides,target_sides=ts)
        f=association(p,t,target,tangent,**kw,sides=sides.flip(1),target_sides=ts)
        torch.testing.assert_close(e['coverage'],f['coverage'])
        g=association(p,t,target,tangent,**kw,sides=sides+.5,target_sides=ts)
        self.assertLess(g['coverage'].sum(),e['coverage'].sum())

    def test_complete_evidence_native_mapping_and_depth_boundary(self):
        from src.direct_curve import evidence
        rgb=np.zeros((800,800,3),np.float32);rgb[:,400:]=1
        depth=np.ones((800,800),np.float32)*2;depth[:,400:]=3
        alpha=np.ones((800,800),np.float32)
        e=evidence(rgb,depth,alpha)
        for key in ['I','D']:
            q=e[key];self.assertGreater(len(q['xy']),300)
            self.assertTrue(np.all(abs(q['xy'][:,0]-399.5)<8))
            self.assertEqual(q['native_edge'].shape,(800,800))
            self.assertGreater(np.nanmean(abs(q['tangent'][:,1])),.95)
            self.assertEqual(q['sides'].shape,(len(q['xy']),2,3))
        r=evidence(rgb,depth,alpha)
        for k in ['I','D']:np.testing.assert_array_equal(e[k]['xy'],r[k]['xy'])

    def test_visibility_and_independent_local_objective(self):
        from src.direct_curve import visibility,view_loss
        uv=torch.tensor([[[10.,10.],[20.,10.],[30.,10.],[40.,10.]]]);z=torch.tensor([[1.,3.,2.,1.]])
        maps=torch.ones(1,4,64,64);maps[:,1:]=2;maps[0,0,:,40:]=.2
        visible,known,state=visibility(uv,z,maps,1.)
        self.assertEqual(state.tolist(),[[0,2,0,1]])
        # A second independent span cannot alter the first local span gradient.
        K=torch.tensor([[100.,0,32.],[0,100.,32.],[0,0,1.]])
        data=dict(K=K,w2c=torch.eye(4),maps=maps,xy=torch.tensor([[10.,10.],[50.,50.]]),tangent=torch.tensor([[1.,0.],[1.,0.]]),sides=None,rgb=None,scale=1.)
        p=torch.tensor([[[-.2,-.4,1.],[-.1,-.4,1.],[0.,-.4,1.],[.1,-.4,1.]]],requires_grad=True)
        a=view_loss(p,torch.ones(1),data,'L',2.,1.)['data'];a.backward();g=p.grad.clone()
        q=torch.cat([p.detach(),p.detach()+torch.tensor([0.,.3,0.])]).requires_grad_()
        b=view_loss(q,torch.ones(2),data,'L',2.,1.)['data'];b.backward()
        torch.testing.assert_close(g,q.grad[:1],atol=1e-5,rtol=1e-5)

    def test_local_matching_cannot_win_by_deleting_its_span(self):
        from src.direct_curve import view_loss
        p=torch.tensor([[[-.3,0,1.],[-.1,0,1.],[.1,0,1.],[.3,0,1.]]])
        xy=torch.stack([torch.linspace(20,80,100),torch.ones(100)*50],1)
        maps=torch.ones(1,4,100,100);maps[:,1:]=2
        d=dict(K=torch.tensor([[100.,0,50],[0,100.,50],[0,0,1.]]),w2c=torch.eye(4),maps=maps,xy=xy,tangent=torch.tensor([[1.,0.]]).repeat(100,1),sides=None,rgb=None,scale=1.)
        on=view_loss(p,torch.ones(1),d,'L',2,1.)['data'];off=view_loss(p,torch.zeros(1),d,'L',2,1.)['data']
        self.assertGreater(off.item(),on.item())

    def test_regularization_redundancy_and_synthetic_recovery(self):
        from src.direct_curve import regularization,fit,bezier,project
        box=np.array([[-1.,-1.,1.],[1.,1.,3.]])
        truth=torch.tensor([[[-.3,0,2.],[-.1,0,2.],[.1,0,2.],[.3,0,2.]]])
        diag=float(np.linalg.norm(box[1]-box[0]))
        one=regularization(truth,torch.ones(1),'I',diag)
        dup=regularization(truth.repeat(2,1,1),torch.ones(2),'I',diag)
        self.assertGreater(dup['redundancy'].item(),one['redundancy'].item())
        self.assertEqual(regularization(truth.repeat(2,1,1),torch.ones(2),'L',diag)['redundancy'].item(),0)
        data=[]
        for tx in [-.2,0,.2]:
            K=torch.tensor([[250.,0,199.5],[0,250.,199.5],[0,0,1.]])
            w=torch.eye(4);w[0,3]=tx
            xy,_=project(bezier(truth,128),K,w)
            maps=torch.ones(1,4,400,400);maps[:,1:]=3
            data.append(dict(K=K,w2c=w,maps=maps,xy=xy[0],tangent=torch.tensor([[1.,0.]]).repeat(128,1),sides=None,rgb=None,scale=1.))
        initial=truth.numpy()+np.array([0,.04,0],np.float32)
        result=fit(initial,data,box,'I',device='cpu')
        self.assertLess(result['history'][-1]['data'],result['history'][0]['data'])
        # Easy sanity: recover a 5-pixel transverse displacement in three known views.
        pred=torch.tensor(result['control']);uv,_=project(bezier(pred,128),data[0]['K'],data[0]['w2c'])
        self.assertLess(float(abs(uv[:,:,1]-199.5).mean()),2.)
        self.assertEqual(result['active'].tolist(),[True]);self.assertTrue(np.isfinite(result['control']).all())

    def test_proposals_keep_empty_cells_and_share_three_starts(self):
        from src.direct_curve import proposals
        cam=dict(native_K=[[100.,0,399.5],[0,100.,399.5],[0,0,1]],w2c=np.eye(4).tolist())
        e=dict(xy=np.array([[100.,100.]],'f4'),tangent=np.array([[1.,0.]],'f4'))
        views=[dict(view=i,camera=cam,evidence={'I':e,'D':e},alpha=np.ones((800,800)),depth=np.ones((800,800))*2) for i in range(8)]
        a=proposals(views,[[-10,-10,.1],[10,10,5]])
        b=proposals(views,[[-10,-10,.1],[10,10,5]])
        self.assertEqual(a['starts'].shape,(3,128,4,3));self.assertEqual(len(a['provenance']),128)
        np.testing.assert_array_equal(a['starts'],b['starts']);self.assertEqual(len(set((p['view'],p['cell']) for p in a['provenance'])),128)
        self.assertGreater(np.max(abs(a['starts'][0]-a['starts'][2])),.1)
        self.assertEqual(a['provenance'][0]['source'],'boundary');self.assertEqual(a['provenance'][1]['source'],'foreground_fallback')

    def test_native_quantiles_are_ten_fifty_ninety_and_calibrated(self):
        from src.direct_curve import native_quantiles
        state={'means2D':np.zeros((4,2),'f4'),'conic':np.array([[1,0,1,.08],[1,0,1,.04/.92],[1,0,1,.76/.88],[1,0,1,.99]],'f4'),
               'rgb':np.ones((4,3),'f4')*.3,'depths':np.arange(1,5,dtype='f4'),'point_list':np.arange(4,dtype='u4'),'ranges':np.array([[0,4]],'u4')}
        a=native_quantiles(state,1,1)
        np.testing.assert_array_equal(a['quantiles'][0,0],[2,3,4]);self.assertAlmostEqual(a['alpha'][0,0],.9988,places=5)
        np.testing.assert_allclose(a['rgb'][0,0],.3*.9988+.0012,atol=1e-6)

    def test_partition_access_and_native_preparation(self):
        from scripts.run_direct_curve_probe import permitted_photos,prepare_view
        cfg=dict(F=[1],C=[7],scenes={'fixture':dict(cameras={'1':dict(path='/F.png'),'7':dict(path='/C.png')})})
        self.assertEqual(permitted_photos(cfg,'fixture','fit'),['/F.png'])
        self.assertEqual(permitted_photos(cfg,'fixture','evaluate'),['/F.png','/C.png'])
        with self.assertRaises(ValueError):permitted_photos(cfg,'fixture','test')
        from src.foundation import native_render
        asset=dict(mu=np.array([[0,0,2]],'f4'),scale=np.array([[.3,.3,.1]],'f4'),quat=np.array([[1,0,0,0]],'f4'),opacity=np.array([[.9]],'f4'),sh=np.zeros((1,16,3),'f4'))
        camera=dict(native_K=[[500,0,399.5],[0,500,399.5],[0,0,1]],w2c=np.eye(4).tolist(),native_height=800,native_width=800)
        v=prepare_view(asset,camera,view=1,photograph=None)
        self.assertEqual(v['maps'].shape,(800,800,4));self.assertLess(v['calibration']['rgb_max'],1/255)
        self.assertTrue(np.isfinite(v['maps']).all());self.assertEqual(v['rgb'].shape,(800,800,3))
        self.assertGreater(v['alpha'].max(),.8)

    def test_native_census_keeps_empty_cells_and_fixed_geometry(self):
        from src.direct_curve_eval import evaluate_drawing
        control=np.array([[[-.3,0,2],[-.1,0,2],[.1,0,2],[.3,0,2]]],'f4');before=control.copy()
        camera=dict(native_K=[[1000.,0,399.5],[0,1000.,399.5],[0,0,1]],w2c=np.eye(4).tolist())
        xy=np.c_[np.linspace(249.5,549.5,301),np.full(301,399.5)].astype('f4');target=dict(xy=xy,tangent=np.tile([1.,0.],(301,1)),sides=np.tile([[[0.,0,0],[1.,1,1]]],(301,1,1)))
        maps=np.ones((800,800,4),'f4');maps[:,:,1:]=3
        d=evaluate_drawing(control,np.array([True]),camera,maps,target,4.)
        self.assertEqual(len(d['cells']),64);self.assertGreater(d['metrics']['coverage'],.99);self.assertLess(d['metrics']['unsupported_fraction'],.01)
        self.assertGreater(d['metrics']['actual_ink'],300);self.assertEqual(d['image'].shape,(800,800,3));np.testing.assert_array_equal(control,before)
        empty=evaluate_drawing(control,np.array([False]),camera,maps,target,4.)
        self.assertEqual(empty['metrics']['coverage'],0);self.assertEqual(empty['metrics']['actual_ink'],0);self.assertIsNone(empty['metrics']['unsupported_fraction'])
        unknown=maps.copy();unknown[:,:,0]=.2
        u=evaluate_drawing(control,np.array([True]),camera,unknown,target,4.);self.assertEqual(u['metrics']['coverage'],0);self.assertGreater(u['metrics']['unknown_length'],200)

    def test_fit_runner_seals_all_arms_starts_and_never_decodes_C(self):
        import tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        from scripts.run_direct_curve_probe import run_fit
        camera=dict(native_K=np.eye(3).tolist(),w2c=np.eye(4).tolist(),path='F')
        cfg=dict(F=[1,14,27,41,53,67,79,93],C=[7],scenes={'toy':dict(checkpoint={'path':'gs'},box=[[-1,-1,1],[1,1,3]],cameras={str(i):dict(camera,path=str(i)) for i in [1,14,27,41,53,67,79,93,7]})})
        e=dict(xy=np.array([[1,1]],'f4'),tangent=np.array([[1,0]],'f4'),sides=np.zeros((1,2,3),'f4'),native_edge=np.zeros((800,800),bool))
        seen=[]
        def prep(asset,cam,view,photograph):
            seen.append(view);return dict(view=view,camera=cam,rgb=np.ones((800,800,3),'f4'),gs_rgb=np.ones((800,800,3),'f4'),maps=np.ones((800,800,4),'f4'),alpha=np.ones((800,800),'f4'),depth=np.ones((800,800),'f4'),evidence={'I':e,'D':e},calibration={'rgb_max':0.})
        calls=[]
        def fakefit(initial,data,box,arm,**kwargs):
            calls.append((arm,len(data)));return dict(control=initial,active=np.ones(128,bool),gate=np.ones(128),history=[],final=dict(data=.5,regularization=.1),seconds=0.)
        with tempfile.TemporaryDirectory() as tmp,patch('scripts.run_direct_curve_probe.prepare_view',prep),patch('scripts.run_direct_curve_probe.load_asset',return_value={}),patch('scripts.run_direct_curve_probe.fit',fakefit):
            run_fit(cfg,'toy',Path(tmp))
            seal=json.loads((Path(tmp)/'SEAL.json').read_text());self.assertEqual(len(seal['assets']),18);self.assertEqual(set(seal['chosen']),{'D','I','L'})
            self.assertEqual(seen,cfg['F']);self.assertEqual(len(calls),18);self.assertEqual(sum(n==7 for a,n in calls),9)

    def test_gpu_sampler_deterministic_gradient(self):
        from src.direct_curve import sample_map
        torch.use_deterministic_algorithms(True)
        try:
            m=torch.arange(100.,device='cuda').reshape(1,1,10,10)
            values=[]
            for i in range(2):
                uv=torch.tensor([[1.25,2.5],[3.1,4.7]],device='cuda',requires_grad=True)
                a=sample_map(m,uv);a.sum().backward();values.append((a.detach().cpu().numpy(),uv.grad.cpu().numpy()))
            np.testing.assert_array_equal(values[0][0],values[1][0]);np.testing.assert_array_equal(values[0][1],values[1][1]);np.testing.assert_allclose(values[0][1],[[1,10],[1,10]])
        finally:torch.use_deterministic_algorithms(False)

    def test_temporal_and_ambiguity_counts_do_not_reward_empty_ink(self):
        from src.direct_curve_eval import temporal,disagreement,scene_gate
        a=np.zeros((20,20),'f4');a[5,2:18]=1;b=np.zeros_like(a);b[12,2:18]=1
        self.assertEqual(disagreement(a,a),0);self.assertEqual(disagreement(a,b),1);self.assertEqual(disagreement(a,np.zeros_like(a)),1)
        t=temporal([dict(per_id_visible_length=np.array([100.,40.])),dict(per_id_visible_length=np.array([140.,40.]))])
        self.assertEqual(t['popping_count'],1)
        m=dict(coverage=.5,interior_coverage=.5,outline_coverage=.5,unsupported_fraction=.05,precision=.95,beyond4_fraction=.02,actual_ink=1000.,improved_cell_fraction=.6)
        g=scene_gate(dict(D=dict(m,interior_coverage=.35),I=m,L=dict(m,coverage=.4)),ambiguity=False,visual=False,budget=True)
        self.assertTrue(g['extra_rgb']);self.assertTrue(g['global_coupling']);self.assertFalse(g['continue'])
        g=scene_gate(dict(D=m,I=m,L=m),ambiguity=False,visual=True,budget=True);self.assertFalse(g['extra_rgb']);self.assertFalse(g['global_coupling'])

    def test_playable_complete_media_and_drawing_disagreement(self):
        import tempfile
        from pathlib import Path
        import cv2
        from scripts.evaluate_direct_curve_probe import video,comparison_sheet,quick_ink
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);frames=[np.full((64,128,3),255-i*10,'u1') for i in range(5)]
            video(p/'movie.mp4',frames);cap=cv2.VideoCapture(str(p/'movie.mp4'));count=0
            while cap.read()[0]:count+=1
            cap.release();self.assertEqual(count,5)
            sheet=comparison_sheet([frames[:3]],['a','b','c'],64);self.assertEqual(sheet.shape[1],192);self.assertGreater(sheet.shape[0],64)
        camera=dict(native_K=[[1000.,0,399.5],[0,1000.,399.5],[0,0,1]],w2c=np.eye(4).tolist());maps=np.ones((800,800,4),'f4');maps[:,:,1:]=3
        c=np.array([[[-.3,0,2],[-.1,0,2],[.1,0,2],[.3,0,2]]],'f4')
        before=c.copy();a=quick_ink(c,np.array([True]),camera,maps,4.);b=quick_ink(c,np.array([True]),camera,maps,4.)
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(c,before);self.assertGreater(a.sum(),300)

    def test_evaluation_requires_seal_and_keeps_every_frame_and_cell(self):
        import tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        from scripts.evaluate_direct_curve_probe import run_evaluation
        from src.foundation import freeze_json
        from scripts.run_direct_curve_probe import sha
        from scripts.render_adaptive_g1 import save_npz
        camera=dict(native_K=[[1000,0,399.5],[0,1000,399.5],[0,0,1]],w2c=np.eye(4).tolist(),path='image')
        cfg=dict(F=[1],C=[7],scenes={'toy':dict(checkpoint={'path':'gs'},box=[[-1,-1,1],[1,1,3]],cameras={'1':camera,'7':camera},arcs=[dict(frames=[camera,camera],endpoints=[1,7])])})
        e=dict(xy=np.empty((0,2),'f4'),tangent=np.empty((0,2),'f4'),sides=np.empty((0,2,3),'f4'),native_edge=np.zeros((800,800),bool))
        def prep(asset,cam,view,photograph=None):return dict(view=view,camera=cam,rgb=np.ones((800,800,3),'f4'),gs_rgb=np.ones((800,800,3),'f4'),maps=np.ones((800,800,4),'f4'),alpha=np.ones((800,800),'f4'),depth=np.ones((800,800),'f4'),evidence={'I':e,'D':e},calibration={'rgb_max':0.})
        with tempfile.TemporaryDirectory() as tmp,patch('scripts.evaluate_direct_curve_probe.prepare_view',prep),patch('scripts.evaluate_direct_curve_probe.load_asset',return_value={}):
            p=Path(tmp);fitdir=p/'fit';fitdir.mkdir();out=p/'eval';out.mkdir()
            with self.assertRaises(FileNotFoundError):run_evaluation(cfg,'toy',fitdir,out)
            assets={}
            for arm in ['D','I','L']:
                key=f'{arm}_full_0';save_npz(fitdir/(key+'.npz'),dict(control=np.zeros((1,4,3),'f4'),active=np.zeros(1,bool),gate=np.zeros(1)));assets[key]=sha(fitdir/(key+'.npz'))
            freeze_json(fitdir/'SEAL.json',dict(assets=assets,chosen={a:f'{a}_full_0' for a in ['D','I','L']},objective_components={k:dict(data=1.) for k in assets},elapsed_seconds=0.))
            run_evaluation(cfg,'toy',fitdir,out)
            result=json.loads((out/'RESULTS.json').read_text());self.assertEqual(result['census_cells_per_arm'],128);self.assertEqual(result['arcs'][0]['frames'],2);self.assertEqual(len(list((out/'figures').glob('C_[0-9]*.png'))),1)
            self.assertFalse(result['gates']['continue'])

    def test_depth_reference_temporal_motion_has_identity_zero_and_detects_pop(self):
        from src.direct_curve_eval import motion_defects
        ink=np.zeros((800,800),'f4');ink[400,300:500]=1
        maps=np.ones((800,800,4),'f4');maps[:,:,1:]=2
        cam=dict(native_K=[[1000.,0,399.5],[0,1000.,399.5],[0,0,1]],w2c=np.eye(4).tolist())
        a=motion_defects(ink,ink,maps,cam,cam);self.assertEqual(a['popping_components'],0);self.assertEqual(a['disappearing_pixels'],0)
        new=ink.copy();new[500,300:500]=1;b=motion_defects(ink,new,maps,cam,cam);self.assertEqual(b['popping_components'],1);self.assertGreater(b['appearing_pixels'],100)

    def test_depth_scale_is_neighbor_difference_not_median_residual(self):
        from src.direct_curve import depth_scale
        z=np.tile(np.arange(7,dtype=float)+2,(7,1));scale=depth_scale(z)
        self.assertAlmostEqual(scale[3,3],1.)
        flat=np.ones((7,7))*2;self.assertAlmostEqual(depth_scale(flat)[3,3],.004)
        from src.direct_curve import native_quantiles
        state={'means2D':np.zeros((4,2),'f4'),'conic':np.array([[1,0,1,.08],[1,0,1,.04/.92],[1,0,1,.76/.88],[1,0,1,.99]],'f4'),'rgb':np.ones((4,3),'f4')*.3,'depths':np.arange(1,5,dtype='f4'),'point_list':np.arange(4,dtype='u4'),'ranges':np.array([[0,4]],'u4')}
        self.assertEqual(native_quantiles(state,1,1)['front'][0,0],1.)

    def test_final_native_stroke_width_is_one_point_five(self):
        from scripts.evaluate_direct_curve_probe import quick_ink
        from src.direct_curve_eval import evaluate_drawing
        control=np.array([[[-.3,0,2],[-.1,0,2],[.1,0,2],[.3,0,2]]],'f4');camera=dict(native_K=[[1000.,0,399.5],[0,1000.,399.5],[0,0,1]],w2c=np.eye(4).tolist())
        maps=np.ones((800,800,4),'f4');maps[:,:,1:]=3
        ink=quick_ink(control,np.array([True]),camera,maps,4.)
        self.assertAlmostEqual(float(ink[:,400].sum()),1.5,places=5)
        t=dict(xy=np.empty((0,2),'f4'),tangent=np.empty((0,2),'f4'),sides=np.empty((0,2,3),'f4'))
        draw=evaluate_drawing(control,np.array([True]),camera,maps,t,4.)
        np.testing.assert_array_equal(ink,draw['arrays']['ink'])

    def test_verification_detects_geometry_and_metric_tampering(self):
        import tempfile,json
        from pathlib import Path
        from scripts.verify_direct_curve_probe import compare_science,verify_fixed_geometry
        from scripts.render_adaptive_g1 import save_npz
        from src.direct_curve import bezier
        c=np.array([[[-.3,0,2],[-.1,0,2],[.1,0,2],[.3,0,2]]],'f4');xyz=bezier(torch.tensor(c,dtype=torch.float64),257).numpy()
        self.assertTrue(verify_fixed_geometry(c,[xyz,xyz.copy()]))
        changed=xyz.copy();changed[0,20,1]+=.001;self.assertFalse(verify_fixed_geometry(c,[xyz,changed]))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);a=p/'a';b=p/'b';a.mkdir();b.mkdir()
            for d in [a,b]:
                save_npz(d/'curve.npz',dict(control=c));(d/'result.json').write_text(json.dumps(dict(coverage=.2,seconds=3 if d==a else 4)))
            self.assertTrue(compare_science(a,b)['passed'])
            (b/'result.json').write_text(json.dumps(dict(coverage=.3,seconds=4)))
            self.assertFalse(compare_science(a,b)['passed'])

    def test_global_fit_allocates_two_spans_to_two_complete_boundaries(self):
        from src.direct_curve import fit,bezier,project
        box=np.array([[-1.,-1.,1.],[1.,1.,3.]])
        line=torch.tensor([[[-.3,0,2.],[-.1,0,2.],[.1,0,2.],[.3,0,2.]]]);truth=torch.cat([line,line+torch.tensor([0,.08,0])])
        data=[]
        for tx in [-.2,0,.2]:
            K=torch.tensor([[250.,0,199.5],[0,250.,199.5],[0,0,1.]]);w=torch.eye(4);w[0,3]=tx
            xy,_=project(bezier(truth,128),K,w);maps=torch.ones(1,4,400,400);maps[:,1:]=3
            data.append(dict(K=K,w2c=w,maps=maps,xy=xy.reshape(-1,2),tangent=torch.tensor([[1.,0.]]).repeat(256,1),sides=None,rgb=None,scale=1.))
        initial=line.repeat(2,1,1).numpy();i=fit(initial,data,box,'I',device='cpu');l=fit(initial,data,box,'L',device='cpu')
        self.assertLess(i['final']['missed'],.25);self.assertGreater(l['final']['missed'],.35)
        self.assertGreater(l['final']['missed']-i['final']['missed'],.2)

    def test_foreground_census_uses_alpha_not_expanded_outline(self):
        from src.direct_curve_eval import evaluate_drawing
        camera=dict(native_K=[[1000.,0,399.5],[0,1000.,399.5],[0,0,1]],w2c=np.eye(4).tolist())
        maps=np.ones((800,800,4),'f4');maps[:,:,1:]=3;maps[:,400:,0]=0
        c=np.array([[[.005,-.2,2],[.005,-.0666667,2],[.005,.0666667,2],[.005,.2,2]]],'f4')
        t=dict(xy=np.c_[np.full(201,402.),np.linspace(299.5,499.5,201)],tangent=np.tile([0.,1.],(201,1)),sides=np.zeros((201,2,3)))
        r=evaluate_drawing(c,np.array([True]),camera,maps,t,4.)
        self.assertEqual(r['metrics']['strata']['foreground']['targets'],0)
        self.assertEqual(r['metrics']['strata']['outline']['targets'],201)
        self.assertGreater(max(cell['active_curves'] for cell in r['cells']),0)

    def test_double_line_pairs_and_detached_runs_are_counted(self):
        from src.direct_curve_eval import evaluate_drawing
        c=np.array([[[-.3,0,2],[-.1,0,2],[.1,0,2],[.3,0,2]]],'f4');c=np.concatenate([c,c+[0,.002,0],c+[0,.02,0]]).astype('f4')
        camera=dict(native_K=[[1000.,0,399.5],[0,1000.,399.5],[0,0,1]],w2c=np.eye(4).tolist());maps=np.ones((800,800,4),'f4');maps[:,:,1:]=3
        target=dict(xy=np.c_[np.linspace(249.5,549.5,301),np.full(301,399.5)],tangent=np.tile([1.,0.],(301,1)),sides=np.zeros((301,2,3)))
        r=evaluate_drawing(c,np.ones(3,bool),camera,maps,target,4.)
        self.assertEqual(r['metrics']['doubling_pairs'],1);self.assertEqual(r['metrics']['detachment_runs'],1)

    def test_media_verification_decodes_all_frames_and_rejects_wrong_count(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        from scripts.evaluate_direct_curve_probe import video
        from scripts.verify_direct_curve_probe import decode_media
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);frames=[np.full((64,64,3),255-i*20,'u1') for i in range(4)]
            Image.fromarray(frames[0]).save(p/'a.png');video(p/'a.mp4',frames)
            r=decode_media(p,4);self.assertTrue(r['passed']);self.assertEqual(r['videos']['a.mp4']['frames'],4)
            self.assertFalse(decode_media(p,5)['passed'])

    def test_doubling_counts_dense_spans_beyond_same_id_neighbors(self):
        from src.direct_curve_eval import evaluate_drawing
        c=np.array([[[-.02,0,2],[-.02/3,0,2],[.02/3,0,2],[.02,0,2]]],'f4')
        c=np.concatenate([c,c+[0,.002,0]]).astype('f4')
        camera=dict(native_K=[[1000.,0,399.5],[0,1000.,399.5],[0,0,1]],w2c=np.eye(4).tolist())
        maps=np.ones((800,800,4),'f4');maps[:,:,1:]=3
        target=dict(xy=np.c_[np.linspace(389.5,409.5,21),np.full(21,399.5)],tangent=np.tile([1.,0.],(21,1)),sides=np.zeros((21,2,3)))
        r=evaluate_drawing(c,np.ones(2,bool),camera,maps,target,4.)
        self.assertEqual(r['metrics']['doubling_pairs'],1)
        self.assertAlmostEqual(r['metrics']['doubling_length'],40.,places=4)

    def test_ambiguity_compares_all_equally_good_data_fits(self):
        from src.direct_curve_eval import ambiguity_from_pairs
        pairs={'a|b':.1,'a|c':.9,'b|c':.9}
        r=ambiguity_from_pairs({'a':.4,'b':.4,'c':.8},'c',{},None,pairs)
        self.assertFalse(r['failed'])  # The selected prior-favored fit is not data-equivalent.
        pairs={'a|b':.1,'a|c':.15,'b|c':.25}
        r=ambiguity_from_pairs({'a':.4,'b':.4,'c':.4},'a',{},None,pairs)
        self.assertTrue(r['failed'])  # Neither selected-to-alternative distance exceeds .2.
        r=ambiguity_from_pairs({'a':.4},'a',{'b':.4,'c':.4},.4,pairs)
        self.assertTrue(r['failed'])  # LOO candidates must also be compared with each other.
