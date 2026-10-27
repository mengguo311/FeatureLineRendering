"""Seal content inventory, preserve raw failures, and verify package copies."""
import runtime
from runtime import sha,js
from pathlib import Path
import json
import shutil
from PIL import Image

UNIT=runtime.ROOT/'units/unit_001'
CODE=Path(__file__).parent

def ledger():
    completed=[];missing=[]
    for path in sorted((UNIT/'logs').glob('*.json')):
        if path.name.endswith('.start.json'):continue
        completed.append(dict(receipt=str(path.relative_to(UNIT)),**json.loads(path.read_text())))
    for start in sorted((UNIT/'logs').glob('*.start.json')):
        end=start.with_name(start.name.replace('.start.json','.json'))
        if not end.exists():missing.append(dict(start=str(start.relative_to(UNIT)),final_receipt=str(end.relative_to(UNIT)),child_returncode='UNKNOWN'))
    js(UNIT/'EXECUTION_RECORDS.json',dict(completed=completed,missing_final_receipts=missing,
        outer_tool_failure=json.loads((UNIT/'INTERRUPTION_view2.json').read_text()),
        rule='Recorded actual child codes only; finalizer may be pending until its wrapper receipt is written. Outer 143 never becomes zero.'))

def main():
    for path,h in json.loads((UNIT/'INPUT_LOCK.json').read_text()).items():assert sha(path)==h,path
    lock=json.loads((UNIT/'SOURCE_LOCK.json').read_text())
    for name,h in lock['files'].items():assert sha(CODE/name)==h and sha(UNIT/'delivery/code'/name)==h
    assert json.loads((UNIT/'logs/002_tdd_red.json').read_text())['child_returncode']==1
    for name in ('003_tdd_green','010_audit','011_cold_spacing','012_cold_paper','013_query','014_finish'):
        assert json.loads((UNIT/'logs'/(name+'.json')).read_text())['child_returncode']==0,name
    assert not (UNIT/'logs/009_view2.json').exists()
    ledger()
    report=(UNIT/'REPORT_ZH.md').read_text()
    docs=CODE.parents[2]/'docs/partwise_sketch_hatching_v08/unit_001.md'
    docs.write_text(report.replace('(ALL_VIEWS.png)','('+str(UNIT/'ALL_VIEWS.png')+')').replace('(delivery/README_ZH.md)','('+str(UNIT/'delivery/README_ZH.md')+')'))
    evidence=UNIT/'delivery/evidence'
    (evidence/'REPORT_ZH.md').write_text(report.replace('(delivery/README_ZH.md)','(../README_ZH.md)'))
    for name in ('STATUS.json','NEXT.json','AUDIT.json','EXECUTION_RECORDS.json','INPUT_LOCK.json','FINAL_VERIFICATION.json'):
        shutil.copy2(UNIT/name,evidence/name)
    handoff={f.name:sha(f) for f in CODE.iterdir() if f.is_file() and f.name not in lock['files']}
    js(UNIT/'HANDOFF_FINAL_SOURCE_LOCK.json',handoff)
    destination=UNIT/'delivery/handoff_source';destination.mkdir(exist_ok=True)
    for name,h in handoff.items():
        shutil.copy2(CODE/name,destination/name);assert sha(destination/name)==h
    shutil.copy2(UNIT/'HANDOFF_FINAL_SOURCE_LOCK.json',evidence/'HANDOFF_FINAL_SOURCE_LOCK.json')
    frameproof=evidence/'source_witnesses';frameproof.mkdir(exist_ok=True)
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    for c in p['cameras']:
        folder=frameproof/c['view'];folder.mkdir(exist_ok=True)
        for name in ('TRACE.npz','SOURCE_WITNESS.npz','RENDER_RECEIPT.json'):
            shutil.copy2(UNIT/'renders'/c['view']/'baseline'/name,folder/name)
        shutil.copy2(UNIT/'renders'/c['view']/'paper_half/SOURCE_WITNESS.npz',folder/'PAPER_HALF_WITNESS.npz')
    package=UNIT/'delivery'
    files={str(f.relative_to(package)):sha(f) for f in sorted(package.rglob('*')) if f.is_file() and f.name!='MANIFEST.json'}
    js(package/'MANIFEST.json',dict(files=files,scope='Content integrity for this actual Chair package; not scientific acceptance or source ownership certification.'))
    for name,h in files.items():assert sha(package/name)==h,name
    decoded=[]
    for f in sorted(package.rglob('*.png')):
        with Image.open(f) as im:im.load()
        decoded.append(str(f.relative_to(package)))
    total=sum(f.stat().st_size for f in UNIT.rglob('*') if f.is_file())
    assert total<20*2**30
    js(UNIT/'PACKAGE_VERIFICATION.json',dict(manifest_sha256=sha(package/'MANIFEST.json'),verified_content_files=len(files),
        decoded_package_pngs=decoded,unit_bytes=total,source_worktree_and_package_locked_files_equal=len(lock['files']),
        old_locked_inputs_unchanged=True,decision_unchanged=True,outer143_and_UNKNOWN_preserved=True,
        platform='Local Linux CPU verified; remote transfer and cross-platform acceptance not asserted'))
    print(json.dumps(dict(files=len(files),package_pngs=len(decoded),unit_MiB=total/2**20,manifest_sha256=sha(package/'MANIFEST.json'))))

if __name__=='__main__':main()
