"""Independent RGB-D geometry and fail-closed role confinement. No mesh imports."""
import copy
import hashlib
import json
from pathlib import Path
import numpy as np

def project(points, K, c2w):
    w = np.linalg.inv(c2w)
    q = np.asarray(points) @ w[:3,:3].T + w[:3,3]
    h = q @ np.asarray(K).T
    with np.errstate(divide='ignore', invalid='ignore'):
        uv = h[:,:2] / h[:,2,None]
    uv[q[:,2] <= 0] = np.nan
    return uv, q[:,2]

def unproject(uv, z, K, c2w):
    ray = np.c_[uv, np.ones(len(uv))] @ np.linalg.inv(K).T
    q = ray * np.asarray(z)[:,None]
    return q @ c2w[:3,:3].T + c2w[:3,3]

def depth_metres(raw):
    return np.asarray(raw, dtype=np.float64) / 5000.

def visibility(uv, z, depth):
    labels = np.full(len(z), 'unknown', dtype='<U13')
    uv = np.asarray(uv); z = np.asarray(z)
    finite = np.isfinite(uv).all(1) & (z > 0)
    ij = np.zeros((len(z),2), int)
    ij[finite] = np.rint(uv[finite]).astype(int)
    ok = finite & (ij[:,0]>=0) & (ij[:,0]<depth.shape[1]) & (ij[:,1]>=0) & (ij[:,1]<depth.shape[0])
    ids = np.flatnonzero(ok); d = depth[ij[ids,1], ij[ids,0]]
    known = (d > 0) & np.isfinite(d)
    ids = ids[known]; d = d[known]; tol = np.maximum(.03, .02*z[ids])
    labels[ids] = 'consistent'
    labels[ids[z[ids]-d > tol]] = 'occluded'
    labels[ids[d-z[ids] > tol]] = 'contradiction'
    return labels

def associate(rgb_times, depth_times, limit):
    used = set(); pairs = []; d = np.asarray(depth_times)
    for i,t in enumerate(rgb_times):
        j = int(np.argmin(abs(d-t)))
        if abs(d[j]-t)<=limit and j not in used:
            pairs.append((i,j)); used.add(j)
    return pairs

def allowed_raw(frames, role):
    if role == 'train': return {f['rgb'] for f in frames if f['split']=='F'}
    if role == 'build': return {f['depth'] for f in frames if f['split']=='F'}
    if role == 'eval': return {f[k] for f in frames for k in ['rgb','depth']}
    raise ValueError('unknown role')

def edit_asset(asset, identity, displacement, width_scale):
    result = copy.deepcopy(asset)
    matches = [c for c in result['curves'] if c['id']==identity]
    if len(matches)!=1 or width_scale<=0: raise ValueError('identity/width')
    c = matches[0]; c['points'] = (np.array(c['points'])+displacement).tolist()
    c['width'] *= width_scale
    return result

def asset_arrays(asset):
    curves = asset['curves']; offsets = np.r_[0,np.cumsum([len(c['points']) for c in curves])]
    return dict(points=np.concatenate([np.array(c['points']) for c in curves]) if curves else np.empty((0,3)),
                widths=np.array([c['width'] for c in curves]), ids=np.array([c['id'] for c in curves],dtype='U80'),offsets=offsets)

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()

def restrict_filesystem(readonly, writable):
    # Landlock applies to Python, native libraries and all children. No broad HOME grants.
    import ctypes, os
    lib=ctypes.CDLL(None,use_errno=True)
    if lib.syscall(444,0,0,1)<3: raise RuntimeError('Landlock ABI >=3 required')
    class Ruleset(ctypes.Structure): _fields_=[('handled_access_fs',ctypes.c_uint64)]
    class Rule(ctypes.Structure):
        _pack_=1
        _fields_=[('allowed_access',ctypes.c_uint64),('parent_fd',ctypes.c_int32)]
    handled=(1<<15)-1; attr=Ruleset(handled)
    ruleset=lib.syscall(444,ctypes.byref(attr),ctypes.sizeof(attr),0)
    if ruleset<0: raise OSError(ctypes.get_errno(),'Landlock create')
    try:
        for write,paths in [(False,readonly),(True,writable)]:
            for name in paths:
                p=Path(name).resolve(strict=True); rights=handled if write else (1|4|8)
                if not p.is_dir(): rights &= (1|2|4|(1<<14))
                fd=os.open(p,os.O_PATH|os.O_CLOEXEC)
                try:
                    rule=Rule(rights,fd)
                    if lib.syscall(445,ruleset,1,ctypes.byref(rule),0): raise OSError(ctypes.get_errno(),'Landlock add '+str(p))
                finally: os.close(fd)
        if lib.prctl(38,1,0,0,0) or lib.syscall(446,ruleset,0): raise OSError(ctypes.get_errno(),'Landlock restrict')
    finally: os.close(ruleset)

class RawReader:
    def __init__(self, inputs, role, audit):
        self.root=Path(inputs['raw_root']); self.role=role; self.allowed=allowed_raw(inputs['frames'],role)
        self.audit=Path(audit); self.splits={f[k]:f['split'] for f in inputs['frames'] for k in ['rgb','depth']}
    def read(self, relative):
        if relative not in self.allowed: raise PermissionError('RAW split/role boundary')
        p=self.root/relative
        if p.is_symlink(): raise PermissionError('RAW symlink')
        b=p.read_bytes()
        with self.audit.open('a') as f:
            f.write(json.dumps(dict(role=self.role,split=self.splits[relative],path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))+'\n')
        from PIL import Image
        import io
        return np.array(Image.open(io.BytesIO(b)))
