"""Run bounded tests synchronously and preserve the actual RED/GREEN receipts."""
from common import *
import unittest,contextlib,sys
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_010')
if __name__=='__main__':
    source=Path(__file__).resolve().parent
    before={str(p):sha(p) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in source.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    red=UNIT/'tests/RED_RECEIPT.json';rr=json.loads(red.read_text());assert rr['returncode']==1 and rr['failures']==1 and rr['errors']==0 and not rr['implementation_existed'];verify(rr['source_files']);assert sha(rr['log'])==rr['log_sha256']
    log=UNIT/'tests/GREEN_FINAL_2.log';start=now()
    with log.open('x') as f,contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
        suite=unittest.TestSuite([unittest.defaultTestLoader.discover(str(source),pattern=p) for p in ('test_local_tangent.py','test_unit10.py')]);result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before)
    receipt=dict(returncode=rc,started_utc=start,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,red_receipt=str(red),red_receipt_sha256=sha(red),tdd_status='Genuine pre-implementation RED: coincident curved alternatives produced0 rather than1 commits after2 real fits. Identical contract GREEN under local tangent equivalence; full bounded regression suite follows. Historical source files unchanged.',scope='<=128 real M3 seedlets, hard fixtures and12-row native render/checkpoint/control comparison; no complete-asset science.',execution='Synchronous unittest, actual process exit equals result',python=sys.executable)
    target=UNIT/('TESTS_RECEIPT.json' if rc==0 else 'FAILED_TESTS_RECEIPT.json');js(target,receipt);print(json.dumps(dict(returncode=rc,tests=result.testsRun,receipt=str(target))));sys.exit(rc)
