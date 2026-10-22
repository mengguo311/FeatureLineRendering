"""Record finite engineering evidence and retain failures without science claims."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import argparse,datetime,difflib,json,os,shutil,subprocess
from unit023_run import U,PREV,SOURCE,protocol,hashes

def review():
    js(U/'metrics/VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent, not independent human review',
        inspected=['unit022 actual source/proxy/regions/hatch panel and four-view restoration panel','unit022 all orbit frames','unit023 whole-object baseline/edited/restored four views','unit023 newly rendered original-GS/proxy/two-region/hatch panel','actual Firefox restored view and shared-support disabled control','all 12 orbit and 6 zoom frames'],
        positives='Recognizable complete Chair. Seat angle edit is visible; exact restore retains the lighter independently authored back patch. Both snapshots survive cold import and can be edited.',
        negatives=['Seat ripples and front-apron fragmented hatching remain.','Thin legs and decorative structures are incomplete in the model-derived proxy.','Manual seat region has side/rear fragments; back box includes rear faces and is not complete semantic segmentation.','Changed shared-source support still disables seat restoration, even when geometrically distant.','GUI controls extend below the initial viewport; scrolling is still required.'],
        visual_quality='partial',scope='Usability improvement only; no improvement to geometry, semantics or independently measured temporal stability'))
    root=SOURCE.parents[1]
    readings=[OUTPUT_ROOT/'orchestration/BRIEF.md',root/'docs/partwise_sketch_hatching/experiment_outline_v1.md',
        Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/REPORT_ZH.md'),Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/NEXT.json'),
        root/'experiments/partwise_sketch_hatching_v02/run_unit010.py',root/'experiments/partwise_sketch_hatching_v02/run_unit011.py',
        Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_011/STATUS.json'),
        Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p2_v03/experiment_001/REPORT_ZH.md'),Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p2_v03/experiment_001/NEXT.json'),
        root/'experiments/partwise_sketch_hatching_v03/run_comparison.py',root/'experiments/partwise_sketch_hatching_v03/diagnostic.py',PREV/'STATUS.json',PREV/'REPORT_ZH.md',PREV/'NEXT.json']
    js(U/'metrics/READING_REVIEW.json',dict(files={str(p):sha(p) for p in readings},history='P1 latest complete unit010; unit011 has stale running status and no final REPORT/NEXT, remains untouched. P2 ZERO_HEADROOM/UNIDENTIFIABLE is not global method failure.',decision=protocol()['decision']))

def finish():
    p=protocol();package=U/'portable_demo'
    receipts={f.stem.removesuffix('.receipt'):json.loads(f.read_text()) for f in sorted((U/'logs').glob('*.receipt.json'))}
    required=['tdd_red','tdd_red_real','tdd_green','candidate','static','reference','negatives','regressions','stage','cold_browser','media_stage','cold_orbit','cold_zoom','build','check']
    assert all(n in receipts for n in required)
    assert all(r['returncode']==r.get('expected_returncode',0) for r in receipts.values())
    assert json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())['new_process_ZIP_import_restore_PNG_exact']
    assert all(sha(SOURCE/f.name)==sha(f) for f in (package/'source').iterdir() if f.is_file())
    assert all(sha(package/n)==v for n,v in json.loads((package/'PACKAGE_FILES.json').read_text())['files'].items())
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    resources=dict(task_output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False)
    assert resources['task_output_bytes']<20*2**30 and resources['root_free_bytes']>=2**30 and resources['hdd_free_bytes']>=10*2**30 and len(resources['cpu_affinity'])<=2
    js(U/'metrics/RESOURCES_FINAL.json',resources)
    # Check only PIDs recorded by our own browser harness, never foreign state.
    cleanup=[]
    for name in ('browser','cold_browser'):
        data=json.loads((U/name/'CLEANUP.json').read_text())
        for child in data['children']:
            alive=Path('/proc')/str(child['pid'])/'comm'
            cleanup.append(dict(pid=child['pid'],comm=alive.read_text().strip() if alive.exists() else None,exited=not alive.exists()))
    assert all(c['exited'] for c in cleanup)
    js(U/'metrics/OWN_PROCESS_CLEANUP.json',dict(utc=now(),children=cleanup,scope='Only own known viewer/WebDriver PIDs; browser sessions closed and own groups terminated by harness.'))
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(p['started_utc'])).total_seconds()/60
    assert elapsed<55
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],newly_rendered_model='chair',original_PLY_newly_rendered=True,original_gaussians=256690,original_GS_views=4,
        complete_static_states=12,manual_regions=[dict(region=4,faces=2704,source_region=2,kind='inherited two visible rectangles; partial seat'),dict(region=5,faces=3055,source_region=3,kind='world box including hidden back faces')],automatic_semantics=False,
        independent_creation_preserves_restore=True,support_geometry_or_label_change_rejected=True,legacy_snapshots_conservative=True,restore_target_path_bytes_exact=True,restore_all_render_arrays_exact_views=4,
        independently_edited_back_preserved=True,actual_browser_second_region_authoring=True,cold_new_server_browser_import_restore_exact=True,motion_frames=18,lossless_video_decoded_exact_frames=18,mp4_decoded_frames=18,
        cold_replay_PNG_arrays_exact_frames=18,relocated_tar_CLI_restore_and_ZIP_cold_import_exact=True,relocated_motion_replay_exact_frames=18,all_previous_defaults_and_examples_byte_exact=True,
        visual_quality='partial; inherited proxy defects and incomplete manual regions remain',reasoning='A real Chair can retain two independently authored regions across local edits and a saved ZIP. Restoring the seat no longer fails merely because a separate back region was created; unsafe support changes still refuse restoration. Four models remain usable.')
    limits=['旧vanilla GS模型的CPU衍生代理及继承平滑，不是独立实测表面；面/路径ID不是原高斯行号。',
        '部分座面2704面、上部椅背3055面都是人工选区；世界盒包含背面，不是自动语义或完整部件。代理波纹、前沿碎线、薄腿和装饰结构缺失未改进。',
        '支持签名保护目标区域与每个保存可见性mask接受的全部面/顶点，故远处同源区域划分也可能保守失效；没有猜测未保存的局部支持。',
        '旧快照仍保留整张mesh哈希规则；不自动迁移或回填未知的创建时信息。新快照只恢复目标路径、全部样式和统计，不恢复几何。',
        '支持之外的几何可改变当前遮挡，允许恢复不等于跨几何版本图像不变。当前整对象精确比较只针对固定几何和两处独立标签编辑。',
        '当前四视图、固定2px边界带之外变化为0，不抹去unit022 az123的1像素历史残差，不宣称普适无泄漏。',
        '有限GUI操作、18帧完整解码和冷重绘不是独立几何/语义/全时序认证，H1/H2/H5未测试，历史P1 NO_GO/P2不可辨识不变。',
        '首次浏览器外层rc143，主测试返回码UNKNOWN；PASS行为文件和cleanup保留。一次隔离进程的冷会话恢复rc0，不据此确定旧143根因。',
        '仅当前Linux CPU依赖环境验证；包无解释器/依赖二进制/原PLY。数秒每帧，GUI需滚动，不承诺实时或跨平台。']
    next_step='对实际Chair交互延迟做一次小范围剖析，然后优先实现固定相机下墨色编辑的逐区域渲染复用：缓存真实2x采样可见覆盖，修改一个区域时保留其他区域和轮廓，避免错误地用低分辨率层重合成。几何/标签/相机/线宽变化必须失效；冷加载无缓存仍能正确运行。保留四模型默认，实测前后耗时、PNG/数组一致和一次冷会话；若剖析显示收益不足，保留测量并改做可用性整理，不展开参数扫选。'
    status=dict(stage='UNIT_COMPLETE_INDEPENDENT_REGION_RESTORE',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,engineering_execution='PASS_WITH_RETAINED_OUTER_INTERRUPTION',scientific_verdict='H1_H2_H5_NOT_TESTED; ENGINEERING_USABILITY_ONLY',demo_progress=progress,
        artifacts=['PROTOCOL.json','SELECTION_RECIPE.json','assets/seat','assets/two_regions','assets/baseline','assets/edited','assets/restored','assets/shared_support_changed','metrics/STATIC.json','metrics/EXPECTED_REJECTION.json','metrics/REGRESSIONS.json','metrics/VISUAL_REVIEW.json','media/full_object_restore.png','media/source_reference_all_views.png','media/chair_orbit.mp4','media/chair_zoom.mp4','browser/BROWSER_VALIDATION.json','cold_browser/BROWSER_VALIDATION.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','PACKAGE_README_ZH.md','source_snapshot','UNIT023_DIFF.patch','EVIDENCE_SHA256.json'],
        tests=dict(new_dependency_tests=5,inherited_authoring_and_restore_tests=11,legacy_catalog_assets_loaded=11,legacy_default_models_smoke_rendered=4,TDD='Actual real Chair independent creation/cold restore rejected rc1 before implementation, passes after; separate initial import-path setup failure retained.',command_receipts={k:dict(returncode=v['returncode'],path='logs/'+k+'.receipt.json') for k,v in receipts.items()}),
        blockers=[],limitations=limits,retained_interruption=json.loads((U/'logs/BROWSER_OUTER_INTERRUPTION.json').read_text()),engineering_recovery='ENGINEERING_RECOVERY.json',scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,reason='完整对象/局部编辑/冷加载已可运行，四模型已覆盖；下一步减少实际交互等待，比继续堆叠恢复证明或第五模型更直接改善Demo。',estimated_next_minutes=25,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    rows=json.loads((U/'metrics/STATIC.json').read_text())['views']
    table='\n'.join(f"| {r['camera']['azimuth']} | {r['edit_delta']['target_interior']['L1']:.3f} | {r['edit_delta']['boundary_band']['L1']:.3f} | {r['edit_delta']['far_other']['L1']:.3f} | {r['edit_delta']['far_background']['L1']:.3f} | 0 |" for r in rows)
    commands='\n'.join(f"| {k} | {r['returncode']} | {r['seconds']:.3f} |" for k,r in receipts.items())
    report=f'''# Unit023：独立人工区域的跨会话精确恢复

工程 **completed**，视觉质量 **partial**，总耗时约{elapsed:.1f}分钟。真实Chair上新增独立椅背区域后，之前的座面创建快照仍可用于精确恢复；椅背自身墨色编辑、非目标路径、当前相机不变。改变共享支持或目标锚点则拒绝。新增 `chair_two_regions` 可选示例，四模型默认和七个旧示例逐文件保留。

完整阅读BRIEF和851行原始大纲，复核P1最新完成unit010源/报告/NEXT及中断unit011源/STATUS、P2源/报告/NEXT；历史P1 NO_GO和P2不可辨识不改写。实际审阅unit022整对象、原GS对照、全部orbit帧及源码。已有四模型可运行；相比继续微弱平滑收益或加第五模型，本轮修复多区域操作中明确的恢复失效问题。阅读/输入哈希在metrics/READING_REVIEW.json和PROTOCOL.json。

协议SHA `{sha(U/'PROTOCOL.json')}` 在真实TDD和候选之前冻结。源资产 `{ASSET_PATH()}`；原Chair PLY `{p['original']['original_ply']}`，SHA `{p['original']['sha256']}`。本轮CPU SH3/EWA重新渲染原256690高斯四视图，库、adapter和C++源hash核验；不是GT表面或GPU等价声明。

座面沿用两个人工可见矩形的2704面/1577段；第二选区固定世界盒[-.32,-1,.4,.32,1,1.1]，从区域3选3055面/1695段为区域5，包含背面，非自动语义。区域5墨色.45保留，区域4角度95→65→显式恢复。四个预先固定新相机az38/128/218/308、elev28、distance4.9；场景和座面已曝光，不称盲测。

新快照以目标面集合、保存mask的逐面接受集合、被接受面及共享顶点几何为依赖。独立region3→5不会改变座面支持region2/4，因此可恢复。共享region2再次划分会改变旧mask接受含义，仍禁用；不扩张旧mask或迁移锚点。保存原NPZ字节、样式及统计，恢复时不重生成。旧快照继续整张mesh哈希规则。该检查覆盖全部被接受区域，是保守依赖，不是假称每像素可见性证明。

| Az | 改角目标内部L1 | 固定2px边界L1 | 远其他L1 | 远背景L1 | 恢复全部数组差异 |
|---:|---:|---:|---:|---:|---:|
{table}

四视图共12张完整对象输出，均全代理入框；改角实际非零，恢复后的image/hatch/contour/depth/labels及全部独立层精确。非目标文件逐字节保留，区域5墨色仍.45。当前远其他与远背景变化0；这是同代理掩码的有限证据，不抹去unit022旧视角的单像素残差。保存完整分母和变化像素数。

真实TDD首次恢复因不相关椅背新标签被拒绝rc1，实现后5项测试通过：独立创建后带cross/宽度编辑的ZIP冷恢复、共享支持和目标分割拒绝、当前路径有效但支持顶点变化拒绝、旧快照保守兼容、损坏依赖拒绝。11项继承作者/恢复回归通过，所有临时目录重定向本unit；11个旧资产加载，四默认模型实际烟测渲染非空。共享支持负例资产、整对象输出、ZIP和拒绝原因保留于assets/shared_support_changed、renders/shared_support_changed、metrics/EXPECTED_REJECTION.json。

Firefox真实世界盒预览→创建椅背（仅划区PNG不变）→改椅背墨色→改座面角度→保存ZIP→座面恢复/Undo/刷新。旧服务结束后新服务/新Firefox导入，Undo初始为空但两个创建快照可用，恢复PNG/数组仍精确；上传共享支持改变负例，座面恢复按钮禁用，新区域恢复可用。真实orbit/zoom按钮和PNG/ZIP下载成功，12+6帧全部视频解码，FFV1每帧RGB精确，MP4完整计数。两次新进程冷重绘18帧精确，最终tar重新解压后再按文档执行restore/edit/restore/export、ZIP新进程导入恢复及18帧重放，全部成功。不是独立全时序认证。

实际查看完整四视图对照、原GS/代理/区域图、浏览器恢复和拒绝控制、全部18帧接触表。两处区域可区分和编辑；座面波纹、前沿碎线、薄腿缺损、手动区域不完整仍明显，不将工程通过升级为视觉完整或科学GO。

首个test模块调用因根目录import路径错误rc1，未执行测试；随后正确脚本入口产生真实行为红灯rc1，均保留。首次浏览器行为文件PASS且cleanup完成，但外层工具session15783返回143、parent receipt缺失，主测试rc UNKNOWN。保留日志和事实，不由PASS倒填rc0。一次有界工程恢复仅将命令子进程独立session，执行新服务冷导入/恢复/Undo/导出/拒绝检查，rc0；恢复约110.5秒，未改候选/参数。原143根因仍未知。

| Command | Return code | Seconds |
|---|---:|---:|
{commands}

准确argv/cwd/UTC/退出码见logs/*.receipt.json及REPRODUCE_ZH.md。全部数值工作串行、线程1、两核affinity，未用GPU、凭据、环境转储、嵌套模型、push/merge。自有浏览器/服务关闭。源快照source_snapshot/、协议和UNIT023_DIFF.patch提供重放；包内runtime源码逐文件核验。只封存验证过的工程证据和真实失败记录，scientific_seal=false、reported_not_independently_verified。

启动：`cd {package} && ./run.sh viewer --scene chair --example chair_two_regions --port 8765`。完整说明PACKAGE_README_ZH.md；portable_demo.tar.gz含四模型资产、八个可选示例、源、真实预览/视频和ZIP。

'''+'\n'.join('- '+x for x in limits)+f'\n\nNEXT=continue：{next_step}\n'
    (U/'REPORT_ZH.md').write_text(report)
    reproduce='# Unit023实际命令\n\n下列JSON记录完整argv/cwd/UTC/返回码；tdd_red为入口错误，tdd_red_real为真实行为失败。第一次browser缺失parent receipt，未知退出保留于BROWSER_OUTER_INTERRUPTION.json。\n\n'
    for k,r in receipts.items():reproduce+=f'## {k}\n\n```json\n'+json.dumps(r,indent=2,ensure_ascii=False)+'\n```\n\n'
    (U/'REPRODUCE_ZH.md').write_text(reproduce)
    summary=f'''# 真实旧模型Demo：unit023

工程completed，视觉partial。Chair的座面与椅背两个人工选区可独立编辑；新增独立区域后仍可从ZIP冷加载并精确恢复座面。改变目标/共享支持则禁用恢复。

```bash
cd {package}
./run.sh viewer --scene chair --example chair_two_regions --port 8765
```

打开 http://127.0.0.1:8765 ，选区域4点 **Restore region’s original strokes**；区域5墨色45%保留。四默认模型和七个旧示例保留。

[完整使用说明]({U}/PACKAGE_README_ZH.md) · [可移植包]({U}/portable_demo.tar.gz) · [报告]({U}/REPORT_ZH.md) · [整对象比较]({U}/media/full_object_restore.png)。

16项新/继承行为测试通过、四默认模型真实烟测、浏览器创建/编辑/恢复/Undo、冷ZIP导入和18帧完整解码/冷重绘通过；解压包CLI也已运行。第一次浏览器外层143且主退出码未知保留，独立进程冷会话恢复rc0。粗代理、人工不完整选区和细结构缺损仍在，未作H1/H2/H5或全时序成功声明。

下一步：{next_step}
'''
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(summary)
    (SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(summary)
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(unit='unit_023',updated_utc=now(),execution_state='completed',demo_progress=progress,package=str(U/'portable_demo.tar.gz'),package_sha256=sha(U/'portable_demo.tar.gz'),report=str(U/'REPORT_ZH.md'),scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    diff=[]
    for name in sorted(set(hashes(U/'source_before'))|set(hashes(SOURCE))):
        before=U/'source_before'/name;after=SOURCE/name
        if before.is_file() and after.is_file() and sha(before)==sha(after):continue
        a=before.read_text().splitlines(True) if before.is_file() else [];b=after.read_text().splitlines(True) if after.is_file() else []
        diff+=difflib.unified_diff(a,b,fromfile='protocol_snapshot/'+name,tofile='unit023/'+name)
    (U/'UNIT023_DIFF.patch').write_text(''.join(diff))
    shutil.copy2(U/'PROTOCOL.json',U/'source_snapshot/UNIT023_PROTOCOL.json')
    shutil.copy2(U/'PACKAGE_README_ZH.md',U/'source_snapshot/UNIT023_DEMO_README_ZH.md')
    files=[]
    for prefix in ('assets','renders','source_model','metrics','media','source_snapshot','source_before','logs'):
        files += [f for f in (U/prefix).rglob('*') if f.is_file()]
    for name in ('browser','cold_browser'):
        files += [f for f in (U/name).iterdir() if f.is_file() and f.suffix in ('.json','.png','.zip','.log')]
    files += [U/name for name in ('STATUS.json','REPORT_ZH.md','NEXT.json','PROTOCOL.json','SELECTION_RECIPE.json','ENGINEERING_RECOVERY.json','PACKAGE_README_ZH.md','REPRODUCE_ZH.md','UNIT023_DIFF.patch','portable_demo.tar.gz','shared_support_changed.zip')]
    manifest={str(f.relative_to(U)):sha(f) for f in sorted(set(files))}
    js(U/'EVIDENCE_SHA256.json',dict(schema='finite_engineering_evidence_v1',created_utc=now(),scientific_seal=False,supervisor_verification='reported_not_independently_verified',files=manifest,excluded='Mutable browser profiles, session scratch, orchestration, runtime/codex responses; cold replay evidence is summarized and preserved in package/metrics.'))
    assert all(sha(U/name)==h for name,h in manifest.items())
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,evidence_files=len(manifest),package_sha256=sha(U/'portable_demo.tar.gz')),ensure_ascii=False))

def ASSET_PATH():return str(PREV/'portable_demo/assets/chair')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['review','finish']);a=p.parse_args();globals()[a.phase]()
