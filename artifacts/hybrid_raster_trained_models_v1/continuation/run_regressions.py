"""Unchanged selected CPU tests; bind fixture writes to authorized external storage."""
import argparse,datetime,hashlib,importlib,json,os,sys,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artifacts/hybrid_raster_trained_models_v1'
EXTERNAL=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1')

def main():
    p=argparse.ArgumentParser();p.add_argument('--group',choices=['transport','independent','acquisition','inherited'],required=True);a=p.parse_args()
    sandbox=EXTERNAL/'tests'/('regression_'+a.group)
    sandbox.mkdir(parents=True,exist_ok=True)
    sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ART/'transport'),str(ART/'independent_review'),str(ART/'acquisition/tests')]
    os.environ['TMPDIR']=str(EXTERNAL/'tmp');os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['PYTHONDONTWRITEBYTECODE']='1'
    import tempfile
    tempfile.tempdir=str(EXTERNAL/'tmp')
    if a.group=='transport':
        import test_adapters,test_runner,test_summarize_results
        for m in (test_adapters.a,test_runner.r,test_summarize_results.s):m.OUT=sandbox
        test_runner.r.native.STAGE=sandbox
        (sandbox/'tests').mkdir(exist_ok=True)
        modules=[test_adapters,test_runner,test_summarize_results];cases=[]
    elif a.group=='independent':
        import test_verify_experiment,test_checkpoint_numeric,test_pinned_source
        test_verify_experiment.TMP=sandbox/'tmp';test_checkpoint_numeric.OUT=sandbox
        modules=[test_verify_experiment,test_checkpoint_numeric,test_pinned_source];cases=[]
    elif a.group=='acquisition':
        import test_acquisition
        test_acquisition.HERE=sandbox/'a/b/c'
        test_acquisition.HERE.mkdir(parents=True,exist_ok=True)
        source_manifest=ART/'acquisition/SOURCE_MANIFEST.json'
        fixture_manifest=test_acquisition.HERE/'SOURCE_MANIFEST.json'
        if fixture_manifest.exists():
            assert fixture_manifest.read_bytes()==source_manifest.read_bytes()
        else:
            fixture_manifest.write_bytes(source_manifest.read_bytes())
        (sandbox/'out/hybrid_raster_trained_models_v1/training').mkdir(parents=True,exist_ok=True)
        modules=[test_acquisition];cases=[]
    else:
        from tests import test_hybrid_raster_io as io_tests,test_hybrid_raster_access as access_tests
        from scripts import audit_hybrid_raster_access as audit
        for name in ('out/hybrid_raster_evidence_v2/tmp','out/hybrid_raster_evidence_v2/test_tmp'):(sandbox/name).mkdir(parents=True,exist_ok=True)
        io_tests.TMP=sandbox/'out/hybrid_raster_evidence_v2/test_tmp';access_tests.ROOT=sandbox;audit.ROOT=sandbox
        names=['tests.test_hybrid_raster_evidence','tests.test_hybrid_raster_io','tests.test_hybrid_raster_stage','tests.test_hybrid_raster_verifier','tests.test_hybrid_raster_access','tests.test_hybrid_dense_v1','tests.test_hybrid_overlay_video','tests.test_hybrid_extra_scenes','tests.test_hao_mukai_source']
        modules=[importlib.import_module(n) for n in names]
        cases=['tests.test_hybrid_raster_native.NativeContractTest.'+n for n in ('test_04_exact_native_principal_point','test_05_calibration_rejects_changed_or_nonfinite_buffers','test_06_export_validation_rejects_wrong_id_shape_and_mass')]
    sources={str(Path(m.__file__).resolve()):hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in modules}
    os.chdir(sandbox)
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules]+[unittest.defaultTestLoader.loadTestsFromNames(cases)])
    start=time.monotonic();r=unittest.TextTestRunner(verbosity=2).run(suite)
    record={'group':a.group,'status':'PASS' if r.wasSuccessful() else 'FAIL','tests_run':r.testsRun,'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'fixture_root':str(sandbox),'test_sources':sources,'selected_cases':cases,'elapsed_seconds':time.monotonic()-start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Unchanged CPU regression cases; only fixture storage relocated; no training or GPU test execution'}
    (sandbox/'RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
    return 0 if r.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
