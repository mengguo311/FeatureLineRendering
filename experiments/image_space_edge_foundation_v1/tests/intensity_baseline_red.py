"""Expected behavioral RED: unchanged classic luminance cannot see isoluminance."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fixtures import fixtures
from boundary import classic_response
class IntensityRegression(unittest.TestCase):
    def test_equal_luminance_color_boundary(self):
        rgb,t=fixtures()['color_step'];soft,_=classic_response(rgb)
        self.assertGreater(float(soft[15:-15,t['center']-2:t['center']+3].max(axis=1).mean()),.25)
if __name__=='__main__':unittest.main()
