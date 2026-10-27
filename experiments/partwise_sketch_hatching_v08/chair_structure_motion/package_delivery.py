"""Package completed evidence without rewriting any frozen science or old units."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil
from structure_motion import verify_unit
UNIT=runtime.ROOT/'units/unit_008';CODE=Path(__file__).parent
def main():
    verify_unit(UNIT);delivery=UNIT/'delivery';evidence=delivery/'evidence';evidence.mkdir(exist_ok=True)
    for name in ('renders','cold_reload','failed_attempts','media'):
        dst=delivery/'media' if name=='media' else evidence/name
        shutil.copytree(UNIT/name,dst)
    for p in UNIT.iterdir():
        if p.is_file() and p.suffix in ('.json','.md'):shutil.copy2(p,evidence/p.name)
    logs=evidence/'logs';logs.mkdir(exist_ok=True)
    for p in (UNIT/'logs').iterdir():
        if not p.name.startswith('020_package'):shutil.copy2(p,logs/p.name)
    audit=delivery/'audit_code';audit.mkdir(exist_ok=True)
    for p in CODE.iterdir():
        if p.suffix in ('.py','.cpp'):shutil.copy2(p,audit/p.name)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',{p.name:sha(p) for p in CODE.iterdir() if p.suffix in ('.py','.cpp')})
    shutil.copy2(UNIT/'HANDOFF_SOURCE_LOCK.json',evidence/'HANDOFF_SOURCE_LOCK.json')
    manifest={str(p.relative_to(delivery)):sha(p) for p in sorted(delivery.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
    js(delivery/'MANIFEST.json',dict(utc=runtime.now(),files=manifest,scope='Local content manifest, not scientific seal. Packaging command final receipt remains in unit/logs after exit.'))
    for name,h in manifest.items():assert sha(delivery/name)==h
    js(UNIT/'PACKAGE_VERIFICATION.json',dict(files=len(manifest),manifest_sha256=sha(delivery/'MANIFEST.json'),all_hashes_match=True,
        bytes=sum(p.stat().st_size for p in delivery.rglob('*') if p.is_file()),scope='Linux CPU local package; no remote/cross-platform certification'))
    verify_unit(UNIT);print('Packaged and verified',len(manifest),'files',flush=True)
if __name__=='__main__':main()
