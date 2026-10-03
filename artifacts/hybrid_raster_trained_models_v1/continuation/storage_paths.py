"""Explicit two-root storage mapping. No rendering or scientific computation."""
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT/'artifacts/hybrid_raster_trained_models_v1/transport'
CONT = ART.parent/'continuation'
EXTERNAL_ROOT = Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1')
OUT = EXTERNAL_ROOT/'transport'
LEGACY_OUT = ROOT/'out/hybrid_raster_trained_models_v1/transport'
NEW_SCENES = ('materials', 'mic', 'ship')
SCENES = ('hotdog',) + NEW_SCENES
RESERVE_BYTES = 1024**3
MAP_PATH = CONT/'STORAGE_MAP.json'
_KINDS = ('raw', 'frames', 'calibration', 'media')
_JSON_NAMES = ('CALIBRATION.json', 'CALIBRATION_FAILURE.json', 'FRAMES.json', 'MEDIA.json')


def require_new_scene(scene):
    if scene not in NEW_SCENES:
        raise ValueError('Storage continuation may launch only materials, mic or ship: '+str(scene))
    return scene


def scene_root(scene):
    if scene not in SCENES: raise ValueError('Unknown frozen scene: '+str(scene))
    return LEGACY_OUT if scene == 'hotdog' else OUT


def output_path(scene, kind, key=None):
    if kind not in _KINDS: raise ValueError('Unknown output kind')
    path = scene_root(scene)/kind/scene
    if key is not None:
        if not re.fullmatch(r'(?:F|C)_\d{3}|arc0_\d{3}', key): raise ValueError('Invalid frame key')
        path /= key
    return path


def storage_map():
    return {
        'schema': 'storage-continuation-map-v1',
        'repo_root': str(ROOT),
        'external_root': str(EXTERNAL_ROOT),
        'legacy_transport_root': str(LEGACY_OUT),
        'new_transport_root': str(OUT),
        'scene_roots': {scene: str(scene_root(scene)) for scene in SCENES},
        'new_scenes': list(NEW_SCENES),
        'minimum_free_bytes_each_root': RESERVE_BYTES,
        'read_only_legacy_scene': 'hotdog',
        'binding_only': ['run_transport.OUT', 'adapters.OUT', 'hybrid_raster_native.STAGE'],
        'retained_real_paths': ['run_transport.ROOT', 'run_transport.ART', 'hybrid_raster_native.NATIVE'],
        'seal_context': 'Original producer and adapter byte hashes stay unchanged; new storage glue identity is recorded separately per launch.',
        'no_symlinks': True,
    }


def _absolute_no_symlinks(path):
    path = Path(os.path.abspath(os.fspath(path)))
    for node in (path, *path.parents):
        if node.is_symlink(): raise ValueError('Symlink path is not authorized: '+str(node))
    return path


def require_safe_output(path):
    path = _absolute_no_symlinks(path)
    if not path.is_relative_to(EXTERNAL_ROOT):
        raise PermissionError('New output must stay in approved external root: '+str(path))
    for node in (path, *path.parents):
        if node.is_relative_to(EXTERNAL_ROOT) and node.exists() and node.stat().st_uid != os.getuid():
            raise PermissionError('External output owner differs: '+str(node))
    return path


def assert_roots():
    """Check real paths, owner, writeability and both hard free-space reserves."""
    _absolute_no_symlinks(ROOT)
    require_safe_output(EXTERNAL_ROOT)
    result = {}
    for label, path in [('repo', ROOT), ('external', EXTERNAL_ROOT)]:
        if not path.is_dir(): raise RuntimeError('Storage root is missing: '+str(path))
        stat = path.stat()
        if stat.st_uid != os.getuid() or not os.access(path, os.W_OK):
            raise PermissionError('Storage root ownership/writeability mismatch: '+str(path))
        free = shutil.disk_usage(path).free
        result[label] = {'path':str(path), 'free_bytes':free, 'minimum_free_bytes':RESERVE_BYTES,
                         'device':stat.st_dev, 'uid':stat.st_uid, 'real_path':str(path.resolve()), 'symlink':False}
        if free < RESERVE_BYTES: raise RuntimeError('Less than 1GiB reserve at '+str(path))
    return result


def require_storage_release():
    # Lazy import keeps the resolver available to independent CPU readers.
    from run_storage_transport import require_storage_release as verify
    return verify()


def _metadata_path_allowed(path, scene):
    allowed = [ART/'STATUS.json', ART.parent/'STATUS.json']
    allowed += [ART/scene/name for name in _JSON_NAMES]
    for target in allowed:
        if path == target: return True
        if path.parent == target.parent and path.name.startswith('.'+target.name+'.'): return True
    return False


def require_write_path(path, scene):
    """Permit large writes externally and only exact producer JSON destinations in repo."""
    require_new_scene(scene)
    path = _absolute_no_symlinks(path)
    if path.is_relative_to(EXTERNAL_ROOT):
        require_safe_output(path)
        for kind in _KINDS:
            if path.is_relative_to(OUT/kind/'hotdog'):
                raise PermissionError('Hotdog remains read-only, including duplicate destinations')
        return path
    if _metadata_path_allowed(path, scene): return path
    raise PermissionError('Producer write outside authorized storage/metadata: '+str(path))


def write_audit_hook(scene):
    """Python write guard; actual child and native I/O remain independently traced."""
    require_new_scene(scene)
    def check_path(value, dir_fd=None):
        if isinstance(value, int): return  # fd opened through the guarded path operation
        if dir_fd not in (None, -1) and not os.path.isabs(value):
            value = Path(os.readlink('/proc/self/fd/'+str(dir_fd)))/os.fsdecode(value)
        require_write_path(os.fsdecode(value), scene)
    def hook(event, args):
        if event == 'open':
            path, mode, flags = args
            if isinstance(path, int): return
            if (flags or 0) & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND): check_path(path)
        elif event == 'os.mkdir':
            path, _, dir_fd = args
            # pathlib.mkdir(exist_ok=True) attempts existing ancestor directories; no mutation occurs.
            candidate = _absolute_no_symlinks(os.fsdecode(path))
            if candidate.is_dir(): return
            check_path(path, dir_fd)
        elif event in ('os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.truncate', 'os.utime'):
            check_path(args[0], args[-1] if event in ('os.remove','os.rmdir') else None)
        elif event in ('os.rename', 'os.link'):
            check_path(args[0], args[2] if len(args)>2 else None)
            check_path(args[1], args[3] if len(args)>3 else None)
        elif event == 'os.symlink':
            raise PermissionError('Producer may not create symlinks')
    return hook
