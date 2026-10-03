#!/usr/bin/env python3
"""Independent CPU integrity checks, without render/GPU or source image decoding.

PASS means engineering artifact integrity only. It never grants scientific GO.
Access parsing examines attempted opens (including failures), never probes their
filesystem targets, and makes no claim about uncaptured processes/syscalls.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT)); sys.dont_write_bytecode=True
SCENES=('hotdog','materials','mic','ship')
F=(1,14,27,41,53,67,79,93)
C=(7,21,33,47,59,73,86,99)
STAGE='hybrid_raster_trained_models_v1'
ART=ROOT/'artifacts'/STAGE/'independent_review'
OUT=ROOT/'out'/STAGE/'independent_review'
LOCK_SHA='d5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926'
PRIOR=Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2')


def require(ok,message):
    if not ok: raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''): h.update(block)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def read(path): return json.loads(Path(path).read_text())


def write(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    temporary.replace(path)


def check_counts(counts):
    require(set(counts)==set(SCENES),'scene count coverage differs')
    require(all(v==49 for v in counts.values()),'production requires every scene 8F+8C+33arc; no empty/partial success')
    return sum(counts.values())


def verify_source_lock(lock,source_hashes):
    require(source_hashes==lock['config']['sources'],'frozen scientific source hashes differ')
    require(canonical(lock['normalization']['recipe'])==lock['normalization']['recipe_hash'],'recipe hash differs')
    require(canonical({'config':lock['config'],'normalization':lock['normalization']})==lock['parameter_hash'],'scientific parameter hash differs')
    require(canonical({k:v for k,v in lock.items() if k!='lock_hash'})==lock['lock_hash'],'canonical lock hash differs')
    return dict(passed=True,parameter_hash=lock['parameter_hash'],sources=source_hashes,
                scales=lock['normalization']['scales'],author_scale=lock['normalization']['author_scale'])


def verify_inheritance():
    path=PRIOR/'out/hybrid_raster_evidence_v2/LOCK.json'
    require(sha(path)==LOCK_SHA,'prior LOCK bytes differ')
    lock=read(path)
    current={name:sha(ROOT/name) for name in lock['config']['sources']}
    report=verify_source_lock(lock,current)
    report['prior_sources_equal']=all(sha(PRIOR/name)==digest for name,digest in current.items())
    require(report['prior_sources_equal'],'prior scientific source changed')
    variants=lock['config']['native_build']['variants']
    report['native_binaries']={name:dict(path=v['path'],expected=v['sha256'],actual=sha(v['path'])) for name,v in variants.items()}
    require(all(v['expected']==v['actual'] for v in report['native_binaries'].values()),'inherited native binary differs')
    report['lock_sha256']=sha(path)
    report['renderer_disclosures']=dict(SH0=True,white_background=True,filter_3D=False,normals='raster splat/ray-plane, not ground truth',author='independent reconstruction, not official')
    return report


def verify_seal(folder,context=None):
    folder=Path(folder); seal=read(folder/'SEAL.json')
    require(sha(folder/'SEAL.json')==(folder/'SEAL.sha256').read_text().strip(),'seal digest differs')
    require(canonical(seal['context'])==seal['context_sha256'],'seal context hash differs')
    if context is not None: require(seal['context']==context,'seal context differs')
    actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}-{'SEAL.json','SEAL.sha256'}
    require(actual==set(seal['files']),'sealed payload inventory missing/extra')
    for name,digest in seal['files'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'seal path escapes folder')
        require(sha(folder/name)==digest,'payload digest differs: '+name)
    return dict(passed=True,seal_sha256=sha(folder/'SEAL.json'),files=seal['files'],context=seal['context'])


def verify_freeze_chain(events):
    keys=('protocol_pushed','training_launched','checkpoint_frozen','arc_frozen','npr_launched')
    require(all(k in events for k in keys),'missing freeze event')
    values=[events[k] for k in keys]
    require(all(a<=b for a,b in zip(values,values[1:])),'freeze/launch ordering violated')
    return True


def verify_camera_set(specs,fov):
    required={(s,f'{s}_{i:03d}') for s,indices in [('F',F),('C',C),('arc0',range(33))] for i in indices}
    require(len(specs)==49 and {(s['split'],s['key']) for s in specs}==required,'camera split/count differs')
    poses=[]
    fx=800/(2*math.tan(fov/2))
    expected=np.array([[fx,0,399.5],[0,fx,399.5],[0,0,1]])
    for spec in specs:
        cam=spec['camera']; matrix=np.asarray(cam['w2c'],np.float64)
        require(cam['native_width']==800 and cam['native_height']==800,'native resolution differs')
        require(matrix.shape==(4,4) and np.isfinite(matrix).all() and abs(np.linalg.det(matrix))>1e-8,'camera invalid')
        require(np.allclose(cam['native_K'],expected,rtol=0,atol=1e-10),'FoV/principal convention differs')
        actual_fov=cam.get('FoVx',2*math.atan(cam['native_width']/(2*cam['native_K'][0][0])))
        require(math.isclose(actual_fov,fov,rel_tol=0,abs_tol=1e-12),'scene FoV differs')
        if spec['split']=='arc0': poses.append(canonical(matrix.tolist()))
    require(len(set(poses))==33,'arc contains duplicate poses')
    return dict(passed=True,count=49,arc_distinct=33,scene_fov=fov,native_principal=399.5)


def _under(path,root):
    try: Path(path).relative_to(root); return True
    except ValueError: return False


def audit_access(text,root,phase,*,allowed_geometry=(),allowed_output_roots=(),completion_receipt=None,initial_cwd=None):
    """Stat-free attempted-open audit; no claim about path symlink changes.

    Requires strace -f -e trace=openat,openat2 with completed process exits.
    Directory annotations (-yy) resolve non-AT_FDCWD paths when present.
    """
    from scripts.audit_hybrid_raster_access import OPEN, PREFIX, RESUMED, decode_c_string
    require(phase in ('acquisition','diagnostic','transport','verification'),'unknown audit phase')
    root=Path(root); initial_cwd=Path(initial_cwd or root);allowed=set(map(str,allowed_geometry)); outputs=[root,*map(Path,allowed_output_roots)]
    calls=[]; forbidden=[]; pending={}; exits=set(); seen=set(); directory_fds={}
    for number,line in enumerate(text.splitlines(),1):
        match=PREFIX.match(line); require(match is not None,'unparsed prefix')
        pid=int(match.group(1) or match.group(2) or 0); body=match.group(3)
        body=re.sub(r'^\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+','',body)
        if body.startswith('+++ exited with') or body.startswith('+++ killed by'):
            exits.add(pid); continue
        if not body.strip() or body.startswith('--- ') or body.startswith('strace:'): continue
        resumed=RESUMED.match(body)
        if resumed:
            require(pid in pending,'resumed without unfinished open')
            body=pending.pop(pid)+resumed.group(2)
        elif '<unfinished ...>' in body:
            require(pid not in pending and re.match(r'^openat2?\(',body),'invalid unfinished open')
            pending[pid]=body.split('<unfinished ...>',1)[0]; seen.add(pid); continue
        match=OPEN.match(body); require(match is not None,'unparsed syscall line '+str(number))
        syscall,dirfd,literal,args,result=match.groups(); seen.add(pid)
        path=decode_c_string(literal)
        if not path.startswith('/'):
            annotation=re.search(r'<([^>]*)>',dirfd)
            if annotation and annotation.group(1).startswith('/'): parent=annotation.group(1)
            elif dirfd.startswith('AT_FDCWD'): parent=str(initial_cwd)
            else:
                key=(pid,int(dirfd.split('<')[0])); require(key in directory_fds,'unresolved numeric dirfd'); parent=directory_fds[key]
            path=os.path.join(parent,path)
        path=os.path.normpath(path)
        flags_match=re.search(r'flags\s*=\s*([^,}]+)',args) if syscall=='openat2' else None
        flags=flags_match.group(1).strip() if flags_match else args.split(',',1)[0].strip()
        result=int(result); p=Path(path)
        if result>=0:
            directory_fds.pop((pid,result),None)
            if 'O_DIRECTORY' in flags: directory_fds[pid,result]=path
        target_match=re.search(r'\)\s*=\s*\d+<(/[^>]*)>',body)
        returned_path=os.path.normpath(target_match.group(1).removesuffix(' (deleted)')) if target_match else None
        record=dict(line=number,pid=pid,path=path,flags=flags,result=result,returned_fd_path=returned_path)
        calls.append(record); reasons=[]
        for candidate in {path,returned_path}-{None}:
            p=Path(candidate)
            if re.match(r'^transforms_(?:test|val|validation|dev)\.json$',p.name,re.I): reasons.append('forbidden metadata attempt')
            dataset=re.match(r'^/home/u00134/cglib/data/full/([^/]+)/([^/]+)/(.*)',candidate)
            if dataset:
                scene,split,remainder=dataset.groups()
                if scene not in SCENES or split!='train': reasons.append('non-authorized TRAIN dataset access')
                elif p.suffix.lower() in ('.png','.jpg','.jpeg','.exr','.npy'):
                    if phase not in ('acquisition','diagnostic'): reasons.append('source image open outside acquisition/diagnostic')
                    elif phase=='diagnostic' and p.stem not in {f'r_{i}' for i in F}: reasons.append('C/non-F diagnostic image access')
            if p.suffix.lower() in ('.obj','.off','.stl','.glb','.gltf','.fbx','.mesh','.3ds','.dae','.vtk','.vtp','.ply'):
                if candidate not in allowed and not any(_under(candidate,o/'out'/STAGE) if o==root else _under(candidate,o) for o in outputs): reasons.append('mesh/unallowlisted geometry attempt')
            if re.search(r'\bO_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND)\b',flags):
                if not any(_under(candidate,o) for o in outputs) and not any(_under(candidate,prefix) for prefix in ('/dev','/proc','/sys')): reasons.append('outside authorized output write')
        if reasons: forbidden.append({**record,'reasons':reasons})
    require(not pending,'incomplete unfinished trace')
    missing_exits=sorted(seen-exits)
    if missing_exits:
        require(completion_receipt is not None,'trace still active or missing child exit')
        require(completion_receipt.get('exit_code')==0 and completion_receipt.get('completed') is True,'external completion receipt invalid')
        require(completion_receipt.get('trace_sha256')==hashlib.sha256(text.encode()).hexdigest(),'external completion receipt trace hash differs')
    require(calls,'empty trace cannot pass')
    require(not forbidden,'forbidden opens: '+json.dumps(forbidden[:5]))
    return dict(passed=True,phase=phase,attempted_opens=len(calls),successful_opens=sum(c['result']>=0 for c in calls),
                failed_opens=sum(c['result']<0 for c in calls),forbidden=forbidden,
                train_source_image_opens=sum('/train/' in c['path'] and Path(c['path']).suffix=='.png' for c in calls),
                missing_exit_sentinels=missing_exits,external_completion_receipt=completion_receipt,
                scope='Only captured attempted openat/openat2 syscalls and child exits; lexical absolute/dirfd resolution plus returned-fd -yy targets when present; no whole-session or unannotated dynamic symlink claim')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inheritance',action='store_true')
    parser.add_argument('--trace',type=Path)
    parser.add_argument('--phase',choices=('acquisition','diagnostic','transport','verification'))
    parser.add_argument('--allowed-geometry',nargs='*',default=[])
    parser.add_argument('--completion-receipt',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); report={'passed':False,'scientific_GO':False,'human_review':'PENDING'}
    try:
        if args.inheritance: report['inheritance']=verify_inheritance()
        if args.trace:
            before=args.trace.stat(); blob=args.trace.read_bytes(); after=args.trace.stat()
            require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'trace changed during audit')
            receipt=read(args.completion_receipt) if args.completion_receipt else None
            report['access']=audit_access(blob.decode(),ROOT,args.phase,allowed_geometry=args.allowed_geometry,completion_receipt=receipt)
            report['trace_sha256']=hashlib.sha256(blob).hexdigest()
        require(args.inheritance or args.trace,'no check selected')
        report['passed']=True; report['status']='PASS'
    except Exception as exc: report.update(status='INVALID',error=f'{type(exc).__name__}: {exc}')
    require(_under(args.output.resolve(),ART),'independent report must stay in owned artifact directory')
    write(args.output,report); print(json.dumps(report,ensure_ascii=False)); return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
