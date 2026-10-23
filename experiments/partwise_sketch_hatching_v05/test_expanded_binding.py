import runtime
import unittest
import numpy as np
from expanded_binding import combine_evidence, transition_counts
from membership import resolve


class ExpandedEvidenceTests(unittest.TestCase):
    def test_duplicate_camera_and_foreign_identity_rejected(self):
        block=dict(source_sha256='a',source_index=np.arange(3),camera_key='view1',score=np.zeros((3,6)))
        with self.assertRaises(ValueError):combine_evidence([block,block],3,'a')
        with self.assertRaises(ValueError):combine_evidence([dict(block,source_index=np.array([1,0,2]))],3,'a')
        with self.assertRaises(ValueError):combine_evidence([block],3,'b')

    def test_new_views_resolve_support_and_conflict_without_filling_unobserved(self):
        first=np.zeros((3,6));first[0,4]=1;first[1,4]=1
        second=first.copy();second[1]=0;second[1,2]=1
        blocks=[dict(source_sha256='a',source_index=np.arange(3),camera_key=str(i),score=v) for i,v in enumerate([first,second])]
        pv=combine_evidence(blocks,3,'a')
        old=resolve(pv[:1],.2,2,.7,.01);new=resolve(pv,.2,2,.7,.01)
        self.assertEqual(new['region_id'].tolist(),[4,0,0])
        self.assertEqual(new['reason'].tolist(),['supported','view_conflict','unobserved'])
        self.assertEqual(transition_counts(old,new)['unknown_to_supported'],1)
        np.testing.assert_array_equal(new['membership'][2],[1,0,0,0,0,0])

    def test_bad_evidence_rejected(self):
        for value in (-1.,np.nan):
            score=np.zeros((2,6));score[0,1]=value
            with self.assertRaises(ValueError):combine_evidence([dict(source_sha256='a',source_index=np.arange(2),camera_key='v',score=score)],2,'a')


if __name__=='__main__':unittest.main()
