"""Serial bounded steps for a scene specified by a frozen unit protocol."""
import runtime
from runtime import output_guard
from pathlib import Path
import argparse, subprocess, sys, json

def run(unit,phase):
    unit=output_guard(unit);here=Path(__file__).resolve().parent;py=sys.executable
    scene=json.loads((unit/'PROTOCOL.json').read_text())['scene']
    def logged(name,args):
        subprocess.run([py,str(here/'run_logged.py'),'--unit',str(unit),'--name',name,'--',*map(str,args)],timeout=590,check=True)
    def script(name,file,*args):logged(name,[py,here/file,*args])
    def render(name,asset,*args):
        script(name,'demo.py','render','--scene',scene,'--asset',unit/f'assets/{asset}',
               '--output',unit/f'renders/{name}',*args)
    if phase=='prepare':script('prepare','run_scene.py','--unit',unit,'prepare')
    elif phase=='stills':
        script('source_model','run_scene.py','--unit',unit,'source')
        render('static_baseline','baseline','--trajectory','static')
        render('static_edited','edited','--trajectory','static')
        render('cold_reload','edited','--view','train_r_7')
    elif phase=='motion':
        render('orbit','edited','--trajectory','orbit')
        render('zoom','edited','--trajectory','zoom')
    elif phase=='checks':
        script('validate','validate_unit.py','--unit',unit)
        script('source_diagnostics','run_scene.py','--unit',unit,'diagnostics')
        script('media','media.py','--unit',unit)
    elif phase=='interactive':
        script('catalog','transfer_package.py','--unit',unit,'catalog')
        script('browser','browser_demo_test.py','--unit',unit,'--name','browser_complete','--catalog',unit/'CATALOG.json')
        script('viewer_smoke','smoke_viewer.py','--unit',unit)
        script('exported_cold_reload','run_scene.py','--unit',unit,'export')
    elif phase=='package':
        script('package_stage','transfer_package.py','--unit',unit,'stage')
        logged('package_archive',['tar','-czf',unit/'portable_demo.tar.gz','-C',unit,'portable_demo'])
        destination=unit/'relocated';destination.mkdir()
        logged('package_extract',['tar','-xzf',unit/'portable_demo.tar.gz','-C',destination])
        script('portable_replay','transfer_package.py','--unit',unit,'replay')
        script('portable_viewer','transfer_package.py','--unit',unit,'viewer')
        script('exported_viewer_reopen','transfer_package.py','--unit',unit,'reopen')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True,type=Path)
    p.add_argument('phase',choices=['prepare','stills','motion','checks','interactive','package'])
    a=p.parse_args();run(a.unit,a.phase)
