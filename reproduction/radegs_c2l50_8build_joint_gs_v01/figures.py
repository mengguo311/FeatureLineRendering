from common import *
def run():
 out=ROOT/'delivery';out.mkdir(exist_ok=True);overview=[]
 for s,key in [('scan24','0036'),('scan65','0036'),('ficus','test_r_14')]:
  items=[]
  for v in registry()[s]['display_views']:
   p=ROOT/'scenes'/s/'views'/v
   for name in ['SOURCE_CPU','JOINT']:items.append((v+' | '+name,np.asarray(Image.open(p/(name+'.png')))/255.))
  panel(out/(s+'_FIVE_VIEWS.jpg'),items,s+' | Five original display cameras','Source CPU and true jointly sorted merged model; fixed exposure, no line edits',2)
  for name in ['SOURCE_CPU','LINE_ONLY','JOINT']:
   a=np.asarray(Image.open(ROOT/'scenes'/s/'views'/key/(name+'.png')))/255.;pad=np.ones((800,800,3));h,w=a.shape[:2];pad[:h,:w]=a;overview.append((s+'/'+key+' | '+name,pad))
 panel(out/'OVERVIEW.jpg',overview,'C2L50 8BUILD arms/C + original full-SH 3DGS','Native-size cells padded only; CPU joint EWA; no retraining / no geometry or opacity edits',3)
 print('FIGURES_COMPLETE')
if __name__=='__main__':run()
