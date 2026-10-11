import unittest
from unittest.mock import patch
import strict_shared_policy as policy


def sample(free=12288, used=30000, util=0, pids=(123,)):
    return dict(uuid=policy.GPU, total_mib=49140, memory_mib=used,
                free_mib=free, util_percent=util,
                contexts=[dict(pid=p, type='C') for p in pids])


class ActualFreeTests(unittest.TestCase):
    def test_reserved_memory_not_available_for_launch(self):
        g=sample(free=12000,used=36000)
        self.assertGreaterEqual(g['total_mib']-g['memory_mib'],12288)
        self.assertFalse(policy.can_start(g))

    def test_missing_free_fails_closed(self):
        g=sample();g.pop('free_mib')
        self.assertFalse(policy.can_start(g))

    def test_free_stop_threshold_uses_actual_free(self):
        self.assertTrue(policy.conflict([sample(free=1800,used=46600)],policy.GPU,{77},{123}))

    def test_missing_free_stops_owned_stage(self):
        g=sample();g.pop('free_mib')
        self.assertTrue(policy.conflict([g],policy.GPU,{77},{123}))

    def test_authorized_shared_boundaries(self):
        self.assertTrue(policy.can_start(sample(free=12288,util=10)))
        self.assertFalse(policy.can_start(sample(free=12287)))
        self.assertFalse(policy.can_start(sample(util=11)))
        g=sample();g['uuid']='GPU-not-authorized'
        self.assertFalse(policy.can_start(g))
        self.assertFalse(policy.conflict([sample(free=2048,pids=(123,77))],policy.GPU,{77},{123}))
        self.assertTrue(policy.conflict([sample(pids=(123,77,99))],policy.GPU,{77},{123}))
        self.assertTrue(policy.conflict(None,policy.GPU,{77},{123}))

    def test_invalid_memory_cannot_admit(self):
        self.assertFalse(policy.can_start(sample(free=49141)))
        self.assertFalse(policy.can_start(sample(free=-1)))


if __name__=='__main__':unittest.main(verbosity=2)
