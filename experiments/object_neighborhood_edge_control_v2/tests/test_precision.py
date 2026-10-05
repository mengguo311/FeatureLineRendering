import unittest,sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT
from data import view
class PrecisionTests(unittest.TestCase):
    def test_diagnostic_fit_precision_matches_native_training_png(self):
        manifest=json.loads((OUT/'data_manifest.json').read_text());f=manifest['roles']['diagnostic-supervision'][0];v=view(f,'diagnostic-supervision')
        self.assertLess(np.max(np.abs(v['rgb']*255-np.round(v['rgb']*255))),1e-5)
        self.assertGreater(np.max(np.abs(v['float_rgb']-v['rgb'])),0)
if __name__=='__main__':unittest.main()
