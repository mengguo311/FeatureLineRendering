"""Copy complete-frame evidence and link all fixed-domain media; no rerendering."""
import hashlib,shutil,json,html
from pathlib import Path
root=Path.cwd();art=root/'artifacts/direct_curve_global_fit_probe';out=root/'out/direct_curve_global_fit_probe/run';fig=art/'figures';fig.mkdir(exist_ok=True)
manifest={};md=['# Complete visual evidence','','All panels are complete native800 frames. Method order uses the frozen randomized labels; the implementing-model review is internal. Original C photographs and interpolated frozen-GS images are different evaluation domains. No successful-window selection. The trajectory contact pages cover every frame; quartiles are fixed in advance. Videos contain all33 frames at12fps. Curated copies are byte-identical to the scientific outputs.',''];page=['<!doctype html><html><meta charset="utf-8"><title>Direct curve global fit probe</title><style>body{font-family:system-ui;max-width:1400px;margin:30px auto;padding:0 20px}img,video{max-width:100%;height:auto}summary{cursor:pointer}a{color:#154f92}figure{margin:20px 0}figcaption{margin-bottom:8px}</style><h1>Complete fixed-domain evidence</h1><p>Original C photos test image evidence. Interpolation uses frozen-GS RGB only. Randomized method labels are keyed separately. All images and videos link to their complete local files.</p>']
for scene in ['lego','chair','drums','ficus']:
 ev=out/scene/'evaluate';md += [f'## {scene}','','[Method key]('+str(ev/'REVIEW_KEY.json')+'). This key was kept separate during initial internal observations.',''];page += [f'<h2>{scene}</h2>']
 names=['C_COMPLETE.png','arc0_quartiles.png','arc1_quartiles.png']
 for name in names:
  p=ev/'figures'/name;q=fig/f'{scene}_{name}';shutil.copyfile(p,q);h=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256(q.read_bytes()).hexdigest()==h;manifest[str(q.relative_to(root))]=dict(source=str(p),sha256=h)
  md.append(f'- [{name}]({q})')
  relative=str(q.relative_to(art));page += [f'<figure><figcaption>{scene} {name}</figcaption><a href="{relative}"><img loading="lazy" src="{relative}"></a></figure>']
 for arc in [0,1]:
  video=ev/'videos'/f'arc{arc}_complete.mp4';md+=['',f'- [Arc{arc} complete playable video]({video})']
  relative='../../'+str(video.relative_to(root));page += [f'<h3>Arc{arc}: all33 frames</h3><video controls preload="metadata" src="{relative}"></video><p><a href="{relative}">Open full video</a></p>']
  pages=sorted((ev/'figures').glob(f'arc{arc}_allframes_*.png'));md += [f'- All-frame contacts: '+', '.join(f'[page{j}]({p})' for j,p in enumerate(pages))]
  page += ['<details><summary>Every-frame contact pages</summary>']
  for p in pages:
   rel='../../'+str(p.relative_to(root));page += [f'<a href="{rel}"><img loading="lazy" src="{rel}"></a>']
  page += ['</details>']
 for split in ['F','C']:
  frames=sorted((ev/'figures').glob(split+'_*.png'));frames=[p for p in frames if p.name!='C_COMPLETE.png'];md+=['',f'- Every native {split} comparison: '+', '.join(f'[{p.stem}]({p})' for p in frames)]
  page += [f'<details><summary>Every native {split} comparison</summary>']
  for p in frames:
   rel='../../'+str(p.relative_to(root));page += [f'<figure><figcaption>{p.stem}</figcaption><a href="{rel}"><img loading="lazy" src="{rel}"></a></figure>']
  page += ['</details>']
 md += ['']
page += ['</html>'];(art/'index.html').write_text('\n'.join(page)+'\n');(art/'FIGURES.md').write_text('\n'.join(md)+'\n');(art/'CURATED_MEDIA.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');print('Curated',len(manifest),'byte-identical complete-frame sheets; all media linked.')
