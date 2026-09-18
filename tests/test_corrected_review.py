import tempfile,unittest,json
from pathlib import Path
import numpy as np
from src.corrected_visuals import write_png

class ReviewTests(unittest.TestCase):
    def test_blind_package_has_random_identities_and_separate_key(self):
        from src.corrected_review import blind_package
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);a=root/'method.png';b=root/'control.png'
            write_png(a,np.zeros((400,400,3)));write_png(b,np.ones((400,400,3)))
            blind_package(root/'review',root/'key.json',[dict(name='fixed',left=a,right=b)],seed=1234)
            key=json.loads((root/'key.json').read_text());self.assertEqual(key['independent_reviews_completed'],0)
            self.assertNotIn('key.json',[p.name for p in (root/'review').rglob('*')])
            pngs=list((root/'review').glob('*.png'));self.assertEqual(len(pngs),2)
            self.assertEqual({p.read_bytes() for p in pngs},{a.read_bytes(),b.read_bytes()})
            self.assertIn('pending',(root/'review/README.md').read_text().lower())
