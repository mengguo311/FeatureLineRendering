"""Only this experiment may write. Fixed storage/ownership guards and seals."""
import ast,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/image_space_edge_foundation_v1'
ART=ROOT/'artifacts/image_space_edge_foundation_v1'
OUT=ROOT/'out/image_space_edge_foundation_v1'
PYTHON='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
DATA_PATH=ROOT/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json'
PRIOR_PATH=ROOT/'artifacts/edge_responsibility_lego_chair_v2/INPUT_FREEZE.json'
for k,v in dict(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',
                PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'tmp'),CUDA_CACHE_PATH=str(OUT/'cache/cuda'),
                TORCH_EXTENSIONS_DIR=str(OUT/'cache/torch'),MPLCONFIGDIR=str(OUT/'cache/mpl'),XDG_CACHE_HOME=str(OUT/'cache')).items():os.environ[k]=v
for p in [OUT/'tmp',OUT/'logs',OUT/'cache',ART/'results',ART/'seals']:p.mkdir(parents=True,exist_ok=True)

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def scoped(path):
    p=Path(path).absolute()
    if not any(p.is_relative_to(root) for root in [EXP,ART,OUT]):raise ValueError('write outside experiment')
    p.parent.mkdir(parents=True,exist_ok=True);return p
def atomic_json(path,obj):
    p=scoped(path);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n');os.replace(tmp,p)
def event(unit,status,**kw):
    obj=dict(unit=unit,status=status,pid=os.getpid(),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw)
    atomic_json(OUT/'STATUS.json',obj)
    with (OUT/'EVENTS.jsonl').open('a') as f:f.write(json.dumps(obj)+'\n')
    print(json.dumps(obj),flush=True)
def guard(unit,gpu=False):
    common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
    if not common.is_absolute():common=ROOT/common
    size=sum(p.stat().st_size for root in [EXP,ART,OUT] for p in root.rglob('*') if p.is_file() and not p.is_symlink())
    free=shutil.disk_usage(ROOT).free;gitfree=shutil.disk_usage(common).free
    if free<4*2**30 or gitfree<1.5*2**30 or size>=8*2**30:raise RuntimeError('fixed 4GiB root / 1.5GiB Git reserve / 8GiB stage cap')
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader'],text=True).splitlines()
    row=next(r for r in rows if r.split(',')[0].strip()=='0');uuid=row.split(',')[1].strip()
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True).splitlines()
    pids=[int(r.split(',')[1]) for r in apps if r.split(',')[0].strip()==uuid]
    ownership=[]
    for pid in pids:
        try:owner=Path(f'/proc/{pid}').stat().st_uid
        except FileNotFoundError:owner=None
        ownership.append(dict(pid=pid,uid=owner,self=pid==os.getpid()))
    foreign=[pid for pid in pids if pid!=os.getpid()]
    record=dict(unit=unit,root_free_bytes=free,git_free_bytes=gitfree,stage_bytes=size,gpu0_processes=ownership,foreign_pids=foreign)
    with (OUT/'logs/RESOURCE_GATE.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
    if gpu and foreign:raise RuntimeError('GPU0 foreign owner; no process termination allowed')
    return record
def discover_native():
    # Read a literal path from the archived adapter runtime; never import it.
    tree=ast.parse((ROOT/'experiments/edge_responsibility_lego_chair_v2/src/runtime.py').read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NATIVE' for t in node.targets):
            return Path(ast.literal_eval(node.value.args[0]))
    raise RuntimeError('archived native location unavailable')
NATIVE=discover_native()
def source_hashes():return {str(p.relative_to(ROOT)):sha(p) for p in sorted(EXP.rglob('*')) if p.is_file() and p.suffix in ['.py','.json','.sh']}
def baseline_snapshot():
    prior=json.loads(PRIOR_PATH.read_text());data=json.loads(DATA_PATH.read_text())
    paths={Path(p) for p in prior['protected_sha256']}
    paths|={DATA_PATH,PRIOR_PATH,ROOT/'artifacts/edge_responsibility_lego_chair_v2/REPORT_ZH.md'}
    for s in data['scenes'].values():
        paths.add(Path(s['model']))
        for group in s['roles'].values():
            for entry in group:paths.add(Path(entry['original_path']))
    paths|={NATIVE/'build/stock/onec_stock_C.so',NATIVE/'build/knn/onec_knn_C.so'}
    paths={p if p.is_absolute() else ROOT/p for p in paths}
    hashes={str(p):sha(p) for p in sorted(paths) if p.is_file()}
    heads=dict(line.split(' ',1) for line in subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],cwd=ROOT,text=True).splitlines())
    return dict(hashes=hashes,heads=heads,data_sha=sha(DATA_PATH),prior_sha=sha(PRIOR_PATH))
def unit(name,freeze,fn,gpu=False):
    seal=ART/'seals'/f'{name}.json';result=ART/'results'/f'{name}.json'
    if seal.exists():
        old=json.loads(seal.read_text())
        if old['freeze']!=freeze:raise RuntimeError('sealed unit input changed')
        if not all(sha(ROOT/p)==h for p,h in old['outputs'].items()):raise RuntimeError('sealed output changed')
        event(name,'SEALED_SKIP');return json.loads(result.read_text())
    event(name,'RUNNING');t=time.perf_counter()
    try:
        guard(name,gpu);obj=fn();obj['seconds']=time.perf_counter()-t
        atomic_json(result,obj)
        files=[result]+[ROOT/p for p in obj.get('files',[])]
        atomic_json(seal,dict(unit=name,freeze=freeze,outputs={str(p.relative_to(ROOT)):sha(p) for p in files},status='COMPLETE'))
        event(name,'COMPLETE',seconds=obj['seconds']);return obj
    except Exception as e:
        import traceback
        failure=dict(unit=name,status='FAILED',error=str(e),traceback=traceback.format_exc())
        atomic_json(ART/'failures'/f'{name}_{time.time_ns()}.json',failure);event(name,'FAILED',error=str(e));return failure
