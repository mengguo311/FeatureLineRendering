"""Bounded, data-only saved-asset ZIP exchange for the local demo.

Archive checksums detect corruption, not authorship. Legacy exports have no
whole-archive manifest; they still need valid mesh/selection hashes and anchors.
No uploaded path is opened outside the new import directory.
"""
import runtime
from runtime import sha,now
from pathlib import Path
import hashlib,io,json,math,re,shutil,stat,zipfile
import numpy as np
from demo import load_asset,new_output
from presentation import camera_values

MAX_UPLOAD=32*2**20
MAX_EXPANDED=128*2**20
MANIFEST='ASSET_MANIFEST.json'

def digest(data):return hashlib.sha256(data).hexdigest()

def json_data(data):
    def invalid(value):raise ValueError('nonfinite JSON value: '+value)
    result=json.loads(data,parse_constant=invalid)
    if not isinstance(result,dict):raise ValueError('JSON object required')
    return result

def safe_name(name):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}',name):
        raise ValueError('saved asset ZIP requires flat, safe filenames')
    return name

def read_zip(payload,nested=False):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        infos=archive.infolist();names=[i.filename for i in infos]
        if not 1<=len(infos)<=128 or len(set(names))!=len(names):raise ValueError('invalid or duplicate ZIP members')
        if sum(i.file_size for i in infos)>MAX_EXPANDED:raise ValueError('expanded ZIP exceeds 128 MiB')
        result={}
        for info in infos:
            safe_name(info.filename)
            mode=stat.S_IFMT(info.external_attr>>16)
            if mode not in (0,stat.S_IFREG) or info.flag_bits&1 or info.is_dir():raise ValueError('ZIP links/directories/encryption are unsupported')
            if info.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):raise ValueError('unsupported ZIP compression')
            if nested:
                if not info.filename.endswith('.npy'):raise ValueError('NPZ must contain NPY arrays')
            elif not info.filename.endswith(('.json','.npz')):raise ValueError('only saved-asset JSON/NPZ files can be imported')
            result[info.filename]=archive.read(info)
        return result

def array_data(payload):
    """Check declared array shape/size before NumPy allocates the array."""
    files=read_zip(payload,nested=True);result={}
    for filename,data in files.items():
        stream=io.BytesIO(data);version=np.lib.format.read_magic(stream)
        shape,fortran,dtype=np.lib.format._read_array_header(stream,version)
        if dtype.kind not in 'biuf' or len(shape)>3 or any(x<0 for x in shape):raise ValueError('only bounded numeric arrays are supported')
        count=math.prod(shape)
        if count*dtype.itemsize>MAX_EXPANDED or stream.tell()+count*dtype.itemsize!=len(data):raise ValueError('array size/header mismatch')
        result[filename[:-4]]=np.load(io.BytesIO(data),allow_pickle=False)
    return result

def validate_arrays(files,meta):
    arrays={};expanded=0
    for name,data in files.items():
        if not name.endswith('.npz'):continue
        with zipfile.ZipFile(io.BytesIO(data)) as z:expanded+=sum(i.file_size for i in z.infolist())
        if expanded>MAX_EXPANDED:raise ValueError('all expanded arrays exceed 128 MiB')
        arrays[name]=array_data(data)
    mesh=arrays['mesh.npz'];v,f=mesh['vertices'],mesh['faces']
    if v.ndim!=2 or v.shape[1]!=3 or not 3<=len(v)<=100000 or not np.isfinite(v).all() or np.max(np.abs(v))>10:
        raise ValueError('invalid or oversized proxy vertices')
    if f.ndim!=2 or f.shape[1]!=3 or not 1<=len(f)<=150000 or f.dtype.kind not in 'iu' or (f<0).any() or (f>=len(v)).any():
        raise ValueError('invalid or oversized proxy faces')
    total=0
    for region in meta['regions']:
        s=arrays[f'region_{region}.npz'];n=len(s['points']);total+=n
        if not 1<=n<=100000 or s['points'].shape!=(n,2,3) or s['bary'].shape!=(n,2,3):raise ValueError('invalid path shapes')
        if s['face'].shape!=(n,) or s['face'].dtype.kind not in 'iu' or (s['face']<0).any() or (s['face']>=len(f)).any():raise ValueError('invalid path face indices')
        if s['stroke_id'].shape!=(n,) or s['stroke_id'].dtype.kind not in 'iu' or (s['stroke_id']<0).any():raise ValueError('invalid stroke IDs')
        if not np.isfinite(s['points']).all() or not np.isfinite(s['bary']).all():raise ValueError('nonfinite path coordinates')
        if np.min(s['bary'])< -1e-8 or np.max(s['bary'])>1+1e-8 or not np.allclose(s['bary'].sum(-1),1,rtol=0,atol=1e-8):
            raise ValueError('invalid barycentric coordinates')
    if total>300000:raise ValueError('total path budget exceeded')

def unpack_archive(payload,destination,originals):
    """Validate first, create a new folder, then check renderer anchor semantics.

    On rejection only the newly created folder is removed. Known catalog model
    hashes constrain compatibility; uploaded provenance is not authentication.
    """
    destination=Path(destination);created=False
    try:
        if not 0<len(payload)<=MAX_UPLOAD:raise ValueError('saved asset ZIP must be at most 32 MiB')
        files=read_zip(payload)
        if 'asset.json' not in files:raise ValueError('choose Download saved asset ZIP, not a presentation ZIP')
        meta=json_data(files['asset.json'])
        scene=meta['scene']
        if scene not in originals or meta['original']['sha256']!=originals[scene]:raise ValueError('saved model identity does not match this catalog')
        regions=meta['regions']
        if not isinstance(regions,dict) or not 1<=len(regions)<=32 or any(not re.fullmatch(r'[1-9]|[12][0-9]|3[0-2]',k) for k in regions):
            raise ValueError('invalid region IDs')
        if any(not isinstance(v,str) or not 1<=len(v)<=160 for v in regions.values()):raise ValueError('invalid region name')
        if set(meta['styles'])!=set(regions) or set(meta['statistics'])!=set(regions):raise ValueError('incomplete region metadata')
        camera_values(meta.get('viewer_camera',dict(azimuth=17,elevation=20,distance=4.7)))
        selected=meta.get('selected_region',2)
        if type(selected) is not int or str(selected) not in regions:raise ValueError('invalid selected region')
        required={'asset.json','mesh.npz'}|{f'region_{r}.npz' for r in regions}
        for item in meta.get('region_history',[]):required.add(safe_name(item['face_ids_file']))
        origins=meta.get('region_origins',{})
        if not isinstance(origins,dict) or not set(origins)<=set(regions):raise ValueError('invalid creation snapshot regions')
        for r,item in origins.items():
            if item['file']!=f'origin_{r}.npz':raise ValueError('invalid creation snapshot filename')
            required.add(item['file'])
        if not required<=files.keys():raise ValueError('saved asset is missing required paths or selections')
        if any(name.startswith('region_') and name.endswith('.npz') and name not in required for name in files):raise ValueError('unexpected region path file')
        if any(name.startswith('origin_') and name.endswith('.npz') and name not in required for name in files):raise ValueError('unexpected creation snapshot file')
        for name,data in files.items():
            if name.endswith('.json'):
                if len(data)>2**20:raise ValueError('metadata file too large')
                json_data(data)
        integrity='legacy_anchor_validation'
        if MANIFEST in files:
            manifest=json_data(files.pop(MANIFEST))
            if manifest.get('schema')!='partwise_saved_asset_v1' or manifest.get('files')!={n:digest(d) for n,d in files.items()}:
                raise ValueError('saved asset archive checksum mismatch')
            integrity='manifest_sha256_and_anchor_validation'
        if digest(files['mesh.npz'])!=meta['mesh_sha256']:raise ValueError('proxy checksum mismatch')
        for item in meta.get('region_history',[]):
            if digest(files[item['face_ids_file']])!=item['face_ids_sha256']:raise ValueError('selection checksum mismatch')
        for item in origins.values():
            if digest(files[item['file']])!=item['sha256']:raise ValueError('creation snapshot checksum mismatch')
        validate_arrays(files,meta)
        # No extractall: every validated basename is written explicitly.
        new_output(destination);created=True
        for name,data in files.items():(destination/name).write_bytes(data)
        load_asset(destination)
        return dict(scene=scene,archive_sha256=digest(payload),integrity=integrity,
            files={n:digest(d) for n,d in files.items()},created_utc=now(),
            original_sha256=meta['original']['sha256'],mesh_sha256=meta['mesh_sha256'],
            scope='Final saved asset and any creation-time region snapshots; no session undo or uncommitted drafts. Checksums are not proof of authorship or geometry truth.')
    except Exception as exc:
        if created:shutil.rmtree(destination)
        if isinstance(exc,(ValueError,KeyError,TypeError,IndexError,OverflowError,zipfile.BadZipFile,EOFError,UnicodeError,NotImplementedError)):
            raise ValueError('Invalid saved asset: '+str(exc)) from exc
        raise

def export_archive(asset,camera,selected_region,example_metadata=None):
    asset=Path(asset);files={p.name:p.read_bytes() for p in sorted(asset.iterdir()) if p.is_file() and p.name!=MANIFEST}
    meta=json_data(files['asset.json']);meta['viewer_camera']=camera_values(camera);meta['selected_region']=int(selected_region)
    if example_metadata:meta['demo_example']=example_metadata
    files['asset.json']=(json.dumps(meta,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    files[MANIFEST]=(json.dumps(dict(schema='partwise_saved_asset_v1',files={n:digest(d) for n,d in files.items()}),indent=2)+'\n').encode()
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(safe_name(name),data)
    return output.getvalue()
