"""Finite engineering evidence and honest third-model handoff; no science seal."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,datetime,shlex,os


def finish(unit):
    unit=output_guard(unit);root=runtime.OUTPUT_ROOT
    if (unit/'ENGINEERING_SEAL.json').exists():raise FileExistsError('already sealed')
    read=lambda f:json.loads((unit/f).read_text())
    p=read('PROTOCOL.json');v=read('metrics/VALIDATION.json');d=read('metrics/SOURCE_DIAGNOSTICS.json')
    proxy=read('proxy/PROXY.json');model=read('proxy/MODEL_IMPORT.json')
    build=read('metrics/BUILD_REPLAY.json');export=read('metrics/EXPORT_REPLAY.json')
    portable=read('metrics/PORTABLE_REPLAY.json');browser=read('browser_complete/BROWSER_VALIDATION.json')
    video=read('media/VIDEO_VALIDATION.json');http=read('metrics/VIEWER_SMOKE.json')
    assert v['execution_validation']=='PASS'
    assert all(x['status']=='PASS' for x in [build,export,portable,browser])
    assert all(x['all_decoded_frames_exact'] for x in video['videos'])
    assert read('proxy/CACHE_REPLAY.json')['all_arrays_exact'] is None
    assert all(sha(f)==h for f,h in p['inputs_sha256'].items())
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-models-v04'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    receipts=[]
    raw=sorted([json.loads(f.read_text())|{'receipt_path':str(f.relative_to(unit))}
                for f in (unit/'logs').glob('*.receipt.json')],key=lambda r:r['start_utc'])
    for r in raw:receipts.append(dict(path=r['receipt_path'],returncode=r['returncode'],seconds=r['seconds']))
    failures=[r for r in receipts if r['returncode']!=0]
    assert {Path(r['path']).name for r in failures}=={'tdd_red.receipt.json','build.receipt.json','viewer_smoke.receipt.json'}
    # Recheck the previous unit's immutable evidence without modifying it.
    previous=Path(p['previous_unit']);old=json.loads((previous/'SHA256_MANIFEST.json').read_text())
    assert all(sha(previous/f['path'])==f['sha256'] for f in old['files'])
    prefix=[]
    for f in sorted((unit/'attempt_interrupted/proxy').glob('train_*.npz')):
        prefix.append(dict(file=f.name,sha256=sha(f),recovered_exact=sha(f)==sha(unit/'proxy'/f.name)))
    assert all(x['recovered_exact'] for x in prefix)
    groups={json.loads(f.read_text())['own_process_group'] for f in (unit/'logs').glob('*.start.json')}
    groups.update(x['pid'] for x in read('browser_complete/CLEANUP.json')['children'])
    groups.add(read('logs/VIEWER_CLEANUP.json')['pid'])
    proc=subprocess.run(['ps','-g',','.join(map(str,sorted(groups))),'-o','pid=,comm='],capture_output=True,text=True)
    assert not proc.stdout.strip(), 'own child group still alive'
    source=Path(__file__).parent;snap=unit/'source_snapshot';snap.mkdir()
    for f in source.iterdir():
        if f.suffix in ('.py','.cpp','.html'):shutil.copy2(f,snap/f.name)
    assert all(sha(f)==sha(unit/'portable_demo/source'/f.name) for f in snap.iterdir())
    js(unit/'SOURCE_LOCK.json',dict(commit=commit,branch=branch,protocol_sha256=sha(unit/'PROTOCOL.json'),
        files={str(f.relative_to(unit)):sha(f) for f in sorted(snap.iterdir())}))
    (unit/'SOURCE_DIFF.patch').write_text(subprocess.check_output(['git','diff','902a4dc8c033ea0f559520ea3860e67cf882bc32',
        'HEAD','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04'],text=True))
    for f in (unit/'browser_complete').glob('*.png'):shutil.copy2(f,unit/'media'/('editor_'+f.name))
    js(unit/'EXECUTION_AMENDMENT.json',dict(utc=now(),failed_commands=failures,
      build_interruption=dict(outer_exit=143,child_returncode=-15,runner_signals=[15],cause='UNKNOWN',
        recovery='identical frozen inputs/settings, one complete rerun, rc0; all six completed original depth files identical',
        preserved='attempt_interrupted/',prefix_comparison=prefix),
      http_test=dict(returncode=1,cause="obsolete static fetch('/render' spelling assertion after frontend adopted post() helper",
        fix='assert served Apply control; keep actual six endpoint operations and separate real Firefox UI test',
        recovery_returncode=0,preserved='attempt_ui_assert/ and logs/viewer_smoke.log'),
      ancillary=[dict(command='python ../run_logged.py (from code directory)',returncode=2,
        cause='wrong relative test-runner path; no test executed; corrected invocation passed'),
        dict(action='read-only guessed historical NEXT/READING_LOG paths',subprocess_returncode='UNKNOWN',
          cause='missing paths; exact P1/P2 roots subsequently read from source and opened')],
      extra_time_extension=False,scientific_settings_changed=False))
    inspected=['media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit_all_frames.png',
      'media/zoom_all_frames.png','browser_complete/05_reloaded.png','renders/first/frame_000_image.png','proxy/reference_train_r_7.png']
    negatives='Thin stands are fragmented or absent, drum rims and cavities are coarse, lower drum has holes, some paths are short or crowded; height regions jointly affect multiple physical pieces.'
    js(unit/'VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent; not independent human/blind assessment',inspected=inspected,
      all_static_views=8,all_orbit_frames=12,all_zoom_frames=6,
      positives='recognizable complete drum kit with major cymbals; middle edit visible and upper/lower appearance retained; usable actual browser',
      negatives=negatives,quality='partial',decision='working third-model demo; no geometry/style sweep or H1/H2 claim'))
    reading=['orchestration/BRIEF.md (complete)','docs/partwise_sketch_hatching/experiment_outline_v1.md (all 851 lines)',
      'docs/partwise_sketch_hatching_v02/REPORT_unit010_ZH.md','P1 unit_010/NEXT.json',
      'docs/partwise_sketch_hatching_v03/REPORT_ZH.md','P2 experiment_001/NEXT.json',
      'v02/base_density.py; v03/run_comparison.py; v04/model_adapter.py, build_proxy.py, fuse_cpu.py, geometry.py, hatching.py, render.py, demo.py, viewer.py',
      'unit_004 STATUS/REPORT/NEXT and actual 8-view comparison/edit images']
    js(unit/'READING_RECORD.json',dict(read=reading,historical_no_go_unchanged=True,no_old_helper_invoked=True))
    audit=dict(utc=now(),previous_sealed_files_unchanged=len(old['files']),inputs_unchanged=True,
      successful_prefix_files=len(prefix),all_static_proxy_bounds_inside=all(read(f'renders/static_baseline/frame_{i:03d}.json')['bounds']['all_proxy_vertices_inside'] for i in range(8)),
      inspected_own_process_groups=sorted(groups),remaining_own_processes=[],ps_fields=['pid','comm'],
      package_source_matches_snapshot=True,root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(root).free,
      task_bytes=sum(f.stat().st_size for f in root.rglob('*') if f.is_file()))
    assert audit['all_static_proxy_bounds_inside'];js(unit/'metrics/FINAL_AUDIT.json',audit)
    base=v['anchors']['baseline'];edited=v['anchors']['edited']
    nextstep='优先提高现有三模型的选区可用性：为浏览器增加基于当前相机射线命中代理面的点击选区/局部框选预览，保存真实face IDs并明确只选可见面还是贯穿选择；用Lego或Drums一次局部编辑、非目标保持、导出冷加载验证。不要把点击工具称为自动语义分割；暂不为凑四模型直接扩展Ficus，也不做平滑/阈值扫描。'
    progress=dict(scene='drums',genuinely_ran_old_model=True,available_models=['chair','lego','drums'],
      original_gaussians=model['audit']['count'],proxy_vertices=proxy['vertices'],proxy_faces=proxy['faces'],editable_regions=3,
      region_source='authored z thresholds -0.15 / 0.42; nonsemantic',
      baseline_paths=sum(x['paths'] for x in base.values()),edited_paths=sum(x['paths'] for x in edited.values()),
      retained_non_target_paths=base['1']['paths']+base['3']['paths'],non_target_paths_and_layers_exact=True,
      far_edit_delta_all_views=0.,complete_object_views=8,cold_reload_exact=True,actual_browser_test=True,
      actual_http_controls=len(http['actual_http_edit_tests']),exported_zip_cold_reload_exact=True,
      relocated_package_cold_reload_exact=True,full_original_model_rebuild_exact=True,full_rebuild_seconds=build['seconds'],
      orbit_frames=12,zoom_frames=6,all_video_frames_decoded_exact=True,visual_quality='partial',
      reasoning='从有缓存的Chair/Lego迁移到无历史源缓存的Drums；原PLY直接构建、保存编辑、浏览器、导出和冷加载均实际运行，扩大可用资产而未改变几何门限。',
      remaining=negatives)
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-21T18:38:43.081315+00:00')).total_seconds()/60
    artifacts=['portable_demo.tar.gz','portable_demo/run.sh','assets/baseline/asset.json','assets/edited/asset.json',
      'media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv',
      'media/editor_05_reloaded.png','metrics/VALIDATION.json','metrics/SOURCE_DIAGNOSTICS.json','metrics/BUILD_REPLAY.json',
      'metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','browser_complete/BROWSER_VALIDATION.json','metrics/FINAL_AUDIT.json']
    assert all((unit/f).is_file() for f in artifacts)
    status=dict(stage='UNIT005_HANDOFF',execution_state='completed',completed_utc=now(),elapsed_minutes=elapsed,
      scientific_verdict='H1_H2_NOT_TESTED; historical P1 NO_GO and P2 ZERO_HEADROOM unchanged',
      engineering_validation='PASS for bounded real-model build/edit/browser/export/cold replay; visual quality partial',
      genuinely_ran_old_model=True,demo_progress=progress,source_commit=commit,artifacts=artifacts+['REPRODUCE_ZH.md'],
      tests_and_command_receipts=receipts,blockers=[],limitations=[negatives,
        'No historical Drums source cache: NOT_AVAILABLE, not a replay pass.',
        'Proxy-relative attachment and masks; same-model depth agreement is not independent accuracy.',
        'Offline finite orbit/zoom decode is not full temporal/occlusion certification; no realtime claim.',
        'Manual region authoring retained from Lego; only three height-region style controls tested on Drums.'],
      failure_records=['EXECUTION_AMENDMENT.json',*[x['path'] for x in failures]],next_action='continue',recommended_next_step=nextstep,
      supervisor_verification='reported_not_independently_verified',seal_scope='validated finite engineering evidence and explicit failure receipts; no scientific certification',
      resources=dict(cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,serial=True,gpu=False,nested_models=False,
        new_dependencies=False,servers_stopped=True,extra_recovery_extension=False))
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=nextstep,demo_progress=progress,
      reason='第三真实模型已完成完整对象/局部编辑/冷加载；数值世界框选仍是实际操作瓶颈，改善点击选区比继续增加模型数量更接近可用demo。',
      ranked_alternatives=['visible-surface click/rectangle region authoring','one hatch readability candidate with ink/coverage accounting','optional Ficus later'],
      estimated_next_minutes=35,deadline_jst='2026-10-22T10:00:00+09:00',no_new_science_after_jst='2026-10-22T09:20:00+09:00',science_wrap_jst='2026-10-22T09:45:00+09:00'))
    rows='\n'.join(f"| {a['view']} | {a['target_delta']:.2f} | {a['far_delta_fraction']:.1f} | {b['source_alpha_proxy_iou']:.5f} | {b['mean_depth_residual']:.6f} |" for a,b in zip(v['static'],d['views']))
    short=sum(x['shorter_than_half_requested'] for x in base.values())
    report=f'''# Unit005 — Drums real-model demo

工程执行 **completed**，外观 **partial**；H1/H2未测试。用时 {elapsed:.1f} 分钟。源码提交 `{commit}`。完整阅读BRIEF、851行大纲、最新P1/P2报告/NEXT与相关源，实际审阅unit004八视角完整对象及局部编辑图：Lego已可独立编辑前部，侧后孔洞、细杆缺失、底板拥挤仍在。本轮选择第三真实模型Drums，不重复toy门槛，不扫参数。

## Frozen protocol and source

原检查点 `{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，{model['audit']['count']:,}个Gaussian。输入相机来自对应 `transforms_train.json`（86帧）/`transforms_test.json`（16帧、文件指向val目录）；参考RGBA也来自该输入目录。原始数据有历史曝光可能，不称盲评。

`PROTOCOL.json` 在候选图前冻结：从train_r_7开始贪心角距选择24训练姿态，400²直接CPU渲染；alpha≥0.95、中心/平面深度差≤0.06、3×3跳变≤0.08，0.012体素/0.036截断TSDF。得到{proxy['vertices']:,}顶点/{proxy['faces']:,}面。没有训练、GT、旧ink或原始Gaussian中心拼造表面。该深度来自冻结vanilla GS协方差平面估计，不是独立测量或RaDe重训练。

Drums不在历史源缓存registry中。新增可选缓存诊断：未指定缓存记录NOT_AVAILABLE且all_arrays_exact=null；指定却缺失仍报错。新测试先真实ImportError/rc1后通过；实际旧Lego源数组的相同/扰动/缺失控制与已有相机、遮挡、附着、长度、区域规则共12测试通过。没有把缺少缓存伪称一致性通过。

人工世界z阈值 -0.15/0.42 按面中心保存标签，不是鼓/镲片语义。固定相机包括4原始视角与新67/157/247/337°虚拟视角；12旋转与6缩放预先冻结。三分区初始角度0/45/-25°，spacing0.045、length0.22、width1px；仅中区45→95°。三维路径基线{progress['baseline_paths']}条，编辑后{progress['edited_paths']}条，非目标808条字节保持；目标几何属于新版本。基线{short}/{progress['baseline_paths']}条路径短于请求长度一半，未靠删线伪造干净度。

## Actual results

| View | Target edit L1 | Far delta fraction | Proxy/source alpha IoU | Mean source depth residual |
|---|---:|---:|---:|---:|
{rows}

八视角上下区域图层/路径、深度、轮廓精确相同；固定2px带外变化全0，目标变化均非零。附着最大2.22e-16仅是相对自身代理的实现约束；上述IoU和深度残差也是同模型诊断，不是独立几何准确度。原RGBA轮廓IoU、合格像素/共同深度/遗漏数、分区覆盖和墨量逐视角保留在metrics。

实际查看完整八组参考RGB/代理/区域/排线、八组编辑前后、全部12旋转/6缩放及Firefox刷新图。鼓组、主要镲片可辨，顶视排线连续；侧后支架断裂、鼓沿粗糙、鼓体底部孔洞和短碎线明显，部分支撑仅剩漂离片段。中区同时包含鼓身/座椅等多个实体，不能称单个语义部件。所有26个静态/轨迹相机代理在框内；18帧均不同，FFV1全部解码与PNG精确，仍不是全路径时序认证。

真实Firefox软件渲染验证场景/标签、角度编辑、Orbit、Zoom、刷新相机保持。HTTP另外实跑角度/间距/长度/线宽/旋转/缩放六操作，非法spacing返回422。关闭服务器后下载ZIP用新CLI重绘，PNG与所有数组精确。`demo.py build --scene drums` 从原PLY再次完整执行24帧→TSDF→路径→首图，{build['seconds']:.2f}s，网格、三份路径及PNG/NPZ精确。打包、搬移解压后的 `./run.sh preview` 实际冷加载也精确；保存资产运行不需要原检查点。

## Failures, delivery and next

首构建收到SIGTERM，child=-15、outer=143、发送方/原因UNKNOWN；原部分输出保留attempt_interrupted。相同设置一次恢复rc0，原6份完成深度文件与恢复逐文件相同。HTTP首辅助测试因过时JS源码字符串断言rc1，在真实Firefox已通过的前提下修复测试；首尝试及自身清理收据保留，恢复六操作/导出rc0。另有测试runner相对路径错误rc2和只读历史路径猜测失败。全部区别记录EXECUTION_AMENDMENT，不改写失败码，没有延长55分钟时限或更换候选。

启动：`cd {unit/'portable_demo'} && ./run.sh viewer`；预览用 `./run.sh preview`。包 `{unit/'portable_demo.tar.gz'}` 含真实资产、源码、预览与视频。根DEMO_README_ZH包含三模型入口和Drums完整构建命令。精确命令/返回码在REPRODUCE_ZH与logs，状态/下一步见STATUS/NEXT，验证指标见metrics。

前unit004封存{len(old['files'])}文件及全部输入哈希未变；仅检查自身子进程组PID/comm，服务器/浏览器/计算进程已关闭。两核、数值单线程、串行；无GPU、安装、凭据、嵌套模型、push/merge。封存只覆盖验证过的有限工程证据与明确失败收据；不要求或伪造完整科学认证。监督状态reported_not_independently_verified。

NEXT=continue：{nextstep} 历史P1 NO_GO、P2 ZERO_HEADROOM保持，H1/H2未测试。
'''
    (unit/'REPORT_ZH.md').write_text(report)
    commands=['# 实际命令与返回码\n\n按启动时间排列；CPU串行，失败尝试保留。\n']
    for r in raw:commands.append(f"\n`{r['start_utc']}` — rc `{r['returncode']}`，{r['seconds']:.3f}s\n\n```bash\n{shlex.join(r['command'])}\n```\n")
    (unit/'REPRODUCE_ZH.md').write_text(''.join(commands))
    shutil.copy2('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md',root/'DEMO_README_ZH.md')
    delivery=dict(updated_utc=now(),execution_state='completed',visual_quality='partial',working_demo=True,current_unit='units/unit_005',
      available_models={'chair':'units/unit_002/portable_demo.tar.gz','lego':'units/unit_004/portable_demo.tar.gz','drums':'units/unit_005/portable_demo.tar.gz'},
      start_command=f'cd {unit}/portable_demo && ./run.sh viewer',demo_progress=progress,report='units/unit_005/REPORT_ZH.md',
      next_action='continue',recommended_next_step=nextstep,scientific_verdict=status['scientific_verdict'],
      supervisor_verification='reported_not_independently_verified')
    js(root/'DELIVERY_STATUS.json',delivery);js(unit/'DELIVERY_STATUS_SNAPSHOT.json',delivery)
    shutil.copy2(root/'DEMO_README_ZH.md',unit/'DEMO_README_ZH_SNAPSHOT.md')
    selected=[]
    for folder in ['assets','proxy','source_model','renders','metrics','media','source_snapshot','viewer_smoke']:
        selected.extend(f for f in (unit/folder).rglob('*') if f.is_file())
    selected.extend((unit/'logs').glob('*.receipt.json'));selected.extend((unit/'logs').glob('*.log'))
    selected.extend((unit/'logs').glob('*CLEANUP.json'))
    selected.extend((unit/'browser_complete').glob('*.json'));selected.extend((unit/'browser_complete').glob('*.png'))
    selected.extend((unit/'attempt_ui_assert').glob('*.json'));selected.extend((unit/'attempt_ui_assert').glob('*.log'))
    for name in ['PROTOCOL.json','INVENTORY.json','DEPENDENCIES.json','STATUS.json','REPORT_ZH.md','NEXT.json','SOURCE_LOCK.json',
      'SOURCE_DIFF.patch','EXECUTION_AMENDMENT.json','VISUAL_REVIEW.json','READING_RECORD.json','REPRODUCE_ZH.md',
      'DELIVERY_STATUS_SNAPSHOT.json','DEMO_README_ZH_SNAPSHOT.md','portable_demo.tar.gz']:
        selected.append(unit/name)
    files=[dict(path=str(f.relative_to(unit)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(set(selected))]
    js(unit/'SHA256_MANIFEST.json',dict(utc=now(),scope=status['seal_scope'],files=files,
       excluded='mutable browser profiles/runtime logs, interrupted numerical arrays, replay duplicate directories, orchestration scratch, final model response'))
    assert all(sha(unit/f['path'])==f['sha256'] for f in files)
    js(unit/'ENGINEERING_SEAL.json',dict(utc=now(),manifest='SHA256_MANIFEST.json',manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),
      file_count=len(files),source_commit=commit,execution_state='completed',scientific_seal=False,
      scope=status['seal_scope'],supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(status=str(unit/'STATUS.json'),files=len(files),elapsed_minutes=elapsed,next_action='continue')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True,type=Path);finish(p.parse_args().unit)
