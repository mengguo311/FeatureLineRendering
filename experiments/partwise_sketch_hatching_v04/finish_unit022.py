"""Seal finite validated engineering evidence; keep visual/scientific limits."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import datetime,difflib,json,shutil,subprocess
import numpy as np
from unit022_run import U,PREV,SOURCE,protocol,hashes

def review():
    from scipy.ndimage import binary_dilation,binary_erosion
    rows=[]
    for i,v in enumerate(protocol()['static_camera_values']):
        with np.load(U/f'renders/authored/frame_{i:03d}_arrays.npz') as a,np.load(U/f'renders/edited/frame_{i:03d}_arrays.npz') as b:
            mask=a['regions']==4;band=binary_dilation(mask,iterations=2)&~binary_erosion(mask,iterations=2)
            other=(a['regions']>0)&~mask&~band;delta=np.abs(a['image']-b['image']);yx=np.argwhere(other&(delta>0))
            rows.append(dict(camera=v,far_other_changed_pixels=len(yx),pixel_yx=yx.tolist(),L1=float(delta[other].sum()),
                interpretation='Finite observed residual under unchanged fixed2px band. Inherited capsule support can straddle labels; no all-boundary correctness claim.'))
    js(U/'metrics/RESIDUAL.json',rows)
    assert sum(r['far_other_changed_pixels'] for r in rows)==1
    js(U/'metrics/VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent, not independent human review',
        inspected=['unit021 whole-object and source-GS panels','unit022 whole-object authored/edit/restored four-view panel','unit022 actual original-GS/proxy/regions/hatch panel','actual Firefox restored view','all 12 orbit and 6 zoom frames in contact sheets'],
        decision='Keep optional restorable-seat example; original defaults and examples retained.',
        positives='Complete recognizable Chair; clear local angle change; restored creation-time images/arrays exact. Cold GUI action works and can be undone.',
        negatives=['Proxy seat ripples, front-apron short lines and thin legs remain.','Manual region is a partial seat patch, with side/rear fragments, not complete semantics.','Angle edit has one changed far-other pixel at az123 with L1 .2 under fixed2px band; no tolerance relaxation.','Orbit/zoom show all object bounds but do not establish independent temporal stability.'],
        visual_quality='partial',science='H1/H2/H5 not tested'))
    js(U/'logs/READ_ATTEMPT.json',dict(command='cat /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_011/REPORT_ZH.md /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_011/NEXT.json',returncode=1,
        reason='Historical unit011 lacks final REPORT/NEXT and retains a stale running STATUS. Read its source/status and latest completed unit010 report/NEXT, also accepted by P2. No old outputs modified.'))
    old=json.loads((PREV/'source_model/LIBRARY_PROVENANCE.json').read_text())
    assert sha(U/'source_model/libsource.so')==old['library_sha256']
    assert sha(SOURCE/'model_adapter.py')==old['adapter_sha256']
    assert sha(SOURCE/'source_ewa.cpp')==old['source_sha256']
    js(U/'source_model/LIBRARY_PROVENANCE.json',dict(**old,reused_from_unit='unit_021',current_library_verified=True,current_source_and_adapter_verified=True))

def finish():
    p=protocol();package=U/'portable_demo'
    receipts={f.stem.removesuffix('.receipt'):json.loads(f.read_text()) for f in sorted((U/'logs').glob('*.receipt.json'))}
    required=['tdd_red','tdd_green','final_restore_tests','candidate','static','reference','regressions','stage','browser','cold_browser_receipt','media_stage','cold_orbit','cold_zoom','build','check']
    assert all(n in receipts for n in required)
    assert all(r['returncode']==r.get('expected_returncode',0) for r in receipts.values())
    interruption=json.loads((U/'logs/COLD_BROWSER_OUTER_INTERRUPTION.json').read_text())
    assert interruption['outer_returncode']==143 and interruption['child_main_returncode'] is None
    assert json.loads((U/'cold_browser_receipt/BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    assert json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())['new_process_ZIP_import_restore_PNG_exact']
    assert all(sha(SOURCE/f.name)==sha(f) for f in (package/'source').iterdir() if f.is_file())
    import os
    resources=dict(task_output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False)
    assert resources['task_output_bytes']<20*2**30 and resources['root_free_bytes']>=2**30 and resources['hdd_free_bytes']>=10*2**30
    assert len(resources['cpu_affinity'])<=2
    js(U/'metrics/RESOURCES_FINAL.json',resources)
    start=datetime.datetime.fromisoformat(p['started_utc']);elapsed=(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()/60
    assert elapsed<55
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],newly_rendered_model='chair',
        original_PLY_newly_rendered=True,original_gaussians=256690,original_GS_views=4,complete_static_states=12,
        manual_region=dict(region=4,faces=2704,source_region=2,partial_seat=True,automatic_semantics=False),
        persistent_creation_snapshot=True,restore_target_path_bytes_exact=True,restore_all_render_arrays_exact_views=4,
        other_edited_region_preserved=True,original_cross_layers_restored_test=True,
        actual_browser_edit_restore_undo=True,cold_new_server_browser_import_restore_exact=True,
        motion_frames=18,lossless_video_decoded_exact_frames=18,mp4_decoded_frames=18,cold_replay_PNG_arrays_exact_frames=18,
        relocated_tar_documented_CLI_restore_and_cold_import=True,all_previous_defaults_and_examples_byte_exact=True,
        visual_quality='partial; inherited proxy artifacts, incomplete manual seat, one far-other pixel changes under angle edit',
        reasoning='Real Chair now carries its manual-region creation paths/styles across ZIP export and a stopped-server cold reload. Explicit restore is exact and local, unlike re-entering an old angle. Four prior models remain usable; no geometry or scientific claim upgraded.')
    limits=[
        '旧vanilla GS的CPU模型衍生代理及继承平滑，不是独立实测表面。路径/面ID不是原高斯行号。',
        '人工2704面只覆盖部分座面；波纹、薄杆缺失、侧后零碎选区未改进。',
        '95→65局部编辑的四视图中az123有1个远其他像素L1=.2；固定2px带不改。非目标路径/分层精确，但复合图不是严格逐像素语义裁剪。恢复后全部数组精确。',
        '只有本版本新建人工区域保存创建快照。旧示例没有初始路径时不猜测补造。',
        '任何后续几何/区域标签变更均保守禁用旧快照，包括对不相关区域的划分；快照仍随ZIP保存。样式/轮廓/相机编辑不影响可恢复性。',
        '恢复包含目标区全部创建时样式与双层路径，可能移除后来新增的cross层；Undo可回到恢复前。普通改回旧角度仍是重生成。',
        '有限视角、GUI操作和18帧完整解码/冷重绘不是独立语义/几何/完整时序认证；H1/H2/H5未测试，历史P1 NO_GO/P2不可辨识不变。',
        '仅在当前Linux CPU依赖环境实际运行；包不含解释器/依赖二进制/原PLY，不承诺实时帧率。']
    next_step='把人工选区的创建快照绑定到该区域实际使用的面/顶点和可见性标签支持，而非整张mesh哈希：目前给不相关区域再划区也会禁用恢复。先用真实Chair做两处相互独立选区，保留失败例；只在目标锚点与支持标签语义完全未变时允许冷恢复。若涉及目标区/共享支持变化继续拒绝。作为有界可用性改进，不启动模型/几何扫参。'
    status=dict(stage='UNIT_COMPLETE_PERSISTENT_REGION_RESTORE',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS',scientific_verdict='H1_H2_H5_NOT_TESTED; ENGINEERING_RESTORE_ONLY',demo_progress=progress,
        artifacts=['PROTOCOL.json','SELECTION_RECIPE.json','assets/authored','assets/edited','assets/restored','metrics/STATIC.json','metrics/RESIDUAL.json','metrics/REGRESSIONS.json','metrics/VISUAL_REVIEW.json','media/full_object_restore.png','media/source_reference_all_views.png','media/chair_orbit.mp4','media/chair_zoom.mp4','browser/BROWSER_VALIDATION.json','cold_browser/BROWSER_VALIDATION.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','PACKAGE_README_ZH.md','source_snapshot','UNIT022_DIFF.patch','EVIDENCE_SHA256.json'],
        tests=dict(restore_tests=5,inherited_authoring_tests=6,legacy_catalog_assets_loaded=10,legacy_default_models_smoke_rendered=4,TDD='Real Chair creation snapshot missing assertion rc1 -> pass; final cold ZIP/locality/cross/stale/corrupt/missing tests pass.',command_receipts={k:dict(returncode=v['returncode'],path='logs/'+k+'.receipt.json') for k,v in receipts.items()}),
        blockers=[],limitations=limits,retained_interruption=interruption,engineering_recovery='ENGINEERING_RECOVERY.json',scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,reason='完整对象/局部编辑/冷加载已运行。本轮解决跨会话精确恢复；下一步解除已明确记录的保守可用性限制，仍保留失效锚点拒绝。',estimated_next_minutes=25,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    rows=json.loads((U/'metrics/STATIC.json').read_text())['views']
    table='\n'.join(f"| {r['camera']['azimuth']} | {r['edit_delta']['target_interior']['L1']:.3f} | {r['edit_delta']['boundary_band']['L1']:.3f} | {r['edit_delta']['far_other']['L1']:.3f} | {r['edit_delta']['far_background']['L1']:.3f} | 0 |" for r in rows)
    commands='\n'.join(f"| {k} | {r['returncode']} | {r['seconds']:.3f} |" for k,r in receipts.items())
    report=f'''# Unit022：跨会话精确恢复人工区域创建时笔触

工程 **completed**，视觉质量 **partial**，耗时约{elapsed:.1f}分钟。实际运行真实Chair的新建区域→改角→保存ZIP→停止旧服务→新服务/新Firefox导入→恢复创建时笔触→Undo→导出旋转/缩放→冷重绘。新增可选示例 `chair_seat_restorable`，四默认和六个旧示例逐文件保留。

完整读取BRIEF、851行原始大纲、P1最新完成unit010报告/NEXT及P2源/报告/NEXT；检查P1中断unit011源和STATUS，其没有最终报告/NEXT，不续写旧状态。实际阅读unit021源/报告/NEXT并查看整对象和GS对照。上轮创建选区已不重排笔触，但改回旧角度不能恢复继承断点；相较继续弱收益的平滑或增加第五模型，本轮补齐这一可复现的使用缺口。

紧凑协议SHA `{sha(U/'PROTOCOL.json')}` 在TDD/候选运行前冻结。输入资产 `{ASSET_PATH()}`，逐文件hash见PROTOCOL；原Chair PLY `{p['original']['original_ply']}`，SHA `{p['original']['sha256']}`。原256690高斯重新用CPU SH3/EWA渲染四幅RGB，库和adapter/C++源码hash与上轮相同；并列图 `media/source_reference_all_views.png`。这不是独立几何真值。

复用上轮两个人工矩形的2704面选区，不调几何/标签/方向。四个新固定相机az33/123/213/303、elev27、distance4.9，在结果前确定；模型与选区早已曝光，不称盲测。区域4的创建时NPZ（1577段）逐字节保存为origin_4.npz，并保存style/statistics及整张带标签mesh哈希。改角65正常重生成目标路径；显式restore复制初始路径及全部样式，不重生成，不改非目标文件。原始快照保留继承visibility_mask，仍允许线帽跨人工边界。恢复不会恢复旧几何；mesh/标签变化后明确拒绝。

| Az | 改角目标内部L1 | 固定2px边界L1 | 远其他L1 | 远背景L1 | 恢复后全部数组差异 |
|---:|---:|---:|---:|---:|---:|
{table}

四静态视图共12张整对象状态，恢复后的image/hatch/contour/depth/labels及各层数组全精确。改角各视图均有非零局部效果。az123的远其他区1个像素L1=.2，原样保留 `metrics/RESIDUAL.json`，没有扩大2px带或追逐完美门槛；其他区路径/独立层未变，不据此宣称合成图完全无泄漏。原始分母见STATIC.json。选区/局部性均来自同一代理，不是独立语义标签。

真实TDD首先断言“创建操作持久保存初始笔触”失败rc1；实现后通过。最终5项恢复测试包括另一区墨色编辑保留、当前区角度/粗细/cross编辑后的ZIP恢复、创建时双层cross恢复、重复划区使旧快照失效、缺失/损坏/路径逃逸拒绝且不产生目标输出。6项继承作者行为测试通过，临时输出显式重定向本unit；四默认模型实渲染烟测非空，10个旧资产加载成功。没有全历史机械重跑。

Firefox实际点编辑/恢复/Undo/刷新、保存ZIP。新服务和新Firefox上传ZIP，初始Undo为空但创建快照可用；点击恢复后PNG/全部数组与创建时精确，Undo回到改角65，刷新再恢复成功。选择无快照旧区域按钮禁用。旋转/缩放保持路径；实际下载PNG、恢复资产ZIP、12帧orbit和6帧zoom。两条视频全部解码：FFV1每帧RGB精确，MP4完整计数；两次新进程串行冷重绘18帧PNG/数组精确。实际检查全部接触图；不是全时序认证。

最终tar解压到新目录后运行文档中的restore/export以及author/edit/restore/export；新Python仅从解压源码和ZIP冷导入再恢复，PNG均精确。包与源码hash核验通过。准确argv/cwd/UTC/返回码见REPRODUCE_ZH.md和logs/*.receipt.json。

| Command | Return code | Seconds |
|---|---:|---:|
{commands}

历史unit011缺少最终REPORT/NEXT的一次只读cat返回1，见logs/READ_ATTEMPT.json；不是本轮实验失败。TDD真实红灯保留。首次cold_browser已写PASS、18帧导出和子进程cleanup，但外层工具返回143，未留下parent receipt，主测试子程序返回码UNKNOWN；原因未确定，绝不从PASS文件倒填rc0。原输出原样保留于cold_browser，详见logs/COLD_BROWSER_OUTER_INTERRUPTION.json。一次有界工程恢复在新服务/新Firefox只重查导入→恢复→Undo→刷新，不重新生成原运动视频，cold_browser_receipt返回0。其后两次冷重绘和压缩包重放返回0；ENGINEERING_RECOVERY.json记录起止。全部数值任务串行，线程1、两核affinity、无GPU/凭据/环境转储/嵌套模型/push/merge，自有浏览器与服务退出。源快照与差异在source_snapshot/和UNIT022_DIFF.patch。

启动：`cd {package} && ./run.sh viewer --scene chair --example chair_seat_restorable --port 8765`。完整说明PACKAGE_README_ZH.md；portable_demo.tar.gz包含四模型资产、旧示例、新可恢复示例、源码、配方、预览和真实视频。

{chr(10).join('- '+x for x in limits)}

仅哈希已验证的工程证据和真实失败记录，scientific_seal=false，reported_not_independently_verified。NEXT=continue：{next_step}
'''
    (U/'REPORT_ZH.md').write_text(report)
    reproduce='# 实际执行命令及返回码\n\n每项为准确argv；预期TDD失败保留。\n\n'
    for key,r in receipts.items():reproduce+='## '+key+'\n\n```json\n'+json.dumps(r,indent=2,ensure_ascii=False)+'\n```\n\n'
    (U/'REPRODUCE_ZH.md').write_text(reproduce)
    readme=f'''# 真实旧模型Demo：unit022\n\n工程completed，视觉partial。新增人工区域的创建时笔触可随ZIP保存；已实测局部编辑→冷导入→精确恢复、Undo、18帧运动解码/冷重绘和解压包CLI运行。\n\n```bash\ncd {package}\n./run.sh viewer --scene chair --example chair_seat_restorable --port 8765\n```\n\n打开 http://127.0.0.1:8765 ，选择区域4，点 **Restore region’s original strokes**。四默认模型和旧示例仍可选。\n\n[完整使用说明]({U/'PACKAGE_README_ZH.md'}) · [可移植包]({U/'portable_demo.tar.gz'}) · [报告]({U/'REPORT_ZH.md'}) · [整对象比较]({U/'media/full_object_restore.png'})。\n\n局限：粗代理、人工部分座面和薄结构缺损未改善；一个侧视角改角有1个远其他像素变化。几何/边界改变后旧快照会保守失效。旧资产无快照时禁用恢复。仅Linux CPU依赖环境验证，无H1/H2/H5或完整时序成功结论。\n\n下一步：{next_step}\n'''
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(readme)
    (SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(readme)
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(updated_utc=now(),latest_unit='unit_022',execution_state='completed',scientific_verdict=status['scientific_verdict'],demo_progress=progress,portable_package=str(U/'portable_demo.tar.gz'),readme=str(U/'PACKAGE_README_ZH.md'),report=str(U/'REPORT_ZH.md'),next_action='continue',recommended_next_step=next_step,scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    before=json.loads((U/'SOURCE_BEFORE.json').read_text());current=hashes(SOURCE)
    js(U/'SOURCE_FINAL.json',dict(source_files=current,changed_preexisting_sources=[n for n in before if current.get(n)!=before[n]],added_sources=sorted(set(current)-set(before)),packaged_runtime_source_exact=True))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    patch=''
    for n in sorted(set(current)|set(before)):
        a=(U/'source_before'/n).read_text().splitlines(keepends=True) if n in before else []
        b=(SOURCE/n).read_text().splitlines(keepends=True) if n in current else []
        if a!=b:patch+=''.join(difflib.unified_diff(a,b,fromfile='a/experiments/partwise_sketch_hatching_v04/'+n,tofile='b/experiments/partwise_sketch_hatching_v04/'+n))
    for n in ('DEMO_README_ZH.md','UNIT022_PROTOCOL.json','UNIT022_DEMO_README_ZH.md'):
        old=U/'docs_before'/n;new=SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04'/n
        patch+=''.join(difflib.unified_diff(old.read_text().splitlines(keepends=True) if old.exists() else [],new.read_text().splitlines(keepends=True),fromfile='a/docs/partwise_sketch_hatching_v04/'+n,tofile='b/docs/partwise_sketch_hatching_v04/'+n))
    (U/'UNIT022_DIFF.patch').write_text(patch)
    files=[U/n for n in ('PROTOCOL.json','SELECTION_RECIPE.json','STATUS.json','NEXT.json','REPORT_ZH.md','REPRODUCE_ZH.md','PACKAGE_README_ZH.md','SOURCE_BEFORE.json','SOURCE_FINAL.json','UNIT022_DIFF.patch','portable_demo.tar.gz','ENGINEERING_RECOVERY.json')]
    for name in ('assets','renders','source_model','metrics','media','source_snapshot','logs'):files.extend(f for f in (U/name).rglob('*') if f.is_file())
    for name in ('browser','cold_browser','cold_browser_receipt'):files.extend(f for f in (U/name).iterdir() if f.is_file() and f.suffix in ('.json','.png','.zip'))
    manifest={str(f.relative_to(U)):sha(f) for f in sorted(set(files))}
    js(U/'EVIDENCE_SHA256.json',dict(utc=now(),scope='Validated finite engineering artifacts and retained failures; excludes mutable browser profiles/sessions, scratch and orchestration. Not scientific success.',scientific_seal=False,files=manifest))
    assert all(sha(U/n)==v for n,v in manifest.items())
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,evidence_files=len(manifest),scientific_seal=False,next_action='continue')))

def ASSET_PATH():return str(PREV/'portable_demo/assets/chair')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['review','finish']);a=p.parse_args();globals()[a.phase]()
