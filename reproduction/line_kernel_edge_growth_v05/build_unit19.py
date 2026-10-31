"""Synchronous unit019 bounded regressions; no full-asset science."""
from common import *
import unittest,contextlib,sys
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_019')
if __name__=='__main__':
    source=Path(__file__).resolve().parent;before={str(p):sha(p) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in source.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    pre=json.loads((UNIT/'tests/PREIMPLEMENTATION.json').read_text());verify(pre['source_files'])
    attempt=1
    while (UNIT/f'tests/REGRESSION_{attempt}.log').exists():attempt+=1
    log=UNIT/f'tests/REGRESSION_{attempt}.log';start=now()
    with log.open('x') as f,contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
        suite=unittest.TestSuite([unittest.defaultTestLoader.discover(str(source),pattern=p) for p in ('test_m5_contract.py','test_protected_contract.py','test_unit19.py')]);result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before);verify(pre['source_files'])
    receipt=dict(returncode=rc,started_utc=start,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,tdd_status='REGRESSION_ONLY_SCENE_CONFIG: no new numerical behavior; historical unit018 genuine RED remains historical',historical_red_receipt=str(UNIT.parent/'unit_018/tests/RED_RECEIPT.json'),historical_red_receipt_sha256=sha(UNIT.parent/'unit_018/tests/RED_RECEIPT.json'),scope='<=128 actual ficus M4 seedlets; hard/protection fixtures;120-kernel ficus routing/native resume/later failure; no full-asset science',python=sys.executable,actual_process_result=True)
    js(UNIT/('TESTS_RECEIPT.json' if rc==0 else f'tests/FAILED_RECEIPT_{attempt}.json'),receipt);print(json.dumps(dict(returncode=rc,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log))));sys.exit(rc)
