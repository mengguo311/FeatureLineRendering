"""Synthetic report aggregation checks, separate from frozen producer tests."""
import json
from pathlib import Path
import tempfile
import unittest
import summarize_results as s

class Summary(unittest.TestCase):
    def frame(self,n,mean,p05,bcount):
        diagnostics={'arms':{},'overlap':dict(A_only=1,B_only=bcount,shared=2,mass=.25),
                     'raw':{'top4_coverage':dict(count=n,mean=mean,min=.0,max=1.,p05=p05)}}
        for arm in ('A','B','C'):
            diagnostics['arms'][arm]={'mass':2.,'support':4,'strata':{k:dict(pixels=10,mass=.5,support=2) for k in ['background','outline','interior']}}
        return {'diagnostics':diagnostics,'B_only_argmax_counts':{k:bcount if i==0 else 0 for i,k in enumerate(s.CHANNELS)}}
    def test_coverage_weighting_not_mean_of_means(self):
        value=s.aggregate_group([self.frame(10,.2,.1,2),self.frame(30,.8,.7,3)])
        self.assertAlmostEqual(value['top4_coverage']['pixel_weighted_mean'],.65)
        self.assertAlmostEqual(value['top4_coverage']['mean_of_frame_p05'],.4)
        self.assertEqual(value['B_only_argmax_counts']['delta_D'],5)
        self.assertEqual(value['B_only_argmax_fractions']['delta_D'],1.)
        self.assertEqual(value['arms']['A']['mass_per_frame']['sum'],4.)
        self.assertEqual(value['arms']['A']['strata']['interior']['support_fraction'],.2)
    def test_empty_group_no_manufactured_measurement(self):
        value=s.aggregate_group([])
        self.assertEqual(value['frames'],0)
        self.assertIsNone(value['top4_coverage']['pixel_weighted_mean'])
        self.assertIsNone(value['arms']['A']['mass_per_frame']['mean'])
    def test_absent_production_remains_missing49(self):
        with tempfile.TemporaryDirectory(dir=s.OUT/'tests') as d:
            value=s.summarize_scene('hotdog',Path(d)/'art',Path(d)/'out')
            self.assertEqual(value['status'],'MISSING_PRODUCTION')
            self.assertEqual(len(value['missing_keys']),49)
            self.assertEqual(value['frames'],[])
    def test_consumed_payload_corruption_rejected(self):
        with tempfile.TemporaryDirectory(dir=s.OUT/'tests') as d:
            path=Path(d);(path/'diagnostics.json').write_text('{"synthetic":true}')
            context={'synthetic':True};seal={'schema':'hybrid-raster-frame-v1','context':context,'context_sha256':s.canonical(context),'files':{'diagnostics.json':s.sha(path/'diagnostics.json')}}
            (path/'SEAL.json').write_text(json.dumps(seal));(path/'SEAL.sha256').write_text(s.sha(path/'SEAL.json'))
            self.assertEqual(s.check_seal_envelope(path,context,['diagnostics.json']),seal)
            (path/'diagnostics.json').write_text('{}')
            with self.assertRaises(ValueError):s.check_seal_envelope(path,context,['diagnostics.json'])
    def test_malformed_manifest_preserves_explicit_invalid_record(self):
        with tempfile.TemporaryDirectory(dir=s.OUT/'tests') as d:
            path=Path(d);(path/'art/hotdog').mkdir(parents=True)
            (path/'art/hotdog/FRAMES.json').write_text('{broken')
            value=s.safe_summarize_scene('hotdog',path/'art',path/'out')
            self.assertEqual(value['status'],'PARTIAL_OR_INVALID')
            self.assertIsNone(value['counts']);self.assertIsNone(value['missing_keys'])
            self.assertIn('JSONDecodeError',value['errors'][0])

if __name__=='__main__':unittest.main(verbosity=2)
