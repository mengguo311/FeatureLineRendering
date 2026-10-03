#!/usr/bin/env python3
"""Run unchanged inherited CPU regressions with task-local fixture paths."""
import datetime
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
sys.dont_write_bytecode=True
ART=ROOT/'artifacts/hybrid_raster_trained_models_v1/independent_review'
SANDBOX=ROOT/'out/hybrid_raster_trained_models_v1/independent_review/regression_sandbox'
for name in ('out/hybrid_raster_evidence_v2/tmp','out/hybrid_raster_evidence_v2/test_tmp'):
    (SANDBOX/name).mkdir(parents=True,exist_ok=True)
from tests import test_hybrid_raster_io as io_tests
from tests import test_hybrid_raster_access as access_tests
from scripts import audit_hybrid_raster_access as audit
io_tests.TMP=SANDBOX/'out/hybrid_raster_evidence_v2/test_tmp'
access_tests.ROOT=SANDBOX; audit.ROOT=SANDBOX
os.chdir(SANDBOX)
modules=[
 'tests.test_hybrid_raster_evidence','tests.test_hybrid_raster_io',
 'tests.test_hybrid_raster_stage','tests.test_hybrid_raster_verifier',
 'tests.test_hybrid_raster_access','tests.test_hybrid_dense_v1',
 'tests.test_hybrid_overlay_video','tests.test_hybrid_extra_scenes',
 'tests.test_hao_mukai_source']
cases=['tests.test_hybrid_raster_native.NativeContractTest.'+name for name in (
 'test_04_exact_native_principal_point',
 'test_05_calibration_rejects_changed_or_nonfinite_buffers',
 'test_06_export_validation_rejects_wrong_id_shape_and_mass')]
started=time.monotonic()
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules+cases))
report=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,
 errors=len(result.errors),failures=len(result.failures),skipped=len(result.skipped),
 modules=modules,native_cpu_cases=cases,elapsed_seconds=time.monotonic()-started,
 created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 interpreter=sys.executable,fixture_sandbox=str(SANDBOX),source_files_modified=False,
 qualification='Unchanged inherited CPU fixtures only; no GPU launch or new-scene experiment evidence',
 excluded_gpu_cases='3 native CUDA fixtures and 4 old wrapper GPU tests not launched in CPU audit')
(ART/'PRIOR_CPU_TESTS.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
