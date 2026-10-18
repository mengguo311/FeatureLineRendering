"""Additional legible depth figures. Preserve the original unfiltered plot evidence."""
from env import *
from plots import plt,plot_image
from geometry_roles import ROLES,PALETTE
from display_layout import native_canvas
def graph_figure(s,out):
 g=json.loads((ROOT/'scenes'/s/'graph/PATCH_GRAPH.json').read_text());ns=[n for n in g['nodes'] if n['arm']=='line'];cases=list(dict.fromkeys(n['case'] for n in ns));fig,ax=plt.subplots(figsize=(12,2+1.2*len(cases)));xy={}
 for n in ns:
  x=VIEWS[s].index(n['view'])*3+(0 if n['side']=='left' else 1);y=len(cases)-1-cases.index(n['case']);xy[n['node_id']]=(x,y);ax.scatter(x,y,s=450,c=[PALETTE[n['role_index']]],edgecolors='black');ax.text(x,y,f'{n["node_id"]}\n{n["side"][0].upper()}',ha='center',va='center',fontsize=8);ax.text(x,y-.32,ROLES[n['role_index']].replace('_','\n') if n['role_index'] in [0,1,2] else ('ambiguous' if n['role_index']==3 else 'UNKNOWN'),ha='center',va='top',fontsize=6)
 for e in g['edges']:
  if e['arm']!='line':continue
  for i,j in e['accepted']:
   p=xy[e['node_ids_a'][i]];q=xy[e['node_ids_b'][j]];ax.plot([p[0],q[0]],[p[1],q[1]],c='green')
 ax.set_yticks(range(len(cases)),list(reversed(cases)));ax.set_xticks([.5,3.5,6.5],VIEWS[s]);ax.set_ylim(-1,len(cases)-.4);ax.set_xlim(-.7,7.7);ax.set_title(f'{s} | Actual source-ID patch measurement nodes\nNo certified cross-view links; node ID is not a physical primitive');ax.grid(axis='x',alpha=.2);fig.tight_layout();save(out/f'{s}_SUPPORT_GRAPH.png',plot_image(fig,1300,300+160*len(cases)))
def run():
 out=ROOT/'summary';out.mkdir(exist_ok=True);rows=[]
 for p in sorted(ROOT.glob('scenes/*/stage1/*/*/line/RESULT.json')):
  r=json.loads(p.read_text());e=npz(p.parent/'EVIDENCE.npz');dst=p.parent.parent/'profile_valid_only.png';assert not dst.exists()
  fig,ax=plt.subplots(1,1,constrained_layout=True);z=e['native_z'];q=e['query_median_center_z'];good=np.isfinite(z)&(z>.2)&(e['native_alpha']>=.5)&e['inside'];qgood=(q>.2)&(e['query_alpha']>=.5)&e['inside'];base=float(np.median(z[good])) if good.any() else 0;pworld=r['info']['pixel_world_proxy']
  for side,col in [(-1,'red'),(0,'green'),(1,'blue')]:
   k=(np.sign(e['side_offset'])==side);a=k&good;b=k&qgood;name=['Left','Center','Right'][side+1];ax.scatter(e['along_index'][a],(z[a]-base)/pworld,color=col,s=22,label=name+' frozen depth');ax.scatter(e['along_index'][b],(q[b]-base)/pworld,color=col,s=25,marker='x',label=name+' EWA center median')
  if not (good.any() or qgood.any()):ax.text(.5,.5,'NO QUALIFIED DEPTH SAMPLES\nUNKNOWN, not zero depth',transform=ax.transAxes,ha='center')
  ax.set_xlabel('Ordered original child sample');ax.set_ylabel('Depth offset / world-pixel proxy');ax.set_title(f'{r["scene"]} {r["view"]} {r["case"]}\nValid-only display; native={good.sum()}/{len(z)}, EWA={qgood.sum()}/{len(z)}');ax.legend(fontsize=7,ncol=3);save(dst,plot_image(fig,1000,650));rows.append(dict(scene=r['scene'],view=r['view'],case=r['case'],native_valid=int(good.sum()),EWA_valid=int(qgood.sum()),path=str(dst)))
 js(out/'VALID_ONLY_PLOT_RECEIPTS.json',dict(reason='Original v00 profiles retain invalid zeros for audit; this additional plot excludes missing depths only, does not alter any evidence or decisions.',plots=rows))
 for s in SCENES:
  cases=[c for c in json.loads((ROOT/'CASE_FREEZE.json').read_text())['cases'] if c['scene']==s and c['selection_valid']];items=[]
  for c in cases:
   for v in VIEWS[s]:
    d=ROOT/'scenes'/s/'stage1'/v/c['case'];r=json.loads((d/'line/RESULT.json').read_text());im=np.asarray(Image.open(d/'figures/ZOOM.jpg').convert('RGB'))/255;items.append((v+' | '+c['case']+' | '+r['role']['role'],im))
  panel(out/f'{s}_MULTIVIEW.jpg',items,f'{s} | ALL frozen cases / three known views','Each cell is an explanatory crop; native full frames remain in scenes. These are historical views, not blind tests. Original source and C8 fixed.',3)
  graph_figure(s,out)
 finish_overview(out)
def finish_overview(out):
 # Mixed native dimensions are padded ONLY, never resized/cropped.
 items=[]
 for s in SCENES:
  a=npz(ROOT/'scenes'/s/'stage0/REFERENCE.npz');items += [(s+' original RGB (native, padded)',native_canvas(a['original_rgb'],800,800)),(s+' ORIGINAL C8 / X-RAY (native, padded)',native_canvas(a['C8_line'],800,800))]
 panel(out/'OVERVIEW.jpg',items,'Original C8 lines -> SOURCE Gaussian responsibility pilot','Three scenes; no source/ink changes; native pixels padded, not resized. Support graphs are NOT physical primitives.',2);seal(out)
if __name__=='__main__':
 if '--resume-overview-only' in sys.argv:finish_overview(ROOT/'summary')
 else:run()
