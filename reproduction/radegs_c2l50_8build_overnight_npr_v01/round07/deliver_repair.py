"""Mixed-native-size display repair only; scientific arrays and frozen code untouched."""
from env import *
def pad_native(items):
 if not items or any(np.asarray(a).ndim!=3 or np.asarray(a).shape[-1]!=3 for _,a in items):raise ValueError('nonempty HWC RGB images required')
 h=max(a.shape[0] for _,a in items);w=max(a.shape[1] for _,a in items);out=[]
 for t,a in items:
  b=np.ones((h,w,3),dtype=a.dtype);b[:a.shape[0],:a.shape[1]]=a;out.append((t,b))
 return out
def pad_panel(path,items,title,legend='',cols=3):return panel(path,pad_native(items),title,legend,cols)
def main():
 import delivery
 delivery.panel=pad_panel
 delivery.main()
if __name__=='__main__':main()
