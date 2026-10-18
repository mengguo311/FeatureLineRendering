from env import *
from geometry_roles import ROLES,PALETTE
from plots import responsibility_render,marked,plot_image,plt
def depth_plot(e,r,w,h):
 p=r['info']['pixel_world_proxy'];st=e['conditional_stats'];fig,ax=plt.subplots(2,1,constrained_layout=True);valid=e['patch_valid'];base=np.median(e['native_z'][valid]) if valid.any() else 0;x=np.arange(len(st));old=e['query_median_center_z'];native=e['native_z']
 for z,color,label,good in [(native,'black','Frozen depth',np.isfinite(native)&(native>.2)),(old,'gray','Center median',old>.2),(st[:,1],'teal','Conditional modes median',st[:,4]>=.8)]:
  good=good&e['inside']&(e['query_alpha']>=.5);ax[0].plot(x[good],(z[good]-base)/p,'.',ms=3,c=color,label=label)
 ax[0].set_ylabel('Depth offset / world-pixel proxy');ax[0].legend(fontsize=8);ax[0].set_title('Same source alpha*T; depth proxies differ')
 ok=(st[:,4]>=.8)&np.isfinite(st[:,5]);ax[1].plot(x,e['query_layer_width']/p,c='gray',label='Old center q90-q10');ax[1].plot(x[ok],st[ok,5]/p,c='teal',label='Conditional width incl sigma');ax[1].axhline(8,c='red',ls='--',label='Frozen gate 8p');ax[1].set_ylim(0,min(100,max(10,float(np.nanpercentile(np.r_[e['query_layer_width']/p,st[ok,5]/p],95)))));ax[1].set_ylabel('Width / world-pixel proxy');ax[1].set_xlabel('Frozen query pixel index');ax[1].legend(fontsize=8);return plot_image(fig,w,h)
def round1_figures(s,views,root):
 a=activate(read_ply(registry()[s]['model']));line=activate(read_ply(linepath(s)/'gaussians.ply'))
 for v in views:
  c=cam(s,v);raw=npz(rawpath(s,v));ink=render(line,c)['rgb']
  for ca in cases(s):
   d=root/s/v/ca['case'];out=d/'figures'
   if not (d/'line/RESULT.json').exists():continue
   if (out/'SEAL.json').exists():checkseal(out);continue
   out.mkdir(exist_ok=True);r=json.loads((d/'line/CENTER_BASELINE.json').read_text());q=json.loads((d/'line/RESULT.json').read_text());e=npz(d/'line/EVIDENCE.npz');actual=responsibility_render(a,c,s,e);role=responsibility_render(a,c,s,e,q['conditional_role']['role_index']);panel(out/'CASE.jpg',[('Original source RGB + fixed queries',marked(raw['rgb'],e)),('Original C8 ink / X-RAY',marked(ink,e)),('SOURCE responsibility: L red / R blue',actual),('Conditional role PROXY: '+q['conditional_role']['role'],role),('Center vs conditional depth (not surface GT)',depth_plot(e,r,c['width'],c['height'])),('Old center role: '+r['role']['role'],responsibility_render(a,c,s,e,r['role']['role_index']))],f'{s} {v} {ca["case"]} | conditional-ray experiment',f'Parent {ca["parent_id"]}; full SH source unchanged; same pixels and alpha*T; missing responsibility remains UNKNOWN.',3)
   items=[]
   for arm in ['line','shifted_12px','source_geometry_axis','shuffled_sides']:
    ee=npz(d/arm/'EVIDENCE.npz');qq=json.loads((d/arm/'RESULT.json').read_text());items.append((arm+' | '+qq['conditional_role']['role'],marked(responsibility_render(a,c,s,ee),ee)))
   panel(out/'CONTROLS.jpg',items,f'{s} {v} {ca["case"]} | matched query budgets','Source-only responsibility. Shuffled null reuses identical pixels, changes side assignment only.',2);seal(out)
