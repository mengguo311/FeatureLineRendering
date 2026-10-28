"""Replay frozen saved policies to a fresh v09 HDD folder, with optional exact readback."""
import runtime
from runtime import js,sha
import argparse,json,shutil
from pathlib import Path
import numpy as np
import run_h2 as science
from linked_asset import npz

def main():
    p=argparse.ArgumentParser();p.add_argument('--from-unit',type=Path,default=science.UNIT);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--view',choices=science.VIEWS,default='orbit_196_36_5.1');p.add_argument('--regenerate',action='store_true');a=p.parse_args()
    source=a.from_unit.resolve();out=runtime.output_guard(a.out);out.mkdir(parents=True,exist_ok=False)
    for folder in (('inputs',) if a.regenerate else ('inputs','paths')):shutil.copytree(source/folder,out/folder)
    names=('GUIDE.npz','DECISION.json','BUILD_MATCH.json') if a.regenerate else ('GUIDE.npz','FIELDS.npz','PROTOCOL.json','DECISION.json','SOURCE_LOCK.json','INPUT_LOCK.json','DERIVED_LOCK.json','BUILD_MATCH.json')
    for name in names:
        shutil.copyfile(source/name,out/name)
    science.UNIT=out;science.ASSET=out/'inputs/assets/on'
    regenerated=[]
    if a.regenerate:
        science.derive()
        for file in sorted((source/'paths').glob('*.npz')):
            old=npz(file);new=npz(out/'paths'/file.name)
            assert old.keys()==new.keys()
            for key in old:np.testing.assert_array_equal(old[key],new[key])
            regenerated.append(file.name)
    science.render_view(a.view)
    comparisons=[]
    for mode in ('natural','matched'):
        for arm in science.ARMS:
            name=f'renders/{a.view}/{mode}/{arm}/FRAME.npz';old=npz(source/name);new=npz(out/name)
            assert old.keys()==new.keys()
            for key in old:np.testing.assert_array_equal(old[key],new[key])
            comparisons.append(dict(mode=mode,arm=arm,arrays_exact=list(old)))
    js(out/'REPLAY_CHECK.json',dict(source_unit=str(source),source_decision_sha256=sha(source/'DECISION.json'),view=a.view,comparisons=comparisons,regenerated_paths_exact=regenerated,
        scope='Fresh-process load and render of saved object-space policy paths. Same-camera originalGS caches reused explicitly, not a cold source recomputation.'))
    print(json.dumps(dict(replay_exact=True,states=len(comparisons))))
if __name__=='__main__':main()
