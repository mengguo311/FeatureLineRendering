"""Bounded serial real-model run. Every child keeps its own command receipt."""
import runtime
from pathlib import Path
import argparse,json,subprocess,sys,signal

def execute(unit):
    code=Path(__file__).parent;p=json.loads((unit/'PROTOCOL.json').read_text());py=sys.executable
    demo=[py,str(code/'demo.py')];asset=unit/'assets'
    tasks=[('prepare',[py,str(code/'run_multiview.py'),'--unit',str(unit),'prepare']),
        ('author_region',demo+['author','--scene','drums','--asset',str(asset/'original'),'--region','3','--selection-recipe',str(unit/'SELECTION_RECIPE.json'),'--name',p['selection']['name'],'--output',str(asset/'baseline')]),
        ('local_edit',demo+['edit','--scene','drums','--asset',str(asset/'baseline'),'--region','4','--angle','35','--output',str(asset/'edited')]),
        ('source_model',[py,str(code/'run_scene.py'),'--unit',str(unit),'source'])]
    for arm in ('original','baseline','edited'):
        tasks.append(('static_'+arm,demo+['render','--scene','drums','--asset',str(asset/arm),'--trajectory','static','--output',str(unit/f'renders/static_{arm}')]))
    for kind in ('orbit','zoom'):
        tasks.append((kind,demo+['render','--scene','drums','--asset',str(asset/'edited'),'--trajectory',kind,'--output',str(unit/f'renders/{kind}')]))
    tasks.append(('cold_reload',demo+['render','--scene','drums','--asset',str(asset/'edited'),'--view','train_r_7','--output',str(unit/'renders/cold_reload')]))
    for phase in ('validate','media'):
        tasks.append((phase,[py,str(code/'run_multiview.py'),'--unit',str(unit),phase]))
    active=None;stopped=[]
    def stop(signum,frame):
        stopped.append(signum)
        if active is not None and active.poll() is None:active.send_signal(signal.SIGTERM)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    for name,command in tasks:
        if stopped:raise SystemExit(128+stopped[0])
        active=subprocess.Popen([py,str(code/'run_logged.py'),'--unit',str(unit),'--name',name,'--']+command)
        code_=active.wait(timeout=595)
        if code_:raise SystemExit(code_)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unit',type=Path,required=True);execute(parser.parse_args().unit)
