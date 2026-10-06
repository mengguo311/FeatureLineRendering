"""Reconstruct only missing ignored RGB/alpha caches against original seal SHA.

No producer seal/result, existing cache, or core file is changed. The sole audit
output is results/CACHE_REHYDRATION_AUDIT.json. Use --verify-one [scene:camera]
to compare a private reconstructed copy with an existing cache before hydration.
Requires the frozen original PLYs and the recorded Python environment.
"""
import os,sys
os.environ.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode=True
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import argparse,ctypes,hashlib,json,shutil,subprocess,tempfile,time,traceback
from pathlib import Path
import numpy as np
import cpu_native

ROOT=Path(__file__).resolve().parents[2];TAG='gaer_multiview_contour_regions_v01'
ART=ROOT/'artifacts'/TAG;OUT=ROOT/'out'/TAG;EXP=ROOT/'experiments'/TAG
EXPECTED_CPU='d360806654584227cc342ce22af7c26399f3d5d387b51a01c2eaddadc3b449a4'
EXPECTED_CPP='cfe764471af11d18feb3ce9060697770489d711c5b890c001cfba305841cc8b4'

def require(ok,message):
 if not ok:raise AssertionError(message)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for b in iter(lambda:stream.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def guard():
 common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
 if not common.is_absolute():common=(ROOT/common).resolve()
 size=sum(p.stat().st_size for r in (EXP,ART,OUT) for p in r.rglob('*') if p.is_file() and not p.is_symlink())
 result=dict(root_free=shutil.disk_usage(ROOT).free,shared_git_free=shutil.disk_usage(common).free,stage_bytes=size)
 require(result['root_free']>=4*2**30 and result['shared_git_free']>=1.5*2**30 and size<6*2**30,'unchanged resource guard failed')
 return result

def private_cpu_library(folder):
 require(sha(cpu_native.__file__)==EXPECTED_CPU,'CPU source differs from frozen calibrated producer')
 require(hashlib.sha256(cpu_native.CPP.encode()).hexdigest()==EXPECTED_CPP,'CPP differs from frozen calibrated producer')
 cpp=folder/'cpu_raster.cpp';binary=folder/'cpu_raster.so'
 with cpp.open('x') as f:f.write(cpu_native.CPP)
 command=['g++','-O3','-std=c++17','-fPIC','-shared','-fopenmp','-ffp-contract=off',str(cpp),'-o',str(binary)]
 process=subprocess.run(command,env=dict(os.environ,TMPDIR=str(folder)),capture_output=True,text=True)
 (folder/'compile.log').write_text(process.stdout+process.stderr)
 require(process.returncode==0,'private CPU compilation failed; compile.log retained')
 library=ctypes.CDLL(str(binary));library.raster.restype=ctypes.c_int
 # Avoid calling core library(), which normally refreshes its BUILD metadata.
 cpu_native._LIB=library
 return dict(cpu_source_sha256=EXPECTED_CPU,cpp_sha256=EXPECTED_CPP,binary_sha256=sha(binary),compile_argv=command,private_folder=str(folder))

def inventory():
 freeze=json.loads((ART/'INPUT_FREEZE.json').read_text());expected={};owners={};prefix='out/'+TAG+'/renders/'
 for sealpath in sorted((ART/'seals').glob('*.json')):
  seal=json.loads(sealpath.read_text())
  for path,value in seal['files'].items():
   if not path.startswith(prefix):continue
   parts=Path(path).parts;require(len(parts)==5 and path.endswith('.npz'),'unexpected render cache path '+path)
   require(path not in expected or expected[path]==value,'inconsistent cache SHA between original seals')
   expected[path]=value;owners.setdefault(path,[]).append(sealpath.name)
 require(expected,'no render cache references found in original seals')
 # Freeze itself is checked against every seal that records it.
 freeze_rel=str((ART/'INPUT_FREEZE.json').relative_to(ROOT));freeze_actual=sha(ART/'INPUT_FREEZE.json')
 for sealpath in sorted((ART/'seals').glob('*.json')):
  files=json.loads(sealpath.read_text())['files']
  if freeze_rel in files:require(files[freeze_rel]==freeze_actual,'INPUT_FREEZE differs from a producer seal')
 return freeze,expected,owners

def camera_for(freeze,scene,key):
 record=freeze['scenes'][scene]
 if key in record['cameras']:camera=record['cameras'][key];role=next((r for r,keys in record['roles'].items() if key in keys),'unassigned')
 else:
  found=[c for c in record['arc'] if c['key']==key];require(len(found)==1,'camera is not a unique frozen actual frame');camera=found[0];role='arc'
 require(role!='unassigned','unassigned metadata camera cannot acquire a new cache')
 if role in ('reserved','arc'):
  # These are already completed producer units, never an opportunity to fit
  # new geometry from reserved evidence in a fresh checkout.
  seal=json.loads((ART/'seals'/(scene+'_asset.json')).read_text())
  for rel,h in seal['files'].items():require((ROOT/rel).exists() and sha(ROOT/rel)==h,'reserved/arc hydration needs the intact original asset seal')
 return record,camera,role

def run():
 parser=argparse.ArgumentParser();parser.add_argument('--verify-one',nargs='?',const='lego:r_7',metavar='SCENE:CAMERA');args=parser.parse_args()
 report=dict(status='INCOMPLETE',mode='verify_one' if args.verify_one else 'hydrate_missing_only',source_sha256=sha(__file__),started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),existing_files_never_overwritten=True,producer_seals_and_results_unchanged=True,units=[],failures=[])
 models={};runfolder=None
 try:
  report['resource_guard']=guard();freeze,expected,owners=inventory();report['referenced_caches']=len(expected)
  missing=[p for p in sorted(expected) if not (ROOT/p).exists()];report['missing_before']=len(missing)
  if args.verify_one:
   scene,key=args.verify_one.split(':',1);paths=['out/'+TAG+'/renders/'+scene+'/'+key+'.npz'];require(paths[0] in expected and (ROOT/paths[0]).is_file(),'verify-one requires an existing original sealed cache')
  else:
   paths=missing
   for path in sorted(set(expected)-set(missing)):
    require(sha(ROOT/path)==expected[path],'existing cache hash mismatch; refusing to overwrite '+path)
   report['existing_cache_hashes_verified']=len(expected)-len(missing)
  if paths:
   parent=OUT/'cache_rehydration';parent.mkdir(parents=True,exist_ok=True);runfolder=Path(tempfile.mkdtemp(prefix='run_',dir=parent));report['private_build']=private_cpu_library(runfolder)
  for index,path in enumerate(paths):
   try:
    guard();parts=Path(path).parts;scene=parts[-2];key=Path(path).stem;record,camera,role=camera_for(freeze,scene,key)
    if scene not in models:models[scene]=cpu_native.load_model_cpu(record)
    started=time.monotonic();rendered=cpu_native.render(models[scene],camera)
    temporary=runfolder/('cache_'+str(index)+'_'+scene+'_'+key+'.npz')
    # Exact producer insertion order and dtypes; ZIP bytes must match the
    # already committed original seal, not merely match array values.
    with temporary.open('xb') as f:np.savez_compressed(f,rgb=rendered['rgb'],alpha=rendered['alpha'])
    actual=sha(temporary);unit=dict(cache=path,role=role,camera_sha256=camera['camera_sha256'],model_sha256=record['model_sha256'],expected_sha256=expected[path],reconstructed_sha256=actual,owner_seals=owners[path],temporary_file=str(temporary),seconds=time.monotonic()-started)
    report['units'].append(unit)
    if actual!=expected[path]:
     if (ROOT/path).exists():
      with np.load(ROOT/path) as old,np.load(temporary) as new:
       unit['array_diagnostics']={k:dict(exact=np.array_equal(old[k],new[k]),max_abs=float(np.max(np.abs(old[k]-new[k])))) for k in ('rgb','alpha')}
     unit['status']='INVALID_HASH_MISMATCH';raise AssertionError('reconstructed bytes mismatch original seal; private output retained: '+path)
    if args.verify_one:
     unit['existing_sha256']=sha(ROOT/path);require(unit['existing_sha256']==expected[path],'existing verify-one cache already corrupt');unit['status']='PASS_BYTE_EXACT_PRIVATE_COPY'
    else:
     destination=ROOT/path;destination.parent.mkdir(parents=True,exist_ok=True)
     # A hard-link creation is atomic and fails rather than replacing any
     # concurrently created destination. The private copy remains auditable.
     try:os.link(temporary,destination);unit['status']='RESTORED_BYTE_EXACT'
     except FileExistsError:
      require(sha(destination)==expected[path],'cache appeared concurrently with wrong SHA');unit['status']='ALREADY_RESTORED_BYTE_EXACT'
    print(unit['status'],scene,key,actual,flush=True)
   except Exception as e:report['failures'].append(dict(cache=path,error=repr(e),traceback=traceback.format_exc()))
  report['status']='PASS' if not report['failures'] else 'INVALID'
  report['missing_after']=sum(not (ROOT/p).exists() for p in expected)
 except Exception as e:report['status']='INVALID';report['failures'].append(dict(error=repr(e),traceback=traceback.format_exc()))
 report['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 target=ART/'results/CACHE_REHYDRATION_AUDIT.json';target.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix='CACHE_REHYDRATION_AUDIT_',suffix='.json.tmp',dir=target.parent)
 with os.fdopen(fd,'w') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
 Path(temp).replace(target)  # The explicitly requested independent audit only.
 if runfolder is not None:(runfolder/'AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('CACHE_REHYDRATION_AUDIT',report['status'],str(target),flush=True)
 return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(run())
