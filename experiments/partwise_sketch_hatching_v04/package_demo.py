"""Assemble a relocatable saved-asset demo; packaging is not scientific sealing."""
import runtime
from runtime import js,now,sha
from pathlib import Path
import argparse
import json
import shutil
import os

def package(unit):
    unit=Path(unit);out=unit/'portable_demo'
    if out.exists():raise FileExistsError(out)
    out.mkdir();(out/'source').mkdir()
    for p in Path(__file__).parent.iterdir():
        if p.suffix in ('.py','.cpp','.html'):shutil.copy2(p,out/'source'/p.name)
    shutil.copytree(unit/'assets',out/'assets')
    previews=out/'previews';previews.mkdir()
    for p in (unit/'media').iterdir():
        if p.suffix in ('.png','.mkv'):shutil.copy2(p,previews/p.name)
    shutil.copy2(unit/'renders/first/frame_000_image.png',previews/'first_hatch.png')
    protocol=json.loads((unit/'PROTOCOL.json').read_text())
    first_view=protocol['static_cameras'][0]['view']
    shutil.copy2(unit/f'proxy/source_{first_view}.png',previews/'source_model_rgb.png')
    deps=json.loads((unit/'DEPENDENCIES.json').read_text())
    (out/'requirements.txt').write_text(''.join(f'{k}=={v}\n' for k,v in deps['packages'].items()))
    protocol=json.loads((unit/'PROTOCOL.json').read_text())
    js(out/'PORTABLE_DEMO.json',dict(scene=protocol['scene'],created_utc=now(),original_model_sha256=protocol['original']['sha256'],
                                   saved_asset_render_requires_original_inputs=False,
                                   quality='partial exploratory proxy',source=unit.name+' source snapshot',
                                   output_rule='portable code writes only inside this package directory'))
    shell='''#!/usr/bin/env bash
set -eu
DEMO_PACKAGE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -z "${DEMO_PY:-}" ]; then
  DEMO_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
  if [ ! -x "$DEMO_PY" ]; then DEMO_PY=$(command -v python3); fi
fi
DEMO_STAMP=$(date +%Y%m%d_%H%M%S)
case "${1:-preview}" in
  preview) exec "$DEMO_PY" "$DEMO_PACKAGE/source/demo.py" render --scene __SCENE__ --asset "$DEMO_PACKAGE/assets/${DEMO_ASSET:-edited}" --view train_r_32 --output "$DEMO_PACKAGE/runs/preview_$DEMO_STAMP" ;;
  viewer) exec "$DEMO_PY" "$DEMO_PACKAGE/source/viewer.py" --asset "$DEMO_PACKAGE/assets/${DEMO_ASSET:-baseline}" --output "$DEMO_PACKAGE/runs/viewer_$DEMO_STAMP" --port "${DEMO_PORT:-8765}" ;;
  orbit|zoom) exec "$DEMO_PY" "$DEMO_PACKAGE/source/demo.py" render --scene __SCENE__ --asset "$DEMO_PACKAGE/assets/${DEMO_ASSET:-edited}" --trajectory "$1" --output "$DEMO_PACKAGE/runs/${1}_$DEMO_STAMP" ;;
  *) printf '%s\n' 'Usage: ./run.sh [preview|viewer|orbit|zoom]'; exit 2 ;;
esac
'''
    (out/'run.sh').write_text(shell.replace('__SCENE__',protocol['scene']).replace('train_r_32',first_view));os.chmod(out/'run.sh',0o755)
    readme=Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').read_text()
    prefix='''# Portable quick start

此包可搬移到其他目录；保存资产的渲染不依赖原始 PLY 或旧工作树。已安装 Python 依赖时，在包目录运行：

```bash
./run.sh preview
./run.sh viewer
```

可用 `DEMO_PY=/path/to/python ./run.sh viewer` 指定解释器。浏览器打开终端显示的本机 URL。新输出只保存在包内 `runs/`。本机现有解释器已实际冷加载运行；其他操作系统未测试。依赖见 `requirements.txt`，未捆绑整个 Python 环境。

下方文档中的原工作树路径用于原机复现；搬移后直接使用上述启动器，或 `source/demo.py` 与包内 `assets/`。

'''
    (out/'README_ZH.md').write_text(prefix+readme)
    print(out,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);package(p.parse_args().unit)
