import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil,subprocess
from structure_motion import verify_unit
UNIT=runtime.ROOT/'units/unit_008';CODE=Path(__file__).parent
def main():
    verify_unit(UNIT)
    revision=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True)
    js(UNIT/'GIT_REVISION.json',dict(argv=['git','rev-parse','HEAD'],returncode=revision.returncode,stdout=revision.stdout,stderr=revision.stderr))
    revision.check_returncode();commit=revision.stdout.strip()
    deviation=dict(description='During final metadata preparation an accidental placeholder was created outside the authorized worktree, then immediately deleted and its newly created empty directory removed.',
        path='/home/u00134/3dgs_line/partwise_sketch_hatching_v08/placeholder',content='placeholder\n',
        corrective_action='apply_patch deletion and rmdir of the newly created empty directory; rmdir actual returncode0',
        old_files_modified=False,scientific_outputs_affected=False,scope='Filesystem scope deviation retained; not a fully compliant path-history claim')
    assert not Path(deviation['path']).exists() and not Path(deviation['path']).parent.exists()
    js(UNIT/'PATH_SCOPE_DEVIATION.json',deviation)
    known={f'{i:03d}':(1 if i==1 else 143 if i==7 else 0) for i in range(24)}
    records=[]
    for start in sorted((UNIT/'logs').glob('*.start.json')):
        name=start.name.removesuffix('.start.json');end=UNIT/'logs'/(name+'.json');d=json.loads((end if end.exists() else start).read_text())
        records.append(dict(command=name,actual_tool_exit_code=known.get(name[:3],'UNKNOWN'),wrapper_final_receipt_exists=end.exists(),
            child_returncode=d.get('child_returncode','UNKNOWN'),receipt=str((end if end.exists() else start).relative_to(UNIT)),
            started_utc=d['started_utc'],finished_utc=d.get('finished_utc','UNKNOWN')))
    js(UNIT/'EXECUTION_RECORDS.json',dict(commands=records,git_revision_command='GIT_REVISION.json',
        note='000..023 actual tool exits observed; active024 final receipt is authoritative after completion. 007 remains143/UNKNOWN.'))
    status=json.loads((UNIT/'STATUS.json').read_text());status.update(local_commit=commit,metadata_utc=runtime.now(),
        protocol_compliance='Partial: one transient outside-worktree placeholder creation, removed immediately; scientific source/assets unchanged. Numeric work remained serial.',
        path_scope_deviation='PATH_SCOPE_DEVIATION.json')
    js(UNIT/'STATUS.json',status)
    with (UNIT/'REPORT_ZH.md').open('a') as f:f.write('\n交付补记：本地提交`'+commit+'`，无push/merge。收尾时一次误写在授权工作树外创建了占位文件，立即删除文件及其新建空目录（rmdir rc0）；无旧文件改写、无科学输出影响，但作为路径范围偏差保留于PATH_SCOPE_DEVIATION.json，不能宣称全程路径合规。最终元数据命令回执在完成后另存。\n')
    handoff={p.name:sha(p) for p in CODE.iterdir() if p.suffix in ('.py','.cpp')};js(UNIT/'HANDOFF_SOURCE_LOCK.json',handoff)
    delivery=UNIT/'delivery';evidence=delivery/'evidence'
    for name in ('STATUS.json','REPORT_ZH.md','EXECUTION_RECORDS.json','PATH_SCOPE_DEVIATION.json','HANDOFF_SOURCE_LOCK.json','GIT_REVISION.json'):
        shutil.copy2(UNIT/name,evidence/name)
    for p in CODE.iterdir():
        if p.suffix in ('.py','.cpp'):shutil.copy2(p,delivery/'audit_code'/p.name)
    for p in (UNIT/'logs').iterdir():
        if not p.name.startswith('024_finalize'):shutil.copy2(p,evidence/'logs'/p.name)
    manifest={str(p.relative_to(delivery)):sha(p) for p in sorted(delivery.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
    js(delivery/'MANIFEST.json',dict(utc=runtime.now(),files=manifest,scope='Local content manifest, not scientific seal; active final metadata receipt is external in unit/logs'))
    for name,h in manifest.items():assert sha(delivery/name)==h
    js(UNIT/'PACKAGE_VERIFICATION.json',dict(files=len(manifest),manifest_sha256=sha(delivery/'MANIFEST.json'),all_hashes_match=True,
        bytes=sum(p.stat().st_size for p in delivery.rglob('*') if p.is_file()),local_commit=commit))
    root=json.loads((runtime.ROOT/'DELIVERY_STATUS.json').read_text());root['status']=status;root['package_manifest_sha256']=sha(delivery/'MANIFEST.json')
    js(runtime.ROOT/'DELIVERY_STATUS.json',root);verify_unit(UNIT)
    print('Final package verified:',len(manifest),'files; commit',commit,flush=True)
if __name__=='__main__':main()
