"""Real Chair edit timing must include saving, not only raster output."""
import runtime
from runtime import sha
from pathlib import Path
import json, tempfile, time, unittest
from unittest.mock import patch
import viewer
from unit025_run import U,PREV

class OperationTiming(unittest.TestCase):
    def test_full_edit_and_saved_record(self):
        with tempfile.TemporaryDirectory(dir=U,prefix='timing_') as tmp:
            e=viewer.Editor(PREV/'portable_demo/examples/chair_ink_preview',Path(tmp)/'session')
            original=viewer.edit
            def delayed_save(*args,**kwargs):
                time.sleep(.15)
                return original(*args,**kwargs)
            before=e.asset
            with patch('viewer.edit',side_effect=delayed_save):
                started=time.monotonic()
                r=e.apply(dict(e.record['styles']['4'],**e.record['camera'],region=4,ink_strength=.65))
                external=time.monotonic()-started
            self.assertIn('operation_seconds',r)
            self.assertGreaterEqual(r['operation_seconds'],r['seconds']+.15)
            self.assertLessEqual(r['operation_seconds'],external)
            self.assertEqual(r,json.loads((e.output/'CURRENT.json').read_text()))
            self.assertTrue(r['render_cache']['hit'])
            self.assertTrue(all(sha(f)==sha(e.asset/f.name) for f in before.iterdir() if f.suffix=='.npz'))
            undone=e.undo();self.assertEqual(undone['operation'],'undo')
            self.assertGreaterEqual(undone['operation_seconds'],undone['seconds'])
            self.assertEqual(e.asset,before)

if __name__=='__main__':unittest.main()
