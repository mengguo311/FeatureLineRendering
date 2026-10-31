"""Synchronous bounded unit005 regression receipt; no full-scene science."""
from common import *
import contextlib,sys,unittest
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_005')
if __name__=='__main__':
    source=Path(__file__).resolve().parent;before={str(p):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for p in source.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    log=UNIT/'tests/GREEN_FINAL.log';start=now()
    with log.open('x') as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        suite=unittest.defaultTestLoader.discover(str(source),pattern='test_unit5.py');result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before);red=UNIT/'tests/RED_RECEIPT.json'
    receipt=dict(returncode=rc,started_utc=start,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,red_receipt=str(red),red_receipt_sha256=sha(red),tdd_status='Three genuine pre-implementation RED failures: predecessor M2_STATE, scene label, saved real three-fragment selection. Initial test resource-config KeyError preserved separately; subsequent equivalence/delivery checks are regressions',scope='124 real ficus M2 seedlets/573 kernels, ten hard fixtures, exact statistics equivalence,12-row native ficus routing, resume/hash tamper/incumbent rejection/later failure; no full-scene science',execution='Synchronous unittest, actual process return equals result.wasSuccessful()',python=sys.executable)
    target=UNIT/('TESTS_RECEIPT.json' if rc==0 else 'FAILED_TESTS_RECEIPT.json');js(target,receipt)
    print(json.dumps(dict(returncode=rc,tests=result.testsRun,receipt=str(target))));sys.exit(rc)
