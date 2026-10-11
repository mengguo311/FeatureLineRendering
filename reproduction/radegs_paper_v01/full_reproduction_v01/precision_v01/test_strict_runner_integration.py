"""CPU-only query and actual Runner integration; subprocess spawn is fake."""
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import strict_diagnostic_runner
import strict_shared_policy as policy
import test_diagnostic_runner as base


class StrictRunnerIntegrationTests(base.DiagnosticRunnerTests):
    def setUp(self):
        base.SAMPLE[0]['free_mib']=38000
        super().setUp()

    def test_actual_free_below_threshold_resets_60_second_gate(self):
        reserved=[dict(base.SAMPLE[0],memory_mib=36000,free_mib=12000)]
        for now,sample in [(0,base.SAMPLE),(59,reserved),(60,base.SAMPLE),(119,base.SAMPLE)]:
            self.e.tick(sample,now)
        self.assertFalse(self.spawned)
        self.e.tick(base.SAMPLE,120)
        self.assertEqual(len(self.spawned),1)

    def test_low_actual_free_requests_only_own_stop(self):
        self.e.tick(base.SAMPLE,0);self.e.tick(base.SAMPLE,60)
        low=[dict(base.SAMPLE[0],memory_mib=46600,free_mib=1800)]
        with patch.object(self.e,'request_own_stop') as stop:
            self.e.tick(low,65);stop.assert_called_once()


class QueryTests(unittest.TestCase):
    def xml(self,free='12000 MiB'):
        return ('<nvidia_smi_log><gpu><uuid>'+policy.GPU+'</uuid>'
                '<fb_memory_usage><total>49140 MiB</total><used>36000 MiB</used>'
                '<free>'+free+'</free></fb_memory_usage>'
                '<utilization><gpu_util>0 %</gpu_util></utilization>'
                '<processes><process_info><pid>123</pid><type>C</type></process_info>'
                '</processes></gpu></nvidia_smi_log>')

    def test_one_snapshot_includes_actual_free_and_foreign_context(self):
        with patch.object(policy.subprocess,'run',return_value=type('R',(),{'stdout':self.xml()})()) as run:
            result=policy.query()
        self.assertEqual(result[0]['free_mib'],12000)
        self.assertFalse(policy.can_start(result[0]))
        self.assertEqual(run.call_count,1)
        self.assertIn('--id='+policy.GPU,run.call_args.args[0])

    def test_invalid_and_missing_free_fail_closed(self):
        for value in ['N/A','50000 MiB','-1 MiB']:
            self.assertIsNone(policy.parse(self.xml(value)))
        self.assertIsNone(policy.parse(self.xml().replace('<free>12000 MiB</free>','')))

    def test_failed_query_fails_closed(self):
        with patch.object(policy.subprocess,'run',side_effect=subprocess.TimeoutExpired('nvidia-smi',20)):
            self.assertIsNone(policy.query())


if __name__=='__main__':unittest.main(verbosity=2)
