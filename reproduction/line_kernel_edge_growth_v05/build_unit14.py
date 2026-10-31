"""Serial small regressions and actual receipts only; no full-asset launch."""
from common import *
import unittest,contextlib,sys
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_014')
if __name__=='__main__':
    source=Path(__file__).resolve().parent
    before={str(p):sha(p) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in source.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    pre=UNIT/'tests/PREIMPLEMENTATION.json';pp=json.loads(pre.read_text());verify(pp['source_files'])
    historical=UNIT.parent/'unit_012/tests/RED_COVERAGE_RECEIPT.json';hr=json.loads(historical.read_text())
    assert hr['returncode']==1 and hr['failures']==1 and hr['errors']==0 and not hr['implementation_existed']
    assert sha(hr['log'])==hr['log_sha256']
    log=UNIT/'tests/REGRESSION.log';start=now()
    with log.open('x') as f,contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
        suite=unittest.TestSuite([unittest.defaultTestLoader.discover(str(source),pattern=p) for p in ('test_endpoint_contract.py','test_unit14.py')])
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before);verify(pp['source_files'])
    receipt=dict(returncode=rc,started_utc=start,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,preimplementation_receipt=str(pre),preimplementation_receipt_sha256=sha(pre),historical_red_receipt=str(historical),historical_red_receipt_sha256=sha(historical),tdd_status='REGRESSION_ONLY: scene/configuration transfer; all63 unit013 source files byte-unchanged. Historical genuine endpoint RED remains unit012 evidence, not a new unit014 RED. No artificial failure manufactured.',scope='At most128 real scan65 M3 seedlets plus finite hard/dense fixtures,120-kernel native routing/checkpoint/resume/later-failure/control-mismatch tests; no full-asset science.',execution='Synchronous unittest; process returncode equals result',python=sys.executable)
    js(UNIT/('TESTS_RECEIPT.json' if rc==0 else 'FAILED_TESTS_RECEIPT.json'),receipt)
    print(json.dumps(dict(returncode=rc,tests=result.testsRun,log=str(log))));sys.exit(rc)
