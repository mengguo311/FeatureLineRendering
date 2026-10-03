"""Offline diagnostic aggregation and modest GitHub review delivery; no rendering."""
import argparse,hashlib,json,os,shutil,sys
from pathlib import Path
sys.dont_write_bytecode=True
from storage_paths import ROOT,ART,CONT,EXTERNAL_ROOT,scene_root
sys.path.insert(0,str(ART))
import summarize_results as summary
from PIL import Image,ImageDraw,ImageFont
SCENES=('hotdog','materials','mic','ship')
KEYS=('F_001','F_041','C_007','C_047','arc0_000','arc0_016','arc0_032')

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def write(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.partial');q.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n');os.replace(q,p)
def aggregate():
 rows={s:summary.safe_summarize_scene(s,ART,scene_root(s)) for s in SCENES}
 out={'schema':'multi-root-offline-summary-v1','scenes':rows,'actual_frames':sum(len(v['frames']) for v in rows.values()),'expected_frames':196,'complete_scenes':[s for s,v in rows.items() if v['status']=='COMPLETE_DIAGNOSTICS_ONLY'],'scientific_GO':False,'human_review':'PENDING','path_mapping_sha256':sha(CONT/'STORAGE_MAP.json'),'aggregator_source_sha256':sha(ART/'summarize_results.py'),'scope':'Existing diagnostics/provenance/seal-envelope aggregation, not full independent verifier; ink/support do not establish quality.'}
 write(CONT/'DIAGNOSTIC_SUMMARY.json',out)
 if out['actual_frames']!=196 or len(out['complete_scenes'])!=4:raise RuntimeError('Incomplete aggregation')
 print(json.dumps({'actual_frames':out['actual_frames'],'complete_scenes':out['complete_scenes']}))
def delivery():
 stage=EXTERNAL_ROOT/'review/github_delivery';stage.mkdir(parents=True,exist_ok=True)
 target=ROOT/'artifacts/hybrid_raster_trained_models_v1/review'
 try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
 except OSError:font=ImageFont.load_default()
 rows=[];sources=[]
 for scene in SCENES:
  out=scene_root(scene);media=out/'media'/scene
  for kind in ('comparison','overlay','matched'):
   p=media/f'arc0_{kind}_telegram1600.mp4'
   rows.append({'source':str(p),'target':str(target/scene/p.name),'sha256':sha(p),'bytes':p.stat().st_size,'kind':'Telegram complete33 comparison'})
  if scene=='hotdog':continue
  for kind in ('line','overlay','matched'):
   sheet=Image.new('RGB',(2000,446*len(KEYS)),'white');draw=ImageDraw.Draw(sheet)
   for n,key in enumerate(KEYS):
    p=out/'frames'/scene/key/f'{kind}_panel.png'
    with Image.open(p) as im:sheet.paste(im.convert('RGB').resize((2000,416),Image.Resampling.LANCZOS),(0,n*446+30))
    draw.text((8,n*446+4),scene+' '+key+' | '+kind+' | model review; human GO pending',font=font,fill='black')
    sources.append({'path':str(p),'sha256':sha(p),'scene':scene,'key':key,'kind':kind})
   p=stage/f'{scene}_{kind}_representatives.jpg';sheet.save(p,quality=88,subsampling=0)
   rows.append({'source':str(p),'target':str(target/scene/p.name),'sha256':sha(p),'bytes':p.stat().st_size,'kind':'JPEG seven fixed representative panels'})
 required=sum(r['bytes'] for r in rows);free=shutil.disk_usage(ROOT).free
 manifest={'schema':1,'rows':rows,'representative_sources':sources,'bytes':required,'repo_free_before':free,'hard_reserve':1024**3,'copy_plus_git_estimate':3*required+16*1024**2,'scope':'Only modest review JPEG and all12 Telegram videos copied; native fields/media stay at explicit per-scene original roots; no image regeneration or science changes'}
 if free-3*required-16*1024**2<1024**3:
  manifest['status']='DELIVERY_BLOCKED_REPO_RESERVE';write(CONT/'DELIVERY.json',manifest);raise RuntimeError('Insufficient root room for modest media plus Git reserve')
 for row in rows:
  p=Path(row['target']);p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():
   if sha(p)!=row['sha256']:raise RuntimeError('Refusing changed delivery overwrite: '+str(p))
  else:shutil.copyfile(row['source'],p)
  if sha(p)!=row['sha256']:raise RuntimeError('Copy digest mismatch')
 manifest['status']='COPIED_PENDING_PUSH_READBACK';manifest['repo_free_after']=shutil.disk_usage(ROOT).free
 write(CONT/'DELIVERY.json',manifest);print(json.dumps({'delivery_files':len(rows),'bytes':required,'repo_free_after':manifest['repo_free_after']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['aggregate','delivery'],required=True);a=p.parse_args()
 aggregate() if a.phase=='aggregate' else delivery()
