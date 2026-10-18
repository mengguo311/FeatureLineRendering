from env import *
from supported import describe_supported
sys.path.append(str(CODE.parent/'round09'))
from texture import describe
def run():
 y,x=np.mgrid[:161,:161];w=np.zeros((161,161));w[:,76:85]=1;a=np.ones((161,161,3));a[w>0]=np.repeat((.2+.3*np.sin(y[w>0]/6)**2)[:,None],3,axis=1);b=a.copy();b[w==0]=np.random.default_rng(2).random(((w==0).sum(),3));fa,_,_=describe_supported(a,w,1);fb,_,_=describe_supported(b,w,1);ua=describe(a,1);ub=describe(b,1)
 return dict(rgb_white=a,rgb_noise=b,weight=w,normalized_white=fa,normalized_noise=fb,unconditional_white=ua,unconditional_noise=ub),dict(normalized_max_foreground_change=float(np.max(abs(fa[w>0]-fb[w>0]))),unconditional_max_foreground_change=float(np.max(abs(ua[w>0]-ub[w>0]))))
def main():
 p=R/'analytic';assert not p.exists();p.mkdir();a,c=run();assert c['normalized_max_foreground_change']==0 and c['unconditional_max_foreground_change']>.01;np.savez_compressed(p/'COUNTERFACTUAL.npz',**a);js(p/'COUNTS.json',c)
 panel(p/'BACKGROUND_COUNTERFACTUAL.jpg',[(k,a[k]) for k in ['rgb_white','rgb_noise','normalized_white','normalized_noise','unconditional_white','unconditional_noise']],'Analytic thin foreground | identical object, changed background','Synthetic diagnostic only, not scene evidence or physical segmentation GT. Fixed feature display 0..1.',3);seal(p)
if __name__=='__main__':main()
