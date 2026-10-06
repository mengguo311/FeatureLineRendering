import unittest
import numpy as np
import cv2
from metrics import boundary_iou

class MetricTests(unittest.TestCase):
    def test_boundary_iou_official_square_erosion(self):
        a=np.zeros((80,80),dtype=np.uint8)
        for i in range(10,70):a[i,10:i+1]=1
        b=np.roll(a,2,axis=1)
        def boundary(x):
            pad=cv2.copyMakeBorder(x,1,1,1,1,cv2.BORDER_CONSTANT,value=0)
            r=max(1,int(round(.02*np.hypot(*x.shape))))
            return x-cv2.erode(pad,np.ones((3,3),np.uint8),iterations=r)[1:-1,1:-1]
        x,y=boundary(a),boundary(b)
        expected=np.logical_and(x,y).sum()/np.logical_or(x,y).sum()
        self.assertAlmostEqual(boundary_iou(a.astype(bool),b.astype(bool)),expected,places=12)
