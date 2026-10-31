"""Synchronous bounded unit006 regression receipt; no full-scene science."""
from common import *
import contextlib,sys,unittest
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_006')
if __name__=='__main__':
    source=Path(__file__).resolve().parent;before={str(p):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for p in source.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    log=UNIT/'tests/GREEN_VERIFIED.log';start=now()
    with log.open('x') as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        suite=unittest.defaultTestLoader.discover(str(source),pattern='test_unit6.py');result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before);red=UNIT/'tests/RED_NOT_APPLICABLE.json'
    receipt=dict(returncode=rc,started_utc=start,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,red_receipt=str(red),red_receipt_sha256=sha(red),tdd_status='REGRESSION_ONLY: no production behavior change; frozen unit005 runner/core/selector reused byte-for-byte. No fabricated RED. Unit006 configuration and scan65 routing are verified by bounded actual tests.',scope='At most128 real scan65 M2 seedlets selected by sealed predecessor proposal order, ten hard fixtures, pinned unit005 exact numerical/statistical equivalence,12-row scan65 native routing, resume/hash tamper/incumbent rejection/later failure and actual config interface; counts in raw log. No full-scene science',execution='Synchronous unittest, actual process return equals result.wasSuccessful()',python=sys.executable)
    target=UNIT/('TESTS_RECEIPT.json' if rc==0 else 'FAILED_TESTS_RECEIPT.json');js(target,receipt)
    print(json.dumps(dict(returncode=rc,tests=result.testsRun,receipt=str(target))));sys.exit(rc)
