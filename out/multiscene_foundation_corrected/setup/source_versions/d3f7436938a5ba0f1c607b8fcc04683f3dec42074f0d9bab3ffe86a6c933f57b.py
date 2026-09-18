"""Auditable vanilla training setup and durable resource-gated execution."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from .foundation import freeze_json


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()


def seed_sources(original):
    """Return the sole allowed semantic upstream patch; reject unexpected input."""
    result = dict(original)
    replacements = {
        'train.py': [('    args = parser.parse_args(sys.argv[1:])',
                      '    parser.add_argument("--seed", type=int, default=0)\n    args = parser.parse_args(sys.argv[1:])'),
                     ('safe_state(args.quiet)', 'safe_state(args.quiet, args.seed)')],
        'utils/general_utils.py': [('def safe_state(silent):', 'def safe_state(silent, seed=0):'),
                                  ('    random.seed(0)', '    random.seed(seed)'),
                                  ('    np.random.seed(0)', '    np.random.seed(seed)'),
                                  ('    torch.manual_seed(0)', '    torch.manual_seed(seed)')]}
    for path, edits in replacements.items():
        for old, new in edits:
            if result[path].count(old) != 1:
                raise ValueError('unexpected upstream seed source: ' + path)
            result[path] = result[path].replace(old, new)
    return result


def stage_training_data(source, destination, cfg):
    """Copy only approved photographs; never reuse an initialization PLY."""
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    for source_split, target_split, indices in [
            ('train', 'train', cfg['training']['optimization_indices']),
            ('val', 'test', cfg['training']['validation_indices'])]:
        metadata = json.loads((source / f'transforms_{source_split}.json').read_text())
        frames = []
        (destination / source_split).mkdir()
        for i in indices:
            frame = metadata['frames'][i]
            relative = Path(frame['file_path']).with_suffix('.png')
            original, target = source / relative, destination / relative
            digest = sha256(original)
            if 'scenes' in cfg:
                frozen = cfg['scenes'][source.name]['cameras'][f'{source_split}_{i:03d}']['sha256']
                if digest != frozen:
                    raise ValueError('image hash mismatch: ' + str(original))
            shutil.copyfile(original, target)
            target.chmod(0o444)
            records.append(dict(path=relative.as_posix(), source=str(original), sha256=digest,
                                bytes=target.stat().st_size))
            frames.append(frame)
        metadata['frames'] = frames
        target = destination / f'transforms_{target_split}.json'
        target.write_text(json.dumps(metadata, sort_keys=True) + '\n')
        target.chmod(0o444)
        records.append(dict(path=target.name, sha256=sha256(target), bytes=target.stat().st_size))
    digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
    return dict(data_digest=digest, files=records, initialization='official per-seed random; no input PLY')


def training_command(python, source, data, output, seed, port, cfg):
    if seed not in cfg['training']['seeds']:
        raise ValueError('unregistered training seed')
    return [str(python), str(Path(source) / 'train.py'), '-s', str(data), '-m', str(output),
            '--eval', '--white_background', '--iterations', str(cfg['training']['iterations']),
            '--seed', str(seed), '--ip', '127.0.0.1', '--port', str(port),
            '--test_iterations', *map(str, cfg['training']['test_iterations']),
            '--save_iterations', *map(str, cfg['training']['save_iterations'])]


def free_memory(gpu):
    output = subprocess.check_output(['nvidia-smi', f'--id={gpu}',
        '--query-gpu=memory.free', '--format=csv,noheader,nounits'], text=True)
    return int(output.strip())


def job_manifests(cfg, root, python):
    root = Path(root).resolve()
    jobs = []
    for scene in cfg['scene_order']:
        for seed in cfg['training']['seeds']:
            gpu = cfg['training']['gpu_for_seed'][str(seed)]
            data = root / 'inputs' / scene / f'seed_{seed}'
            directory = root / 'training' / scene / f'seed_{seed}'
            source = root / 'vendor/gaussian-splatting'
            output = directory / 'checkpoints'
            command = training_command(python, source, data, output, seed, 26009 + gpu, cfg)
            jobs.append(dict(scene=scene, seed=seed, gpu=gpu, data=str(data),
                directory=str(directory), output=str(output), source=str(source), command=command,
                expected_iteration=cfg['training']['iterations'], source_commit=cfg['training']['source_commit']))
    return jobs


def run_job(command, directory, env, gpu, limits, memory_query=free_memory, sleep=time.sleep):
    """One durable launch; waiting and failures never become successful posteriors."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also prevents concurrent workers from running the same job.
    with (directory / 'launch_claim.json').open('x') as f:
        json.dump(dict(claimed_utc=utc(), pid=os.getpid(), command=command), f)
    elapsed_wait = 0
    while True:
        memory = memory_query(gpu)
        disk = shutil.disk_usage(directory).free / 2**30
        row = dict(utc=utc(), gpu=gpu, free_mib=memory, free_disk_gib=disk)
        with (directory / 'resources.jsonl').open('a') as f:
            f.write(json.dumps(row) + '\n')
        if memory >= limits['min_free_mib'] and disk >= limits['min_disk_gib']:
            break
        if elapsed_wait >= limits['resource_wait_seconds']:
            freeze_json(directory / 'exit_status.json', dict(exit_code=124,
                state='ENGINEERING_NOT_READY', reason='resource wait exhausted', utc=utc()))
            return 124
        sleep(limits['resource_poll_seconds'])
        elapsed_wait += limits['resource_poll_seconds']
    start = utc()
    with (directory / 'train.log').open('x') as log:
        try:
            process = subprocess.run(command, env=dict(os.environ, **env),
                stdout=log, stderr=subprocess.STDOUT, timeout=limits['timeout_seconds'])
            code, reason = process.returncode, 'completed' if process.returncode == 0 else 'process failure'
        except subprocess.TimeoutExpired:
            code, reason = 124, 'training timeout'
        except OSError as error:
            code, reason = 127, repr(error)
            log.write(reason + '\n')
    freeze_json(directory / 'exit_status.json', dict(exit_code=code, reason=reason,
        state='COMPLETE' if code == 0 else 'ENGINEERING_NOT_READY',
        started_utc=start, finished_utc=utc(), resource_wait_seconds=elapsed_wait))
    return code
