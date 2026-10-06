"""Native 800px images and nearest-neighbor frozen fragment profiles, fixed gain."""
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from runtime import *
def save(p,a):
 a=np.asarray(a);a=np.repeat(a[...,None],3,axis=2) if a.ndim==2 else a;p=scoped(p);Image.fromarray(np.round(np.clip(a,0,1)*255).astype(np.uint8)).save(p);return rel(p)
def sheet(p,rows,labels,title,tile=800):
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18);canvas=Image.new('RGB',(len(labels)*tile,len(rows)*(tile+30)+45),'white');d=ImageDraw.Draw(canvas);d.text((8,8),title,fill='black',font=font)
 for j,row in enumerate(rows):
  for i,a in enumerate(row):
   a=np.asarray(a);a=np.repeat(a[...,None],3,2) if a.ndim==2 else a;im=Image.fromarray(np.round(np.clip(a,0,1)*255).astype(np.uint8));im=im.resize((tile,tile),Image.Resampling.NEAREST);canvas.paste(im,(i*tile,45+j*(tile+30)+30));d.text((i*tile+5,45+j*(tile+30)+5),labels[i],fill='black',font=font)
 p=scoped(p);canvas.save(p);return rel(p)
def profile_plot(p,profiles,title):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(7,4));x=np.arange(-12,13)
 for label,a in profiles.items():ax.plot(x,a,label=label)
 ax.set(xlabel='normal offset (native pixels)',ylabel='ink (gain 1)',title=title,ylim=(-.02,1.02));ax.legend();fig.tight_layout();p=scoped(p);fig.savefig(p,dpi=140);plt.close(fig);return rel(p)
