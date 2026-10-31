"""Bounded scan65 M4 regressions and actual test receipt; no full science."""
from common import *
import contextlib,sys,unittest
UNIT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units/unit_009')
if __name__=='__main__':
    source=Path(__file__).resolve().parent
    before={str(p):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for p in source.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    log=UNIT/'tests/GREEN_FINAL.log';start=now()
    with log.open('x') as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
        suite=unittest.defaultTestLoader.discover(str(source),pattern='test_unit9.py')
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    rc=0 if result.wasSuccessful() else 1;verify(before)
    pre=UNIT/'tests/PREIMPLEMENTATION_RECEIPT.json';predata=json.loads(pre.read_text());assert predata['returncode']==0
    verify(predata['source_files'])
    receipt=dict(returncode=rc,started_utc=start,ended_utc=now(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),log=str(log),log_sha256=sha(log),source_files=before,preimplementation_receipt=str(pre),preimplementation_receipt_sha256=sha(pre),tdd_status='No new scientific/runner behavior: all36 pre-existing source files unchanged. Nine pre-implementation scan65 M4 regressions already GREEN before unit009 config builder existed. No new RED claimed; historical unit007 RED remains historical. Config/interface checks added for this unit.',red_status='NOT_APPLICABLE_UNCHANGED_PRODUCTION_BEHAVIOR',scope='At most128 deterministic real scan65 M3 seedlets plus ten hard fixtures; pinned unit008 core/statistics equivalence;12-row native M4/history colors, incumbent/restore/hash/later-failure preservation; exact config/all-source interface. No complete-asset science.',execution='Synchronous unittest; process return equals result.wasSuccessful()',python=sys.executable,production_source_unchanged=True)
    target=UNIT/('TESTS_RECEIPT.json' if rc==0 else 'FAILED_TESTS_RECEIPT.json');js(target,receipt)
    print(json.dumps(dict(returncode=rc,tests=result.testsRun,receipt=str(target))));sys.exit(rc)
