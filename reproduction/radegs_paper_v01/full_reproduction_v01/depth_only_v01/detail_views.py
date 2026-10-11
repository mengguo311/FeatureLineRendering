"""Unclipped per-camera depth comparisons; scale fixed across both checkpoints.
Different cameras may have different labeled scales. No depth editing or GT.
"""
import json,os,sys
from pathlib import Path
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');D=H/'depth_only_v01'
os.environ['MPLCONFIGDIR']=str(D/'cache/matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from depth_checks import valid_depth,paired_thumbnail
P=Path(__file__).resolve().parent;W=P.parents[3];sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import sha256,atomic_json
def make_details(model,output):
 model=Path(model);out=Path(output);out.mkdir(parents=True,exist_ok=False);cams=json.loads((model/'depth_normal/cameras_and_conventions.json').read_text());limits=[];selected=[];tiles=[]
 for index,c in enumerate(cams):
  pair=[];hashes={}
  for directory in ('depth_normal_15000','depth_normal'):
   p=model/directory/(c['view']+'.npz');hashes[str(p)]=sha256(p)
   with np.load(p) as z:depth=z['median_camera_z'][0];mask=valid_depth(depth,z['alpha'][0]);pair.append(np.ma.masked_where(~mask,depth))
  lo=min(float(x.min()) for x in pair);hi=max(float(x.max()) for x in pair);assert hi>lo
  limits.append({'view':c['view'],'vmin':lo,'vmax':hi,'clipped_valid_pixels':0,'source_NPZ_sha256':hashes})
  tiles.append((c['view'],paired_thumbnail(*[x[::5,::5] for x in pair]),lo,hi))
  if index in (0,len(cams)//2,len(cams)-1):selected.append((c['view'],pair,lo,hi))
 cmap=plt.get_cmap('viridis').copy();cmap.set_bad('#999999');fig,axs=plt.subplots(3,2,figsize=(11,11))
 for r,(view,pair,lo,hi) in enumerate(selected):
  for j,x in enumerate(pair):
   im=axs[r,j].imshow(x,cmap=cmap,vmin=lo,vmax=hi);axs[r,j].set_title(view+' / '+str((15000,30000)[j])+' / fixed [%.3f, %.3f]'%(lo,hi));axs[r,j].set_axis_off();fig.colorbar(im,ax=axs[r,j],fraction=.046,pad=.02,label='camera-z / scene units')
 fig.suptitle(model.name+' / RAW median camera-z\nSame camera: exact same15k/30k scale from all valid values, no display clipping. Gray=invalid.\nDifferent rows use labeled ranges; colors are not comparable across rows. Training views only.');fig.tight_layout();fig.savefig(out/'DEPTH_NOCLIP_15K_30K.png',dpi=145);plt.close(fig)
 fig,axs=plt.subplots((len(cams)+6)//7,7,figsize=(20,2.2*((len(cams)+6)//7)),squeeze=False)
 for ax,(view,tile,lo,hi) in zip(axs.flat,tiles):ax.imshow(tile,cmap=cmap,vmin=lo,vmax=hi);ax.set_title(view+' 15k|30k [%.2f,%.2f]'%(lo,hi),fontsize=8)
 for ax in axs.flat:ax.set_axis_off()
 fig.suptitle(model.name+' all cameras / labeled scale shared within each15k|30k pair / no clipping / gray invalid');fig.tight_layout();fig.savefig(out/'ALL_VIEWS_NOCLIP.png',dpi=140);plt.close(fig)
 atomic_json(out/'PREVIEW_SCALES.json',{'method_variant':'official_code_fix_v01','input_model':str(model),'unit':'preprocessed scene units, not asserted meters','no_GT_or_RGB_depth_change':True,'bounds_rule':'min/max of all valid median depths from BOTH checkpoints at each camera; no pixel dropped; fixed within pair','limits':limits,'output_sha256':{str(p):sha256(p) for p in out.glob('*.png')}})
 return [p for p in out.iterdir() if p.is_file()]
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--model',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();make_details(a.model,a.output)
