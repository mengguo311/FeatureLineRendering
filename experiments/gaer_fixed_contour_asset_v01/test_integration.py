import unittest,subprocess,sys,json
from pathlib import Path

class AssetIntegration(unittest.TestCase):
    def test_native_to_fixed_3d_export(self):
        r=Path(__file__).resolve().parents[2]
        result=subprocess.run([sys.executable,str(Path(__file__).with_name("run.py"))],cwd=r,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for scene in ["lego","chair"]:
            p=r/"artifacts/gaer_fixed_contour_asset_v01"/scene
            self.assertGreater((p/"fixed_contour.glb").stat().st_size,100)
            audit=json.loads((p/"EXPORT_AUDIT.json").read_text())
            self.assertTrue(audit["serialization_roundtrip_pass"])
            self.assertGreater(audit["vertices"],0)
            self.assertLess(audit["construction_reprojection_max_px"],1e-5)

if __name__=="__main__":unittest.main()
