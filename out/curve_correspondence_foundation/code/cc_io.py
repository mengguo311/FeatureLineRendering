"""Immutable artifact IO and explicit scientific split selection."""
import gzip,hashlib,json,pathlib,datetime
import numpy as np

def clean(x):
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,(np.integer,np.bool_)):return x.item()
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x

def write_json(path,value):
    path=pathlib.Path(path);data=(json.dumps(clean(value),sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if path.suffix=='.gz':data=gzip.compress(data,mtime=0)
    with path.open('xb') as f:f.write(data)
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    path=pathlib.Path(path);data=path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def seal(directory):
    directory=pathlib.Path(directory)
    return dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),artifacts={str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*')) if p.is_file() and p.name!='frozen.json'})

def verify_seal(directory,record):
    return all((pathlib.Path(directory)/p).is_file() and sha(pathlib.Path(directory)/p)==h for p,h in record['artifacts'].items())

def scene_inputs(cfg,scene,split):
    if split not in ['F','C','DEV']:raise ValueError('scientific split forbidden')
    cameras={i:cfg['scenes'][scene]['cameras'][f'train_{i:03d}'] for i in cfg['splits'][split]}
    return dict(cameras=cameras,photos=[c['path'] for c in cameras.values()])
