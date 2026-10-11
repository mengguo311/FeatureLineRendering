import unittest
from pathlib import Path
import numpy as np
from cull_outcome import classify_author_mask
class CullOutcome(unittest.TestCase):
 def test_actual_all_removed(self):
  p=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01/scan63_result_v01/diagnosis/cull_cpu_arrays.npz')
  with np.load(p) as z:r=classify_author_mask(z['final_vertex_mask'],z['raw_faces'])
  self.assertEqual(r,{'status':'EMPTY_AFTER_AUTHOR_MASK','kept_vertices':0,'kept_faces':0,'official_metric_defined':False})
 def test_partial_vertices_without_face_is_empty(self):
  r=classify_author_mask(np.array([True,True,False]),np.array([[0,1,2]]))
  self.assertFalse(r['official_metric_defined']);self.assertEqual(r['kept_vertices'],2)
 def test_nonempty_faces_not_misclassified(self):
  r=classify_author_mask(np.array([True,True,True,False]),np.array([[0,1,2],[1,2,3]]))
  self.assertEqual(r['status'],'NONEMPTY_AUTHOR_MASK');self.assertEqual(r['kept_faces'],1)
 def test_corrupt_indices_rejected_not_negative_geometry(self):
  with self.assertRaises(ValueError):classify_author_mask(np.zeros(2,dtype=bool),np.array([[0,1,2]]))
if __name__=='__main__':unittest.main(verbosity=2)
