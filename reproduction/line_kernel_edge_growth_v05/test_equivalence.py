"""Reference equivalence on small real and synthetic carrier sets only."""
from common import *
from core import Engine,Carrier
from pipeline import load_state,Journal,verify_checkpoint,restore
from test_build import fixture
import types,sys,copy,unittest,tempfile
REFERENCE=Path('/home/u00134/3dgs_line/line_kernel_edge_growth_v04/reproduction/line_kernel_edge_growth_v04/core.py')
mod=types.ModuleType('v04_reference');sys.modules[mod.__name__]=mod
exec(compile(REFERENCE.read_text(),str(REFERENCE),'exec'),mod.__dict__)

def same(a,b):
    if isinstance(a,np.ndarray):np.testing.assert_array_equal(a,b)
    elif hasattr(a,'cid'):
        for k in vars(a):same(getattr(a,k),getattr(b,k))
    elif isinstance(a,dict):
        assert a.keys()==b.keys(),(a.keys(),b.keys())
        for k in a:same(a[k],b[k])
    elif isinstance(a,(tuple,list)):
        assert len(a)==len(b)
        for x,y in zip(a,b):same(x,y)
    else:assert a==b,(a,b)

def comparison(new,ref):
    same(new.candidates(),ref.candidates());same(dict(new.stats),dict(ref.stats))
    with tempfile.TemporaryDirectory(dir=os.environ['V05_TEST_DIR']) as td:
        new.observer=Journal(Path(td));na=new.pass_once(False);ra=ref.pass_once(False);same(na,ra)
        same(new.records,ref.records);same(new.events,ref.events);same(new.carriers,ref.carriers);same(dict(new.stats),dict(ref.stats));same(new.fit_count,ref.fit_count);same(dict(new.aux),dict(ref.aux));same(new.next_version,ref.next_version)
        baseline=np.full(len(new.x),-1,np.int64)
        for c in ref.carriers.values():
            if c.baseline:baseline[c.rows]=c.cid
        for a,b in zip(new.primary(baseline),ref.primary(baseline)):same(a,b)
        verify_checkpoint(Path(td),'S2_MERGE_COMPLETE');cold=load_state(Path(td)/'STATE.pkl');same(cold['carriers'],new.carriers)
        # Replay all sealed delta batches against exact initial state in independent test below.
    return dict(accepted=na,candidates=len(new.records),fits=new.fit_count,reasons=dict(new.stats))

class Equivalence(unittest.TestCase):
    def test_hard_cases(self):
        for kind in ('straight','duplicate','gentle_curve','curve','S','parallel','T','X','gap','tie'):
            with self.subTest(kind=kind):
                a=fixture(kind);b=fixture(kind,mod.Engine,mod.Carrier);result=comparison(a,b);print('FIXTURE',kind,json.dumps(result),flush=True)
                if kind=='straight':self.assertEqual(result['accepted'],1)
                if kind=='curve':self.assertEqual(result['accepted'],0);self.assertEqual(result['reasons'].get('turn'),1) # Both frozen algorithms reject this quarter-circle template.
                if kind in ('parallel','T','X','gap'):self.assertEqual(result['accepted'],0)
    def test_real_128(self):
        root=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');old=root/'line_kernel_edge_growth_v04/units/unit_001/scan24/L1';expected=json.loads((old/'CHECKPOINT.json').read_text())['files']['STATE.pkl'];verify({str(old/'STATE.pkl'):expected});state=load_state(old/'STATE.pkl');chosen=sorted(k for k,c in state['carriers'].items() if c.valid)[:128]
        source=root/'c2l50_multiview05_v01/arms/C/scenes/scan24/full';verify(json.loads((old/'INPUT_HASHES_BEFORE.json').read_text()));a=dict(np.load(source/'gaussians.npz'));r=dict(np.load(root/'line_kernel_edge_grouping_v03/units/unit_001/scan24/REPRESENTATIVES.npz'));p=json.loads((old/'GROUPS.json').read_text())['p']
        # Only selected rows need tangents; no full-asset fitting or proposals.
        rows=np.concatenate([state['carriers'][k].rows for k in chosen]);z=dict(np.load(source/'SHARED_CONTROL_AND_SAMPLING.npz'));d=(z['control'][z['control_index'][rows]]*z['derivative_basis'][rows,:,None]).sum(1);t=np.zeros_like(a['means'],dtype=float);t[rows]=d/np.maximum(np.linalg.norm(d,axis=1)[:,None],1e-15)
        aa=Engine(a,r,t,p);bb=mod.Engine(a,r,t,p)
        for e,cl in ((aa,Carrier),(bb,mod.Carrier)):
            e.carriers={k:cl(**copy.deepcopy(vars(state['carriers'][k]))) for k in chosen};e.next_version=state['next_version'];e.level=2
            e.aux=copy.deepcopy(state['aux'])
        result=comparison(aa,bb);print('REAL_128',json.dumps(result),flush=True)
    def test_journal_replay_and_tamper(self):
        a=fixture();initial=copy.deepcopy(a.carriers)
        with tempfile.TemporaryDirectory(dir=os.environ['V05_TEST_DIR']) as td:
            out=Path(td);a.observer=Journal(out);a.pass_once(False)
            for seal in sorted((out/'journal').glob('*.seal.json')):
                s=json.loads(seal.read_text());verify({str(seal.parent/s['file']):s['sha256']})
                with open(seal.parent/s['file'],'rb') as f:d=pickle.load(f)
                for item in d['commits']:
                    for cid,version in item['event']['inputs']:self.assertEqual(initial[cid].version,version);del initial[cid]
                    c=item['carrier'];initial[c.cid]=c
            same(initial,a.carriers)
            with open(out/'STATE.pkl','ab') as f:f.write(b'tamper')
            with self.assertRaises(RuntimeError):verify_checkpoint(out,'S2_MERGE_COMPLETE')
if __name__=='__main__':unittest.main()
