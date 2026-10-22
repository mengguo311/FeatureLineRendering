"""Write honest unit011 handoff and an engineering-only integrity manifest."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import datetime,difflib,json,os,shutil,subprocess

def main():
    unit=output_guard(OUTPUT_ROOT/'units/unit_011');here=Path(__file__).resolve().parent
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    p=json.loads((unit/'PROTOCOL.json').read_text());previous=Path(p['previous_unit'])
    read=lambda name:json.loads((unit/name).read_text())
    comparison=read('metrics/COMPARISON.json');video=read('media/VIDEO_VALIDATION.json')
    for name in ('PORTABLE_REPLAY','EXPORT_REPLAY','FINAL_ARCHIVE_REPLAY','CAMERA_NORMALIZATION_REPLAY'):
        assert read(f'metrics/{name}.json')['status']=='PASS'
    assert read('browser/BROWSER_VALIDATION.json')['status']=='PASS'
    required=['contour_tdd_green','regression','normalized_static_ficus','normalized_static_chair','motion_recovery','normalized_metrics','media','browser','package_replay_resume','export_replay','package_refresh']
    for name in required:assert read(f'logs/{name}.receipt.json')['returncode']==0
    # Explicit recheck of old model/assets; no old outputs are written.
    input_checks={}
    for scene,entry in p['scenes'].items():
        input_checks[scene]=dict(original_ply=sha(entry['original']['original_ply'])==entry['original']['sha256'],
            files={name:sha(Path(entry['asset'])/name)==h for name,h in entry['files'].items()})
        assert input_checks[scene]['original_ply'] and all(input_checks[scene]['files'].values())
    catalog_inputs=read('CATALOG_INPUTS.json')
    for scene,entry in catalog_inputs.items():
        assert all(sha(Path(entry['source'])/name)==h for name,h in entry['files'].items())
        assert all(sha(unit/'portable_demo/assets'/scene/name)==h for name,h in entry['files'].items())
    assert sha(previous/'portable_demo/CATALOG.json')==sha(unit/'portable_demo/CATALOG.json')
    groups={read(str(f.relative_to(unit)))['own_process_group'] for f in (unit/'logs').glob('*.start.json')}
    groups.update(x['pid'] for x in read('browser/CLEANUP.json')['children'])
    groups.add(read('metrics/EXPORT_VIEWER_CLEANUP.json')['pid'])
    processes=[]
    for pid in sorted(groups):
        try:os.killpg(pid,0);exists=True
        except ProcessLookupError:exists=False
        processes.append(dict(own_process_group=pid,exists=exists))
    assert not any(x['exists'] for x in processes), 'owned process group remains'
    resources=dict(root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
        total_task_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),own_process_groups=processes,
        final_affinity=sorted(os.sched_getaffinity(0)),gpu=False)
    assert resources['root_free_bytes']>=2**30 and resources['hdd_free_bytes']>=10*2**30 and resources['total_task_bytes']<20*2**30
    js(unit/'metrics/FINAL_INPUT_AND_RESOURCE_CHECK.json',dict(inputs=input_checks,default_four_assets_and_catalog_exact=True,**resources))
    snapshot=unit/'source_snapshot';snapshot.mkdir()
    source_files={};diff=[]
    for f in sorted(here.iterdir()):
        if f.is_file() and f.suffix in ('.py','.cpp','.html'):
            shutil.copy2(f,snapshot/f.name);source_files[f.name]=sha(f)
            old=previous/'source_snapshot'/f.name
            before=old.read_text().splitlines(keepends=True) if old.exists() else []
            after=f.read_text().splitlines(keepends=True)
            if before!=after:diff.extend(difflib.unified_diff(before,after,fromfile='unit010/'+f.name,tofile='unit011/'+f.name))
    (unit/'UNIT011_DIFF.patch').write_text(''.join(diff))
    (unit/'WORKTREE_FINAL.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    js(unit/'SOURCE_LOCK.json',dict(utc=now(),source_files=source_files,protocol_sha256=sha(unit/'PROTOCOL.json'),
        library_sha256=sha(unit/'build/libsource.so'),camera_normalization_sha256=sha(unit/'CAMERA_NORMALIZATION.json'),
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_state='Working-tree snapshot with inherited WIP preserved; no commit/push/merge. UNIT011_DIFF compares prior sealed source snapshot.'))
    receipts={f.stem.removesuffix('.receipt'):json.loads(f.read_text()) for f in sorted((unit/'logs').glob('*.receipt.json'))}
    rows=comparison['frames'];max_far=max((r['edits']['reduced']['far_other_L1']+r['edits']['reduced']['background_L1'])/r['edits']['reduced']['total_L1'] for r in rows)
    progress=dict(available_models=['chair','lego','drums','ficus'],genuinely_ran_old_model=True,original_PLY_render_this_unit=['ficus','chair'],
        original_gaussians={s:read(f'source_model/{s}/RECEIPT.json')['original_gaussians'] for s in ('ficus','chair')},
        saved_contour_visibility_and_strength=True,CLI_and_browser_controls=True,default_contour_strength=1.,candidate_strength=.35,
        default_four_assets_preserved=True,candidate_promoted_to_default=False,comparison_views=8,comparison_render_frames=32,
        all_static_complete=True,display_hatch_layers_and_paths_exact=True,local_edit_non_target_paths_and_layers_exact=True,
        local_edit_strict_locality='PARTIAL_FIXED_2PX_RESIDUAL',max_reduced_far_change_fraction=max_far,
        orbit_frames=12,zoom_frames=6,all_motion_complete=True,all_video_frames_decoded_exact=True,
        browser_four_model_switch_edit_display_undo_reload=True,exported_asset_cold_CLI_and_viewer_exact=True,
        relocated_four_default_previews_exact=True,relocated_display_and_local_edit_exact=True,final_archive_cold_preview_exact=True,
        visual_quality='partial',scientific_seal=False,
        reasoning='A usable saved display layer now makes hatch edits inspectable on existing complete models, with export and process restart verified. Foliage quality and strict pixel locality remain limited; no geometry or H1/H2 claim.')
    next_step='给当前浏览器增加下载当前PNG与短旋转/缩放导出：固定当前保存资产、轮廓/风格和明确相机轨迹，串行有界渲染并导出逐帧图/视频与资产哈希；在Ficus和Chair实际测试导出冷重开以及完整入框。只提升现有demo的可分享性，不再用更密网格或全局淡化冒充叶片几何改进。'
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='Complete-object editing and reload already work across four real models. Users can currently download assets but need CLI/scripts to export a matching presentation; a bounded export flow makes the demo easier to use and share.',
        estimated_next_minutes=25,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-22T05:17:47.355243+09:00')).total_seconds()/60
    status=dict(stage='UNIT_COMPLETE_WITH_LIMITATIONS',execution_state='partial',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS_AFTER_EXPLICIT_ENGINEERING_CORRECTIONS',scientific_verdict='H1_H2_NOT_TESTED_DISPLAY_ONLY',demo_progress=progress,
        artifacts=['PROTOCOL.json','CAMERA_NORMALIZATION.json','VISUAL_REVIEW.json','metrics/COMPARISON.json','media/ficus_comparison.png','media/chair_comparison.png',
            'media/ficus_local_edit.png','media/chair_local_edit.png','media/orbit.mkv','media/zoom.mkv','browser/BROWSER_VALIDATION.json','browser/exported_asset.zip',
            'metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','source_snapshot','UNIT011_DIFF.patch'],
        tests=dict(real_model_behavior_tests=5,coordinate_visibility_regression_tests=7,command_receipts={n:dict(returncode=r['returncode'],path=f'logs/{n}.receipt.json') for n,r in receipts.items()}),
        blockers=[],limitations=['Ficus holes/short paths remain; 35% may look washed out. Legacy defaults kept.',
            'Exact non-target paths/layers do not imply strict zero pixel leakage; fixed2px residuals retained.',
            'No independent surface truth, blind human preference study, full temporal certification, or H1/H2 test.',
            'Dependencies not bundled; only current Linux CPU environment tested.'],
        failures_preserved=['logs/contour_tdd_red.receipt.json','EXECUTION_AMENDMENT.json','attempt_schedule_overlap',
            'logs/package_replay.receipt.json','CAMERA_NORMALIZATION.json','attempt_camera_sizes','logs/path_typo.receipt.json'],
        resource_check='metrics/FINAL_INPUT_AND_RESOURCE_CHECK.json',scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    assert elapsed<55
    js(unit/'STATUS.json',status)
    table='| Model / view | Hatch ink (both) | Total ink 100% → 35% | Target edit L1 100% → 35% | Far L1 at35% |\n|---|---:|---:|---:|---:|\n'
    for r in rows:
        a,b=r['edits']['baseline'],r['edits']['reduced']
        table+=f"| {r['scene']} / {r['view']} | {r['hatch_ink']:.2f} | {r['baseline_total_ink']:.2f} → {r['reduced_total_ink']:.2f} | {a['target_L1']:.2f} → {b['target_L1']:.2f} | {b['far_other_L1']+b['background_L1']:.6f} |\n"
    originals='\n'.join(f"- {s}: `{e['original']['original_ply']}`，SHA256 `{e['original']['sha256']}`。" for s,e in p['scenes'].items())
    report=f'''# Unit011 — Saved independent contour display

执行状态 **partial**：新增功能及真实模型/浏览器/冷重开已执行通过，视觉质量与严格像素局部性仍有限。耗时约{elapsed:.1f}分钟，未延长55分钟预算。默认四模型不变，35%轮廓作为可选显示。H1/H2未测试。

## Scope and inputs

完整读取BRIEF、原大纲、P1/P2来源/报告/NEXT，实际检查unit010整对象图。更多Ficus面未带来明确可读性收益，因此不重建/扩模型，选择独立轮廓显示控制。保持原始失败与GT诊断局限，不以旧NO_GO阻止真实demo。输入为unit010 portable_demo的真实模型资产，两模型均30000面；不是GT替身。

{originals}

本轮从原PLY实渲染两模型各4个相机的RGB/深度；最终8张512图在source_model。区域是已有人工高度规则，不是语义恢复。协议先冻结100%与35%唯一显示变量、两个历史相机加91/271°仰角28距离5.2新虚拟相机；没有盲测或独立几何真值。初次相机尺寸执行错误及修正见下。

## Behavior and evidence

asset.json保存contours_visible及contour_strength，旧资产默认true/1。渲染器只在合成前缩放原.85轮廓墨层，不改轮廓检测、网格、区域、排线路径或遮挡。CLI新增display命令；浏览器独立保存、撤销、切换模型保留状态、导出均实测。非法强度/类型与过期revision返回422且状态不变。

Ficus原1425条路径、Chair原1315条路径；轮廓操作保留全部文件字节。中区95→45度单独重生成，Ficus非目标1092条、Chair非目标595条路径及其分层数组完全相同。8视角×4显示/编辑状态共32张完整对象图。排线墨量100%保留，减少的是明确声明的轮廓墨量；总墨量降低不能解释成几何改善。

{table}

表中L1为归一化灰度数组之和，不是人类偏好分数。两图层的合成使较淡轮廓下局部编辑更显眼，但Ficus侧面仍稀疏、发白，Chair差异较小。已检查最终512全图对比、全部局部编辑和18张轨迹接触表，见VISUAL_REVIEW.json。默认100%未改。

严格2px带外：Ficus35%在train_r_7背景0.125625，91°其他区0.251250+背景0.125625，271°背景0.125625；test_r_27为0。最大远区占总变化{max_far*100:.5f}%。Chair train_r_32两强度均有(y211,x226)的0.200000，其余三视角0。坐标/分母完整保留；没有扩大mask、改图或补造独立子像素归因。全局轮廓设置本身是整体显示操作，不冒称局部修改。

12旋转+6缩放使用同一Ficus中区45度、35%轮廓保存资产，18/18完整入框；两个FFV1视频全部解码RGB逐帧精确。只是有限帧展示/解码，不是全路径时序认证。媒体位于media，实际所有帧在renders/orbit、renders/zoom。

5项真实Ficus行为测试先red rc1后green rc0；7项坐标、可见性与基础行为回归rc0。真实Firefox软件渲染测试通过四模型切换、局部风格、轮廓强度/隐藏/恢复、撤销、相机、刷新与HTTP导出。服务器停止后，ZIP搬移到新包，新CLI与新viewer精确复现PNG和全部数组。搬移包四默认模型预览逐文件与unit010精确；新display .35以及随后局部edit在512图/数组精确。最终重新打包、解压另一路径再冷预览也通过。

## Engineering failures retained

1. 父代理误在Chair批次完成前启动motion，实际重叠17.781秒；两个进程都受同两核限制，但违背串行协议。主动停止自有motion，child rc-15/shell241；原Chair rc0。原输出保留attempt_schedule_overlap。串行同参数重跑约81.5秒，所有原已完成帧逐文件精确；最终只用串行证据。EXECUTION_AMENDMENT.json保留原收据。
2. 搬移CLI对比首次rc1：测试脚本直接使用继承Ficus400/Chair800相机，而协议声明512、CLI实际512。四默认冷重放当时已成功。保留全部旧尺寸source/renders/metrics/图与原包至attempt_camera_sizes，CAMERA_NORMALIZATION.json在修正输出前冻结同视角/FOV的512相机。使用既有像素中心保持resize，仅修复执行尺寸；约99.9秒串行重画参考与静态对比，候选参数没有重选。重用原已完成rc0 CLI命令收据，完成此前未启动的编辑检查；原父rc1不覆盖。
3. 一次无关版本查询拼错venv路径返回127，未启动解释器、未写输出；原事实保留logs/path_typo.receipt.json。无缺失子退出码被补造。

两次工程修正都在本轮普通预算内，未请求额外延长期、未进行新的科学候选扫描。CPU≤2/数值单线程，最终批次串行；无GPU、安装、凭据、环境dump、嵌套模型/代理、push/merge。已确认全部自有进程组结束。原输入与四默认资产/目录重新哈希不变。

## Replay and next

进入portable_demo执行 `./run.sh viewer --scene ficus`。具体display/edit/导出冷重开命令见PACKAGE_README_ZH.md；原始精确命令和退出码逐条在REPRODUCE_ZH.md与logs/*.receipt.json。portable_demo.tar.gz包含真实资产、运行源、对比图和视频；依赖环境未打包。source_snapshot及UNIT011_DIFF.patch记录本轮源码和相对unit010差异，保留继承WIP，不冒称干净HEAD。

仅对已验证主产物、执行源及明确标注的失败收据做工程完整性清单，scientific_seal=false。旧尺寸/重叠图不作为主证据，原尝试仍保留。NEXT=continue：{next_step}
'''
    (unit/'REPORT_ZH.md').write_text(report)
    reproduce='# Unit011 exact execution receipts\n\n以下保留原命令/原退出码；输出目录必须为空，重放时换新授权输出目录。已完成命令的恢复仅复核其原收据，不补造新执行。\n\n'
    import shlex
    for n,r in receipts.items():
        reproduce+=f"## {n}\n\nReturn code: `{r['returncode']}`. Receipt: `logs/{n}.receipt.json`.\n\n```bash\n{shlex.join(r['command'])}\n```\n\n"
    (unit/'REPRODUCE_ZH.md').write_text(reproduce)
    readme=f'''# 真实模型分区排线 Demo — unit011

当前四模型入口：`{unit}/portable_demo`。已实跑Ficus/Chair原始PLY、完整对象局部编辑、轮廓控制、浏览器导出及新进程冷重开。状态partial：Ficus叶片几何和少量像素局部性残差仍在，H1/H2未测试。

```bash
cd {unit}/portable_demo
./run.sh viewer --scene ficus
```

打开本机 http://127.0.0.1:8765。可选Chair/Lego/Drums/Ficus。View contours支持独立显示开关/强度，保存到下载资产；默认外观不变。操作与CLI：[{unit.name}说明]({unit}/PACKAGE_README_ZH.md)。[报告]({unit}/REPORT_ZH.md)，[便携包]({unit}/portable_demo.tar.gz)，[Ficus对照]({unit}/media/ficus_comparison.png)，[Chair对照]({unit}/media/chair_comparison.png)。依赖未打包；当前Linux CPU环境已验证。NEXT=continue，下一步补当前资产图片/短视频导出。
'''
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(readme)
    Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(readme)
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(updated_utc=now(),current_unit=unit.name,execution_state='partial',demo_progress=progress,
        package=str(unit/'portable_demo.tar.gz'),package_sha256=sha(unit/'portable_demo.tar.gz'),report=str(unit/'REPORT_ZH.md'),
        readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),scientific_seal=False,next_action='continue'))
    # Re-snapshot final documentation/diff, then hash only stable checked evidence.
    shutil.copy2(unit/'PACKAGE_README_ZH.md',snapshot/'PACKAGE_README_ZH.md')
    shutil.copy2(unit/'PROTOCOL.json',snapshot/'UNIT011_PROTOCOL.json')
    (unit/'WORKTREE_FINAL.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    selected=[]
    for folder in ('assets','source_model','renders','media','metrics','source_snapshot','catalog_assets','logs'):
        selected.extend(f for f in (unit/folder).rglob('*') if f.is_file())
    selected.extend(f for f in unit.iterdir() if f.is_file() and f.suffix in ('.json','.md','.patch','.diff'))
    selected += [unit/'portable_demo.tar.gz',unit/'build/libsource.so']
    selected.extend(f for f in (unit/'browser').iterdir() if f.is_file() and f.suffix in ('.json','.png','.zip'))
    for f in selected:
        assert 'orchestration' not in f.parts and 'fresh_profile' not in f.parts
    files=[dict(path=str(f.relative_to(unit)),sha256=sha(f),bytes=f.stat().st_size,
        role='retained_failure_receipt_or_amendment' if f.name in ('contour_tdd_red.receipt.json','motion.receipt.json','package_replay.receipt.json','path_typo.receipt.json','EXECUTION_AMENDMENT.json','CAMERA_NORMALIZATION.json') else 'engineering_evidence_or_source') for f in sorted(set(selected))]
    js(unit/'SHA256_MANIFEST.json',dict(scope='Validated engineering artifacts/source plus explicitly retained failure records. Rejected attempt raster directories and browser profiles excluded.',files=files))
    assert all(sha(unit/f['path'])==f['sha256'] for f in files)
    js(unit/'SEAL.json',dict(utc=now(),kind='engineering_integrity_only',scientific_seal=False,manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),
        files=len(files),execution_state='partial',supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='partial',minutes=elapsed,files=len(files),package_sha256=sha(unit/'portable_demo.tar.gz'),next_action='continue')))

if __name__=='__main__':main()
