"""Deterministic acquisition contracts. No GPU initialization at import."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess


def utc(): return datetime.now(timezone.utc).isoformat()

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(2**20),b''): h.update(chunk)
    return h.hexdigest()

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def atomic_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+f'.tmp.{os.getpid()}')
    with temp.open('w') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp,path)

def read_train_metadata(root):
    value=json.loads((Path(root)/'transforms_train.json').read_text())
    if not 0<float(value['camera_angle_x'])<3.141592653589793: raise ValueError('invalid TRAIN FoV')
    if not value['frames']: raise ValueError('empty TRAIN')
    for frame in value['frames']:
        rel=PurePosixPath(frame['file_path'])
        if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='train' or len(rel.parts)!=2:
            raise ValueError('not a strictly TRAIN relative image: '+str(rel))
        if rel.suffix not in ('','.png'): raise ValueError('unexpected TRAIN image extension')
        if len(frame['transform_matrix'])!=4 or any(len(row)!=4 for row in frame['transform_matrix']):
            raise ValueError('invalid TRAIN camera')
    return value

def patch_sources(original):
    result=dict(original)
    edits={
      'utils/general_utils.py': [('def safe_state(silent):','def safe_state(silent, seed=0):'),('    random.seed(0)','    random.seed(seed)'),('    np.random.seed(0)','    np.random.seed(seed)'),('    torch.manual_seed(0)','    torch.manual_seed(seed)')],
      'scene/dataset_readers.py': [('    print("Reading Test Transforms")\n    test_cam_infos = readCamerasFromTransforms(path, "transforms_test.json", white_background, extension)','    # Strict TRAIN-only acquisition: do not open any TEST/VAL metadata.\n    test_cam_infos = []')],
      'train.py': [('    args = parser.parse_args(sys.argv[1:])','    parser.add_argument("--seed", type=int, default=0)\n    args = parser.parse_args(sys.argv[1:])'),('safe_state(args.quiet)','safe_state(args.quiet, args.seed)'),('        (model_params, first_iter) = torch.load(checkpoint)','        (model_params, first_iter) = acquisition_runtime.load_checkpoint(checkpoint)'),('    viewpoint_stack = None\n    ema_loss_for_log = 0.0','    viewpoint_stack, ema_loss_for_log = acquisition_runtime.restore_loop(checkpoint, scene)'),('                torch.save((gaussians.capture(), iteration), scene.model_path + "/chkpnt" + str(iteration) + ".pth")','                acquisition_runtime.save_checkpoint(gaussians, iteration, scene, viewpoint_stack, ema_loss_for_log)'),('import os\n','import os\nimport acquisition_runtime\n')]
    }
    for path, pairs in edits.items():
        for old,new in pairs:
            if result[path].count(old)!=1: raise ValueError('unexpected upstream patch context: '+path+' '+old)
            result[path]=result[path].replace(old,new)
    return result

def check_resume(manifest,sidecar):
    if sidecar['manifest_sha256']!=canonical_hash(manifest): raise ValueError('resume manifest mismatch')
    if not 0<int(sidecar['iteration'])<=int(manifest['iterations']): raise ValueError('invalid resume iteration')

def validate_checkpoint_sidecar(path,sidecar):
    if sha256(path)!=sidecar['sha256']: raise ValueError('checkpoint hash mismatch')

def gpu_guard_rows(selected_uuid,rows,own_pids):
    for row in rows:
        if row['gpu_uuid']==selected_uuid: raise RuntimeError('selected GPU already occupied: '+str(row))
        if int(row['pid']) not in own_pids: raise RuntimeError('foreign GPU process: '+str(row))

def gpu_guard(gpu,runroot):
    query=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,memory.total','--format=csv,noheader,nounits'],text=True)
    devices=[]
    for line in query.splitlines():
        index,uuid,free,total=[x.strip() for x in line.split(',')]
        devices.append(dict(index=int(index),uuid=uuid,free_mib=int(free),total_mib=int(total)))
    selected=next(x for x in devices if x['index']==gpu)
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory','--format=csv,noheader,nounits'],text=True)
    rows=[]; own=set()
    for line in raw.splitlines():
        if not line.strip(): continue
        uuid,pid,name,memory=[x.strip() for x in line.split(',',3)]
        row=dict(gpu_uuid=uuid,pid=int(pid),process_name=name,memory_mib=memory)
        try:
            proc=Path('/proc')/pid
            row['uid']=proc.stat().st_uid
            cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            row['cmdline']=cmd
            # An exact frozen scene manifest inside this run and our entry script
            # identify our acquisitions; same uid alone never establishes ownership.
            entry=str(Path(runroot).parents[1]/'artifacts/hybrid_raster_trained_models_v1/acquisition/train_entry.py')
            manifests=str(Path(runroot).parents[1]/'artifacts/hybrid_raster_trained_models_v1/acquisition/manifests')
            if row['uid']==os.getuid() and entry in cmd and ('--manifest '+manifests+'/') in cmd:
                own.add(int(pid))
        except (FileNotFoundError,PermissionError): pass
        rows.append(row)
    gpu_guard_rows(selected['uuid'],rows,own)
    if selected['free_mib']<12000: raise RuntimeError('insufficient GPU free memory')
    return dict(utc=utc(),gpu=gpu,devices=devices,processes=rows,own_pids=sorted(own),nvidia_smi=subprocess.check_output(['nvidia-smi'],text=True))

def audit_trace(path,original_data,local_initialization=None):
    import re
    violations=[]; allowed=[]; image_paths=set(); lines=0
    data=Path(original_data)
    for line in Path(path).read_text(errors='replace').splitlines():
        lines+=1
        for raw in re.findall(r'"([^"\n]+)"',line)+re.findall(r'<(/[^>]+)>',line):
            clean=raw.lower()
            if 'transforms_test.json' in clean or 'transforms_val.json' in clean or re.search(r'/(test|val|mesh|meshes)(/|\.)',clean): violations.append(line)
            if str(data) in raw:
                target=Path(raw)
                if local_initialization and target==Path(local_initialization): continue
                if target==data/'train' and ('O_PATH' in line or 'O_DIRECTORY' in line):
                    allowed.append(raw);continue
                if target==data/'transforms_train.json' or (data/'train') in target.parents:
                    allowed.append(raw)
                    if target.suffix=='.png': image_paths.add(str(target))
                else: violations.append(line)
    return dict(scope='actual strace descendant open/openat/openat2/creat syscalls only; not whole-session audit',lines=lines,violations=violations,allowed_dataset_opens=len(allowed),distinct_train_image_paths=len(image_paths),passed=not violations)
