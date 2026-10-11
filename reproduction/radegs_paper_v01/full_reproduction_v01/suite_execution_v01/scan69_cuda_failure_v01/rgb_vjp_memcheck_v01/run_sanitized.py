import argparse,json,os,subprocess,sys
from pathlib import Path
from memcheck_gate import validate

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args();c=json.loads(Path(a.config).read_text())
    from safety import atomic_json,sha256
    log=Path(c['sanitizer_log_dir'])/(os.environ['RADEGS_ATTEMPT']+'.log');log.parent.mkdir(exist_ok=True)
    cmd=[c['sanitizer_binary'],'--tool','memcheck','--error-exitcode','86','--target-processes','application-only','--destroy-on-device-error','context','--print-limit','20','--log-file',str(log),sys.executable,str(Path(__file__).with_name('worker.py')),'--config',a.config]
    p=subprocess.run(cmd)
    rp=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT']/'result.json'
    result=json.loads(rp.read_text()) if rp.exists() else {}
    validate(p.returncode,log.read_text() if log.exists() else '',result)
    report=Path(c['reports']['smoke']);r=json.loads(report.read_text());r['outputs'][str(log)]=sha256(log);r['details'].update(memcheck_zero_errors=True,finite_through_iteration=1000,original_NaN_cause_proven=False,scientificdone=False);atomic_json(report,r)

if __name__=='__main__':main()
