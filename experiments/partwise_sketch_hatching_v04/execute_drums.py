"""Bounded serial phases for the frozen Drums engineering transfer."""
import runtime
from runtime import output_guard
from pathlib import Path
import argparse,subprocess,sys


def run(unit,phase):
    unit=output_guard(unit);code=Path(__file__).resolve().parent
    py=sys.executable
    def logged(name,args):
        command=[py,str(code/'run_logged.py'),'--unit',str(unit),'--name',name,'--',*map(str,args)]
        subprocess.run(command,timeout=590,check=True)
    def script(name,file,*args):logged(name,[py,code/file,*args])
    def scene(name,action):script(name,'run_scene.py','--unit',unit,action)
    def render(name,asset,*args):
        script(name,'demo.py','render','--scene','drums','--asset',unit/f'assets/{asset}',
               '--output',unit/f'renders/{name}',*args)
    if phase=='prepare':scene('prepare','prepare')
    elif phase=='stills':
        scene('source_model','source')
        render('static_baseline','baseline','--trajectory','static')
        render('static_edited','edited','--trajectory','static')
        render('cold_reload','edited','--view','train_r_7')
    elif phase=='motion':
        render('orbit','edited','--trajectory','orbit')
        render('zoom','edited','--trajectory','zoom')
    elif phase=='checks':
        script('validate','validate_unit.py','--unit',unit)
        scene('source_diagnostics','diagnostics')
        script('media','media.py','--unit',unit)
    elif phase=='interactive':
        script('browser','browser_demo_test.py','--unit',unit,'--name','browser_complete')
        script('viewer_smoke','smoke_viewer.py','--unit',unit)
        scene('exported_cold_reload','export')
    elif phase=='rebuild':
        script('end_to_end_build','demo.py','build','--scene','drums','--unit',unit,
               '--output',unit/'replay_end_to_end')
        script('validate_build','validate_replays.py','--unit',unit,'build')
    elif phase=='package':
        script('package_stage','package_demo.py','--unit',unit)
        logged('package_archive',['tar','-czf',unit/'portable_demo.tar.gz','-C',unit,'portable_demo'])
        destination=unit/'portable_relocated';destination.mkdir()
        logged('package_extract',['tar','-xzf',unit/'portable_demo.tar.gz','-C',destination])
        logged('portable_cold_reload',[destination/'portable_demo/run.sh','preview'])
        script('validate_portable','validate_replays.py','--unit',unit,'portable')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True,type=Path)
    p.add_argument('phase',choices=['prepare','stills','motion','checks','interactive','rebuild','package'])
    a=p.parse_args();run(a.unit,a.phase)
