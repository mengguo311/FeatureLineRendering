from env import *
from collections import Counter
from plots import plot_image,plt,marked
from partition_plots import patch_paint

def map_image(x,title,vmax,w,h):
 fig,ax=plt.subplots();im=ax.imshow(x,cmap='magma',vmin=0,vmax=vmax);ax.set_title(title,fontsize=10);ax.axis('off');fig.colorbar(im,ax=ax,shrink=.7);fig.tight_layout();return plot_image(fig,w,h)
if __name__=='__main__':
 out=ROOT/'delivery_images_v01';out.mkdir(exist_ok=True);items=[];chosen={'scan24':'roof_wall_eave','scan65':'cap_marks','ficus':'thin_leaf_edge'}
 for s in SCENES:
  c=cam(s,DEV[s]);raw=npz(rawpath(s,DEV[s]));ref=npz(ROOT/'round1/scenes'/s/DEV[s]/'reference/REFERENCE.npz');w,h=c['width'],c['height'];z=raw['median_camera_z'].squeeze();alpha=raw['alpha'].squeeze();good=(z>.2)&(alpha>=.5)&(ref['median_center_z']>.2);err=np.full_like(z,np.nan);err[good]=abs(ref['median_center_z'][good]-z[good])/z[good]
  panel(out/f'CALIBRATION_{s}.jpg',[('Frozen source RGB reference',raw['rgb']),('Same source: CPU fullSH EWA',ref['rgb']),('RGB absolute error / fixed 0..0.1',map_image(abs(raw['rgb']-ref['rgb']).mean(2),'Mean RGB absolute difference',.1,w,h)),('Alpha absolute error / fixed 0..0.1',map_image(abs(alpha-ref['alpha']),'Alpha difference',.1,w,h)),('Center vs frozen-depth relative error',map_image(err,'NOT surface GT; relative depth difference',.15,w,h)),('Original alpha coverage (NOT object mask)',np.repeat(alpha[...,None],3,2))],f'{s} {DEV[s]} | source-only calibration','Native RaDe for DTU; vanilla + CPU plane-readout proxy for Ficus. CPU EWA is not official CUDA equivalence.',3)
  ca=chosen[s];e=npz(ROOT/'round1/scenes'/s/DEV[s]/ca/'line/EVIDENCE.npz');a=activate(read_ply(registry()[s]['model']));ink=render(activate(read_ply(linepath(s)/'gaussians.ply')),c)['rgb'];roles=npz(ROOT/'round2/models'/s/DEV[s]/ca/'line/SOURCE_ROLES.npz');paint=patch_paint(a,c,s,roles)
  items.extend([(s+' | Original RGB / fixed interval',marked(raw['rgb'],e)),(s+' | Original C8 ink / unchanged',marked(ink,e)),(s+' | LOCAL proxy / no certified primitive',paint)]);del a,ink
 padded=[]
 for label,im in items:
  hh,ww=im.shape[:2];q=np.ones((800,800,3));yy=(800-hh)//2;xx=(800-ww)//2;q[yy:yy+hh,xx:xx+ww]=im;padded.append((label,q))
 panel(ROOT/'OVERVIEW.jpg',padded,'Three completed rounds | original C8-guided surface partition pilot','Original pixels, white padding only. R1 proxy correction; R2 zero line cross-view groups; R3 zero passes. NO formal NPR upgrade.',3)
 # Readable textual evidence boards supplement long labels in preserved scientific panels; no numeric changes.
 for s in SCENES:
  canvas=Image.new('RGB',(1500,800),'white');d=ImageDraw.Draw(canvas);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19);d.text((30,20),s+' | Frozen reserved-view patch checks',font=font,fill='black');y=80
  for v in RESERVED[s]:
   d.text((30,y),'Camera '+v+' (historically observed, not blind)',font=small,fill='black');y+=35
   for ca in cases(s):
    if not ca['selection_valid']:continue
    r=json.loads((ROOT/'round3/validation'/s/v/ca['case']/'line/RESULT.json').read_text());states=Counter(z['state'] for z in r['frozen_patch_validation']);msg=', '.join(str(n)+' '+k for k,n in states.items()) or 'No frozen R2 candidate';d.text((55,y),ca['case']+': '+msg,font=small,fill='black');y+=32
   y+=15
  d.text((30,650),'Occluded / missing observations are NOT negative votes.',font=small,fill='black');d.text((30,685),'No refitting on reserved views. No new source or ink geometry.',font=small,fill='black');canvas.save(out/f'DECISIONS_{s}.png')
 seal(out)
