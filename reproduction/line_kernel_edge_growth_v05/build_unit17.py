"""Bounded synchronous unit017 tests and actual exit/log receipts."""
from common import *
import unittest,contextlib,sys
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_017')
if __name__=='__main__':
    source=Path(__file__).resolve().parent;before={str(p):sha(p) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in source.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    prepath=UNIT/'tests/PREIMPLEMENTATION.json';pre=json.loads(prepath.read_text());verify(pre['source_files'])
    redpath=UNIT.parent/'unit_015/tests/RED_RECEIPT.json';red=json.loads(redpath.read_text());assert red['returncode']==1 and red['failures']==1 and red['errors']==0 and not red['implementation_existed'];assert sha(red['log'])==red['log_sha256']
    attempt=1
    while (UNIT/f'tests/GREEN_{attempt}.log').exists():attempt+=1
    log=UNIT/f'tests/GREEN_{attempt}.log';start=now()
    with log.open('x') as f,contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
        suite=unittest.TestSuite([unittest.defaultTestLoader.discover(str(source),pattern=p) for p in ('test_protected_contract.py','test_unit17.py')]);result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before);verify(pre['source_files'])
    receipt=dict(returncode=rc,started_utc=start,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,preimplementation_receipt=str(prepath),preimplementation_receipt_sha256=sha(prepath),historical_red_receipt=str(redpath),historical_red_receipt_sha256=sha(redpath),tdd_status='REGRESSION_ONLY: scene/control configuration transfer; all76 unit016 source files byte-unchanged. Historical genuine protected-policy RED remains unit015 evidence, not a new unit017 RED. No artificial failure manufactured.',scope='<=128 real scan65 M3 seedlets; small hard fixtures;120-kernel native export/resume/failure tests; no full-asset science',python=sys.executable,actual_process_result=True)
    js(UNIT/('TESTS_RECEIPT.json' if rc==0 else f'tests/FAILED_RECEIPT_{attempt}.json'),receipt);print(json.dumps(dict(returncode=rc,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log))));sys.exit(rc)
