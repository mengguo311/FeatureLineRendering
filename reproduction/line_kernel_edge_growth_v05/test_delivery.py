"""Small actual fitting + native CPU Gaussian I/O integration; 12 rows only."""
from common import *
from test_build import fixture
from pipeline import merge_then_export,verify_checkpoint,load_state,restore
from runner import export_membership,fresh_geometry,render_whole,tables,diagnostics,record_arrays
import unittest,tempfile,copy

ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
class Delivery(unittest.TestCase):
    def test_twelve_row_pipeline_and_replay(self):
        e=fixture();n=len(e.x);pre=copy.deepcopy(e.carriers);e.a['covariance']=np.tile(np.eye(3)*1e-4,(n,1,1));e.a['opacity']=np.full(n,.7);e.a['rotation']=np.tile([1.,0,0,0],(n,1));e.a['width']=np.full(n,.01);e.a['scale']=np.full((n,3),.01)
        ids=np.repeat([0,6],6);base=dict(edge_id=ids,reason_code=np.zeros(n,np.uint8));prev=dict(edge_id=ids,carrier_id=ids)
        with tempfile.TemporaryDirectory(dir=os.environ['V05_TEST_DIR']) as td:
            u=Path(td);src=u/'original_line.npz';nz(src,**e.a)
            camsource=ROOT/'line_kernel_edge_growth_v04/units/unit_001/CAMERAS.json'
            c=dict(gaussians=str(src),previous_lineage='fixture',cameras=str(camsource),input_files={str(src):sha(src),str(camsource):sha(camsource)},renderer='/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01/renderer.py',libroot=str(ROOT/'c2l50_8build_joint_gs_v01'),previous_membership='fixture')
            merge=u/'merge';merge_then_export(e,merge,lambda:None);verify_checkpoint(merge,'S2_MERGE_COMPLETE');restore(e,load_state(merge/'STATE.pkl'))
            out=u/'out';out.mkdir();m=export_membership(c,out,e,e.a,e.r,base,prev);fresh,audit=fresh_geometry(c,e.a);self.assertTrue(audit['row_order_bitexact']);self.assertEqual(len(m['edge_id']),12)
            render=helpers(c)['render'];cams=json.loads(camsource.read_text())['scan24'];render_whole(c,out,fresh,m['edge_id'],render,cams,'TEST_ONLY_12')
            for cam in cams:
                cold=dict(np.load(out/'DISPLAY_COLORS.npz'));asset={k:fresh[k] for k in ('means','covariance','opacity')};asset['colors']=cold['colors'];replay=render(asset,cam,(1,1,1),.0144)['rgb'];np.testing.assert_array_equal(np.uint8(np.rint(np.clip(replay,0,1)*255)),np.asarray(Image.open(out/f"{cam['view']}_FULL.png")))
            groups=tables(e,m['edge_id'],pre,base['edge_id']);self.assertEqual(len(groups),1);self.assertEqual(len(groups[0]['L1_contributions']),2);self.assertGreater(groups[0]['outward_support_p'],0)
            diag=out/'diagnostics';diag.mkdir();record_arrays(diag/'RECORDS.npz',e);diagnostics(c,diag,e,fresh,m['edge_id'],groups,pre,base,prev,render,cams)
            self.assertTrue((diag/'CONTEXT_SELECTION.json').exists());self.assertEqual(len(e.events),1);print('DELIVERY_12_ROWS: actual merge, full-row mapping, finite intervals, exact lineage, cold native replay BOTH CAMERAS bitexact',flush=True)
    def test_three_arm_guard(self):
        e=fixture();dirs=np.array([[1.,0,0],[-.5,.866025403784,0],[-.5,-.866025403784,0]]);e.rx=np.concatenate([np.array([.3,1.5,2.8])[:,None]*d for d in dirs]);e.rt=np.repeat(dirs,3,axis=0)
        self.assertTrue(e.branch(np.arange(9),np.array([[0.,0,0],[1.,0,0]])))
if __name__=='__main__':unittest.main()
