from env import *
import unittest
from test_color import ColorTests
from test_render import RenderTests
from test_protocol import ProtocolTests
from test_labels import LabelTests
from test_layout import LayoutTests
s=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(x) for x in [ColorTests,RenderTests,ProtocolTests,LabelTests,LayoutTests]);r=unittest.TextTestRunner(verbosity=2).run(s);raise SystemExit(not r.wasSuccessful())
