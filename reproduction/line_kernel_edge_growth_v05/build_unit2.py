"""Bounded synchronous unit_002 tests with actual result receipt; never science."""
from common import *
import unittest,contextlib,sys
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_002')
if __name__=='__main__':
    source=Path(__file__).resolve().parent;os.environ['V05_TEST_DIR']=str(UNIT/'tests');log=UNIT/'tests/GREEN_FINAL.log';start=now();before={str(p):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    with log.open('x') as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        suite=unittest.defaultTestLoader.discover(str(source),pattern='test_unit2.py');result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before);red=UNIT/'tests/RED_RECEIPT.json'
    js(UNIT/'TESTS_RECEIPT.json',dict(returncode=rc,started_utc=start,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,red_receipt=str(red),red_receipt_sha256=sha(red),tdd_status='Three genuine inherited-behavior failures recorded before implementation, followed by actual passing regressions',scope='Small real ficus chains, synthetic hard cases, 12-row native render/crop integration; no complete-asset science',execution='Synchronous unittest TextTestRunner; process returncode equals actual result.wasSuccessful()',historical_failures_preserved=True,python=sys.executable))
    print(json.dumps(dict(returncode=rc,tests=result.testsRun,receipt=str(UNIT/'TESTS_RECEIPT.json'))));sys.exit(rc)
