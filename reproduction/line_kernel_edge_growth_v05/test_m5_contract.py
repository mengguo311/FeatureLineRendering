"""Test-first M5 public contract; original runner must reject before adaptation."""
import unittest
try:
    from progressive_runner import level_contract
except ModuleNotFoundError as exc:
    if exc.name != 'progressive_runner': raise
    from protected_runner import level_contract

class M5Contract(unittest.TestCase):
    def test_m5_uses_m4_predecessor(self):
        self.assertEqual(level_contract({'level':5,'predecessor_label':'M4'}),(5,'M5','M4'))

if __name__=='__main__':unittest.main()
