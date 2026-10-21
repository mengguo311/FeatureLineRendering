"""Pre-evaluation camera interface correction; original frozen draft retained."""
from common import *
import shutil
from datetime import datetime,timezone
U=OUT.parent/'unit_006'
assert not (U/'dataset').exists() and not (U/'SOURCE_LOCK.json').exists()
old=U/'PROTOCOL_INITIAL.json';assert not old.exists();shutil.copy2(U/'PROTOCOL.json',old)
p=json.loads(old.read_text());p['revision']=2;p['camera']['principal_point']=[255.5,255.5]
p['renderer']['name']='CPU triangle z-buffer, perspective-correct optical-depth interpolation, 2x2 box AA'
p['camera']['export']+='; principal point (size-1)/2 agrees with official ndc2Pix; no subpixel export offset'
p['created_utc']=datetime.now(timezone.utc).isoformat()
write_json(U/'PROTOCOL.json',p);write_json(WORK/'docs/partwise_sketch_hatching_v02/PROTOCOL_unit006.json',p)
files=[Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/RaDe-GS')/s for s in ['utils/graphics_utils.py','submodules/diff-gaussian-rasterization/cuda_rasterizer/auxiliary.h']]
write_json(U/'PRE_EVALUATION_REFINEMENT.json',dict(phase='BEFORE_ANY_RGB_GENERATION_OR_EVALUATION',old_protocol_sha256=sha(old),new_protocol_sha256=sha(U/'PROTOCOL.json'),reason='Read-only official source review found half-pixel principal-point mismatch; match official 512 ndc2Pix center255.5 before data production. Also clarify depth-only perspective interpolation wording.',changed=['principal point256->255.5','renderer description depth interpolation'],unchanged=['all split angles/counts','geometry/material/light','resolution/focal/distance/elevations','all gates'],evidence=[dict(path=str(x),sha256=sha(x)) for x in files]))
print('pre-evaluation refinement recorded; no images yet')
