"""Apply one saved recipe to RGB only, writing task-owned evidence; no 3D call."""
import argparse,json
import numpy as np
from pathlib import Path
from common import *
from detector import *
from render_boards import save_png
ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--preset',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
output=Path(args.output).resolve()
if not output.is_relative_to(T.resolve()):raise ValueError('Output must be within this task root')
if output.exists():raise FileExistsError(output)
p=next(x for x in json.loads((T/'PRESETS.json').read_text())['presets'] if x['id']==args.preset)
with np.load(args.input) as z:rgb=rgb_from_npz(z)
f=analyze_rgb(rgb,p['analysis']);r=candidate(mix_fields(f,p['detail_lambda']),p['threshold'])
output.mkdir(parents=True);np.savez_compressed(output/'maps.npz',**r)
write(output/'recipe.json',p);save_png(output/'candidate.png',1-r['candidate_darkness']);save_png(output/'marked.png',1-r['marked'].astype(np.float32))
print(str(output))
