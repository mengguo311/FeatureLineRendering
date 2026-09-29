import json,tempfile,unittest
from pathlib import Path

class SchedulerTests(unittest.TestCase):
    def test_evaluation_failure_does_not_block_other_scene_fits(self):
        from scripts.schedule_direct_curve_probe import schedule
        seen=[]
        def stage(scene,kind):
            seen.append((scene,kind))
            return not (scene=='lego' and kind=='evaluate')
        result=schedule(['lego','chair','drums','ficus'],stage)
        self.assertFalse(result['lego']['evaluate'])
        for scene in ['chair','drums','ficus']:self.assertTrue(result[scene]['fit'])
        self.assertEqual(seen[:4],[(s,'fit') for s in ['lego','chair','drums','ficus']])

    def test_atomic_seal_is_exclusive_and_complete(self):
        from scripts.schedule_direct_curve_probe import atomic_json
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'seal.json';atomic_json(p,{'complete':True})
            self.assertEqual(json.loads(p.read_text()),{'complete':True})
            with self.assertRaises(FileExistsError):atomic_json(p,{'complete':False})
            self.assertEqual(json.loads(p.read_text()),{'complete':True})

    def test_partial_fit_is_blocked_and_existing_seal_verified(self):
        from scripts.schedule_direct_curve_probe import fit_state
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);self.assertEqual(fit_state(p),'empty')
            (p/'valuable.npz').write_bytes(b'valuable');self.assertEqual(fit_state(p),'partial')
            assets={f'arm{i}':hashlib.sha256(b'asset').hexdigest() for i in range(18)}
            for k in assets:(p/(k+'.npz')).write_bytes(b'asset')
            data=(json.dumps({'assets':assets})+'\n').encode();(p/'SEAL.json').write_bytes(data)
            (p/'SEAL.json.sha256').write_text(hashlib.sha256(data).hexdigest()+'\n')
            self.assertEqual(fit_state(p),'sealed')
            (p/'arm0.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):fit_state(p)

if __name__=='__main__':unittest.main()
