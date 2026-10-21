"""Cold saved-asset previews of the existing Chair and Drums, serially."""
import runtime
from runtime import OUTPUT_ROOT,js,sha
import json,subprocess,sys
from pathlib import Path
from PIL import Image
from media import contact
U=OUTPUT_ROOT/'units/unit_008';HERE=Path(__file__).parent.resolve();rows=[]
for scene in ('chair','drums'):
 a=U/'catalog_assets'/scene;m=json.loads((a/'asset.json').read_text())
 cmd=[sys.executable,str(HERE/'catalog_demo.py'),'preview','--catalog',str(U/'CATALOG.json'),'--scene',scene,'--output',str(U/'catalog_reference'/scene)]
 r=subprocess.run(cmd,timeout=120);r.check_returncode()
 rows.append(dict(scene=scene,command=cmd,returncode=r.returncode,original=m['original'],asset_sha256=sha(a/'asset.json'),frame=json.loads((U/f'catalog_reference/{scene}/frame_000.json').read_text())))
js(U/'metrics/CATALOG_PREVIEWS.json',dict(scenes=rows,scope='cold replay of genuine saved proxy/3D paths, no new Chair/Drums original PLY rendering or geometry reconstruction'))
contact(U/'media/three_models.png',[(s.capitalize()+' | actual saved model',Image.open(U/f'catalog_reference/{s}/frame_000_image.png' if s!='lego' else U/'renders/static_edited/frame_000_image.png')) for s in ('chair','lego','drums')],cols=3,size=512,title='One portable editor | same 3D assets across cameras and local edits')
