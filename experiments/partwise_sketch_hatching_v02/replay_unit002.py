"""Cold process replay from the frozen source snapshot; explicit fresh output."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/orchestration/scratch'
os.sched_setaffinity(0,[0,1])
import sys
import time
import json
import hashlib
from pathlib import Path
OUT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_002')
SNAPSHOT=OUT/'source_snapshot'
sys.path.insert(0,str(SNAPSHOT))
sys.path.insert(0,str(SNAPSHOT/'experiments/partwise_sketch_hatching_v02'))
import common
import renderer
from PIL import Image
import numpy as np

assert Path(common.__file__).is_relative_to(SNAPSHOT)
assert Path(renderer.__file__).is_relative_to(SNAPSHOT)
assert Path(common.core.__file__).is_relative_to(SNAPSHOT)
start=time.perf_counter()
mesh,strokes,cfg=common.load_inputs()
cfg['renderer']['contour_visibility']='visible_centerline'
result=renderer.render(mesh,strokes,cfg,azimuth=30,elevation=20,distance=4.5)
seconds=time.perf_counter()-start
folder=OUT/'replay';folder.mkdir(exist_ok=False)
pixels=np.uint8(np.rint(np.clip(result['image'],0,1)*255))
Image.fromarray(pixels).save(folder/'base_030.png')
with Image.open(OUT/'stills/base_030.png') as im:original=np.asarray(im)
with np.load(OUT/'stills/base_030.npz',allow_pickle=False) as saved:
    comparisons={k:bool(np.array_equal(saved[k],result[k])) for k in ('image','hatch','contours','rings','parts','depth')}
comparisons['actual_png_exact']=bool(np.array_equal(original,pixels))
record={'all_exact':all(comparisons.values()),'comparisons':comparisons,'load_and_render_seconds':seconds,
        'source_files':{str(Path(m.__file__)):common.sha(m.__file__) for m in (common,renderer,common.core)},
        'source':'Frozen source_snapshot in fresh process, immutable unit001 mesh/strokes, explicit visible_centerline config.',
        'scope':'Cold rendering replay only; contour unit does not regenerate the unchanged paths.'}
common.write_json(OUT/'COLD_REPLAY.json',record)
print(json.dumps(common.native(record),allow_nan=False))
sys.exit(0 if record['all_exact'] else 1)
