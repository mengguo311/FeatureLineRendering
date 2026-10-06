import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP,OUT,resource_guard,sha
from targets import generate
if __name__=='__main__':
    resource_guard(gpu=False)
    frozen=EXP/'data/manifests/data_freeze.json'
    if frozen.exists():
        for scene,groups in json.loads(frozen.read_text())['records'].items():
            for group,rows in groups.items():
                for row in rows:
                    for task in ('A','B'):
                        path=OUT/'data'/scene/group/row['id']/(task+'_target.npz')
                        if sha(path)!=row[task+'_sha256']:raise RuntimeError('frozen data changed: '+str(path))
        print('Existing data freeze verified; generation remains closed.')
    else:
        generate(json.loads((EXP/'configs/pilot.json').read_text()))
