"""Package verified unit013 assets and real downloads; no old-output writes."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import json,shutil,tarfile,difflib,subprocess
from crosshatch_delivery import refresh
unit=OUTPUT_ROOT/'units/unit_013';package=unit/'portable_demo'
for kind in ('orbit','zoom'):
    report=json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text())
    assert report['all_png_exact'] and report['all_arrays_exact']
assert json.loads((unit/'browser/BROWSER_VALIDATION.json').read_text())['status']=='PASS'
refresh()
readme=Path('docs/partwise_sketch_hatching_v04/UNIT013_DEMO_README_ZH.md')
shutil.copy2(readme,package/'README_ZH.md');shutil.copy2(readme,unit/'PACKAGE_README_ZH.md')
previews=package/'previews';previews.mkdir()
for file in (unit/'media').iterdir():
    if file.is_file():shutil.copy2(file,previews/file.name)
for name in ('02_cross_enabled.png','03_export_complete.png'):
    shutil.copy2(unit/'browser'/name,previews/name)
js(package/'VALIDATION.json',dict(unit='unit_013',utc=now(),
    paths=json.loads((unit/'metrics/PATHS.json').read_text()),
    browser=json.loads((unit/'browser/BROWSER_VALIDATION.json').read_text()),
    cold_replay={kind:{k:json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text())[k]
        for k in ('scene','frame_count','all_png_exact','all_arrays_exact')} for kind in ('orbit','zoom')},
    visual_quality='partial; cross layer is controllable and may be dense; proxy defects unchanged',scientific_seal=False))
js(package/'PACKAGE_FILES.json',dict(files={str(p.relative_to(package)):sha(p) for p in sorted(package.rglob('*'))
    if p.is_file() and 'runs' not in p.relative_to(package).parts and p.name!='PACKAGE_FILES.json'}))
archive=unit/'portable_demo.tar.gz'
def exclude(info):return None if any(x in ('runs','__pycache__') for x in Path(info.name).parts) else info
with tarfile.open(archive,'w:gz') as tar:tar.add(package,arcname='portable_demo',filter=exclude)
destination=unit/'final_archive';destination.mkdir()
with tarfile.open(archive,'r:gz') as tar:tar.extractall(destination)
extracted=destination/'portable_demo';manifest=json.loads((extracted/'PACKAGE_FILES.json').read_text())
assert all(sha(extracted/name)==digest for name,digest in manifest['files'].items())
js(unit/'metrics/PACKAGE_INTEGRITY.json',dict(archive='portable_demo.tar.gz',sha256=sha(archive),bytes=archive.stat().st_size,
    extracted_files_verified=len(manifest['files']),all_exact=True,extracted=str(extracted)))
print(json.dumps(dict(archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,verified_files=len(manifest['files']))))
