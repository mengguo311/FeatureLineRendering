"""Serial bounded real Lego demo execution, every child has a durable receipt."""
import runtime
from runtime import OUTPUT_ROOT
from pathlib import Path
import subprocess,sys,json
U=OUTPUT_ROOT/'units/unit_008';HERE=Path(__file__).parent.resolve();PY=sys.executable
p=json.loads((U/'PROTOCOL.json').read_text())
def run(name,command):
 r=subprocess.run([PY,str(HERE/'run_logged.py'),'--unit',str(U),'--name',name,'--',*map(str,command)],timeout=590)
 r.check_returncode()
def demo(name,args):run(name,[PY,HERE/'demo.py',*args])
demo('author_region',['author','--scene','lego','--asset',U/'assets/original','--region','3','--selection-recipe',U/'SELECTION_RECIPE.json','--name',p['selection']['name'],'--output',U/'assets/baseline'])
demo('local_edit',['edit','--scene','lego','--asset',U/'assets/baseline','--region','4','--angle','35','--output',U/'assets/edited'])
run('source_model',[PY,HERE/'catalog_run.py','source'])
for arm in ('original','baseline','edited'):
 demo('static_'+arm,['render','--scene','lego','--asset',U/f'assets/{arm}','--trajectory','static','--output',U/f'renders/static_{arm}'])
for kind in ('orbit','zoom'):
 demo(kind,['render','--scene','lego','--asset',U/'assets/edited','--trajectory',kind,'--output',U/f'renders/{kind}'])
demo('cold_reload',['render','--scene','lego','--asset',U/'assets/edited','--view',p['static_cameras'][0]['view'],'--output',U/'renders/cold_reload'])
for phase in ('validate','media'):run(phase,[PY,HERE/'run_multiview.py','--unit',U,phase])
run('selection_evidence',[PY,HERE/'selection_evidence.py','--unit',U])
