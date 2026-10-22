"""One portable entrypoint for saved real-model scenes."""
import runtime
from pathlib import Path
import argparse,json,sys,subprocess

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('command',choices=['viewer','preview','orbit','zoom','edit','restore','author','display','export','replay','refine'])
 p.add_argument('--catalog',type=Path,required=True);p.add_argument('--scene')
 p.add_argument('--output',type=Path,required=True);p.add_argument('--port',type=int,default=8765)
 p.add_argument('--asset',type=Path,help='Override saved asset; viewer opens it as a single model')
 p.add_argument('--example',help='Optional saved example ID from the catalog (default keeps the original model asset)')
 p.add_argument('--region','--part',type=int);p.add_argument('--selection-recipe',type=Path);p.add_argument('--name',default='Manual region')
 for k in ('angle','spacing','length','width'):p.add_argument('--'+k,type=float)
 p.add_argument('--ink-strength',type=float)
 p.add_argument('--cross',choices=['on','off']);p.add_argument('--cross-angle',type=float);p.add_argument('--cross-spacing',type=float)
 p.add_argument('--contour-strength',type=float);p.add_argument('--contours',choices=['on','off'])
 p.add_argument('--iterations',type=int,default=10);p.add_argument('--max-displacement',type=float,default=.018)
 p.add_argument('--kind',choices=['image','orbit','zoom'],default='orbit');p.add_argument('--bundle',type=Path)
 for k in ('azimuth','elevation','distance'):p.add_argument('--'+k,type=float)
 a=p.parse_args();cat=json.loads(a.catalog.read_text());scene=a.scene or cat['default_scene']
 if scene not in cat['scenes']:p.error('unknown scene')
 if a.asset and a.example:p.error('--asset and --example are mutually exclusive')
 asset=a.asset or a.catalog.resolve().parent/cat['scenes'][scene]['asset']
 if a.example and a.example!='default':
  from scene_catalog import read_catalog
  _,_,examples=read_catalog(a.catalog)
  if a.example not in examples or examples[a.example]['scene']!=scene:p.error('unknown example for this model')
  asset=examples[a.example]['asset']
 meta=json.loads((asset/'asset.json').read_text())
 if meta['scene']!=scene:p.error('scene/asset mismatch')
 here=Path(__file__).parent
 if a.command in ('export','replay'):
  command=[sys.executable,str(here/'presentation.py'),a.command,'--output',str(a.output)]
  if a.command=='replay':
   if not a.bundle:p.error('replay requires --bundle')
   bundle_meta=json.loads((a.bundle/'asset/asset.json').read_text())
   if bundle_meta['scene']!=scene:p.error('scene/bundle mismatch')
   command+=['--bundle',str(a.bundle)]
  else:
   command+=['--asset',str(asset),'--kind',a.kind]
   for k in ('azimuth','elevation','distance'):
    if getattr(a,k) is not None:command+=['--'+k,str(getattr(a,k))]
 elif a.command=='refine':
  if a.region is None:p.error('refine requires --region')
  command=[sys.executable,str(here/'local_refinement.py'),'--asset',str(asset),'--output',str(a.output),
           '--region',str(a.region),'--iterations',str(a.iterations),'--max-displacement',str(a.max_displacement)]
 elif a.command=='viewer':
  source_args=['--asset',str(asset)] if a.asset else ['--catalog',str(a.catalog),'--scene',scene]
  if a.example:source_args+=['--example',a.example]
  command=[sys.executable,str(here/'viewer.py'),*source_args,'--output',str(a.output),'--port',str(a.port)]
 else:
  command=[sys.executable,str(here/'demo.py'),'render' if a.command in ('preview','orbit','zoom') else a.command,'--scene',scene,'--asset',str(asset),'--output',str(a.output)]
  if a.command=='preview':command+=['--view',meta['cameras'][0]['view']]
  elif a.command in ('orbit','zoom'):command+=['--trajectory',a.command]
  elif a.command=='display':
   if a.contour_strength is not None:command+=['--contour-strength',str(a.contour_strength)]
   if a.contours is not None:command+=['--contours',a.contours]
  else:
   if a.region is None:p.error('edit/author requires --region')
   command+=['--region',str(a.region)]
   if a.command=='author':
    if a.selection_recipe is None:p.error('author requires --selection-recipe')
    command+=['--selection-recipe',str(a.selection_recipe),'--name',a.name]
   else:
    for k in ('angle','spacing','length','width'):
     if getattr(a,k) is not None:command+=['--'+k,str(getattr(a,k))]
    for k in ('cross','cross_angle','cross_spacing','ink_strength'):
     if getattr(a,k) is not None:command+=['--'+k.replace('_','-'),str(getattr(a,k))]
 # Replace process so interruption never leaves an unowned rendering child.
 import os
 os.execv(sys.executable,command)
if __name__=='__main__':main()
