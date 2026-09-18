"""Verdicts and artifact totals cannot silently promote invalid prerequisites."""
import copy
import tempfile
from pathlib import Path
import numpy as np
import unittest
from test_multiscene import CFG


class ReportTests(unittest.TestCase):
    def test_route_b_rgb_pass_does_not_override_bad_parent_quality(self):
        from src.multiscene_report import scene_prerequisites
        quality=[dict(eligibility=dict(passed=False,calibration_pass=True)),
                 dict(eligibility=dict(passed=True,calibration_pass=True))]
        controlled=dict(valid_parent_geometry=True,variants=[dict(name='small',eligibility=dict(passed=True))])
        r=scene_prerequisites('lego',quality,dict(passed=False),controlled)
        self.assertFalse(r['route_a']['eligible']);self.assertFalse(r['route_b']['eligible'])
        self.assertEqual(r['route_b']['rgb_qualified_doses'],['small'])
        self.assertFalse(r['may_run_local_probe']);self.assertEqual(r['verdict'],'UNDETERMINED')
        quality[0]['eligibility']['passed']=True
        r=scene_prerequisites('lego',quality,dict(passed=False),controlled)
        self.assertTrue(r['may_run_local_probe']);self.assertTrue(r['route_b']['eligible'])

    def test_combined_decision_cannot_rescue_a_failed_scene_or_certify_missing_review(self):
        from src.multiscene_report import combined_decision
        scenes=[dict(engineering_ready=True,input_valid=True,route_a=True,route_b=True,
            machine_pass=True,seed_stable=True,controlled_stable=True,manual_certified=False,
            negative_evidence=False,image_only_certified=False,gs_benefit=True) for _ in range(4)]
        self.assertEqual(combined_decision(scenes),'UNDETERMINED')
        for s in scenes:s['manual_certified']=True
        self.assertEqual(combined_decision(scenes),'FOUNDATION-GO')
        scenes[-1]['machine_pass']=False;scenes[-1]['negative_evidence']=True
        self.assertEqual(combined_decision(scenes),'STOP_B')
        scenes[-1]['input_valid']=False
        self.assertEqual(combined_decision(scenes),'UNDETERMINED')
        scenes[-1]['engineering_ready']=False
        self.assertEqual(combined_decision(scenes),'ENGINEERING_NOT_READY')
        for s in scenes:
            s.update(engineering_ready=True,input_valid=True,machine_pass=True,negative_evidence=False,
                     route_b=False,controlled_stable=False,manual_certified=False)
        self.assertEqual(combined_decision(scenes),'SEED_ONLY')
        for s in scenes:s.update(route_a=False,seed_stable=False,route_b=True,controlled_stable=True)
        self.assertEqual(combined_decision(scenes),'CONTROLLED_ONLY')

    def test_report_consistency_detects_tampered_counts_and_qualification_rows(self):
        from src.multiscene_report import render_prerequisite_report,check_report
        result=dict(verdict='UNDETERMINED',totals=dict(training_expected=8,training_complete=8,
            seeds_eligible=0,doses_expected=36,doses_measured=36,doses_rgb_qualified=24,
            doses_invariance_eligible=0),scenes=[dict(scene='lego',verdict='UNDETERMINED',
            route_a=dict(eligible=False),route_b=dict(eligible=False,rgb_qualified_doses=['a']),
            gates=dict(G0='INVALID',G1='NOT_EVALUATED',G2_machine='NOT_EVALUATED',
                G2_manual='UNCERTIFIED',G3='NOT_EVALUATED',G4='NOT_EVALUATED',G5='UNCERTIFIED'))],
            training_rows=[],dose_rows=[dict(scene='lego',name='a',family='redistribute',dose=.03125,
                qualified_pairs=32,total_pairs=32,psnr_min=40.1,ssim_min=.996,p99_max=.02,
                selected_mass_min=.4,minor_mass_min=.02,passed=True,invariance_eligible=False)],
            unreached=['local probes','glyphs','video'],diagnosis='Frozen 400px quality failed.')
        text=render_prerequisite_report(result)
        self.assertTrue(check_report(result,text))
        with self.assertRaises(AssertionError):check_report(result,text.replace('doses_measured: 36','doses_measured: 35'))
        with self.assertRaises(AssertionError):check_report(result,text.replace('40.100000','41.100000'))

    def test_pair_measurements_use_the_identical_photo_roi_and_keep_each_view(self):
        from src.multiscene_report import pair_measurements
        cfg=copy.deepcopy(CFG);cfg['splits']['TRAIN']=[1]
        with tempfile.TemporaryDirectory() as tmp:
            paths=[Path(tmp)/str(seed) for seed in [1729,2718]]
            roi=np.ones((16,16),bool);gt=np.full((16,16,3),.5)
            for k,p in enumerate(paths):
                p.mkdir()
                for split in ['train','val']:
                    np.savez(p/f'{split}_001.npz',roi=roi,rgb_0=gt+.01*(k+1),rgb_1=gt+.01*(k+1),gt_0=gt,gt_1=gt)
            rows=pair_measurements(paths,cfg)
            self.assertEqual(len(rows),4)
            self.assertAlmostEqual(rows[0]['rmse_pair'],.01)
            self.assertAlmostEqual(rows[0]['rmse_seed0'],.01)
            self.assertAlmostEqual(rows[0]['rmse_seed1'],.02)
            np.savez(paths[1]/'train_001.npz',roi=~roi,rgb_0=gt,rgb_1=gt,gt_0=gt,gt_1=gt)
            with self.assertRaisesRegex(ValueError,'ROI'):pair_measurements(paths,cfg)


if __name__=='__main__':unittest.main()
