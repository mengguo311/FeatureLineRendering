#!/usr/bin/env python3
"""Install filesystem restrictions, then execute unchanged upstream training args."""
import argparse
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.foundation import restrict_filesystem


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    source = Path(spec['source']).resolve()
    # The driver initializes OS resources before confinement; no scene input has
    # been read. Upstream safe_state subsequently resets all RNG streams.
    import torch
    torch.cuda.init()
    runtime = [sys.prefix, '/usr', '/lib', '/lib64', '/etc', '/proc', '/sys']
    readonly = [str(source), str(Path(__file__).resolve()), *spec['site'], *runtime]
    writable = [spec['data'], spec['output'], '/dev']
    readonly = [p for p in readonly if Path(p).exists()]
    restrict_filesystem(readonly, writable)
    # Prefer verified packages over any incompatible globally installed rasterizer.
    sys.path = [str(source), *spec['site']] + [p for p in sys.path if p != str(ROOT)]
    sys.argv = [str(source / 'train.py'), *spec['arguments']]
    runpy.run_path(str(source / 'train.py'), run_name='__main__')


if __name__ == '__main__':
    main()
