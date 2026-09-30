"""Synthetic behavior contracts, written before the implementation."""
import unittest
import tempfile
from pathlib import Path
import numpy as np


def camera(tx=0):
    w=np.eye(4);w[0,3]=tx
    return {'native_K':[[20.,0,15.],[0,20.,15.],[0,0,1]],'w2c':w.tolist(),'native_width':32,'native_height':32}


def frame(key='000', tx=0):
    mask=np.zeros((32,32),bool);mask[16,8:24]=True
    return dict(key=key,mask=mask,depth=np.full((32,32),2.),alpha=np.ones((32,32)),camera=camera(tx),gs_rgb=np.ones((32,32,3)))


class TemporalBehavior(unittest.TestCase):
    def test_camera_flow_projection(self):
        from src.temporal_depth2d import project_points, transport
        a=frame();b=frame(tx=.2)
        p,z=project_points(np.array([[10.,16.],[20.,16.]]),np.array([2.,2.]),a['camera'],b['camera'])
        np.testing.assert_allclose(p,[[12,16],[22,16]],atol=1e-10)
        np.testing.assert_allclose(z,2)
        ink=np.zeros((32,32));ink[16,10]=1
        warped,valid,info=transport(ink,a,b)
        self.assertEqual(warped[16,12],1);self.assertTrue(valid[16,12]);self.assertEqual(info['accepted'],1)

    def test_occlusion_and_reappearance_keeps_identity(self):
        from src.temporal_depth2d import Tracker, transport
        a=frame();t=Tracker();first=t.update(a)
        hidden=frame('001');hidden['mask'][:]=False;hidden['depth'][:]=1
        warped,_,info=transport(a['mask'].astype(float),a,hidden)
        self.assertEqual(warped.sum(),0);self.assertGreater(info['occluded'],0)
        middle=t.update(hidden);self.assertEqual(len(middle['xy']),0)
        again=t.update(frame('002'))
        np.testing.assert_array_equal(first['ids'],again['ids'])
        self.assertGreater(again['events']['reappeared'],0)

    def test_split_merge_no_bridge_and_complete_graph(self):
        from src.temporal_depth2d import Tracker, graph
        t=Tracker();a=frame();first=t.update(a)
        split=frame('001');split['mask'][16,14:18]=False
        second=t.update(split)
        self.assertGreater(second['events']['split'],0)
        for chain in second['chains']:
            x=second['xy'][chain,0]
            self.assertFalse(x.min()<14 and x.max()>17)
        third=t.update(frame('002'));self.assertGreater(third['events']['merge'],0)
        xy,chains=graph(a['mask']);self.assertEqual(len(xy),16)
        self.assertEqual(set(np.concatenate(chains)),set(range(16)))

    def test_identity_texture_follows_camera(self):
        from src.temporal_depth2d import Tracker, texture
        t=Tracker();a=frame();old=t.update(a)
        b=frame('001',tx=.2);b['mask'][:]=False;b['mask'][16,10:26]=True
        new=t.update(b)
        np.testing.assert_array_equal(old['ids'],new['ids'])
        np.testing.assert_array_equal(texture(old['ids']),texture(new['ids']))
        self.assertGreater(np.ptp(texture(old['ids'])),.01)

    def test_reverse_recomputes_equal_atlas(self):
        from src.temporal_depth2d import atlas
        a=frame('000');b=frame('001',tx=.1)
        b['mask'][:]=False;b['mask'][16,9:25]=True
        forward=atlas([a,b]);reverse=atlas([b,a])
        for key in ['000','001']:
            for field in ['xy','ids','native']:
                np.testing.assert_array_equal(forward[key][field],reverse[key][field])

    def test_closed_camera_loop_identity_and_image(self):
        from src.temporal_depth2d import atlas
        a=frame('000');b=frame('001',tx=.2)
        b['mask'][:]=False;b['mask'][16,10:26]=True
        c=frame('002')
        result=atlas([a,b,c])
        np.testing.assert_array_equal(result['000']['ids'],result['002']['ids'])
        np.testing.assert_allclose(result['000']['native'],result['002']['native'],atol=1/255)

    def test_quantized_actual_ink_preserves_separate_structures(self):
        from src.temporal_depth2d import match_ink, actual_ink
        ink=np.zeros((32,32));ink[5,4:15]=.65;ink[25,18:29]=.9
        target=60.
        result,info=match_ink(ink,target)
        self.assertLess(abs(actual_ink(result)/target-1),.05)
        self.assertTrue(np.all(result[5,4:15]>.1));self.assertTrue(np.all(result[25,18:29]>.1))
        self.assertEqual(info['deleted_components'],0)
        self.assertEqual(actual_ink(result),float(np.round(result*255).sum()/255))

    def test_reject_abnormal_poses(self):
        from src.temporal_depth2d import validate_camera
        validate_camera(camera())
        for value in [float('nan'),2.,-1.]:
            bad=camera();bad['w2c'][0][0]=value
            with self.assertRaises(ValueError):validate_camera(bad)
        bad=camera();bad['native_K'][0][0]=0
        with self.assertRaises(ValueError):validate_camera(bad)

    def test_atomic_seal_resume_and_corruption_refusal(self):
        from src.temporal_depth2d import seal_directory, verify_seal
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);stage=root/'unit.partial';stage.mkdir();(stage/'frame.txt').write_text('complete')
            dest=root/'unit';seal_directory(stage,dest,{'science_hash':'abc'})
            self.assertFalse(stage.exists());self.assertTrue(verify_seal(dest,{'science_hash':'abc'}))
            (dest/'frame.txt').write_text('corrupt')
            with self.assertRaises(ValueError):verify_seal(dest,{'science_hash':'abc'})

if __name__=='__main__':unittest.main()
