import unittest
import numpy as np
from edge_profiles import measure, linear_to_srgb, lab

class ProfileTests(unittest.TestCase):
    def test_linear_width(self):
        t=np.linspace(-20,20,801); f=1/(1+np.exp(-t/2))
        rgb=np.array([.08,.1,.2])+f[:,None]*np.array([.5,.3,.2])
        p=measure(t,rgb)
        self.assertAlmostEqual(p['width_px'],4*np.log(9),delta=.03)
        self.assertGreater(p['deltaE76_D65_2deg'],10)
    def test_low_contrast_and_hidden_null(self):
        t=np.arange(21); c=np.ones((21,3))*.4
        self.assertIsNone(measure(t,c)['width_px'])
        self.assertEqual(measure(t,c,visible=False)['reason'],'hidden')
    def test_nonmonotonic_refusal(self):
        t=np.linspace(-20,20,801); f=1/(1+np.exp(-t/2))+.5*np.sin(t)*np.exp(-t*t/30)
        c=.1+f[:,None]*np.array([[.6,.4,.2]])
        self.assertIsNone(measure(t,c)['width_px'])
    def test_lab_conditions(self):
        self.assertAlmostEqual(lab(np.ones(3))[0],100,delta=.001)
        self.assertAlmostEqual(linear_to_srgb(np.array([.18]))[0],.461356,delta=1e-5)
