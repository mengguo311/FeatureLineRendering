"""Byte-level inventory and actual PNG decoding for retained experiment artifacts."""
from pathlib import Path
from PIL import Image
from .multiscene_training import sha256


def _paths(root,exclude):
    root=Path(root).resolve();excluded=set(exclude)
    return sorted(p for p in root.rglob('*') if p.is_file()
        and not {'.git','__pycache__'}.intersection(p.relative_to(root).parts)
        and p.relative_to(root).as_posix() not in excluded)


def inventory(root,exclude=()):
    root=Path(root).resolve()
    return [dict(path=str(p),relative_path=p.relative_to(root).as_posix(),
        bytes=p.stat().st_size,sha256=sha256(p)) for p in _paths(root,exclude)]


def verify_inventory(root,records,exclude=()):
    actual=_paths(root,exclude)
    if len(records)!=len({r['path'] for r in records}) or {str(p) for p in actual}!={r['path'] for r in records}:
        raise ValueError('inventory file set differs')
    for row in records:
        path=Path(row['path'])
        if path.stat().st_size!=row['bytes']:raise ValueError('inventory size differs: '+str(path))
        if sha256(path)!=row['sha256']:raise ValueError('inventory hash differs: '+str(path))
    return True


def verify_png(path):
    path=Path(path)
    with Image.open(path) as image:
        if image.format!='PNG':raise ValueError('not PNG: '+str(path))
        image.verify()
    with Image.open(path) as image:
        image.load()
        return dict(path=str(path.resolve()),size=list(image.size),mode=image.mode,decoded=True)
