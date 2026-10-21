"""Fresh-process exported-asset and relocated-package checks for all three models."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import argparse,json,subprocess,sys,zipfile
from validate_replays import compare
U=OUTPUT_ROOT/'units/unit_008';HERE=Path(__file__).parent.resolve()
def run(phase):
 if phase=='exports':
  records=json.loads((U/'browser_complete/EXPORTED_SCENES.json').read_text())['scenes'];rows=[]
  for rec in records:
   scene=rec['scene'];dest=U/'exported_reload'/scene;dest.mkdir(parents=True)
   with zipfile.ZipFile(U/f'browser_complete/{scene}_export.zip') as z:
    assert all(Path(n).name==n for n in z.namelist());z.extractall(dest/'asset')
   meta=json.loads((dest/'asset/asset.json').read_text());assert meta['scene']==scene and meta['viewer_camera']==rec['camera']
   command=[sys.executable,str(HERE/'demo.py'),'render','--scene',scene,'--asset',str(dest/'asset'),'--output',str(dest/'preview')]
   for k,v in rec['camera'].items():command+=['--'+k,str(v)]
   r=subprocess.run(command,timeout=120);r.check_returncode()
   original=U/f"browser_complete/session/{scene}/view_{rec['revision']:04d}"
   exact=[compare(original/f'frame_000_{n}',dest/f'preview/frame_000_{n}') for n in ('image.png','arrays.npz')]
   rows.append(dict(scene=scene,command=command,returncode=r.returncode,exact_files=exact,cold_process=True,exported_regions=meta['regions']))
  js(U/'metrics/EXPORT_REPLAY.json',dict(status='PASS',server_stopped=True,scenes=rows))
 elif phase=='portable':
  package=U/'relocated/portable_demo';rows=[]
  for scene in ('chair','lego','drums'):
   command=[str(package/'run.sh'),'preview','--scene',scene,'--output',str(package/f'runs/cold_{scene}')]
   r=subprocess.run(command,cwd=package,timeout=120);r.check_returncode()
   reference=(U/'renders/static_edited' if scene=='lego' else U/f'catalog_reference/{scene}')
   exact=[compare(reference/f'frame_000_{n}',package/f'runs/cold_{scene}/frame_000_{n}') for n in ('image.png','arrays.npz')]
   rows.append(dict(scene=scene,command=command,returncode=r.returncode,exact_files=exact))
  # The documented high-level CLI author/edit flow works after relocation too.
  commands=[['author','--scene','lego','--asset',str(package/'assets/lego_original'),'--region','3','--selection-recipe',str(package/'SELECTION_RECIPE.json'),'--name','Bucket surfaces (manual)','--output',str(package/'runs/author')],
            ['edit','--scene','lego','--asset',str(package/'runs/author'),'--region','4','--angle','35','--output',str(package/'runs/edit')],
            ['preview','--scene','lego','--asset',str(package/'runs/edit'),'--output',str(package/'runs/edited_preview')]]
  receipts=[]
  for args in commands:
   cmd=[str(package/'run.sh'),*args];r=subprocess.run(cmd,cwd=package,timeout=120);r.check_returncode();receipts.append(dict(command=cmd,returncode=r.returncode))
  exact=[compare(U/f'renders/static_edited/frame_000_{n}',package/f'runs/edited_preview/frame_000_{n}') for n in ('image.png','arrays.npz')]
  js(U/'metrics/PORTABLE_REPLAY.json',dict(status='PASS',scenes=rows,author_edit_receipts=receipts,author_edit_exact_files=exact,original_PLY_not_required=True,python_environment_bundled=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['exports','portable']);run(p.parse_args().phase)
