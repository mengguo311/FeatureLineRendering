import runtime
import tempfile
import unittest
from pathlib import Path
from catalog import file_record, check_records

class IntegrityTests(unittest.TestCase):
    def test_missing_and_corrupt_evidence_is_rejected(self):
        scratch = runtime.UNIT / 'scratch'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            p = Path(folder) / 'evidence.txt'
            p.write_text('saved scientific result')
            records = [file_record(p, 'fixture')]
            self.assertEqual(check_records(records), [])
            p.write_text('changed scientific result')
            self.assertEqual(check_records(records)[0]['kind'], 'mismatch')
            p.unlink()
            self.assertEqual(check_records(records)[0]['kind'], 'missing')

    def test_cannot_write_decision_old_unit_or_escape(self):
        forbidden = [runtime.UNIT/'DECISION.json', runtime.ROOT/'units/unit_004/STATUS.json',
                     runtime.ROOT/'orchestration/BRIEF.md', runtime.UNIT/'scratch/../../unit_004/x']
        for path in forbidden:
            with self.assertRaises(ValueError): runtime.guard(path)
        self.assertEqual(runtime.guard(runtime.UNIT/'AUDIT.json'), runtime.UNIT/'AUDIT.json')

if __name__ == '__main__':
    unittest.main()
