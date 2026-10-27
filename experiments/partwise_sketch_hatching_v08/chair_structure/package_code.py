import runtime
from runtime import sha,js
from pathlib import Path
import shutil,json
UNIT=runtime.ROOT/'units/unit_007';CODE=Path(__file__).parent
def main():
    names=['runtime.py','base_model.py','geometry.py','hatching.py','render.py','display_settings.py','membership.py','hybrid.py','link_renderer.py','sh_utils_cpu.py','source_ewa_baseline.cpp','source_ewa_link.cpp','linked_asset.py','whole_asset.py','parts_asset.py','structure.py','structure_asset.py']
    source=json.loads((UNIT/'SOURCE_LOCK.json').read_text());out=UNIT/'delivery/code';out.mkdir(exist_ok=True)
    for name in names:
        assert sha(CODE/name)==source[name];shutil.copy2(CODE/name,out/name);assert sha(out/name)==source[name]
    js(UNIT/'PACKAGE_SOURCE_CHECK.json',{name:sha(out/name) for name in names})
    print('Copied verified package modules',len(names))
if __name__=='__main__':main()
