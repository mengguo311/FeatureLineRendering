import json,subprocess,os,re
from pathlib import Path
W=Path(__file__).resolve().parents[5];R=W/'reproduction/radegs_paper_v01';H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01/cpu_regressions_v02';O.mkdir(exist_ok=False)
assert (H/'full_reproduction_v01/precision_v01/eigen_probe.so').is_file()
files=[f for d in ['stage2','gradient_fix_v01','full_reproduction_v01/precision_v01'] for f in sorted((R/d).glob('test_*.py'))];assert len(files)==14
files += [Path(__file__).parent/'rgb_vjp_fix_v01/test_math_vjp.py'];env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(H/'tmp'),OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2');rows=[]
for i,p in enumerate(files):
 log=O/(str(i)+'_'+p.stem+'.log');cmd=[str(H/'envs/c24_py39/bin/python'),'-m','unittest','discover','-s',str(p.parent),'-p',p.name]
 with log.open('w') as f:r=subprocess.run(cmd,env=env,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 txt=log.read_text();count=re.search(r'Ran (\d+) test',txt);expected_red=p.name=='test_eigen_precision.py';ok=(r.returncode!=0 and 'FAILED (failures=1)' in txt) if expected_red else r.returncode==0
 row={'file':str(p),'returncode':r.returncode,'tests':int(count.group(1)) if count else None,'expected_legacy_RED':expected_red,'as_expected':ok,'log':str(log)};rows.append(row);print(json.dumps(row),flush=True)
(O/'RESULT.json').write_text(json.dumps({'files':rows,'all_as_expected':all(r['as_expected'] for r in rows),'legacy_test_intentionally_still_RED':True,'isolated_process_per_file':True,'CUDA_disabled':True,'scientificdone':False},indent=2)+'\n');assert all(r['as_expected'] for r in rows)
