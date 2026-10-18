from env import *
import unittest
from test_color import ColorTests
from test_render import RenderTests
from test_protocol import ProtocolTests
s=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(x) for x in [ColorTests,RenderTests,ProtocolTests]);r=unittest.TextTestRunner(verbosity=2).run(s);raise SystemExit(not r.wasSuccessful())
