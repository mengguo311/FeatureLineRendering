"""Package only actual saved models, sources and validated presentation exports."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import json,shutil,tarfile,importlib.metadata,sys,difflib,subprocess
from presentation_delivery import refresh

unit=OUTPUT_ROOT/'units/unit_012';package=unit/'portable_demo'
assert json.loads((unit/'metrics/COLD_REPLAY.json').read_text())['all_arrays_exact']
assert json.loads((unit/'browser/PRESENTATIONS.json').read_text())['status']=='PASS'
refresh()
shutil.copy2(unit/'PACKAGE_README_ZH.md',package/'README_ZH.md')
previews=package/'previews';previews.mkdir()
for p in (unit/'media').iterdir():
    if p.is_file():shutil.copy2(p,previews/p.name)
for name in ('chair_export_complete.png','ficus_export_complete.png'):
    shutil.copy2(unit/'browser'/name,previews/name)
versions={}
for name in ('numpy','scipy','open3d','Pillow','imageio-ffmpeg'):
    try:versions[name]=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:versions[name]='not installed; existing local ffmpeg fallback tested'
js(package/'TESTED_ENVIRONMENT.json',dict(python=sys.version.split()[0],packages=versions,cpu_affinity=[0,1],gpu=False,dependencies_bundled=False))
js(package/'VALIDATION.json',dict(unit='unit_012',utc=now(),browser_downloads=json.loads((unit/'browser/PRESENTATIONS.json').read_text()),
    cold_replay=[{k:r[k] for k in ('scene','kind','frame_count','all_png_exact','all_arrays_exact')} for r in json.loads((unit/'metrics/COLD_REPLAY.json').read_text())['replays']],
    visual_quality='partial; thin foliage holes and short strokes remain',scientific_seal=False))
js(package/'PACKAGE_FILES.json',dict(files={str(p.relative_to(package)):sha(p) for p in sorted(package.rglob('*'))
    if p.is_file() and 'runs' not in p.relative_to(package).parts}))
archive=unit/'portable_demo.tar.gz'
def exclude(info):
    return None if any(x in ('runs','__pycache__') for x in Path(info.name).parts) else info
with tarfile.open(archive,'w:gz') as tar:tar.add(package,arcname='portable_demo',filter=exclude)
destination=unit/'final_archive';destination.mkdir()
with tarfile.open(archive,'r:gz') as tar:tar.extractall(destination)
extracted=destination/'portable_demo';manifest=json.loads((extracted/'PACKAGE_FILES.json').read_text())
assert all(sha(extracted/name)==digest for name,digest in manifest['files'].items())
js(unit/'metrics/PACKAGE_INTEGRITY.json',dict(archive=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,
    extracted_files_verified=len(manifest['files']),all_exact=True,extracted=str(extracted)))
snapshot=unit/'source_snapshot';shutil.copytree(Path(__file__).parent,snapshot,ignore=shutil.ignore_patterns('__pycache__'))
before=unit/'source_before';diff=[]
for name in sorted({p.name for p in before.iterdir() if p.is_file()}|{p.name for p in snapshot.iterdir() if p.is_file()}):
    old=(before/name).read_text().splitlines(keepends=True) if (before/name).is_file() else []
    new=(snapshot/name).read_text().splitlines(keepends=True) if (snapshot/name).is_file() else []
    diff.extend(difflib.unified_diff(old,new,fromfile='before/'+name,tofile='after/'+name))
(unit/'UNIT012_DIFF.patch').write_text(''.join(diff))
js(unit/'SOURCE_SNAPSHOT.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    source_files={p.name:sha(p) for p in snapshot.iterdir() if p.is_file()},inherited_dirty_worktree=True))
print(json.dumps({'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'verified_files':len(manifest['files'])}))
