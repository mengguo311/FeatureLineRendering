"""Fresh-view tests for UNKNOWN rendering and non-vacuous path coverage."""
import runtime
import unittest
import numpy as np
from transfer_audit import membership_projection, coverage_assessment, kernel_damage_bound


class TransferTests(unittest.TestCase):
    def test_original_row_soft_evidence_and_abstention_are_distinct(self):
        q=np.zeros((4,6));q[:,0]=1
        q[3]=[.1,0,0,0,.9,0];q[1]=[.2,.8,0,0,0,0]
        b=dict(membership=q,unknown=np.array([True,True,True,False]))
        t=dict(sample_index=np.array([0,0,1]),source_index=np.array([3,1,1]),weight=np.array([.3,.2,.5]))
        out=membership_projection(t,b,3)
        np.testing.assert_allclose(out['soft_q'][0],[.14,.32,0,0,.54,0])
        np.testing.assert_allclose(out['abstaining_q'][0],[.46,0,0,0,.54,0])
        np.testing.assert_allclose(out['abstaining_q'][1],[1,0,0,0,0,0])
        np.testing.assert_allclose(out['soft_q'][2],[1,0,0,0,0,0])
        np.testing.assert_allclose(out['mass'],[.5,.5,0])
        np.testing.assert_allclose(out['unknown_kernel_mass'],[.2,.5,0])

    def test_coverage_retains_occluded_zero_and_low_support_anchors(self):
        ps=dict(source_index=np.array([3,1,3,0]),weight=np.array([.4,.2,.2,.1]),
                eligible=np.array([True,True,True,False]),offsets=np.array([0,2,3,4,4]),
                unknown=np.array([False,False,True,True]),proxy_visible=np.array([True,True,False,True]),
                retained_mass=np.array([.6,.2,0,0]))
        gate=dict(min_supported_anchors=2,min_edited_anchor_fraction=.5,min_retained_mass_fraction=.05,
                  edit_mass_threshold=.01)
        out=coverage_assessment(ps,np.array([0,0,0,.1]),gate)
        np.testing.assert_allclose(out['edited_mass_per_anchor'],[.04,.02,0,0])
        self.assertTrue(out['coverage_gate']);self.assertEqual(out['attempted'],4)
        self.assertEqual(out['supported_anchors'],2)
        zero=coverage_assessment(ps,np.zeros(4),gate)
        self.assertFalse(zero['coverage_gate'])
        ps['unknown'][:]=True
        empty=coverage_assessment(ps,np.ones(4),gate)
        self.assertFalse(empty['coverage_scorable']);self.assertFalse(empty['coverage_gate'])
        self.assertIsNone(empty['edited_anchor_fraction'])

    def test_kernel_damage_is_bound_not_additive_pixel_damage(self):
        mass=np.array([[1,.5,0,.5,.5],[1,.5,0,.5,.5]])
        color=np.array([[1,0,0],[0,1,0]]);tint=np.array([.5,.5,0]);strength=np.ones(2)
        out=kernel_damage_bound(mass,color,strength,tint)
        np.testing.assert_allclose(out,[.5,.5])
        # Two opposite RGB changes can cancel at the same far pixel.
        actual=np.abs(((tint-color)*.5).sum(0)).sum()
        self.assertEqual(actual,0);self.assertGreater(out.sum(),actual)


if __name__=='__main__':unittest.main()
