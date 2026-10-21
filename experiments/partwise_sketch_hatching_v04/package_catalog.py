"""Portable three-model package containing immutable saved surfaces and paths."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import shutil,json,os
U=OUTPUT_ROOT/'units/unit_008';OUT=U/'portable_demo'
if OUT.exists():raise FileExistsError(OUT)
(OUT/'source').mkdir(parents=True)
files=['runtime.py','demo.py','geometry.py','hatching.py','render.py','viewer.py','viewer.html','region_tools.py','screen_selection.py','selection_draft.py','scene_catalog.py','catalog_demo.py']
for name in files:shutil.copy2(Path(__file__).with_name(name),OUT/'source'/name)
for scene in ('chair','lego','drums'):
 src=U/'assets/edited' if scene=='lego' else U/'catalog_assets'/scene
 dest=OUT/'assets'/scene;shutil.copytree(src,dest)
 if scene=='lego':
  meta=json.loads((dest/'asset.json').read_text());meta['selected_region']=4;js(dest/'asset.json',meta)
shutil.copytree(U/'assets/original',OUT/'assets/lego_original')
shutil.copy2(U/'SELECTION_RECIPE.json',OUT/'SELECTION_RECIPE.json')
js(OUT/'CATALOG.json',dict(schema='partwise_scene_catalog_v1',default_scene='lego',scenes={s:dict(label=s.capitalize(),asset=f'assets/{s}') for s in ('chair','lego','drums')}))
js(OUT/'AUTHORING_CATALOG.json',dict(schema='partwise_scene_catalog_v1',default_scene='lego',scenes={s:dict(label=s.capitalize(),asset='assets/lego_original' if s=='lego' else f'assets/{s}') for s in ('chair','lego','drums')}))
preview=OUT/'previews';preview.mkdir()
for folder in (U/'media',U/'selection'):
 for f in folder.iterdir():
  if f.suffix in ('.png','.mkv'):shutil.copy2(f,preview/f.name)
for scene in ('chair','drums'):shutil.copy2(U/f'catalog_reference/{scene}/frame_000_image.png',preview/f'{scene}.png')
shutil.copy2(U/'renders/static_edited/frame_000_image.png',preview/'lego.png')
deps=json.loads((U/'DEPENDENCIES.json').read_text())
needed=('numpy','scipy','Pillow','open3d')
(OUT/'requirements.txt').write_text(''.join(f'{k}=={v}\n' for k,v in deps['packages'].items() if k in needed))
js(OUT/'PORTABLE_DEMO.json',dict(schema='partwise_catalog_package_v1',scenes=['chair','lego','drums'],created_utc=now(),source_unit='unit_008',original_models=json.loads((U/'SCOPE.json').read_text())['originals'],saved_asset_render_requires_original_inputs=False,quality='partial exploratory proxies',output_rule='new outputs inside this relocated package only'))
script='''#!/usr/bin/env bash
set -eu
DEMO_PACKAGE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -z "${DEMO_PY:-}" ]; then
 DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
 if [ ! -x "$DEMO_PY" ]; then DEMO_PY=$(command -v python3); fi
fi
DEMO_COMMAND=${1:-preview}
if [ "$#" -gt 0 ]; then shift; fi
DEMO_STAMP=$(date +%Y%m%d_%H%M%S)_$$
exec "$DEMO_PY" "$DEMO_PACKAGE/source/catalog_demo.py" "$DEMO_COMMAND" --catalog "$DEMO_PACKAGE/${DEMO_CATALOG:-CATALOG.json}" --output "$DEMO_PACKAGE/runs/${DEMO_COMMAND}_$DEMO_STAMP" "$@"
'''
(OUT/'run.sh').write_text(script);os.chmod(OUT/'run.sh',0o755)
shutil.copy2('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md',OUT/'README_ZH.md')
print(OUT)
