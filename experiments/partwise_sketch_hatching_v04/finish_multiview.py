"""Seal only the finite Unit007 engineering evidence, with all limitations retained."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT,output_guard
from pathlib import Path
import datetime,json,shlex,shutil,subprocess

def finish():
    unit=output_guard(OUTPUT_ROOT/'units/unit_007')
    if (unit/'ENGINEERING_SEAL.json').exists():raise FileExistsError('already sealed')
    read=lambda name:json.loads((unit/name).read_text())
    p=read('PROTOCOL.json');v=read('metrics/VALIDATION.json');selection=read('selection/SELECTION_EVIDENCE.json')
    browser=read('browser_complete/BROWSER_VALIDATION.json');export=read('metrics/EXPORT_REPLAY.json')
    portable=read('metrics/PORTABLE_REPLAY.json');video=read('media/VIDEO_VALIDATION.json')
    assert browser['status']==export['status']==portable['status']=='PASS'
    assert v['status']=='PASS_WITH_AUTHORING_LOCALITY_LIMITATION'
    assert all(x['far_edit_L1']==0 for x in v['views'])
    assert all(x['all_decoded_frames_exact'] for x in video['videos'])
    assert all(sha(f)==h for f,h in p['input_sha256'].items())
    assert sha(p['original']['original_ply'])==p['original']['sha256']
    previous=Path(p['source_unit']);manifest=json.loads((previous/'SHA256_MANIFEST.json').read_text())
    assert all(sha(previous/f['path'])==f['sha256'] for f in manifest['files'])
    receipts=sorted([json.loads(f.read_text())|dict(path=str(f.relative_to(unit))) for f in (unit/'logs').glob('*.receipt.json')],key=lambda r:r['start_utc'])
    failed=[dict(path=r['path'],returncode=r['returncode']) for r in receipts if r['returncode']]
    assert {Path(r['path']).stem for r in failed}=={'tdd_red.receipt','navigation_red.receipt','zoom.receipt'}
    groups={json.loads(f.read_text())['own_process_group'] for f in (unit/'logs').glob('*.start.json')}
    for directory in ('browser_initial','browser_complete'):
        groups.update(x['pid'] for x in read(directory+'/CLEANUP.json')['children'])
    proc=subprocess.run(['ps','-g',','.join(map(str,sorted(groups))),'-o','pid=,comm='],capture_output=True,text=True)
    assert not proc.stdout.strip(), 'own child processes remain'
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-models-v04'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    snapshot=unit/'source_snapshot';snapshot.mkdir()
    for f in Path(__file__).parent.iterdir():
        if f.suffix in ('.py','.html','.cpp'):shutil.copy2(f,snapshot/f.name)
    assert all(sha(f)==sha(unit/'portable_demo/source'/f.name) for f in snapshot.iterdir())
    js(unit/'SOURCE_LOCK.json',dict(commit=commit,branch=branch,protocol_sha256=sha(unit/'PROTOCOL.json'),files={str(f.relative_to(unit)):sha(f) for f in sorted(snapshot.iterdir())}))
    (unit/'SOURCE_DIFF.patch').write_text(subprocess.check_output(['git','diff','3ddf92106bb93ba4d649c01e62f47482be60dad9','HEAD','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04'],text=True))
    prefix=[]
    for receipt in sorted((unit/'attempt_interrupted/zoom').glob('frame_*.json')):
        stem=receipt.stem
        for f in sorted(receipt.parent.glob(stem+'_*')):
            if f.suffix in ('.png','.npz'):
                assert sha(f)==sha(unit/'renders/zoom'/f.name)
                prefix.append(str(f.relative_to(unit)))
    js(unit/'metrics/INTERRUPTED_PREFIX_REPLAY.json',dict(complete_frames=len(list((unit/'attempt_interrupted/zoom').glob('frame_*.json'))),checked_files=prefix,all_exact=True,partial_trailing_files_not_certified=True))
    negatives=('Thin stands remain broken, rims rough, drum surfaces perforated and strokes fragmented. '
        'Manual target still contains nearby cymbal/drum/stand fragments and hidden omissions: 36 indexed-edge components, largest 495 of 718 faces. '
        'Full triangles can extend past rectangles and include previously occluded portions. The old test_r_79 clips the left edge by about 1.56 px.')
    js(unit/'VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent; no independent human/blind review',
        inspected=['construction/view_00_proxy.png','construction/view_01_proxy.png','construction/view_02_proxy.png',
            'selection/selection_all_views.png','media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png',
            'media/orbit_all_frames.png','media/zoom_all_frames.png','browser_initial/06_total_preview_after_refresh.png',
            'browser_complete/06_total_preview_after_refresh.png','browser_complete/09_orbit_zoom_export.png'],
        positives='Same upper cymbal surface can be accumulated from multiple views and edited. Camera navigation leaves saved path asset unchanged. Finite complete-object previews, browser actions and cold reload are real.',
        negatives=negatives,quality='partial',semantic_completeness='NOT_ESTABLISHED',independent_temporal_validation=False))
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-21T19:12:07.411962+00:00')).total_seconds()/60
    progress=dict(scene='drums',available_models=['chair','lego','drums'],genuinely_ran_old_model=True,
        original_gaussians=v['original_gaussians'],proxy_vertices=v['vertices'],proxy_faces=v['faces'],editable_regions=4,
        multi_view_draft=True,selection_operations=4,construction_views=3,face_counts=[s['after_faces'] for s in selection['steps']],
        first_view_faces=v['single_view_faces'],selected_faces=v['selected_faces'],new_faces_beyond_first=v['new_faces_beyond_first'],removed_from_first=v['removed_from_first'],
        selected_components=selection['selected_indexed_edge_components'],largest_component_faces=max(selection['component_face_counts']),
        baseline_paths=sum(a['paths'] for a in v['anchors']['baseline'].values()),edited_paths=sum(a['paths'] for a in v['anchors']['edited'].values()),
        retained_non_target_paths=sum(v['anchors']['baseline'][str(r)]['paths'] for r in (1,2,3)),donor_unselected_segments=v['source_segments_retained'],
        donor_unselected_segments_exact=True,style_edit_other_layers_exact=True,style_edit_far_delta_all_views=0.,
        authoring_far_delta=[dict(view=r['view'],L1=r['authoring_far_L1']) for r in v['views'] if r['authoring_far_L1']],
        static_views=8,complete_object_views=sum(r['complete_object'] for r in v['views']),orbit_frames=12,zoom_frames=6,
        all_trajectory_views_complete=True,all_video_frames_decoded_exact=True,
        actual_browser_pointer_and_keyboard=True,actual_browser_controls=True,navigation_does_not_regenerate_or_copy_asset=True,
        draft_page_refresh=True,typed_name_page_refresh=True,cold_reload_exact=True,exported_zip_cold_reload_exact=True,relocated_package_cold_reload_exact=True,
        full_original_model_rebuild_this_unit=False,original_model_reference_render_this_unit=True,visual_quality='partial',
        region_source='agent visually authored four rectangles in three frozen views; saved proxy face IDs, not original Gaussian IDs or automatic semantics',
        reasoning='真实Drums现在可跨视角累积/减去可见面，旋转不丢选区，不复制或重生成路径；总预览后一次提交，命名/局部风格编辑/导出冷加载均实跑。',remaining=negatives)
    next_step=('整理一个含Chair/Lego/Drums真实保存资产的可搬移多场景入口，让当前跨视角选区与四参数编辑在同一界面可用；'
        '在较干净的Lego铲斗完成一次有限选区/局部编辑/导出冷加载，记录误选，不修补几何或做阈值扫选。'
        '这一步完成后再决定是否用同一路径适配Ficus；不把Drums完美语义分部作为前置。')
    artifacts=['portable_demo.tar.gz','portable_demo/run.sh','SELECTION_RECIPE.json','assets/baseline/asset.json','assets/edited/asset.json',
        'selection/selection_all_views.png','selection/SELECTION_EVIDENCE.json','media/reference_proxy_regions_hatch.png',
        'media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv','browser_complete/BROWSER_VALIDATION.json',
        'metrics/VALIDATION.json','metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','REPRODUCE_ZH.md','SOURCE_LOCK.json']
    status=dict(stage='UNIT007_HANDOFF',execution_state='partial',completed_utc=now(),elapsed_minutes=elapsed,
        scientific_verdict='H1_H2_NOT_TESTED; historical P1 NO_GO and P2 ZERO_HEADROOM unchanged',engineering_validation=v['status'],
        genuinely_ran_old_model=True,demo_progress=progress,source_commit=commit,artifacts=artifacts,
        tests_and_command_receipts=[dict(path=r['path'],returncode=r['returncode'],seconds=r['seconds']) for r in receipts],
        blockers=[],limitations=[negatives,'Region authoring has measured 0.2 L1 far raster change in two views; no universal zero-leak claim.',
        'Self-proxy masks/attachment and same-model depths are not independent accuracy; finite decoded video is not full temporal certification.',
        'Draft/name survive page refresh only in the active session/tab; server restart requires a committed exported asset.'],
        failure_records=['INTERRUPTION.json','UI_NAME_REGRESSION.json','attempt_interrupted/','browser_initial/'],
        next_action='continue',recommended_next_step=next_step,supervisor_verification='reported_not_independently_verified',
        resources=dict(cpu_affinity=[0,1],numeric_threads=1,serial=True,gpu=False,nested_models=False,new_dependencies=False,servers_stopped=True))
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='当前单模型编辑流程已能实际使用；统一三个已运行模型的入口和保存流程比继续追逐Drums完美选区更接近可交付demo。',
        ranked_alternatives=['one portable multi-scene demo with actual Lego edit','one bounded hatch readability candidate','optional Ficus afterwards'],
        estimated_next_minutes=30,deadline_jst='2026-10-22T10:00:00+09:00',no_new_science_after_jst='2026-10-22T09:20:00+09:00',science_wrap_jst='2026-10-22T09:45:00+09:00'))
    rows='\n'.join(f"| {r['view']} | {r['target_edit_L1']:.2f} | {r['far_edit_L1']:.2f} | {r['authoring_far_L1']:.2f} | {r['target_ink_before']:.2f} / {r['target_ink_after']:.2f} |" for r in v['views'])
    report=f'''# Unit007 — Multi-view selection on real Drums

执行 **partial**：跨视角选面草稿、增减/撤销/总预览、一次提交、局部编辑、真实浏览器与导出/搬移冷加载均已实跑；完整语义部位和干净几何未达成。用时{elapsed:.1f}分钟。H1/H2未测试。源码 `{commit}`。

## Review and frozen scope

完整读取BRIEF与851行大纲，P1 unit010/P2 experiment001报告/NEXT/相关源码，unit006报告/NEXT、screen selection/region/viewer/demo实现，并实际查看八视角原RGB/代理/标签/排线/编辑对照。旧Drums整体可辨，但单视角上区patch误含多个部位、背面缺失；选择本轮跨视角编辑，不扩第四模型或做几何/风格扫选。

先冻结SCOPE（输入哈希、构建与评价相机、固定几何/风格、最多6次作者操作），实际渲染三构建代理图；通过一个面点的投影识别同一上方镲面，人工一次指定4矩形，再冻结PROTOCOL/SELECTION_RECIPE，才运行新区域及评价。不是盲标注或人类交互实验。原静态训练/测试相机历史曝光；4个新虚拟静态相机和12/6轨迹事前冻结。

原PLY `{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，{v['original_gaussians']:,} Gaussian。继承unit005真实模型CPU深度TSDF代理（{v['vertices']:,}顶点/{v['faces']:,}面），输入为unit006保存的原三区资产；再次直接渲染原PLY八参考视角。本轮未重跑完整融合，不是GT、独立几何真值或原Gaussian面ID。

## Actual changes and results

新增相机独立的固定代理面草稿、add/subtract/replace、单步撤销/清空、当前视角总预览；旋转/缩放使用相机专用入口，不写资产、不重生成路径。完成选择后只提交一次区域。CLI新增 `--selection-recipe`，按相同网格哈希与操作顺序重放；旧单框和世界框入口保留。草稿存在时限制风格更改以避免底层资产变动。页面刷新保留草稿/相机/输入名称；服务器重启需先提交导出。

三构建视角157°/55°、337°/55°、247°/35°，distance4.9，512²。source区3，共5854面。矩形操作：replace[116,125,218,214]；add[297,143,398,218]；add[224,78,309,141]；回第一视角subtract[116,204,218,240]。选面640→855→911→718，最终较第一框新增227面、移除149面；跨视角并集没有隐藏扩张。第二构建视角可见覆盖4074.25→4878.25像素，第一视角5568.75→5454.75，第三2924.25→3048.25；这是作者选面覆盖，不是语义完整度评分。

选区36个索引边连通片，最大495面；图中仍有邻近镲片、鼓沿/支架碎片，且隐藏侧未补全。不能声称完整镲片。保存整三角面，可能越出框或包含之前遮挡的局部。`selection/selection_all_views.png`展示这些误选与遗漏，未清理以追求完美门槛。

角度只改新region4的-25→35°。新区域73→79路径，全对象{progress['baseline_paths']}→{progress['edited_paths']}路径；非目标{progress['retained_non_target_paths']}路径、来源区未选择2643段全部字段保持，mesh顶点/面索引不变。八视角其他图层、深度和轮廓精确不变。最大自身代理锚定误差2.22e-16，不是独立几何精度。

| View | Target angle-edit L1 | Far angle-edit L1 | Far region-creation L1 | Target ink before / after |
|---|---:|---:|---:|---:|
{rows}

使用实际4子像素中任一命中目标面的mask及固定2px边界带。角度编辑远区L1全部0；作者创建区域在test_r_27与orbit83各约0.2，原因未独立定位，保留partial，不更改渲染器、目标区或边界阈值。

## Actual tests and replay

TDD两次真实红灯保留：缺SelectionDraft模块rc1、Editor缺navigate方法rc1；最终3项行为测试通过，含真实多视角集合增减/撤销、错误recipe/hash/op、选面冷保存/非目标保持、相机导航不修改资产、过期token/视图拒绝、草稿存在时风格变更拒绝。Firefox软件渲染使用真实鼠标拖框及键盘命名，验证清空、四次多视角操作、撤销再做、刷新、总预览、一次提交、四个风格参数、资产撤销、Orbit/Zoom与下载。与CLI选面/所有路径精确一致。

初次浏览器检查rc0但截图复核发现刷新后名称退回My region且当前选择回旧区；原检查漏测名称。保留browser_initial、初次冷加载/收据；修复标签页名称与会话选中区状态，增加实际键盘命名/名称/选区断言后同操作重跑rc0。没有换选区或新候选。

关闭服务器后，导出ZIP在新CLI进程冷重绘PNG/数组精确。portable_demo.tar.gz搬移解压后实际 `./run.sh preview` 精确；包内真实网格、标签、固定路径、源、配方、预览/视频均可重放，无需原PLY，未捆绑Python环境，其他平台未测。

已实际审阅全部八视角对照、三构建选区、八组编辑、12旋转/6缩放与浏览器截图。7/8静态完整入框，旧test_r_79左缘约1.56px裁切保留；18轨迹完整且图像各异。18个FFV1视频帧完整解码与PNG精确，不是全路径时序认证。支架破碎、鼓沿/鼓体孔洞与短碎线未改善。

## Failures, safety and handoff

外层执行在zoom收到外部SIGTERM，outer143、child-15、来源UNKNOWN；保留attempt_interrupted和原日志。确认自身进程组退出后，仅同协议重跑zoom，继续原先未执行cold/validate/media；已完整写出的{len(prefix)}个中断前图/数组与重跑精确一致。另一次解释器路径误写的只读-V命令rc127、P2只读报告初次路径猜错已记录。没有额外超时恢复窗口。

上unit006封存{len(manifest['files'])}文件及当前所有输入复核相同；CPU affinity[0,1]、数值单线程、计算串行、无GPU/新依赖/凭据/嵌套模型/push/merge；自身浏览器/服务器/计算进程退出。科学seal=false，封存仅有限工程证据和明确失败；监督状态reported_not_independently_verified。

启动：`cd {unit}/portable_demo && ./run.sh viewer`；冷预览`./run.sh preview`；从原三区开始 `DEMO_ASSET=original ./run.sh viewer`。详细用法在根DEMO_README_ZH，精确命令/返回码在REPRODUCE_ZH及logs。真实对照/视频在media，累计选面在selection，浏览器在browser_complete，可搬移包portable_demo.tar.gz。

NEXT=continue：{next_step}
'''
    (unit/'REPORT_ZH.md').write_text(report)
    commands=['# Unit007 actual commands and return codes','','所有为实际执行，失败保留；初次浏览器/导出已移入 *_initial，缩放中断产物在attempt_interrupted。','']
    for r in receipts:commands += [f"## {Path(r['path']).stem}",'',f"returncode={r['returncode']}；seconds={r['seconds']:.3f}",'','```bash',f"cd {shlex.quote(r['cwd'])}",shlex.join(r['command']),'```','']
    (unit/'REPRODUCE_ZH.md').write_text('\n'.join(commands))
    js(unit/'metrics/FINAL_AUDIT.json',dict(utc=now(),branch=branch,commit=commit,previous_unit_files_checked=len(manifest['files']),all_prior_hashes_exact=True,
        own_child_groups_checked=sorted(groups),remaining_pid_comm=proc.stdout,task_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),
        root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free))
    shutil.copy2('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md',OUTPUT_ROOT/'DEMO_README_ZH.md')
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(unit='unit_007',execution_state='partial',demo_progress=progress,entrypoint=str(unit/'portable_demo/run.sh'),
        portable_package=str(unit/'portable_demo.tar.gz'),report=str(unit/'REPORT_ZH.md'),next_action='continue',supervisor_verification='reported_not_independently_verified'))
    selected=[]
    for folder in ('assets','renders','source_model','media','selection','construction','metrics','logs','source_snapshot','attempt_interrupted'):
        selected += [f for f in (unit/folder).rglob('*') if f.is_file()]
    for folder in ('browser_complete','browser_initial'):
        selected += [f for f in (unit/folder).iterdir() if f.is_file()]
    selected += [unit/name for name in ('SCOPE.json','PROTOCOL.json','SELECTION_RECIPE.json','READING_RECORD.json','STATUS.json','REPORT_ZH.md','NEXT.json',
        'REPRODUCE_ZH.md','INTERRUPTION.json','UI_NAME_REGRESSION.json','VISUAL_REVIEW.json','SOURCE_LOCK.json','SOURCE_DIFF.patch','DEPENDENCIES.json','portable_demo.tar.gz')]
    files=[dict(path=str(f.relative_to(unit)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(set(selected))]
    js(unit/'SHA256_MANIFEST.json',dict(utc=now(),scope='finite engineering evidence plus explicit failed attempts; no scientific certification; no mutable profiles/orchestration/runtime response files',files=files))
    assert all(sha(unit/f['path'])==f['sha256'] for f in files)
    js(unit/'ENGINEERING_SEAL.json',dict(utc=now(),execution_state='partial',scientific_seal=False,manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),files=len(files),
        validated_scope='real model, multi-view face operations, path locality, actual browser, cold replay and finite video; semantic completeness and authoring raster locality partial',
        supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='partial',elapsed_minutes=elapsed,files=len(files),commit=commit)))

if __name__=='__main__':finish()
