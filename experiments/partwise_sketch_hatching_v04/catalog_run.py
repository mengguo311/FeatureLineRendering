"""Bounded unit008 construction and original-model references."""
import runtime
from runtime import OUTPUT_ROOT,js,sha
from pathlib import Path
import argparse,json,subprocess
import numpy as np
from PIL import Image
from demo import load_asset,save_frame
from geometry import resize_camera
from media import contact
U=OUTPUT_ROOT/'units/unit_008'
def run(phase):
 p=json.loads((U/'SCOPE.json').read_text())
 if phase=='construction':
  mesh,strokes,meta=load_asset(U/'catalog_assets/lego');out=U/'construction';out.mkdir()
  items=[]
  for i,c in enumerate(p['construction_cameras']):
   save_frame(out,f'view_{i:02d}',mesh,strokes,meta,c)
   for key in ('proxy','region_rgb'):items.append((c['view']+' | '+key,Image.open(out/f'view_{i:02d}_{key}.png')))
  contact(out/'construction.png',items,cols=2,size=512,title='Lego | frozen construction views | before manual face selection')
 elif phase=='source':
  import model_adapter as m
  out=U/'source_model';out.mkdir();(U/'build').mkdir()
  command=['g++','-O3','-std=c++17','-shared','-fPIC',str(Path(__file__).with_name('source_ewa.cpp')),'-o',str(U/'build/libsource.so')]
  r=subprocess.run(command,timeout=90);r.check_returncode();js(U/'build/COMPILE.json',dict(command=command,returncode=r.returncode))
  m.LIB_PATH=U/'build/libsource.so';a=m.load_source(p['original']['original_ply'],p['original']['sha256'])
  js(out/'MODEL_IMPORT.json',dict(audit=a['audit'],original=p['original']))
  for i,c in enumerate(p['static_cameras']):
   arrays=m.render_source(a,resize_camera(c,512));np.savez_compressed(out/f'frame_{i:03d}.npz',**arrays)
   Image.fromarray(np.uint8(np.clip(arrays['rgb'],0,1)*255+.5)).save(out/f'frame_{i:03d}_rgb.png')
   print('original Lego',i,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['construction','source']);run(p.parse_args().phase)
