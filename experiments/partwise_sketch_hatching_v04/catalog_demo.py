"""One portable entrypoint for saved Chair, Lego and Drums models."""
import runtime
from pathlib import Path
import argparse,json,sys,subprocess

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('command',choices=['viewer','preview','orbit','zoom','edit','author'])
 p.add_argument('--catalog',type=Path,required=True);p.add_argument('--scene')
 p.add_argument('--output',type=Path,required=True);p.add_argument('--port',type=int,default=8765)
 p.add_argument('--asset',type=Path,help='Override saved asset for render/edit/author')
 p.add_argument('--region','--part',type=int);p.add_argument('--selection-recipe',type=Path);p.add_argument('--name',default='Manual region')
 for k in ('angle','spacing','length','width'):p.add_argument('--'+k,type=float)
 a=p.parse_args();cat=json.loads(a.catalog.read_text());scene=a.scene or cat['default_scene']
 if scene not in cat['scenes']:p.error('unknown scene')
 asset=a.asset or a.catalog.resolve().parent/cat['scenes'][scene]['asset']
 meta=json.loads((asset/'asset.json').read_text())
 if meta['scene']!=scene:p.error('scene/asset mismatch')
 here=Path(__file__).parent
 if a.command=='viewer':
  command=[sys.executable,str(here/'viewer.py'),'--catalog',str(a.catalog),'--scene',scene,'--output',str(a.output),'--port',str(a.port)]
 else:
  command=[sys.executable,str(here/'demo.py'),'render' if a.command in ('preview','orbit','zoom') else a.command,'--scene',scene,'--asset',str(asset),'--output',str(a.output)]
  if a.command=='preview':command+=['--view',meta['cameras'][0]['view']]
  elif a.command in ('orbit','zoom'):command+=['--trajectory',a.command]
  else:
   if a.region is None:p.error('edit/author requires --region')
   command+=['--region',str(a.region)]
   if a.command=='author':
    if a.selection_recipe is None:p.error('author requires --selection-recipe')
    command+=['--selection-recipe',str(a.selection_recipe),'--name',a.name]
   else:
    for k in ('angle','spacing','length','width'):
     if getattr(a,k) is not None:command+=['--'+k,str(getattr(a,k))]
 # Replace process so interruption never leaves an unowned rendering child.
 import os
 os.execv(sys.executable,command)
if __name__=='__main__':main()
