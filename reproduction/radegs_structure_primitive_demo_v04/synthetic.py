from common import *
from primitive import *
from run import show_panel

def make(points,view=0,kind='surface',pixel=.02):
    s=fit_segment(points,pixel);s.update(view=view,kind=kind,uv=np.stack([np.arange(len(points)),np.zeros(len(points))],1),camera=None,source_ids=list(range(len(points))),normal=[0,0,1]);return s
def main():
    dst=T/'synthetic';dst.mkdir(exist_ok=True);t=np.linspace(0,1,25);x=(t-.5)*.5;p=np.stack([x,0*x,2+0*x],1)
    cases={
      'straight':[make(p)],
      'curved':[make(np.stack([x,.13*np.sin(np.pi*t),2+0*x],1))],
      'parallel_2pixel':[make(p),make(p+[0,.04,0],1)],
      'depth_layers_2pixel':[make(p),make(p+[0,0,.04],1)],
      'T_junction':[make(p[:13]),make(p[12:]),make(np.stack([0*x[:13],np.linspace(0,.25,13),2+0*x[:13]],1))],
      'true_corner':[make(p[:13]),make(np.stack([0*x[:13],np.linspace(0,.25,13),2+0*x[:13]],1))],
      'perturbed_depth':[make(p+np.stack([0*x,0*x,.001*np.sin(np.arange(25))],1))],
      'missing_support':[make(p)],
      'moving_silhouette_conflict':[make(p,0,'silhouette'),make(p+[0,.016,0],1,'silhouette')]
    }
    cs=[{'width':201,'height':161,'fx':240.,'fy':240.,'extrinsic':np.eye(4).tolist()}]
    E=np.eye(4);theta=.3;E[:3,:3]=[[np.cos(theta),0,np.sin(theta)],[0,1,0],[-np.sin(theta),0,np.cos(theta)]];E[:3,3]=[-2*np.sin(theta),0,2-2*np.cos(theta)];cs.append(dict(cs[0],extrinsic=E.tolist()))
    info={};items=[]
    for name,segs in cases.items():
        g,amb=associate(segs);a=sample_graph(g);np.savez_compressed(dst/(name+'.npz'),**a);r=core.render(a,cs[1]);demo.saveimage(dst/(name+'.png'),r);items.append((name,r));info[name]={'observed_segments':len(segs),'primitives':len(g),'gaussians':len(a['means']),'types':[s['type'] for s in g],'ambiguities':amb}
    # Actual fixed-render duplication, not count-only proof.
    dup=[]
    for n in (3,12,47):
        g,_=associate([make(p,i) for i in range(n)]);a=sample_graph(g);r=core.render(a,cs[0]);dup.append(r);info[f'duplicate_{n}']={'primitives':len(g),'gaussians':len(a['means']),'darkness_sum':float((1-r[...,0]).sum())}
    np.testing.assert_array_equal(dup[0],dup[1]);np.testing.assert_array_equal(dup[0],dup[2])
    show_panel(dst/'controls.jpg',items,'DETERMINISTIC SYNTHETIC CONTROLS / not real-scene results',cols=3,scale=2)
    js(dst/'RESULTS.json',{'cases':info,'duplicate_render_bitexact':True,'camera':cs,'known_correspondence_not_used_in_real_data':True,'near_layer_scope':'2 reference pixels separated; subpixel layers remain ambiguous','missing_support_kept':True,'no_source_GT_or_holdouts':True});seal(dst)
    print('SYNTHETIC_COMPLETE',len(cases),'assets; duplicate renders bit exact')
if __name__=='__main__':main()
