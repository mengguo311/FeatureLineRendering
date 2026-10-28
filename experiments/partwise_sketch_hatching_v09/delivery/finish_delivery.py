"""Close only unit005 metadata after actual delivery checks have completed."""
import runtime
from runtime import ROOT, UNIT, WORK, CODE, js, sha, now
from catalog import file_record, check_records
import argparse
import json
import shutil
import subprocess
from pathlib import Path

def read(p):return json.loads(Path(p).read_text())

def finish():
    audit=read(UNIT/'AUDIT.json')
    assert audit['delivery_integrity']=='PASS' and not audit['errors']
    assert read(UNIT/'logs/005_audit.json')['child_returncode']==0
    assert sha(UNIT/'DECISION.json')==read(UNIT/'PROTOCOL.json')['decision_sha256']
    prior=read(ROOT/'DELIVERY_STATUS.json')
    assert prior['stage']=='assembled_pending_integrity_audit'
    js(UNIT/'ASSEMBLED_STATUS.json',prior)
    status=dict(execution_state='completed',stage='final_in_place_delivery_and_integrity_audit_complete',
        scientific_verdict='PARTIAL: H2 S limited authored style-margin capability; S coverage costs and D negative result retained. H1 conditional temporal differences only. No whole-object or Gaussian superiority.',
        gaussian_link_progress='No new Gaussian experiment. Original256690 PLY rows/order/geometry/covariance/opacity/fullSH and UNKNOWN170281 remain byte-identical through existing input locks; seatS27873 unchanged. Upper-back/guide proxy-only. Historical original-GS cold checks indexed, not repeated.',
        H2='RUN previously: unit001 U/S/D/sham five-view static; unit00339-camera/37-frame four-policy output. No new unit005 run.',
        H1='RUN previously: unit00225-frame azimuth and unit00413-frame elevation; label-conditioned, unequal coverage/generators.',
        D='RUN previously; no added whole-object benefit; do not promote default',second_object='NOT_RUN',new_interface='NOT_RUN',
        default_reference='Original U retained; S optional authored operation; D negative/scoped result',
        packaging='In-place local dependency package; old units stay at absolute paths. No archive or cross-machine portability claim.',
        artifacts=['PROTOCOL.json','INPUT_MANIFEST.json','SOURCE_MANIFEST.json','CAMERA_REFERENCES.json','MEDIA_INDEX.json',
                   'COMMANDS.json','DEPENDENCIES.json','FAILURE_INDEX.json','AUDIT.json','REPORT_ZH.md','NEXT.json','source',
                   '../../DEMO_README_ZH.md','../../DELIVERY_STATUS.json','../../DELIVERY_CONTENTS.json'],
        commands_tests=['logs/001_RED.json','logs/002_GREEN.json','logs/003_freeze.json','logs/004_assemble.json','logs/005_audit.json'],
        checks=dict(immutable_files=3800,media_files=18,animated_files=6,animated_frames=150,static_images=12,
                    historical_lock_maps=9,linked_original_assets=4,readme_links=42,unit_tests=2,expected_RED_rc=1,GREEN_rc=0),
        scientific_runs_this_unit=0,cold_renders_this_unit=0,new_scientific_metrics=0,
        preserved_failures='See FAILURE_INDEX; S4 losses,D36of37 losses,nonzero FAR,143UNKNOWN,failed B0,mislabelled conventional reference,holes/open return/high rear zero and v08 failures all retained.',
        blockers=[],limitations=['Existing absolute worktree and unit paths required','No independent perceptual preference study',
        'File identity/decoding does not prove scientific superiority','Parent verification pending'],
        decision_sha256=sha(UNIT/'DECISION.json'),parent_verification='pending independent parent read',scientific_seal=False,
        resources=dict(affinity=sorted(runtime.os.sched_getaffinity(0)),numerical_threads=1,CUDA_VISIBLE_DEVICES='',serial=True),
        completed_utc=now(),next='stop',commit_metadata='COMMIT.json after actual local commit',final_closure='FINAL_MANIFEST.json and FINAL_READBACK.json after metadata/commit')
    js(UNIT/'STATUS.json',status)
    root=dict(status,unit='unit_005',entry_readme=str(ROOT/'DEMO_README_ZH.md'),
              unit_status=str(UNIT/'STATUS.json'),contents_manifest=str(ROOT/'DELIVERY_CONTENTS.json'),
              final_manifest=str(UNIT/'FINAL_MANIFEST.json'),final_readback=str(UNIT/'FINAL_READBACK.json'),
              artifact_base=str(UNIT),deadline='scientific wrap15:45/hard16:00 JST; no new science after15:20')
    # Replace only this unit's explicit pending root placeholder. Preserve it above.
    runtime.guard(ROOT/'DELIVERY_STATUS.json').write_text(json.dumps(root,ensure_ascii=False,indent=2)+'\n')
    js(UNIT/'NEXT.json',dict(action='stop',
        recommended_next_step='Hand the completed joint delivery to the parent for independent readback; no further autonomous science or replay-only unit in this authorization window.',
        why='All selected unit005 delivery work is complete.15:20 new-science cutoff has passed; no remaining independent in-scope execution route. Stop is not an aesthetic gate or a claim that all future research is exhausted. Preserve15:45 wrap and16:00 hard stop.'))
    report='''# Unit005：最终联合交付

**交付工程完成，科学结论保持PARTIAL。** 已生成根级DEMO_README_ZH.md、DELIVERY_STATUS.json和DELIVERY_CONTENTS.json，集中展示H2 U/S/D/sham及两条条件性H1轨迹，保存可追溯命令、依赖、失败索引与原位文件清单。本单元新科学运行、相机、冷渲染和科学指标均为0。

[根级入口](../../DEMO_README_ZH.md) · [交付核验](AUDIT.json) · [失败索引](FAILURE_INDEX.json) · [命令](COMMANDS.json) · [依赖](DEPENDENCIES.json)

## 实际交付与验证

父级DECISION未改。评价前冻结PROTOCOL、3800个既有文件的INPUT_MANIFEST、交付源码SOURCE_MANIFEST和相机引用CAMERA_REFERENCES。原位文件包约729.83MB的清单字节包含已有输入、逐帧数组、保存源码、日志、失败和旧v08精选证据；不重新复制多套源PLY或创建大归档。清单排除build/scratch/__pycache__，这些原目录也没有被删除或改写。

18份展示媒体是原文件逐字节副本，保留英文图例。包括H2自然/匹配五相机整图、结构/自身墨层、更正后的传统代理图、37帧四政策影片及完整关键帧；H1方位25帧、抬高13帧的自然/匹配影片、关键帧和分层。6个APNG共150个播放帧全部解码，12张静态媒体也全部解码；这些是保存结果的副本，不是150个新相机或独立样本。

实际TDD：001_RED因尚缺catalog模块rc1；002_GREEN两项测试rc0，检查损坏/缺失证据拒绝和DECISION/旧单元/路径逃逸写保护。003冻结、004组装、005审计实际rc0，串行。审计重新核对3800个冻结文件、28个当时交付文件、9份历史输入/源码/派生锁、4个原PLY及绑定链接、42个README链接；没有缺失或哈希差异。旧科学脚本、编译器、renderer和数值模块没有执行或导入。最终元数据与本地提交另作交付闭合记录，不伪造本次审计的自回执。

本会话只读阶段已检查H2完整自然对照、unit004关键帧及027/006原尺寸图。交付阶段又目视检查匹配五相机整图、H2独立结构/自身墨层、H1方位关键帧。确认S效果局部，D上缘弯曲及必要内部变稀、弱后侧压缩、高后侧结构不可用、开放返回/孔洞仍在。没有独立感知偏好或真人播放认证。

## 科学边界没有升级

H2存在7次BUILD可见同面交叉，U保留原裁剪并恢复原AA墨，所有臂完整169段结构ON，guide只承担人工风格作用。S有局部留白能力，但动态4个仰角必要覆盖下降；D在37帧中36帧覆盖低于U。S与U_on_S在同一保留支持的自身墨跌落相同，不能宣称时序改善。静态五相机和动态39相机结论均保持PARTIAL。

H1方位及抬高两轨迹已实际比较合理二维B0与原U三维B1。本单元只索引原结果。抬高的每共同像素误差B0/B1为0.078717/0.048731，但共同支持79.762%，B1源可见却无自身墨累计71.4868px；不能归为纯锚定或整物体赢家。Gaussian连接仍限原行来源与座面S，上背/guide为proxy-only。

保留匹配FAR非零、错误零FAR审计rc1、unit003143/UNKNOWN缺失最终回执、初始B0漏种子及启动/路径失败、误标传统proxy及更正，以及v08开放返回、孔洞、高后侧零合成增量、3次自身墨跌落/1次重现、2.562698秒调度偏差。没有扩掩码或改写失败门槛。第二对象、新界面NOT_RUN；D和两条H1则是此前RUN，不互相替代。

## 使用范围与收尾

原位包要求原绝对路径、已有只读Python及工作树源码存在。unit003/004 guard固定写入各自新命名目录，SOURCE_LOCK还引用原工作树；没有为搬迁而改旧guard。README命令列出后来复现可用的新输出名，COMMANDS保存真实已运行的旧argv/rc0。本单元不重复冷核验，避免把回放包装成新科学单元。

源码及文档只写授权v09分支，新媒体/清单/回执只写v09 HDD。两核亲和、单线程、CUDA空、串行；无GPU/训练/安装/下载/嵌套模型/push/merge。工程核验不等于研究胜利，父级独立核验仍待完成。

NEXT=stop：所选联合交付已完成，15:20后不再启新科学单元，当前授权范围没有剩余独立执行问题；不是因为局部美学失败或声称未来研究路线耗尽。交付在15:45前收尾，保持16:00硬停。
'''
    runtime.write(UNIT/'REPORT_ZH.md',report)
    # Freeze post-audit reporting code separately; leave original SOURCE_MANIFEST intact.
    sources=[]
    for src in sorted(CODE.glob('*.py')):
        dst=runtime.guard(UNIT/'source'/src.name);dst.parent.mkdir(exist_ok=True)
        if dst.exists():raise FileExistsError(dst)
        shutil.copyfile(src,dst)
        sources.extend([file_record(src,'worktree_delivery_source'),file_record(dst,'saved_delivery_source')])
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files=sources,scope='Includes post-audit finish script; original pre-audit SOURCE_MANIFEST remains unchanged.'))
    print(json.dumps(dict(state='completed',scientific_verdict='PARTIAL',next='stop',new_science=0)),flush=True)

def close():
    audit=read(UNIT/'AUDIT.json');status=read(UNIT/'STATUS.json')
    assert status['execution_state']=='completed' and audit['delivery_integrity']=='PASS'
    errors=check_records(read(UNIT/'INPUT_MANIFEST.json')['files'])
    errors+=check_records(read(UNIT/'HANDOFF_SOURCE_LOCK.json')['files'])
    assert not errors, errors
    assert sha(ROOT/'DEMO_README_ZH.md')==sha(WORK/'docs/partwise_sketch_hatching_v09/DEMO_README_ZH.md')
    assert sha(UNIT/'DECISION.json')==status['decision_sha256']
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=WORK,text=True).strip()
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True)
    assert branch=='partwise-sketch-hatching-gaussian-link-v09' and not dirty
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip()
    js(UNIT/'COMMIT.json',dict(commit=commit,branch=branch,worktree_clean=True,push=False,merge=False,utc=now()))
    receipts=[]
    for p in sorted((UNIT/'logs').glob('*.json')):
        if p.name.endswith('.start.json'):continue
        r=read(p);expected=1 if p.name=='001_RED.json' else 0
        assert r['child_returncode']==expected,(p,r)
        receipts.append(dict(path=str(p),child_returncode=r['child_returncode'],started_utc=r['started_utc'],finished_utc=r['finished_utc']))
    for prev,nxt in zip(receipts,receipts[1:]):
        assert prev['finished_utc']<=nxt['started_utc'],(prev,nxt)
    for name in status['artifacts']:assert (UNIT/name).exists(),name
    records=[]
    for p in sorted(UNIT.rglob('*')):
        if p.is_file() and 'scratch' not in p.parts and 'logs' not in p.parts:
            records.append(file_record(p,'final_unit005'))
    for name in ('DEMO_README_ZH.md','DELIVERY_STATUS.json','DELIVERY_CONTENTS.json'):
        records.append(file_record(ROOT/name,'root_delivery'))
    records.extend(file_record(Path(r['path']),'completed_unit005_receipt') for r in receipts)
    js(UNIT/'FINAL_MANIFEST.json',dict(files=records,
        exclusions='Self manifest, FINAL_READBACK and live close command log/receipt cannot contain their own hashes; these remain outside this manifest. All historical logs are covered by INPUT_MANIFEST.',utc=now()))
    assert not check_records(records)
    js(UNIT/'FINAL_READBACK.json',dict(utc=now(),execution_state='completed',scientific_verdict='PARTIAL unchanged',
        all_frozen_3800_files_unchanged=True,parent_decision_unchanged=True,saved_delivery_source_exact=True,
        root_readme_matches_worktree=True,final_manifest_sha256=sha(UNIT/'FINAL_MANIFEST.json'),
        finalized_files_checked=len(records),completed_receipts=receipts,actual_serial=True,
        self_receipt='Actual close child rc is written by wrapper only after this command exits; not synthesized here.',
        commit=commit,branch=branch,worktree_clean=True,parent_verification='pending independent parent read'))
    print(json.dumps(dict(finalized_files=len(records),commit=commit,state='completed',science='PARTIAL')),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['finish','close']);a=p.parse_args();globals()[a.stage]()
