"""Fail-closed GPU observations, atomic manifests and untrusted-archive handling.

This module uses only the standard library and never initializes CUDA.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile

STAGES = ('smoke', 'train', 'export', 'tsdf', 'eval')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with open(tmp, 'xb') as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        tmp.unlink(missing_ok=True)


def parse_gpu_xml(raw):
    try:
        root = ET.fromstring(raw)
        result = []
        for node in root.findall('gpu'):
            ident = node.findtext('uuid')
            mem = int(node.findtext('fb_memory_usage/used').split()[0])
            util = int(node.findtext('utilization/gpu_util').split()[0])
            processes = node.find('processes')
            if (not ident or processes is None or mem < 0 or util < 0
                    or (processes.text or '').strip()):
                return None
            contexts = []
            for p in processes.findall('process_info'):
                pid, kind = int(p.findtext('pid')), p.findtext('type')
                if pid <= 0 or not kind:
                    return None
                contexts.append({'pid': pid, 'type': kind})
            result.append({'uuid': ident, 'memory_mib': mem, 'util_percent': util,
                           'contexts': contexts})
        if not result or len({x['uuid'] for x in result}) != len(result):
            return None
        return result
    except (ET.ParseError, TypeError, ValueError, AttributeError):
        return None


def query_gpus():
    try:
        result = subprocess.run(['nvidia-smi', '-q', '-x'], capture_output=True,
                                text=True, timeout=20, check=True)
        return parse_gpu_xml(result.stdout)
    except (subprocess.SubprocessError, OSError):
        return None


def is_idle(gpu):
    return (not gpu['contexts'] and gpu['memory_mib'] <= 128
            and gpu['util_percent'] == 0)


class IdleGate:
    def __init__(self, stable_seconds=60):
        self.stable_seconds = stable_seconds
        self.since = {}

    def observe(self, samples, now=None):
        now = time.monotonic() if now is None else now
        if samples is None:
            self.since.clear()
            return []
        idle = {g['uuid'] for g in samples if is_idle(g)}
        self.since = {key: value for key, value in self.since.items() if key in idle}
        ready = []
        for key in sorted(idle):
            if key in self.since and now - self.since[key] >= self.stable_seconds:
                ready.append(key)
            self.since.setdefault(key, now)
        return ready


def stage_conflict(samples, selected_uuid, owned_pids):
    if samples is None:
        return True
    gpu = next((g for g in samples if g['uuid'] == selected_uuid), None)
    return gpu is None or any(c['pid'] not in owned_pids for c in gpu['contexts'])


def seal_stage(path, stage, inputs, outputs):
    if stage not in STAGES:
        raise ValueError('unknown stage')
    files = {str(Path(p).resolve()): sha256(p) for p in outputs}
    if not files:
        raise ValueError('no evidence to seal')
    atomic_json(path, {'schema': 1, 'stage': stage, 'inputs': inputs,
                       'outputs': files, 'sealed_unix': time.time()})


def verify_seal(path, stage, inputs):
    try:
        seal = json.loads(Path(path).read_text())
        return (seal['schema'] == 1 and seal['stage'] == stage
                and seal['inputs'] == inputs and bool(seal['outputs'])
                and all(sha256(p) == h for p, h in seal['outputs'].items()))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def next_stage(verified):
    missing = False
    next_missing = None
    for stage in STAGES:
        if verified.get(stage, False):
            if missing:
                raise ValueError('noncontiguous verified stages')
        else:
            missing = True
            if next_missing is None:
                next_missing = stage
    return next_missing


def archive_failure(state, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / (str(time.time_ns()) + '-' + uuid.uuid4().hex + '.json')
    atomic_json(output, json.loads(Path(state).read_text()))
    return output


def safe_member(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or '..' in path.parts or '\\' in name
            or not path.parts or ':' in path.parts[0]):
        raise ValueError('unsafe archive member: ' + name)
    return path


def validate_members(entries):
    seen = set()
    for name, isdir, isfile in entries:
        path = safe_member(name)
        key = str(path)
        if not (isdir or isfile) or key in seen:
            raise ValueError('link, special file or duplicate: ' + name)
        seen.add(key)
    # Reject file-as-parent conflicts before any extraction takes place.
    files = {str(safe_member(n)) for n, d, f in entries if f}
    for name, _, _ in entries:
        if any(str(p) in files for p in safe_member(name).parents):
            raise ValueError('archive file/directory conflict')


def safe_extract_tar(archive, destination):
    destination = Path(destination)
    if destination.exists():
        raise ValueError('extraction destination must not exist')
    with tarfile.open(archive, 'r:*') as t:
        members = t.getmembers()
        validate_members([(m.name, m.isdir(), m.isfile()) for m in members])
        destination.mkdir(parents=True)
        count = total = 0
        for m in members:
            target = destination.joinpath(*safe_member(m.name).parts)
            if m.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with t.extractfile(m) as src, open(target, 'xb') as dst:
                    shutil.copyfileobj(src, dst, 8 << 20)
                count += 1
                total += m.size
        return {'files': count, 'bytes': total, 'members': len(members)}


def safe_extract_zip_selected(archive, destination, select):
    destination = Path(destination)
    if destination.exists():
        raise ValueError('extraction destination must not exist')
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        validate_members([(m.filename, m.is_dir(),
                           not m.is_dir() and ((m.external_attr >> 16) & 0o170000) != 0o120000)
                          for m in members])
        chosen = [m for m in members if not m.is_dir() and select(m.filename)]
        if not chosen:
            raise ValueError('selection empty')
        destination.mkdir(parents=True)
        for m in chosen:
            target = destination.joinpath(*safe_member(m.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as src, open(target, 'xb') as dst:
                shutil.copyfileobj(src, dst, 8 << 20)  # zipfile checks CRC at EOF
        return {'files': len(chosen), 'bytes': sum(m.file_size for m in chosen),
                'selected': [m.filename for m in chosen]}
