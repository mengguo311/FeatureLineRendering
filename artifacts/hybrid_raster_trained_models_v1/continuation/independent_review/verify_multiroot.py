#!/usr/bin/env python3
"""Independent storage-continuation integrity/audit; original checkers stay immutable.

Imports the established numeric and media checks but explicitly selects each
scene's approved payload root. New operational receipts are verified separately:
they are not retroactively inserted in old frame seal contexts. PASS is artifact
integrity, never scientific or human GO; the historical Hotdog trace gap persists.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import time
import traceback

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[4]
EXTERNAL=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1')
TART=ROOT/'artifacts/hybrid_raster_trained_models_v1/transport'
CONT=TART.parent/'continuation'
ART=CONT/'independent_review'
LEGACY=ROOT/'out/hybrid_raster_trained_models_v1/transport'
SCENES=('hotdog','materials','mic','ship')
NEW_SCENES=SCENES[1:]
sys.path.insert(0,str(TART.parent/'independent_review'))
sys.path.insert(0,str(ROOT))
from verify_experiment import require,sha,canonical,read,write,verify_seal,verify_inheritance,check_counts
from scripts.audit_hybrid_raster_access import PREFIX,OPEN,RESUMED,decode_c_string


def scene_root(scene):
    require(scene in SCENES,'scene outside frozen four-model map')
    return LEGACY if scene=='hotdog' else EXTERNAL/'transport'


def under(path,root):
    try:Path(path).relative_to(root);return True
    except ValueError:return False


def assert_owned_path(path,root):
    """Check lexical ownership and every extant parent without following symlinks."""
    path=Path(path);root=Path(root)
    require(path.is_absolute() and '..' not in path.parts,'non-absolute/escaping owned path')
    require(under(path,root),'path outside explicit approved root')
    for node in (path,*path.parents):
        require(not node.is_symlink(),'symlink in owned artifact path '+str(node))
    if path.exists():require(path.stat().st_uid==os.getuid(),'artifact owner differs')
    return path


def verify_owned_seal(folder,root,context=None):
    folder=assert_owned_path(folder,root)
    for path in folder.rglob('*'):assert_owned_path(path,root)
    return verify_seal(folder,context)


def _metadata_write(path):
    p=Path(path)
    if under(p,ART):return p.suffix in ('.json','.tmp')
    allowed={TART/'STATUS.json',TART.parent/'STATUS.json'}
    for scene in NEW_SCENES:
        allowed|={TART/scene/name for name in ('FRAMES.json','CALIBRATION.json','CALIBRATION_FAILURE.json','MEDIA.json')}
    return (p in allowed or (p.name.endswith('.tmp') and p.with_suffix('') in allowed)
            or any(p.parent==target.parent and re.fullmatch(re.escape('.'+target.name+'.')+r'[A-Za-z0-9_]{8}',p.name) for target in allowed))


def _normalize_open(body):
    # Linux may emit open/creat as well as openat; preserve quoted C strings.
    match=re.match(r'^(open|creat)\(\s*("(?:\\.|[^"\\])*")\s*,(.*)$',body)
    if match:
        kind,literal,rest=match.groups()
        if kind=='creat':rest=' O_WRONLY|O_CREAT|O_TRUNC,'+rest
        body=f'openat(AT_FDCWD, {literal},'+rest
    return re.sub(r'(\)\s*=\s*\d+</dev/[^<>]+)<(?:char|block) \d+:\d+>>(\s.*)?$',
                  lambda m:m.group(1)+'>'+(m.group(2) or ''),body)


def strict_access(text,*,allowed_geometry=(),required_reads=(),initial_cwd=ROOT):
    """Stat-free audit of attempted open/openat/openat2/creat and real exits.

    All observed opening PIDs must have normal exit 0. A completion receipt does
    not replace missing trace exits. Returned -yy paths are checked too. Relative
    AT_FDCWD assumes documented unchanged cwd; unrelated syscalls are not covered.
    """
    allowed=set(map(str,allowed_geometry));required=set(map(str,required_reads))
    pending={};seen=set();exits={};directories={};calls=[];violations=[];read_paths=set()
    for number,line in enumerate(text.splitlines(),1):
        match=PREFIX.match(line);require(match is not None,'invalid strace prefix')
        pid=int(match.group(1) or match.group(2) or 0);body=match.group(3)
        body=re.sub(r'^\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+','',body)
        ending=re.fullmatch(r'\+\+\+ exited with (\d+) \+\+\+',body)
        if ending:exits[pid]=int(ending.group(1));continue
        if body.startswith('+++ killed by'):raise ValueError('traced process killed: '+body)
        if not body.strip() or body.startswith('--- ') or body.startswith('strace:'):continue
        resumed=re.match(r'^<\.\.\. (openat2?|open|creat) resumed>(.*)$',body)
        if resumed:
            require(pid in pending,'resumed without pending syscall')
            kind,prefix=pending.pop(pid);require(kind==resumed.group(1),'resumed syscall differs')
            body=prefix+resumed.group(2)
        elif '<unfinished ...>' in body:
            opening=re.match(r'^(openat2?|open|creat)\(',body)
            require(opening is not None and pid not in pending,'invalid unfinished call')
            pending[pid]=(opening.group(1),body.split('<unfinished ...>',1)[0]);seen.add(pid);continue
        body=_normalize_open(body)
        require(re.search(r'\)\s*=\s*\d+<[^>]*<',body) is None,'unhandled nested returned descriptor')
        opened=OPEN.match(body);require(opened is not None,'unparsed syscall at line '+str(number))
        syscall,dirfd,literal,args,result=opened.groups();seen.add(pid);raw=decode_c_string(literal)
        if raw.startswith('/'):path=raw
        else:
            annotation=re.search(r'<([^>]*)>',dirfd)
            if annotation and annotation.group(1).startswith('/'):parent=annotation.group(1)
            elif dirfd.startswith('AT_FDCWD'):parent=str(initial_cwd)
            else:
                fd=(pid,int(dirfd.split('<')[0]));require(fd in directories,'unresolved numeric dirfd')
                parent=directories[fd]
            path=os.path.join(parent,raw)
        path=os.path.normpath(path);result=int(result)
        flags_match=re.search(r'flags\s*=\s*([^,}]+)',args) if syscall=='openat2' else None
        flags=flags_match.group(1).strip() if flags_match else args.split(',',1)[0].strip()
        is_write=bool(re.search(r'\bO_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND)\b',flags))
        if result>=0:
            directories.pop((pid,result),None)
            if 'O_DIRECTORY' in flags:directories[pid,result]=path
        returned=re.search(r'\)\s*=\s*\d+<(/[^>]*)>',body)
        target=os.path.normpath(returned.group(1).removesuffix(' (deleted)')) if returned else None
        record={'line':number,'pid':pid,'path':path,'returned_fd_path':target,'flags':flags,'result':result}
        calls.append(record);reasons=[]
        for candidate in {path,target}-{None}:
            p=Path(candidate)
            if re.match(r'^transforms_(?:test|val|validation|dev)\.json$',p.name,re.I):reasons.append('forbidden metadata attempted')
            if re.match(r'^/home/u00134/cglib/data/full/[^/]+/',candidate):
                if p.suffix.lower() in ('.png','.jpg','.jpeg','.exr','.npy','.npz','.webp','.tif','.tiff','.bmp','.ppm','.hdr'):
                    reasons.append('source dataset image/array attempted during NPR')
                if p.name.startswith('transforms_') and p.name!='transforms_train.json':reasons.append('non-TRAIN metadata')
            if p.suffix.lower() in ('.obj','.off','.stl','.glb','.gltf','.fbx','.mesh','.3ds','.dae','.vtk','.vtp','.ply') and candidate not in allowed:
                reasons.append('mesh/unallowlisted geometry attempted')
            if is_write and not (under(p,EXTERNAL) or _metadata_write(p) or any(under(p,r) for r in ('/dev','/proc','/sys'))):
                reasons.append('write outside approved external payload/small metadata scope')
            if result>=0 and not is_write:read_paths.add(candidate)
        if reasons:violations.append({**record,'reasons':reasons})
    require(not pending,'incomplete unfinished trace')
    require(calls,'empty trace')
    require(not(seen-set(exits)),'missing explicit process exits')
    require(all(code==0 for code in exits.values()),'nonzero traced process exit')
    require(not violations,'forbidden opens: '+json.dumps(violations[:5]))
    require(required<=read_paths,'qualifying frozen/source reads missing: '+str(sorted(required-read_paths)))
    return {'passed':True,'attempted_opens':len(calls),'successful_opens':sum(c['result']>=0 for c in calls),
            'failed_opens':sum(c['result']<0 for c in calls),'normal_exit_pids':sorted(exits),
            'required_reads_observed':sorted(required),'write_paths':sorted({c['path'] for c in calls if re.search(r'\bO_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND)\b',c['flags'])}),
            'source_image_opens':0,'forbidden':[],
            'scope':'Only recorded attempted open/openat/openat2/creat, returned -yy paths and explicit process exits. Relative AT_FDCWD assumes recorded cwd. No whole-session/inherited-descriptor/mmap/network or historical Hotdog-gap repair claim.'}


def verify_frame_manifest(manifest,scene,frames):
    require(manifest['scene']==scene,'frame manifest scene differs')
    require(manifest['expected_frames']==manifest['actual_frames']==49 and manifest['missing']==[],'partial frame manifest')
    records=manifest['records'];require(len(records)==49 and len({r['key'] for r in records})==49,'frame manifest count/duplicates')
    require({r['key'] for r in records}==set(frames),'frame manifest keys differ')
    for row in records:
        verified=frames[row['key']]
        require(row['seal_sha256']==verified['seal_sha256'] and row['context']==verified['context'],'frame manifest seal/context differs')
    return True


def verify_storage_freeze():
    """Recheck committed bytes and remote ancestry independently of producer gate."""
    path=CONT/'STORAGE_FREEZE.json';receipt=read(path);commit=receipt['commit']
    required=('PROTOCOL.md','PROTOCOL.json','STORAGE_MAP.json','storage_paths.py','run_storage_transport.py',
              'test_storage_adapter.py','launch_storage.py','test_launch_storage.py',
              'independent_review/verify_multiroot.py','independent_review/test_verify_multiroot.py')
    require({str((CONT/n).relative_to(ROOT)) for n in required}<=set(receipt['files']),'incomplete storage freeze file set')
    for relative,digest in receipt['files'].items():
        target=assert_owned_path(ROOT/relative,CONT)
        require(sha(target)==digest,'storage freeze current bytes differ: '+relative)
        committed=subprocess.check_output(['git','show',commit+':'+relative],cwd=ROOT)
        require(hashlib.sha256(committed).hexdigest()==digest,'storage freeze committed bytes differ: '+relative)
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/hybrid-raster-trained-models-v1'],cwd=ROOT,text=True).split()[0]
    subprocess.run(['git','merge-base','--is-ancestor',commit,remote],cwd=ROOT,check=True)
    mapping=read(CONT/'STORAGE_MAP.json')
    require(mapping['repo_root']==str(ROOT) and mapping['external_root']==str(EXTERNAL),'frozen approved roots differ')
    require(mapping['scene_roots']=={s:str(scene_root(s)) for s in SCENES},'frozen root resolver differs')
    return {'passed':True,'path':str(path),'sha256':sha(path),'commit':commit,'remote_at_verification':remote,'files':receipt['files']}


def _binding_receipts(scene):
    paths=sorted((EXTERNAL/'transport/bindings').glob(scene+'_*.json'))
    require(paths,'new scene missing storage binding receipts')
    result=[]
    for path in paths:
        assert_owned_path(path,EXTERNAL);r=read(path)
        require(r['scene']==scene and r['schema']=='storage-binding-v1','binding scene/schema differs')
        require(Path(r['repo_root'])==ROOT and Path(r['external_root'])==EXTERNAL,'binding approved roots differ')
        require(Path(r['new_transport_root'])==scene_root(scene) and Path(r['legacy_transport_root'])==LEGACY,'binding payload root differs')
        require(r['scene_roots']=={s:str(scene_root(s)) for s in SCENES},'binding scene root map differs')
        source=r['original_source_manifest'];require(sha(source['path'])==source['sha256'],'binding original source manifest changed')
        for name,digest in source['files'].items():require(sha(TART/name)==digest,'binding original producer changed')
        for name,digest in r['storage_glue_sources'].items():require(sha(CONT/name)==digest,'binding storage glue changed')
        mapping=r['storage_map'];require(sha(mapping['path'])==mapping['sha256'],'binding path map changed')
        b=r['binding']
        for key in ('runner_OUT','adapters_OUT','native_STAGE'):require(Path(b[key])==scene_root(scene),'active bound output differs')
        require(Path(b['ROOT'])==ROOT and Path(b['ART'])==TART,'binding pretends different source/freeze context')
        require(Path(b['native_NATIVE'])==Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2/out/hybrid_raster_evidence_v2/native'),'native build root differs')
        for name,record in r['unchanged_functions'].items():
            require(Path(record['co_filename'])==TART/'run_transport.py' and record['source_sha256']==sha(TART/'run_transport.py'),'scientific producer function replaced: '+name)
        for label,root in [('repo',ROOT),('external',EXTERNAL)]:
            check=r['storage_checks'][label]
            require(Path(check['path'])==root and check['free_bytes']>=1024**3 and check['minimum_free_bytes']==1024**3,'launch storage guard differs')
            require(check['uid']==os.getuid() and not check['symlink'] and Path(check['real_path'])==root,'launch storage ownership differs')
        release=r['storage_release'];require(sha(release['path'])==release['sha256'],'storage release receipt changed')
        require(Path(release['path'])==CONT/'STORAGE_FREEZE.json' and release['commit']==read(CONT/'STORAGE_FREEZE.json')['commit'],'binding storage freeze differs')
        frozen=read(TART/'INHERITED_LOCK.json');heritage=r['scientific_heritage']
        require(heritage['sources']==frozen['config']['sources'] and heritage['native_build']==frozen['config']['native_build'] and heritage['parameter_hash']==frozen['parameter_hash'],'binding scientific inheritance differs')
        result.append({'path':str(path),'sha256':sha(path),'phase':r['phase'],'pid':r['pid']})
    require({r['phase'] for r in result}>={'render','media'},'storage bindings incomplete phases')
    return result


def audit_launch(launch_dir,scene,phase,lock):
    launch_dir=assert_owned_path(launch_dir,EXTERNAL);receipt=read(launch_dir/'EXIT.json')
    require(receipt['exit_code']==0 and receipt['completed'] is True and receipt['normal_exit'] is True,'launch did not complete normally')
    trace=launch_dir/'production.strace';before=trace.stat();blob=trace.read_bytes();after=trace.stat()
    require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'trace changed while auditing')
    require(hashlib.sha256(blob).hexdigest()==receipt['trace_sha256'],'launch trace hash differs')
    require(receipt['scene']==scene and receipt['phase']==phase,'launch receipt scene/phase differs')
    launch=read(launch_dir/'LAUNCH.json');require(Path(launch['cwd'])==ROOT,'traced launch cwd differs')
    require(launch['scene']==scene and launch['phase']==phase and launch['child']['uid']==os.getuid(),'launch identity/ownership differs')
    require(read(launch_dir/'GPU_GUARD.json')['processes']==[],'foreign GPU compute process at launch')
    guards=read(launch_dir/'STORAGE_GUARD.json')
    for label,root in [('repo',ROOT),('external',EXTERNAL)]:
        guard=guards[label];require(Path(guard['path'])==root and guard['free_bytes']>=1024**3 and guard['minimum_free_bytes']==1024**3,'launch root reserve invalid')
    release=read(launch_dir/'STORAGE_RELEASE_GUARD.json');require(sha(release['path'])==release['sha256'],'launch storage freeze receipt changed')
    binding=receipt['binding_receipt'];require(binding and sha(binding['path'])==binding['sha256'],'actual launch binding receipt differs')
    b=read(binding['path']);require(b['scene']==scene and b['phase']==phase,'actual launch storage binding scene differs')
    manifest=read(TART/scene/'CAMERAS.json')
    required=[str(TART/scene/'CAMERAS.json'),manifest['checkpoint']['path'],str(TART/'adapters.py'),str(TART/'run_transport.py'),str(CONT/'storage_paths.py'),str(CONT/'run_storage_transport.py'),str(CONT/'STORAGE_MAP.json')]
    required.extend(str(Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2')/name) for name in lock['config']['sources'])
    required.append('/home/u00134/3dgs_line/hybrid_raster_evidence_v2/out/hybrid_raster_evidence_v2/LOCK.json')
    if phase=='render':required.extend(v['path'] for v in lock['config']['native_build']['variants'].values())
    result=strict_access(blob.decode(),allowed_geometry=[manifest['checkpoint']['path']],required_reads=required)
    for name,row in receipt.get('files',{}).items():
        require(sha(row['path'])==row['sha256'],'launch evidence hash differs: '+name)
    result.update(scene=scene,phase=phase,launch_dir=str(launch_dir),exit_receipt_sha256=sha(launch_dir/'EXIT.json'),trace_sha256=hashlib.sha256(blob).hexdigest())
    return result


def historical_limitations():
    files=('HOTDOG_RENDER_ATTEMPT000_ACCESS.json','PRODUCTION_ATTEMPT001_ACCESS.json')
    rows={}
    for name in files:
        p=TART.parent/'independent_review'/name;r=read(p)
        require(r['passed'] is False and r['status']=='INVALID','historical invalid audit was upgraded')
        snapshot=CONT/'historical_607b908/independent_review'/name
        require(sha(p)==sha(snapshot),'historical invalid audit differs from immutable snapshot')
        rows[name]={'path':str(p),'sha256':sha(p),'status':'INVALID','error':r['error']}
    snapshot_manifest=read(CONT/'historical_607b908/SNAPSHOT_MANIFEST.json')
    for row in snapshot_manifest['files']:
        require(sha(row['snapshot_path'])==row['sha256'],'historical snapshot altered: '+row['snapshot_path'])
    return {'snapshot_files_verified':len(snapshot_manifest['files']),'snapshot_manifest_sha256':sha(CONT/'historical_607b908/SNAPSHOT_MANIFEST.json'),'initial_hotdog_execution_access':'INCOMPLETE_INVALID; exit143 historical trace not repaired',
            'first_checker_access':'INVALID; preserved independently of new success','evidence':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenes',nargs='+',choices=SCENES,default=SCENES)
    parser.add_argument('--output',type=Path,default=ART/'PRODUCTION.json')
    parser.add_argument('--launch-index',type=Path)
    parser.add_argument('--skip-launch-audits',action='store_true',help='Partial engineering verification only; cannot issue final aggregate PASS.')
    args=parser.parse_args();assert_owned_path(args.output,ART)
    start=time.monotonic();report={'schema':'storage-continuation-independent-production-v1','passed':False,'scientific_GO':False,'human_review':'PENDING',
        'scene_roots':{s:str(scene_root(s)) for s in SCENES},'expected_frames':196,'expected_videos':24,'scenes':{},'errors':[]}
    try:
        report['inheritance']=verify_inheritance();report['historical_audit_limitations']=historical_limitations()
        report['storage_freeze']=verify_storage_freeze()
        lock=read(TART/'INHERITED_LOCK.json');require(lock['parameter_hash']=='6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9','parameter hash differs')
        prod=importlib.import_module('verify_production')
        for scene in args.scenes:
            rows={};entry=report['scenes'][scene]={'frames':rows,'root':str(scene_root(scene))}
            try:
                active=scene_root(scene);assert_owned_path(active,LEGACY if scene=='hotdog' else EXTERNAL)
                prod.TOUT=active
                prod.verify_seal=lambda folder,context=None:verify_owned_seal(folder,active,context)
                manifest,specs,cameras=prod.verify_cameras(scene);entry['cameras']=cameras
                calibration=prod.verify_calibration(scene,manifest,lock)
                require(read(TART/scene/'CALIBRATION.json')==calibration,'calibration metadata copies differ')
                for row in calibration['frames']:
                    assert_owned_path(row['path'],active);assert_owned_path(row['unpatched_path'],active)
                entry['calibration']={'frames':len(calibration['frames']),'status':'PASS','path':str(active/'calibration'/scene/'CALIBRATION.json'),'sha256':sha(active/'calibration'/scene/'CALIBRATION.json')}
                require({p.name for p in (active/'frames'/scene).iterdir()}=={s['key'] for s in specs},'frame directory set differs')
                require({p.name for p in (active/'raw'/scene).iterdir()}=={s['key'] for s in specs},'raw directory set differs')
                for spec in specs:
                    result=prod.verify_frame(spec,manifest,lock,calibration)
                    result['context']=read(active/'frames'/scene/spec['key']/'camera.json');rows[spec['key']]=result
                    print('VERIFIED',scene,spec['key'],flush=True)
                frame_manifest=read(TART/scene/'FRAMES.json');verify_frame_manifest(frame_manifest,scene,rows)
                entry['media']=prod.verify_media(scene,rows,lock)
                entry['frame_manifest_sha256']=sha(TART/scene/'FRAMES.json')
                if scene!='hotdog':entry['storage_bindings']=_binding_receipts(scene)
            except Exception as exc:report['errors'].append({'where':scene,'error':repr(exc),'traceback':traceback.format_exc()})
            report['verified_frames']=sum(len(v['frames']) for v in report['scenes'].values());write(args.output,report)
        if args.launch_index:
            index=read(args.launch_index);report['launch_audits']=[]
            for row in index['launches']:
                report['launch_audits'].append(audit_launch(Path(row['path']),row['scene'],row['phase'],lock))
            require(len(report['launch_audits'])==6,'six distinct successful launch audits required')
            require({(r['scene'],r['phase']) for r in report['launch_audits']}=={(s,p) for s in NEW_SCENES for p in ('render','media')},'six new launch audits missing')
        elif not args.skip_launch_audits:raise ValueError('full verification requires actual six-launch index')
        report['verified_videos']=sum(len(v.get('media',{}).get('videos',{})) for v in report['scenes'].values())
        report['verified_contacts']=sum(v.get('media',{}).get('contacts',0) for v in report['scenes'].values())
        report['verified_first_mid_last']=sum(v.get('media',{}).get('first_mid_last',0) for v in report['scenes'].values())
        if not report['errors'] and set(args.scenes)==set(SCENES) and not args.skip_launch_audits:
            check_counts({s:len(v['frames']) for s,v in report['scenes'].items()})
            require((report['verified_videos'],report['verified_contacts'],report['verified_first_mid_last'])==(24,60,36),'aggregate media counts differ')
            report['passed']=True
    except Exception as exc:report['errors'].append({'where':'global','error':repr(exc),'traceback':traceback.format_exc()})
    report['status']='PASS_ARTIFACT_INTEGRITY_HISTORICAL_AUDIT_GAP_RETAINED' if report['passed'] else 'INCOMPLETE_OR_INVALID'
    report['elapsed_seconds']=time.monotonic()-start
    report['scope']='Both roots: full native/typed/response/provenance numeric integrity, exact camera/source/parameter/calibration seals, complete PNG and 33-frame distinct video decode. New storage receipts and normal-completion traces. Historical Hotdog execution trace gap remains.'
    write(args.output,report);print(json.dumps({k:report.get(k) for k in ('passed','status','verified_frames','verified_videos','errors')}),flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
