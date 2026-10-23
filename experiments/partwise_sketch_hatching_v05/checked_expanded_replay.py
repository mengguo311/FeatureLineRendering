"""Hash-checked replay/query entrypoint; outputs must be a new directory."""
import runtime
from runtime import sha
from pathlib import Path
import argparse,json
from run_expanded_unit import load
from membership import load_binding
from inspect_footprint_link import run


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True)
    ap.add_argument('--scene',choices=['chair','lego'],required=True);ap.add_argument('--index',type=int,default=0)
    ap.add_argument('--operation',choices=['tint','opacity'],default='tint')
    ap.add_argument('--arm',choices=['specific','previous_path','nearest_path','shuffled'],default='specific')
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--query',action='store_true')
    a=ap.parse_args();p=load(a.unit);s=p['scenes'][a.scene];root=a.unit/'results'/a.scene
    for name,h in json.loads((root/'BINDING_LOCK.json').read_text())['files'].items():
        if sha(root/name)!=h:raise ValueError('saved binding identity changed: '+name)
    load_binding(root/'SOURCE_BINDING.npz',s['source']['sha256'],s['source_count'])
    run(a.unit,a.scene,a.index,a.operation,a.arm,a.output,a.query)


if __name__=='__main__':main()
