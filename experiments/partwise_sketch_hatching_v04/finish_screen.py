"""Record partial engineering progress without converting failed checks into a science pass."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT,output_guard
from pathlib import Path
import json,shutil,subprocess,datetime,shlex

def finish():
    unit=output_guard(OUTPUT_ROOT/'units/unit_006')
    if (unit/'ENGINEERING_SEAL.json').exists():raise FileExistsError('already sealed')
    read=lambda name:json.loads((unit/name).read_text())
    p=read('PROTOCOL.json');v=read('metrics/VALIDATION.json')
    browser=read('browser_complete/BROWSER_VALIDATION.json')
    export=read('metrics/EXPORT_REPLAY.json');portable=read('metrics/PORTABLE_REPLAY.json')
    video=read('media/VIDEO_VALIDATION.json')
    assert browser['status']==export['status']==portable['status']=='PASS'
    assert v['status']=='PASS_WITH_AUTHORING_LOCALITY_LIMITATION'
    assert all(x['far_edit_L1']==0 for x in v['views'])
    assert all(x['all_decoded_frames_exact'] for x in video['videos'])
    assert all(sha(f)==h for f,h in p['input_sha256'].items())
    assert sha(p['original']['original_ply'])==p['original']['sha256']
    old=Path(p['source_unit']);manifest=json.loads((old/'SHA256_MANIFEST.json').read_text())
    assert all(sha(old/f['path'])==f['sha256'] for f in manifest['files'])
    receipts=sorted([json.loads(f.read_text())|dict(path=str(f.relative_to(unit))) for f in (unit/'logs').glob('*.receipt.json')],key=lambda x:x['start_utc'])
    failed=[dict(path=r['path'],returncode=r['returncode']) for r in receipts if r['returncode']]
    assert {Path(x['path']).stem for x in failed}=={'tdd_red.receipt','validate.receipt','validate_mask_recovery.receipt','browser.receipt'}
    groups={json.loads(f.read_text())['own_process_group'] for f in (unit/'logs').glob('*.start.json')}
    groups.update(x['pid'] for x in read('browser_complete/CLEANUP.json')['children'])
    groups.update(read('browser_interrupted/INTERRUPTION_CLEANUP.json')['own_child_groups'])
    proc=subprocess.run(['ps','-g',','.join(map(str,sorted(groups))),'-o','pid=,comm='],capture_output=True,text=True)
    assert not proc.stdout.strip(), 'own child process groups still alive'
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-models-v04'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    snap=unit/'source_snapshot';snap.mkdir()
    for file in Path(__file__).parent.iterdir():
        if file.suffix in ('.py','.html','.cpp'):shutil.copy2(file,snap/file.name)
    assert all(sha(file)==sha(unit/'portable_demo/source'/file.name) for file in snap.iterdir())
    js(unit/'SOURCE_LOCK.json',dict(commit=commit,branch=branch,protocol_sha256=sha(unit/'PROTOCOL.json'),
        files={str(f.relative_to(unit)):sha(f) for f in sorted(snap.iterdir())}))
    (unit/'SOURCE_DIFF.patch').write_text(subprocess.check_output(['git','diff','cf1d908478f6811d3e784168d5c6badd7519c5c1','HEAD','--',
        'experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04'],text=True))
    failures=dict(failed_commands=failed,
        tdd='Expected ModuleNotFoundError before screen_selection implementation; final four behavior tests pass.',
        validation='Initial point-sampled target mask missed subpixel islands: 0.2 L1 in two views. Diagnostic uses any of the SAME four renderer rays, fixed 2px band, zero style-edit far delta. Original point-mask numbers retained. No rerender or parameter change.',
        authoring='Second validation found genuine nonzero raster side effects of region creation: 0.4/0.2/0.2 L1 in three views outside fixed target band. No renderer fix or threshold relaxation; marked partial and measured. Cause not independently resolved.',
        browser='First browser run externally SIGTERM: child -15, outer 143, sender/cause UNKNOWN. Owned children identified by test-specific loopback ports and cleaned; rerun same protocol succeeded. Cleanup signal handler/PID receipts added.',
        ancillary=[dict(returncode=1,action='first diagnostic',reason='forgot to resize 400-pixel protocol camera to rendered 512 before reshape; no output produced'),
            dict(returncode=1,action='read-only inventory',reason='missing unit011 report and absent interrupted-browser CLEANUP; then read actual P1 unit010 and own port receipts')],
        extra_recovery_extension=False,images_or_geometry_changed_for_validation=False)
    js(unit/'EXECUTION_AMENDMENT.json',failures)
    negatives='Thin stands remain broken, rims rough and some drum surfaces perforated. Visible selection is a patch with islands and hidden omissions, not a whole semantic part. Saved full triangles may include previously occluded portions. Original test_r_79 clips the left edge by about 1.56 px.'
    js(unit/'VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent; no independent human or blind assessment',
        inspected=['media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit_all_frames.png',
            'media/zoom_all_frames.png','browser_complete/02_selection_preview.png','browser_complete/03_region_saved.png','browser_complete/07_reload_export.png'],
        all_static_views=8,all_orbit_frames=12,all_zoom_frames=6,
        positives='Complete recognizable kit in most views; visible upper patch and local angle change; actual pointer drag preview, save, edit, orbit, zoom, undo and reload.',
        negatives=negatives,quality='partial',authoring_raster_side_effect_not_resolved=True))
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-21T18:57:20.994762+00:00')).total_seconds()/60
    progress=dict(scene='drums',genuinely_ran_old_model=True,available_models=['chair','lego','drums'],
        original_gaussians=v['original_gaussians'],proxy_vertices=v['vertices'],proxy_faces=v['faces'],editable_regions=4,
        selected_faces=v['selected_faces'],source_region_faces=v['inherited_source_faces'],
        baseline_paths=sum(a['paths'] for a in v['anchors']['baseline'].values()),
        edited_paths=sum(a['paths'] for a in v['anchors']['edited'].values()),
        retained_non_target_paths=sum(v['anchors']['baseline'][str(r)]['paths'] for r in (1,2,3)),
        donor_unselected_segments_exact=True,style_edit_other_layers_exact=True,style_edit_far_delta_all_views=0.,
        authoring_far_delta=[dict(view=x['view'],L1=x['authoring_far_L1']) for x in v['views'] if x['authoring_far_L1']],
        static_views=8,complete_object_views=sum(x['complete_object'] for x in v['views']),
        orbit_frames=12,zoom_frames=6,all_trajectory_views_complete=True,all_video_frames_decoded_exact=True,
        actual_browser_pointer_pick_and_drag=True,actual_browser_controls=True,cold_reload_exact=True,
        exported_zip_cold_reload_exact=True,relocated_package_cold_reload_exact=True,
        full_original_model_rebuild_this_unit=False,original_model_reference_render_this_unit=True,
        visual_quality='partial',region_source='manual visible proxy face IDs from one frozen view; not automatic semantics',
        reasoning='原有Drums三高度区现在可直接在图像上点选并拖框保存局部3D面集合；真实浏览器操作与CLI、导出冷加载一致。更接近可用编辑demo，无需猜世界坐标。',
        remaining=negatives+' Small authoring raster side effects remain measured; angle editing has exact other layers.')
    next_step='为可见面选区增加跨视角累积的添加/减去操作和保存前总预览，最终一次提交固定face IDs；在同一Drums或Lego上完成一个更完整的人工部位并验证非目标路径、冷加载。保持同一代理，不借此宣称自动语义或修复薄结构。小量作者操作栅格副作用记录为已知限制，不把追求零toy门槛作为推进前置。'
    artifacts=['portable_demo.tar.gz','portable_demo/run.sh','assets/baseline/asset.json','assets/edited/asset.json',
        'media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv',
        'browser_complete/BROWSER_VALIDATION.json','metrics/VALIDATION.json','metrics/MASK_DIAGNOSTIC.json',
        'metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','REPRODUCE_ZH.md','SOURCE_LOCK.json']
    status=dict(stage='UNIT006_HANDOFF',execution_state='partial',completed_utc=now(),elapsed_minutes=elapsed,
        scientific_verdict='H1_H2_NOT_TESTED; historical P1 NO_GO and P2 ZERO_HEADROOM unchanged',
        engineering_validation=v['status'],genuinely_ran_old_model=True,demo_progress=progress,source_commit=commit,
        artifacts=artifacts,tests_and_command_receipts=[dict(path=r['path'],returncode=r['returncode'],seconds=r['seconds']) for r in receipts],
        blockers=[],limitations=[negatives,'Region creation has measured small raster changes outside the selection band; no zero-leak claim for authoring.',
            'Self-proxy attachment/masks and same-model depth are not independent accuracy; finite decoded video is not full temporal certification.'],
        failure_records=['EXECUTION_AMENDMENT.json','attempt_validation/','browser_interrupted/'],
        next_action='continue',recommended_next_step=next_step,supervisor_verification='reported_not_independently_verified',
        resources=dict(cpu_affinity=[0,1],numeric_threads=1,serial=True,gpu=False,nested_models=False,new_dependencies=False,servers_stopped=True))
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='单视角框选现在可用，但其背面遗漏和碎片使完整部位编辑仍困难；跨视角增减选择比扩到第四模型更接近可用demo。',
        ranked_alternatives=['multi-view add/subtract face selection','one bounded hatch readability candidate','optional Ficus later'],
        estimated_next_minutes=35,deadline_jst='2026-10-22T10:00:00+09:00',no_new_science_after_jst='2026-10-22T09:20:00+09:00',science_wrap_jst='2026-10-22T09:45:00+09:00'))
    rows='\n'.join(f"| {x['view']} | {x['target_edit_L1']:.2f} | {x['far_edit_L1']:.2f} | {x['authoring_far_L1']:.2f} | {x['target_ink_before']:.2f} / {x['target_ink_after']:.2f} |" for x in v['views'])
    report=f'''# Unit006 — Visible-face authoring on real Drums

执行 **partial**：真实旧模型上的点选、可见拖框、保存局部区、风格编辑、浏览器/CLI导出冷加载已实跑；作者操作的少量区域外栅格变化与粗几何限制仍保留。用时{elapsed:.1f}分钟。H1/H2未测试。源码提交 `{commit}`。

## Review and frozen scope

完整读取BRIEF及851行大纲，最新P1 unit010/P2报告、NEXT与相关源，检查unit005的全部八组原RGB/代理/区域/排线和编辑图。Drums鼓组可辨，但三高度区牵连多个实体，侧后支架破碎。选择提升已有模型选区可用性，未增加第四模型或扫描几何/风格参数。

原PLY `{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，360,012个Gaussian。本轮固定unit005真实模型深度TSDF代理（16,839顶点/29,999面），再次直接CPU渲染原PLY八参考视角；不是重建、GT或独立几何真值。协议先于候选输出冻结：相机157°/24°/4.9，512²图像边坐标矩形[128,128,260,240]，来源上区3，2x首命中射线。选中1,291/5,854面，保存真实代理face IDs，非原高斯行号。

新界面点选已有区、拖框粉色预览、命名保存、撤销与下载。完全无可见射线命中的面不选；整个三角面保存，部分面可能越过矩形或包含原遮挡部分。该区域是人工可见表面patch，有碎片和背面遗漏，不是完整语义镲片。世界框选模式仍保留并明确含隐藏侧。

## Actual results

只把新区域角度-25→35°。baseline {progress['baseline_paths']}条/edited {progress['edited_paths']}条；新区域143→140条，非目标1,476条字节保持，原上区未选择的2,334段全部字段保持，网格顶点/面索引不变。原区域在新边界的路径会截短。附着最大2.22e-16只证明相对自身代理实现。

| View | Target angle-edit L1 | Far angle-edit L1 | Far region-creation L1 | Target ink before / after |
|---|---:|---:|---:|---:|
{rows}

目标mask取实际四子像素射线中任一命中目标面，边界带仍固定2px；三份非目标排线图层、深度、轮廓精确不变。原单子像素标签mask漏掉小面岛，在train_r_7和orbit259各报0.2 L1，原数字保留于MASK_DIAGNOSTIC与失败日志，不把其当作独立真值。作者操作另在test_r_79/orbit259/orbit349报0.4/0.2/0.2远区L1，原因尚未独立定位，**没有宣称作者操作零泄漏**，没有改图或扩大容差以通过。

实际查看八组完整对象对照、编辑前后、全部12旋转/6缩放和浏览器预览/保存/刷新截图。7/8静态完整在框内，旧test_r_79左缘约1.56px裁切保留；18轨迹都完整且图像各异。全部FFV1帧解码与PNG精确，不是完整时序认证。薄支架缺失、鼓沿噪声、孔洞、短碎线与patch碎片仍可见。新虚拟评价姿态/轨迹事先冻结；旧训练/测试有历史曝光，不称盲评。

## Tests and replay

TDD先真实缺模块rc1后通过。最终4行为测试覆盖真实Drums首命中选面、非法坐标、解析遮挡、保存/编辑/冷读非目标保持，以及旧Lego世界框选路径逐文件精确回归。真实Firefox软件渲染通过实际鼠标点选/背景拒绝/缩放图像上的拖框、预览不修改、保存、角度/间距/长度/线宽、撤销、Orbit、Zoom、刷新和导出；过期视图/预览请求返回422。浏览器选面/路径与CLI完全一致。

服务器关闭后导出ZIP在新CLI进程重绘，PNG/数组精确；portable_demo.tar.gz搬移解压后的 `./run.sh preview` 也实际冷加载精确。包有真实网格、标签、固定路径、源码、预览、视频，无需原PLY；未捆绑Python环境，其他平台未测。本轮没有重跑完整深度融合，unit005原PLY全链重建证据按继承标记。

## Failures and delivery

两次原验证失败rc1保留：第一次标签采样不完整，第二次作者操作真实小量远区变化；最终记录partial而非修图换阈值。首次浏览器收到外部SIGTERM（child -15、outer143、来源UNKNOWN），当时点选/拖框截图保留；按本轮独有本机端口确认并清理自身子进程，添加中断清理/PID收据后同设置一次重跑rc0。一次诊断忘记相机resize导致reshape rc1，未产出数据。详见EXECUTION_AMENDMENT；所有原日志保留，未申请额外时间恢复。

启动 `cd {unit}/portable_demo && ./run.sh viewer`，冷预览 `./run.sh preview`；从原三区操作用 `DEMO_ASSET=original ./run.sh viewer`。精确命令/返回码见REPRODUCE_ZH及logs；完整图 `media/reference_proxy_regions_hatch.png`，编辑图 `media/local_edit_all_views.png`，视频 `media/orbit.mkv` / `zoom.mkv`，浏览器 `browser_complete/`，可搬移包 `portable_demo.tar.gz`。

上unit005封存{len(manifest['files'])}文件及所有当前输入哈希复核未变；仅授权分支/工作树写代码，输出在当前unit。数值单线程、两核、串行、无GPU/新依赖/凭据/嵌套模型/push/merge；自身服务器/浏览器/计算进程已清理。封存仅为已验证有限工程证据与明确失败记录，不是科学认证；监督状态reported_not_independently_verified。

NEXT=continue：{next_step}
'''
    (unit/'REPORT_ZH.md').write_text(report)
    commands=['# Unit006 exact commands and return codes','', '所有条目为实际执行；失败码保留。当前源码与初次失败版本区别见SOURCE_DIFF和attempt_validation。','']
    for r in receipts:commands += [f"## {Path(r['path']).stem}",'',f"returncode={r['returncode']}；seconds={r['seconds']:.3f}",'','```bash',f"cd {shlex.quote(r['cwd'])}",shlex.join(r['command']),'```','']
    (unit/'REPRODUCE_ZH.md').write_text('\n'.join(commands))
    audit=dict(utc=now(),branch=branch,commit=commit,previous_unit_files_checked=len(manifest['files']),all_prior_hashes_exact=True,
        own_child_groups_checked=sorted(groups),remaining_pid_comm=proc.stdout,serial_receipts=True,
        task_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),
        root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free)
    js(unit/'metrics/FINAL_AUDIT.json',audit)
    shutil.copy2('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md',OUTPUT_ROOT/'DEMO_README_ZH.md')
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(unit='unit_006',execution_state='partial',demo_progress=progress,
        entrypoint=str(unit/'portable_demo/run.sh'),portable_package=str(unit/'portable_demo.tar.gz'),
        report=str(unit/'REPORT_ZH.md'),next_action='continue',supervisor_verification='reported_not_independently_verified'))
    # Mutable browser profiles, runtime response files, relocation/runs and orchestration are never sealed.
    selected=[]
    for folder in ('assets','renders','source_model','media','metrics','logs','source_snapshot','attempt_validation'):
        selected += [f for f in (unit/folder).rglob('*') if f.is_file()]
    for folder in ('browser_complete','browser_interrupted'):
        selected += [f for f in (unit/folder).iterdir() if f.is_file()]
    selected += [unit/name for name in ('PROTOCOL.json','READING_RECORD.json','STATUS.json','REPORT_ZH.md','NEXT.json',
        'REPRODUCE_ZH.md','EXECUTION_AMENDMENT.json','VISUAL_REVIEW.json','SOURCE_LOCK.json','SOURCE_DIFF.patch','DEPENDENCIES.json','portable_demo.tar.gz')]
    files=[dict(path=str(f.relative_to(unit)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(set(selected))]
    js(unit/'SHA256_MANIFEST.json',dict(utc=now(),scope='finite validated engineering evidence plus explicit failures; no scientific certification',files=files))
    assert all(sha(unit/f['path'])==f['sha256'] for f in files)
    js(unit/'ENGINEERING_SEAL.json',dict(utc=now(),execution_state='partial',scientific_seal=False,
        manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),files=len(files),validated_scope='real model, selection identity, local style edit, browser pointer actions, cold replay, finite video; authoring raster locality is partial',
        supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='partial',elapsed_minutes=elapsed,files=len(files),commit=commit)))

if __name__=='__main__':finish()
