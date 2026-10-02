"""Atomic local artifacts and complete media verification for raster evidence v2.

This module has no scene loader, GPU dependency, or scientific verdict logic.
Frame seals bind the caller's exact camera/config/source context to every output.
"""
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def canonical_hash(value):
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sync_directory(path):
    fd = os.open(Path(path), os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, value, *, replace=False):
    """Publish valid JSON atomically. Only mutable status should use replace=True."""
    path = Path(path)
    payload = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                         allow_nan=False).encode('utf-8') + b'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        if replace:
            os.replace(tmp, path)
        else:
            os.link(tmp, path)
        _sync_directory(path.parent)
    finally:
        if tmp.exists(): tmp.unlink()


def _inventory(root):
    root = Path(root)
    if root.is_symlink(): raise ValueError('artifact root must not be a symlink')
    files = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink(): raise ValueError('artifact symlinks are not permitted: ' + str(p))
        if p.is_file() and p.relative_to(root).as_posix() not in ('SEAL.json', 'SEAL.sha256'):
            files[p.relative_to(root).as_posix()] = hash_file(p)
    return files


def valid_seal(frame, expected_context):
    """False means absent; an existing partial, damaged, or mismatched frame raises."""
    frame = Path(frame)
    if not frame.exists():
        if frame.is_symlink(): raise ValueError('dangling frame symlink')
        return False
    try:
        if not frame.is_dir() or frame.is_symlink(): raise ValueError('frame is not a real directory')
        seal_path = frame / 'SEAL.json'
        checksum = frame / 'SEAL.sha256'
        if not seal_path.is_file() or not checksum.is_file(): raise ValueError('missing frame seal')
        if hash_file(seal_path) != checksum.read_text().strip(): raise ValueError('seal checksum mismatch')
        seal = json.loads(seal_path.read_text())
        if seal.get('schema') != 'hybrid-raster-frame-v1': raise ValueError('unknown seal schema')
        expected_hash = canonical_hash(expected_context)
        if seal.get('context_sha256') != expected_hash or canonical_hash(seal['context']) != expected_hash:
            raise ValueError('frame camera/config/source context mismatch')
        files = _inventory(frame)
        if not files or files != seal['files']: raise ValueError('frame artifact inventory/hash mismatch')
        return True
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid frame seal: ' + str(frame)) from exc


def seal_frame(staging, final, context):
    """Seal complete staging outputs, then atomically rename without replacing final."""
    staging, final = Path(staging), Path(final)
    if final.exists() or final.is_symlink(): raise FileExistsError(final)
    if not staging.is_dir() or staging.is_symlink(): raise ValueError('missing real staging directory')
    if (staging / 'SEAL.json').exists() or (staging / 'SEAL.sha256').exists():
        raise ValueError('staging already contains a seal; verify or preserve it explicitly')
    files = _inventory(staging)
    if not files: raise ValueError('cannot seal an empty frame')
    seal = dict(schema='hybrid-raster-frame-v1', context=context,
                context_sha256=canonical_hash(context), files=files)
    final.parent.mkdir(parents=True, exist_ok=True)
    # Sibling lock serializes cooperating publishers and preserves exclusive final paths.
    lock = final.parent / ('.' + final.name + '.seal.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        if final.exists() or final.is_symlink(): raise FileExistsError(final)
        atomic_json(staging / 'SEAL.json', seal)
        checksum = staging / 'SEAL.sha256'
        with checksum.open('x') as stream:
            stream.write(hash_file(staging / 'SEAL.json') + '\n')
            stream.flush(); os.fsync(stream.fileno())
        if not valid_seal(staging, context): raise ValueError('staging validation failed')
        _sync_directory(staging)
        os.rename(staging, final)
        _sync_directory(final.parent)
    finally:
        os.close(fd)
        lock.unlink()
    return seal


def _ink_array(ink):
    ink = np.asarray(ink)
    if ink.ndim != 2 or not ink.size or not np.isfinite(ink).all():
        raise ValueError('ink must be a nonempty finite H x W array')
    if np.any(ink < 0) or np.any(ink > 1): raise ValueError('ink concentration must be in [0,1]')
    return ink.astype(np.float32, copy=False)


def _rgb8(rgb):
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[-1] != 3 or not rgb.size or not np.isfinite(rgb).all():
        raise ValueError('RGB must be a nonempty finite H x W x 3 array')
    if rgb.dtype == np.uint8: return rgb
    if not np.issubdtype(rgb.dtype, np.floating) or np.any(rgb < 0) or np.any(rgb > 1):
        raise ValueError('RGB must be uint8 or floating [0,1]')
    return np.rint(rgb * 255).astype(np.uint8)


def white_ink(ink):
    ink = _ink_array(ink)
    gray = np.rint(255 * (1 - ink)).astype(np.uint8)
    return np.repeat(gray[..., None], 3, axis=2)


def overlay_ink(rgb, ink):
    rgb, ink = _rgb8(rgb), _ink_array(ink)
    if rgb.shape[:2] != ink.shape: raise ValueError('RGB and ink dimensions differ')
    return np.rint(rgb.astype(np.float32) * (1 - ink[..., None])).astype(np.uint8)


def panel(images, labels, columns=None, header=32):
    """Return a full-resolution PIL sheet; original pixels are never resized/cropped."""
    images, labels = list(images), list(labels)
    if not images or len(images) != len(labels): raise ValueError('one label per nonempty image list required')
    arrays = [_rgb8(np.asarray(im)) for im in images]
    h, w = arrays[0].shape[:2]
    if any(im.shape != arrays[0].shape for im in arrays): raise ValueError('panel tile dimensions differ')
    columns = len(images) if columns is None else columns
    if not isinstance(columns, int) or columns < 1 or not isinstance(header, int) or header < 0:
        raise ValueError('invalid panel layout')
    sheet = Image.new('RGB', (columns * w, math.ceil(len(images) / columns) * (h + header)), 'white')
    draw = ImageDraw.Draw(sheet)
    for i, (im, label) in enumerate(zip(arrays, labels)):
        x, y = (i % columns) * w, (i // columns) * (h + header)
        sheet.paste(Image.fromarray(im), (x, y + header))
        if header: draw.text((x + 8, y + max(0, (header - 12) // 2)), str(label), fill='black')
    return sheet


def save_contact_sheet(paths, output, labels=None, columns=3, header=32):
    paths, output = [Path(p) for p in paths], Path(output)
    if output.exists(): raise FileExistsError(output)
    images = []
    for p in paths:
        with Image.open(p) as im: images.append(np.asarray(im.convert('RGB')).copy())
    labels = [p.stem for p in paths] if labels is None else labels
    sheet = panel(images, labels, columns=columns, header=header)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + output.stem + '.', suffix='.png', dir=output.parent)
    os.close(fd); tmp = Path(name)
    try:
        sheet.save(tmp, format='PNG')
        with Image.open(tmp) as check:
            check.load()
            if check.size != sheet.size: raise ValueError('contact sheet decode dimensions differ')
        os.link(tmp, output); _sync_directory(output.parent)
    finally:
        if tmp.exists(): tmp.unlink()
    return dict(path=str(output), frames=len(paths), size=list(sheet.size), sha256=hash_file(output))


def validate_video(path, *, expected_frames, expected_size, require_distinct=True):
    """Decode every frame and check count, dimensions, and distinct decoded content."""
    path = Path(path)
    if expected_frames < 1 or len(expected_size) != 2: raise ValueError('invalid video expectations')
    cap = cv2.VideoCapture(str(path))
    hashes = []
    try:
        if not cap.isOpened(): raise ValueError('video could not be opened: ' + str(path))
        while True:
            ok, frame = cap.read()
            if not ok: break
            if (frame.shape[1], frame.shape[0]) != tuple(expected_size):
                raise ValueError('decoded video dimension mismatch: ' + str(path))
            hashes.append(hashlib.sha256(frame.tobytes()).hexdigest())
    finally:
        cap.release()
    if len(hashes) != expected_frames:
        raise ValueError(f'incomplete video decode {path}: {len(hashes)}/{expected_frames}')
    if require_distinct and len(set(hashes)) != expected_frames:
        raise ValueError(f'repeated video frames {path}: {len(set(hashes))}/{expected_frames} distinct')
    return dict(path=str(path), frames=len(hashes), distinct_frames=len(set(hashes)),
                size=list(expected_size), frame_sha256=hashes, sha256=hash_file(path), passed=True)


def encode_video(frames, output, *, fps=12, expected_frames=None):
    """Encode RGB frames, fully validate temporary MP4, then publish exclusively.

    Failed temporary clips remain beside output for inspection and are never promoted.
    Input is an iterable to avoid materializing an entire full-resolution comparison.
    """
    output = Path(output)
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    if not np.isfinite(fps) or fps <= 0: raise ValueError('fps must be positive')
    iterator = iter(frames)
    try: first = _rgb8(next(iterator))
    except StopIteration as exc: raise ValueError('cannot encode an empty video') from exc
    h, w = first.shape[:2]
    if h % 2 or w % 2: raise ValueError('MP4 dimensions must be even to avoid implicit cropping')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + output.stem + '.partial.', suffix='.mp4', dir=output.parent)
    os.close(fd); tmp = Path(name)
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*'mp4v'), float(fps), (w, h))
    if not writer.isOpened():
        writer.release()
        raise RuntimeError('MP4 encoder unavailable; temporary path: ' + str(tmp))
    count = 0
    try:
        writer.write(cv2.cvtColor(first, cv2.COLOR_RGB2BGR)); count += 1
        for item in iterator:
            frame = _rgb8(item)
            if frame.shape != first.shape: raise ValueError('video input dimensions changed: ' + str(tmp))
            writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)); count += 1
    finally:
        writer.release()
    expected = count if expected_frames is None else expected_frames
    if count != expected: raise ValueError(f'video input frame count {count}/{expected}; temporary path: {tmp}')
    result = validate_video(tmp, expected_frames=expected, expected_size=(w, h))
    os.link(tmp, output); tmp.unlink(); _sync_directory(output.parent)
    result.update(path=str(output), fps=float(fps), input_frames=count)
    return result
