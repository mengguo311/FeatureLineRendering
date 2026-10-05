from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from io_utils import guard
from media_helpers import _rgb,mask_image,_font,_save,make_contact,encode_video

def tiles(path,items,title,cols=5,footer='原始贡献显示增益1；未匹配墨量；非三维曲线'):
    guard(32*1024**2);w=h=800;rows=(len(items)+cols-1)//cols
    im=Image.new('RGB',(cols*w,48+rows*(h+36)+48),'white');d=ImageDraw.Draw(im);d.text((12,5),title,font=_font(24),fill='black')
    for i,(label,a,kind) in enumerate(items):
        x=(i%cols)*w;y=48+(i//cols)*(h+36);d.text((x+8,y+4),label,font=_font(21),fill='black')
        tile=_rgb(a) if kind=='rgb' else mask_image(a)
        im.paste(tile,(x,y+36))
    d.text((12,im.height-38),footer,font=_font(21),fill='black');return _save(im,path)
def chunk_image(c):
    colors=np.zeros((*c.shape,3),np.float32)
    valid=c>0
    for k in range(3):colors[:,:,k]=np.where(valid,((c*(37+42*k))%211+32)/255.,1.)
    return colors
def evidence_panel(path,raw,e,title):
    items=[('原始 RGB',raw['rgb'],'rgb'),('fine sigma0.8',e['fine'].max(-1),'mask'),('MAJOR 持久支持',e['major'].max(-1),'mask'),('DETAIL 未删除',e['detail'].max(-1),'mask'),('32px chunks (union display)',chunk_image(e['chunks'].max(-1)),'rgb')]
    items += [(name+' MAJOR',e['major'][:,:,i],'mask') for i,name in enumerate(('color','geometry','outline'))]
    items += [('原始 alpha',raw['alpha'],'mask'),('可见 offedge 区域',e['offedge'],'mask')]
    return tiles(path,items,title,footer='独立RGB/depth/alpha方向NMS；outline视角相关；fine/detail保留；未以路径长度筛边界')
def comparison(path,raw,e,q,labels,title):
    items=[('原始 RGB',raw['rgb'],'rgb'),('fine',e['fine'].max(-1),'mask'),('MAJOR',e['major'].max(-1),'mask'),('DETAIL',e['detail'].max(-1),'mask'),('原始 alpha',raw['alpha'],'mask')]
    items += [(label,q[:,:,j],'mask') for j,label in enumerate(labels)]
    return tiles(path,items,title)
