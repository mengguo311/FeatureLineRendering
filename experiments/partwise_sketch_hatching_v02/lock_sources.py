from common import *
import subprocess
assert not (OUT/'SOURCE_LOCK.json').exists()
files=list((WORK/'experiments/partwise_sketch_hatching_v02').glob('*.py'))
files += [LEGACY/'core.py',LEGACY/'core_walk_v2.py',OUT/'PROTOCOL.json']
files += list((OUT/'inputs').glob('*.npz'))
files += list((WORK/'docs/partwise_sketch_hatching_v02').glob('*.md'))
files += [WORK/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json',Path(FFMPEG)]
lock=dict(code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
          protocol_commit='7dff4ce4',files={str(p):sha(p) for p in files})
write_json(OUT/'SOURCE_LOCK.json',lock)
write_json(WORK/'docs/partwise_sketch_hatching_v02/SOURCE_LOCK_unit001.json',lock)
snapshot=OUT/'source_snapshot';snapshot.mkdir()
for p in files:
    if p.suffix in ('.py','.md') and WORK in p.parents:
        dest=snapshot/p.relative_to(WORK);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
print(json.dumps(dict(files=len(files),sha256=sha(OUT/'SOURCE_LOCK.json'))))
