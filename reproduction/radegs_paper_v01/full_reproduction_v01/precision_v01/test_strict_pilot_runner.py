import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from strict_pilot_runner import PilotRunner


class ReserveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'preflight.json').write_text(json.dumps({'passed':True}))
        self.path=self.root/'config.json'
        self.path.write_text(json.dumps({'state_dir':str(self.root/'state'),'log_dir':str(self.root/'logs'),
            'scene':'scan24','automatic_scene_limit':1,'engineering_ready':True,'immutable_files':{},
            'stable_seconds':60,'inputs':{},'preflight_report':str(self.root/'preflight.json')}))

    def tearDown(self):self.tmp.cleanup()

    def usage(self,root,hdd):
        return lambda path:type('Usage',(),{'free':(root if str(path)=='/' else hdd)*1024**3})()

    def test_HDD_40_GiB_refuses_start(self):
        with patch('shutil.disk_usage',side_effect=self.usage(20,40)):
            with self.assertRaisesRegex(ValueError,'disk reserve'):
                PilotRunner(self.path)

    def test_root_9_GiB_refuses_start(self):
        with patch('shutil.disk_usage',side_effect=self.usage(9,100)):
            with self.assertRaisesRegex(ValueError,'disk reserve'):
                PilotRunner(self.path)

    def test_exact_reserves_accepted(self):
        with patch('shutil.disk_usage',side_effect=self.usage(10,50)):
            runner=PilotRunner(self.path)
            try:self.assertTrue(runner.space_check())
            finally:runner.close()


if __name__=='__main__':unittest.main(verbosity=2)
