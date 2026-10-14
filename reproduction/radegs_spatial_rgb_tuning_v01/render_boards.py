from PIL import Image,ImageDraw,ImageFont
import numpy as np
from pathlib import Path
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(n):return ImageFont.truetype(FONT,n)
def fitted(text,n,width):
    while n>10 and font(n).getlength(text)>width:n-=1
    return font(n)
def image(a):
    if isinstance(a,(str,Path)):return Image.open(a).convert('RGB')
    if isinstance(a,Image.Image):return a.convert('RGB')
    a=np.asarray(a)
    if a.dtype!=np.uint8:a=np.uint8(np.clip(a,0,1)*255+.5)
    return Image.fromarray(a).convert('RGB')
def save_png(p,a):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);image(a).save(p)
def board(p,items,title,footer='',columns=3,full_frame=True,binary=False):
    ims=[image(a) for label,a in items];w=max(im.width for im in ims);h=max(im.height for im in ims)
    pad=14;head=92;cellhead=58;foot=50;rows=(len(items)+columns-1)//columns
    out=Image.new('RGB',(columns*(w+pad)+pad,head+rows*(h+cellhead+pad)+foot),'#f1f3f5');d=ImageDraw.Draw(out)
    subtitle=('Full frame' if full_frame else 'Secondary explanatory crop')+(' | binary candidates | every marked pixel black' if binary else ' | gain=1 | ink sigma=0.5 | black on white | no per-image normalization')
    d.text((pad,12),title,font=fitted(title,29,out.width-2*pad),fill='#15212d');d.text((pad,52),subtitle,font=fitted(subtitle,19,out.width-2*pad),fill='#324558')
    for i,((label,_),im) in enumerate(zip(items,ims)):
        x=pad+(i%columns)*(w+pad);y=head+(i//columns)*(h+cellhead+pad)
        for j,line in enumerate(label.split('\n')):d.text((x,y+j*25),line,font=fitted(line,20,w-5),fill='#15212d')
        # Native pixels. Different aspect ratios never stretched.
        out.paste(im,(x+(w-im.width)//2,y+cellhead));d.rectangle((x,y+cellhead,x+w-1,y+cellhead+h-1),outline='#c8cdd3')
    d.text((pad,out.height-foot+12),footer,font=fitted(footer,18,out.width-2*pad),fill='#324558')
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);out.save(p,quality=93,subsampling=0)
    return out.size
