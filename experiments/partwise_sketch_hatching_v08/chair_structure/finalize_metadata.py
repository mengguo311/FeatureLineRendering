"""Package completed evidence; never alter scientific locks or old results."""
import runtime
from runtime import js,sha
from pathlib import Path
import argparse,json,shutil,datetime
from PIL import Image
UNIT=runtime.ROOT/'units/unit_007';CODE=Path(__file__).parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);a=p.parse_args()
    assert len(a.commit)==40
    lock=json.loads((UNIT/'SOURCE_LOCK.json').read_text())
    for name,h in lock.items():assert sha(CODE/name)==h
    status=json.loads((UNIT/'STATUS.json').read_text())
    status.update(local_commit=a.commit,completed_utc=runtime.now(),metadata_snapshot='Final packaging command has its own raw receipt after completion; last_engine_exit_code remains parent-owned UNKNOWN')
    status['git_staging_recovery']=dict(initial_add_returncode=1,cause='existing sparse-checkout excludes new unit paths',recovery='git add --sparse restricted to this unit source/doc paths; sparse configuration unchanged',empty_index_check_not_substantive=True)
    js(UNIT/'STATUS.json',status)
    report_path=UNIT/'REPORT_ZH.md'
    report_path.write_text(report_path.read_text()+'\n交付补记：本地提交`'+a.commit+'`，无push/merge。首次git add因既有稀疏检出规则rc1；022仅对本轮新路径使用--sparse恢复，未修改稀疏配置。021空索引检查不作为实质验证，023对实际暂存内容检查rc0。原失败回执保持。\n')
    handoff={p.name:sha(p) for p in CODE.glob('*.py') if p.name not in lock}
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',handoff)
    records={}
    for start in sorted((UNIT/'logs').glob('*.start.json')):
        name=start.name[:-11];end=start.with_name(name+'.json')
        records[name]=json.loads(end.read_text()) if end.exists() else json.loads(start.read_text())
        records[name]['completion_receipt_present']=end.exists()
    js(UNIT/'EXECUTION_RECORDS.json',dict(snapshot_utc=runtime.now(),commands=records,
        note='Missing completion receipt means UNKNOWN, never rc0. This snapshot may precede its own metadata command completion; raw logs remain authoritative. Parent engine rc is separate.'))
    d=UNIT/'delivery';e=d/'evidence';e.mkdir(exist_ok=True)
    for f in UNIT.glob('*.json'):shutil.copy2(f,e/f.name)
    # Localize links in the copied report; preserve scientific text and unit original.
    report=(UNIT/'REPORT_ZH.md').read_text().replace('(media/','(../media/').replace('(delivery/README_ZH.md)','(../README_ZH.md)')
    (e/'REPORT_ZH.md').write_text(report)
    shutil.copy2(UNIT/'AUTHOR_PREVIEW.png',e/'AUTHOR_PREVIEW.png')
    shutil.copytree(UNIT/'media',d/'media',dirs_exist_ok=True)
    shutil.copytree(UNIT/'logs',e/'logs',dirs_exist_ok=True)
    for root in (UNIT/'renders',UNIT/'cold_reload',UNIT/'serial_recovery'):
        for f in sorted(root.rglob('*')):
            if f.is_file() and (f.suffix in ('.json','.npz','.png')) and 'scratch' not in f.parts:
                out=e/f.relative_to(UNIT);out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,out)
    for name in handoff:
        out=d/'audit_code'/name;out.parent.mkdir(exist_ok=True);shutil.copy2(CODE/name,out)
    images={}
    for f in sorted(d.rglob('*.png')):
        im=Image.open(f);im.load();images[str(f.relative_to(d))]=dict(sha256=sha(f),size=list(im.size))
    js(e/'IMAGE_DECODE.json',dict(local_only=True,images=images,frames=len(images),new_video=False))
    js(e/'REPORT_LINK_LOCALIZATION.json',dict(original_sha256=sha(UNIT/'REPORT_ZH.md'),package_sha256=sha(e/'REPORT_ZH.md'),change='Relative links only; original report retained unchanged'))
    manifest={str(f.relative_to(d)):sha(f) for f in sorted(d.rglob('*')) if f.is_file() and f.name!='MANIFEST.json'}
    js(d/'MANIFEST.json',dict(utc=runtime.now(),files=manifest,scientific_seal=False,local_commit=a.commit,
        scope='Self-contained Chair runtime code/data/assets and exact current output evidence; local Linux CPU only. Historical evidence paths are provenance. Manifest is delivery integrity, not scientific acceptance.'))
    for name,h in manifest.items():assert sha(d/name)==h
    size=sum(f.stat().st_size for f in UNIT.rglob('*') if f.is_file());assert size<20*2**30
    js(UNIT/'DELIVERY_VERIFICATION.json',dict(files=len(manifest),all_hashes_equal=True,decoded_package_pngs=len(images),unit_bytes=size,
        decision_sha256=sha(UNIT/'DECISION.json'),source_lock_sha256=sha(UNIT/'SOURCE_LOCK.json'),manifest_sha256=sha(d/'MANIFEST.json'),
        metadata_command_completion='See original logs/025_finalize_metadata.json after this process returns; not defaulted to zero here.'))
    print('Verified package',len(manifest),'files, decoded',len(images),'PNGs; unit bytes',size)
if __name__=='__main__':main()
