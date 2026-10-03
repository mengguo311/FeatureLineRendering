"""Detached, traced storage-only continuation supervisor; no scientific changes.

Only the three previously unrun scenes are accepted. Every new persistent log,
trace, cache, temporary file and runtime receipt is beneath EXTERNAL_ROOT.
The original transport's native GPU guard remains independently active.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import traceback
import uuid

sys.dont_write_bytecode = True
from storage_paths import (ROOT, ART, CONT, EXTERNAL_ROOT, OUT, assert_roots,
                           require_safe_output, require_new_scene)

PYTHON = '/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
LAUNCH_ROOT = EXTERNAL_ROOT / 'launchlogs'
BUDGET_CLOCK = EXTERNAL_ROOT / 'CONTINUATION_CLOCK.json'
RUNTIME = EXTERNAL_ROOT / 'SUPERVISOR_RUNTIME.json'
POLL_SECONDS = 3.0


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_once_json(path, value):
    path = require_safe_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def atomic_json(path, value):
    path = require_safe_output(path)
    temporary = path.with_name(path.name + '.partial.' + str(os.getpid()))
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def producer_command(scene, phase):
    require_new_scene(scene)
    if phase not in ('render', 'media'):
        raise ValueError('Only render/media continuation is authorized')
    return [PYTHON, str(CONT / 'run_storage_transport.py'), '--phase', phase, '--scene', scene]


def trace_command(command, trace):
    require_safe_output(trace)
    return ['strace', '-f', '-q', '-yy', '-s', '4096', '-e',
            'trace=open,openat,openat2,creat', '-o', str(trace), '--', *command]


def child_environment():
    environment = os.environ.copy()
    settings = {
        'TMPDIR': EXTERNAL_ROOT / 'tmp', 'TMP': EXTERNAL_ROOT / 'tmp',
        'TEMP': EXTERNAL_ROOT / 'tmp', 'XDG_CACHE_HOME': EXTERNAL_ROOT / 'cache',
        'TORCH_HOME': EXTERNAL_ROOT / 'cache/torch',
        'TORCH_EXTENSIONS_DIR': EXTERNAL_ROOT / 'cache/torch_extensions',
        'CUDA_CACHE_PATH': EXTERNAL_ROOT / 'cache/cuda',
        'MPLCONFIGDIR': EXTERNAL_ROOT / 'cache/matplotlib',
        'NUMBA_CACHE_DIR': EXTERNAL_ROOT / 'cache/numba',
    }
    for name, path in settings.items():
        require_safe_output(path).mkdir(parents=True, exist_ok=True)
        environment[name] = str(path)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    environment['GIT_OPTIONAL_LOCKS'] = '0'
    return environment


def process_identity(pid):
    """Linux PID identity, including start ticks to reject PID reuse."""
    proc = Path('/proc') / str(pid)
    try:
        stat = (proc / 'stat').read_text()
        fields = stat[stat.rfind(')') + 2:].split()
        return {'pid': int(pid), 'uid': proc.stat().st_uid,
                'starttime': int(fields[19]), 'ppid': int(fields[1]), 'pgid': int(fields[2]),
                'session': int(fields[3]),
                'cmdline': (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')}
    except FileNotFoundError:
        return None


def stop_owned(identity, sig):
    """Signal only this supervisor's exact private child process group."""
    current = process_identity(identity['pid'])
    if current is None:
        return False
    keys = ('pid', 'uid', 'ppid', 'starttime', 'pgid')
    if any(current[key] != identity[key] for key in keys):
        raise RuntimeError('Refusing termination: child ownership changed')
    if current['uid'] != os.getuid() or current['ppid'] != os.getpid() or current['pgid'] != current['pid']:
        raise RuntimeError('Refusing termination: not our private process group')
    os.killpg(current['pgid'], sig)
    return True


def require_idle_gpu(rows):
    # Even a same-user process is foreign here: production launches are serial.
    if rows:
        raise RuntimeError('GPU_BUSY: existing compute PID(s): ' + json.dumps(rows, sort_keys=True))
    return rows


def gpu_guard():
    devices = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,name,memory.free,memory.total',
                                      '--format=csv,noheader,nounits'], text=True)
    raw = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory',
                                  '--format=csv,noheader,nounits'], text=True)
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        gpu_uuid, pid, name, memory = [part.strip() for part in line.split(',', 3)]
        rows.append({'gpu_uuid': gpu_uuid, 'pid': int(pid), 'process_name': name,
                     'memory_mib': memory, 'identity': process_identity(int(pid))})
    record = {'utc': utc(), 'supervisor_pid': os.getpid(), 'devices': devices,
              'processes': rows, 'ownership_rule': 'No existing compute PID is owned by a new serial launch',
              'nvidia_smi': subprocess.check_output(['nvidia-smi'], text=True)}
    return record


def storage_guard():
    # Shared implementation validates both exact roots, symlink/uid ownership,
    # filesystem devices and >=1 GiB available on each filesystem.
    return assert_roots()


def budget_remaining(clock, ledger, now=None):
    now = time.time() if now is None else now
    gpu_used = sum(float(row.get('elapsed_seconds', 0)) for row in ledger if row.get('phase') == 'render')
    result = {'gpu_used_seconds': gpu_used,
              'gpu_remaining_seconds': float(clock['gpu_limit_seconds']) - gpu_used,
              'wall_remaining_seconds': float(clock['wall_limit_seconds']) - (now - float(clock['started_epoch']))}
    if result['wall_remaining_seconds'] <= 0:
        raise RuntimeError('CONTINUATION_BUDGET_EXHAUSTED: ' + json.dumps(result))
    return result


def continuation_clock():
    if BUDGET_CLOCK.exists():
        return json.loads(BUDGET_CLOCK.read_text())
    metadata = CONT / 'PROTOCOL.json'
    if not metadata.is_file():
        raise RuntimeError('Continuation protocol missing; refuse to start budget clock')
    value = json.loads(metadata.read_text())
    started = value['created_utc']
    limits = value['budgets']
    epoch = datetime.datetime.fromisoformat(started.replace('Z', '+00:00')).timestamp()
    clock = {'started_utc': started, 'started_epoch': epoch,
             'wall_limit_seconds': min(float(limits['wall_seconds']), 8 * 3600),
             'gpu_limit_seconds': min(float(limits['gpu_phase_seconds']), 4 * 3600),
             'source': str(metadata), 'source_sha256': hash_file(metadata),
             'historical_runtime_excluded': True}
    write_once_json(BUDGET_CLOCK, clock)
    return clock


def trace_finished(text, exit_code):
    if exit_code != 0 or not text.strip():
        return False
    seen, exits, pending = set(), {}, set()
    for line in text.splitlines():
        match = re.match(r'^\s*(?:(\d+)\s+|\[pid\s+(\d+)\]\s+)?(.*)$', line)
        pid = int(match.group(1) or match.group(2) or 0)
        body = match.group(3)
        if re.match(r'(open|openat|openat2|creat)\(', body):
            seen.add(pid)
        if '<unfinished ...>' in body:
            pending.add(pid)
        if re.match(r'<\.\.\. (open|openat|openat2|creat) resumed>', body):
            pending.discard(pid)
        exited = re.match(r'\+\+\+ exited with (\d+) \+\+\+', body)
        if exited:
            exits[pid] = int(exited.group(1))
        if body.startswith('+++ killed by'):
            return False
    return bool(seen) and not pending and seen.issubset(exits) and all(exits[pid] == 0 for pid in seen) and bool(re.search(r'\+\+\+ exited with 0 \+\+\+\s*$', text))


def run_traced(command, attempt, *, scene, phase, remaining_seconds, guard=storage_guard):
    """Run one already-authorized command; all file handles survive client exit.

    The generic command/guard arguments support the synthetic CPU integration
    tests. The production CLI constructs only producer_command(scene, phase).
    """
    attempt = require_safe_output(attempt)
    trace = attempt / 'production.strace'
    log = attempt / 'stdout.log'
    resources = attempt / 'resources.jsonl'
    started = time.monotonic()
    binding_dir = OUT / 'bindings'
    pattern = scene + '_' + phase + '_*.json'
    prior_bindings = set(binding_dir.glob(pattern)) if binding_dir.exists() else set()
    command = trace_command(command, trace)
    proc = None
    identity = None
    aborted = None
    error = None
    caught_signal = []
    previous = {}
    if __name__ == '__main__':
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.signal(sig, lambda number, frame: caught_signal.append(number))
    try:
        with log.open('xb') as stream, resources.open('x') as monitor:
            initial = guard()
            monitor.write(json.dumps({'utc': utc(), 'elapsed_seconds': 0, 'storage': initial}) + '\n')
            monitor.flush()
            proc = subprocess.Popen(command, cwd=ROOT, env=child_environment(), stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            identity = process_identity(proc.pid)
            if identity is None:
                # A successful strace cannot normally finish before /proc lookup;
                # preserve a failed receipt if this exceptional race occurs.
                raise RuntimeError('Cannot establish traced process ownership')
            write_once_json(attempt / 'LAUNCH.json', {'utc': utc(), 'scene': scene, 'phase': phase,
                            'supervisor_pid': os.getpid(), 'child': identity, 'command': command,
                            'cwd': str(ROOT), 'trace': str(trace), 'stdout': str(log),
                            'remaining_seconds': remaining_seconds})
            while proc.poll() is None:
                elapsed = time.monotonic() - started
                try:
                    current = guard()
                    if elapsed >= remaining_seconds:
                        raise RuntimeError('CONTINUATION_BUDGET_EXHAUSTED')
                    if caught_signal:
                        raise RuntimeError('SUPERVISOR_SIGNAL_' + str(caught_signal[0]))
                    monitor.write(json.dumps({'utc': utc(), 'elapsed_seconds': elapsed, 'storage': current}) + '\n')
                    monitor.flush()
                except BaseException as exc:
                    aborted = repr(exc)
                    stop_owned(identity, signal.SIGTERM)
                    try:
                        proc.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        stop_owned(identity, signal.SIGKILL)
                    break
                try:
                    proc.wait(timeout=min(POLL_SECONDS, max(0.1, remaining_seconds - elapsed)))
                except subprocess.TimeoutExpired:
                    pass
            exit_code = proc.wait()
            stream.flush()
            os.fsync(stream.fileno())
            monitor.flush()
            os.fsync(monitor.fileno())
    except BaseException as exc:
        error = repr(exc)
        if proc is not None and proc.poll() is None:
            if identity is not None:
                stop_owned(identity, signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                if identity is not None:
                    stop_owned(identity, signal.SIGKILL)
                proc.wait()
        exit_code = proc.returncode if proc is not None else None
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    trace_text = trace.read_text(errors='replace') if trace.exists() else ''
    normal = trace_finished(trace_text, exit_code)
    completed = normal and not error and not aborted
    bindings = sorted(set(binding_dir.glob(pattern)) - prior_bindings) if binding_dir.exists() else []
    if scene in ('materials', 'mic', 'ship') and len(bindings) != 1:
        completed = False
        error = (error or '') + 'Expected exactly one new binding receipt; found ' + str(len(bindings))
    receipt = {'utc': utc(), 'scene': scene, 'phase': phase,
               'state': 'COMPLETE' if completed else 'FAILED', 'completed': completed,
               'exit_code': exit_code, 'normal_exit': normal, 'elapsed_seconds': time.monotonic() - started,
               'reserve_or_budget_abort': aborted, 'error': error, 'attempt': str(attempt),
               'trace_sha256': hash_file(trace) if trace.exists() else None,
               'trace_tail': '\n'.join(trace_text.splitlines()[-8:]),
               'binding_receipt': {'path': str(bindings[0]), 'sha256': hash_file(bindings[0])} if len(bindings) == 1 else None,
               'files': {p.name: {'path': str(p), 'sha256': hash_file(p), 'bytes': p.stat().st_size}
                         for p in sorted(attempt.iterdir()) if p.is_file() and p.name not in ('supervisor.log', 'EXIT.json')}}
    write_once_json(attempt / 'EXIT.json', receipt)
    return receipt


def supervise(attempt):
    attempt = require_safe_output(attempt)
    start = json.loads((attempt / 'START.json').read_text())
    scene, phase = start['scene'], start['phase']
    command = producer_command(scene, phase)
    LAUNCH_ROOT.mkdir(parents=True, exist_ok=True)
    with (LAUNCH_ROOT / 'SUPERVISOR.lock').open('a+') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            from run_storage_transport import require_storage_release
            release = require_storage_release()
            write_once_json(attempt / 'STORAGE_RELEASE_GUARD.json', release)
            ledger = json.loads(RUNTIME.read_text()) if RUNTIME.exists() else []
            if any(row.get('state') == 'RUNNING' for row in ledger):
                raise RuntimeError('UNRESOLVED_OWNED_LAUNCH: retain evidence and reconcile before resuming')
            remaining = budget_remaining(continuation_clock(), ledger)
            storage = storage_guard()
            write_once_json(attempt / 'STORAGE_GUARD.json', storage)
            gpu = gpu_guard()
            write_once_json(attempt / 'GPU_GUARD.json', gpu)
            require_idle_gpu(gpu['processes'])
            seconds = remaining['wall_remaining_seconds']
            if phase == 'render':
                if remaining['gpu_remaining_seconds'] <= 0:
                    raise RuntimeError('CONTINUATION_GPU_BUDGET_EXHAUSTED')
                seconds = min(seconds, remaining['gpu_remaining_seconds'])
            entry = {'scene': scene, 'phase': phase, 'attempt': str(attempt),
                     'state': 'RUNNING', 'started_utc': utc(), 'started_epoch': time.time()}
            ledger.append(entry)
            atomic_json(RUNTIME, ledger)
            receipt = run_traced(command, attempt, scene=scene, phase=phase, remaining_seconds=seconds)
            entry.update({'state': receipt['state'], 'elapsed_seconds': receipt['elapsed_seconds'],
                          'exit_path': str(attempt / 'EXIT.json'), 'exit_sha256': hash_file(attempt / 'EXIT.json')})
            atomic_json(RUNTIME, ledger)
            return 0 if receipt['completed'] else 1
        except BaseException as exc:
            if not (attempt / 'EXIT.json').exists():
                write_once_json(attempt / 'EXIT.json', {'utc': utc(), 'scene': scene, 'phase': phase,
                                'state': 'BLOCKED_BEFORE_LAUNCH', 'completed': False, 'normal_exit': False,
                                'exit_code': None, 'attempt': str(attempt), 'error': repr(exc),
                                'traceback': traceback.format_exc()})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', choices=('materials', 'mic', 'ship'))
    parser.add_argument('--phase', choices=('render', 'media'))
    parser.add_argument('--supervise', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.supervise:
        return supervise(args.supervise)
    if not args.scene or not args.phase:
        parser.error('--scene and --phase are required')
    command = producer_command(args.scene, args.phase)
    storage = storage_guard()
    LAUNCH_ROOT.mkdir(parents=True, exist_ok=True)
    name = args.scene + '_' + args.phase + '_' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
    attempt = require_safe_output(LAUNCH_ROOT / name)
    attempt.mkdir()
    write_once_json(attempt / 'START.json', {'utc': utc(), 'scene': args.scene, 'phase': args.phase,
                    'repo_root': str(ROOT), 'external_root': str(EXTERNAL_ROOT), 'output_root': str(OUT),
                    'command': command, 'cwd': str(ROOT), 'storage': storage,
                    'historical_hotdog_audit': 'Original incomplete exit143 trace remains INVALID; unchanged'})
    supervisor_command = [PYTHON, str(Path(__file__).resolve()), '--supervise', str(attempt)]
    with (attempt / 'supervisor.log').open('xb') as log:
        proc = subprocess.Popen(supervisor_command, cwd=ROOT, env=child_environment(), stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    receipt = {'utc': utc(), 'attempt': str(attempt), 'supervisor_pid': proc.pid,
               'supervisor_identity': process_identity(proc.pid), 'command': supervisor_command,
               'detached_session': True, 'exit_receipt': str(attempt / 'EXIT.json')}
    write_once_json(attempt / 'OUTER_LAUNCH.json', receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
