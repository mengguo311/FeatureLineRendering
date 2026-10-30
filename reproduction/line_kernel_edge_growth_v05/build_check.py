"""Synchronous bounded BUILD tests, with actual programmatic exit receipt."""
from common import *
import unittest,contextlib,sys
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_001')
if __name__=='__main__':
    source=Path(__file__).resolve().parent;os.environ['V05_TEST_DIR']=str(UNIT/'tests');log=UNIT/'tests/GREEN_FINAL.log';started=now();before={str(p):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    with log.open('x') as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        suite=unittest.defaultTestLoader.discover(str(source),pattern='test_*.py');result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before)
    receipt=dict(returncode=rc,started_utc=started,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,red_receipt=str(UNIT/'tests/RED_RECEIPT.json'),red_receipt_sha256=sha(UNIT/'tests/RED_RECEIPT.json'),tdd_status='GENUINE_RED_THEN_GREEN_CHECKPOINT_ORDER; equivalence and delivery regressions before science',historical_v04_tdd='POST_HOC_NOT_CERTIFIED',execution='unittest TextTestRunner in this synchronous process; exit status equals actual result.wasSuccessful()',scope='12-row fitting/native render integration, 128 deterministic real L1 carriers, small hard cases; NO complete-asset science',preserved_attempt_logs=['RED.log','GREEN_CHECKPOINT.log','EQUIVALENCE_1.log','EQUIVALENCE_2.log','GREEN_ALL_1.log'],reference='final v04 batched algorithm; archived scalar full ranking equivalence NOT_VERIFIED')
    js(UNIT/'TESTS_RECEIPT.json',receipt);print(json.dumps(dict(returncode=rc,tests=result.testsRun,receipt=str(UNIT/'TESTS_RECEIPT.json'))));sys.exit(rc)
