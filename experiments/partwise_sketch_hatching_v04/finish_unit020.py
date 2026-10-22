"""Finalize validated unit020 evidence only; never touches orchestration/old units."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT,output_guard
from pathlib import Path
import datetime,json,shutil,difflib,subprocess,os
from unit020_run import U,PREV,SOURCE,protocol,hashes,ASSET

def main():
    output_guard(U);p=protocol();assert hashes(ASSET)==p['inputs']
    required=['tests','reference','candidate','static','stage','browser','cold_browser','media_stage','cold_orbit','cold_zoom','package_build','package_check']
    receipts={f.name.removesuffix('.receipt.json'):json.loads(f.read_text()) for f in (U/'logs').glob('*.receipt.json')}
    assert all(receipts[n]['returncode']==0 for n in required)
    real=json.loads((U/'metrics/REAL_ASSET_TEST.json').read_text());loc=json.loads((U/'metrics/LOCALITY.json').read_text())
    reference=json.loads((U/'source_model/RECEIPT.json').read_text())
    assert reference['original_gaussians']==256690 and len(reference['views'])==4
    assert json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())['archive_sha256']==sha(U/'portable_demo.tar.gz')
    cold=json.loads((U/'metrics/COLD_REPLAY.json').read_text());assert sum(v['frame_count'] for v in cold.values())==18
    assert all(v['all_png_exact'] and v['all_arrays_exact'] for v in cold.values())
    children=[]
    for folder in ('browser','cold_browser'):
        assert json.loads((U/folder/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
        records=json.loads((U/folder/'CLEANUP.json').read_text())['children']
        for r in records:
            try:os.kill(r['pid'],0)
            except ProcessLookupError:pass
            else:raise AssertionError('owned child PID still exists')
        children.extend(records)
    r=json.loads((U/'logs/relocated_viewer_cleanup.json').read_text())
    try:os.kill(r['pid'],0)
    except ProcessLookupError:pass
    else:raise AssertionError('relocated viewer PID still exists')
    children.append(r)
    js(U/'metrics/OWN_PROCESS_CLEANUP.json',dict(utc=now(),all_recorded_child_PIDs_absent=True,children=children))
    js(U/'metrics/RESOURCES.json',dict(utc=now(),cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,
        serial_numerical_execution=True,gpu_used=False,root_free_bytes=shutil.disk_usage('/').free,
        hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
        task_output_bytes_before_final_snapshot=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file())))
    before=json.loads((U/'SOURCE_BEFORE.json').read_text());current=hashes(SOURCE)
    changed=[k for k,v in before.items() if current.get(k)!=v]
    assert not changed,changed
    js(U/'SOURCE_FINAL.json',dict(source_files=current,preexisting_source_unchanged=True,added_sources=sorted(set(current)-set(before))))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    introduced=[SOURCE/n for n in ('unit020_run.py','test_chair_seat_selection.py','unit020_browser.py','unit020_delivery.py','finish_unit020.py')]
    introduced += [SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04'/n for n in ('UNIT020_PROTOCOL.json','UNIT020_DEMO_README_ZH.md')]
    patch=''
    for f in introduced:patch+=''.join(difflib.unified_diff([],f.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+str(f.relative_to(SOURCE.parents[1]))))
    (U/'UNIT020_DIFF.patch').write_text(patch)
    next_step='让人工划分新区域在参数不变时保留原有笔触外观：当前author会重生成目标路径，四视角即使angle95不变也有32–467.8的图像L1变化。先用本轮真实Chair选区写失败的无外观变化测试，再实现保留选中原路径段/显式父ID映射的划区模式，保证非目标原样；随后只改region4角度、浏览器保存与冷导入。保留当前两矩形配方，不同时调边界、几何或风格。'
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],newly_rendered_model='chair',
        original_PLY_newly_rendered=True,original_gaussians=256690,original_GS_views=4,complete_static_states=12,
        manual_selection=dict(region=4,faces=2704,source_region_faces=17768,rectangle_steps=2,second_view_added_faces=173,
            semantic_completeness=False,geometry_exact=True,unselected_source_segments_retained=5491),
        local_style_edit='Manual seat surface patch only, angle95->65; mesh and region1/2/3 paths/styles/layers exact',
        target_interior_L1=[v['angle_delta']['target_interior']['L1'] for v in loc['views']],
        far_other_L1=[v['angle_delta']['far_other']['L1'] for v in loc['views']],
        far_background_L1=[v['angle_delta']['far_background']['L1'] for v in loc['views']],
        authored_same_style_is_noop=False,actual_browser_edit_undo_save=True,cold_new_server_browser_import_exact=True,
        motion_frames=18,lossless_video_decoded_exact_frames=18,mp4_decoded_frames=18,cold_replay_PNG_arrays_exact_frames=18,
        relocated_tar_CLI_author_edit_export_and_import=True,defaults_and_inherited_examples_unchanged=True,
        optional_example='chair_seat_patch',visual_quality='partial; useful local artistic control, visible patch borders and original proxy defects retained',
        reasoning='A real Chair now offers a smaller saved, editable seat patch in the runnable catalog; local editing no longer changes the entire middle height band. Browser save, cold reload, motion and relocated regeneration were exercised. This advances control, not independent reconstruction quality.')
    limits=['代理来自旧vanilla GS的CPU深度融合，含一次继承平滑；本轮几何未变。不是独立实测表面、自动分割或原高斯ID。',
        '两个agent手工矩形仅选可见整三角形；2704面是座面局部，不是完整语义座垫。矩形/锯齿边界、侧后小碎面保留。',
        '划区时现有工具重生成目标笔触，angle95不变也改变间断位置；原始→划区与划区→改角两阶段分开报告。',
        '改角使正面墨量下降、侧面上升，未做匹配墨量审美比较；不宣称整体画质、H1/H2/H5改善。',
        '四曝光视角和18帧是有限工程证据；零远区变化使用同代理标签及固定2px带，不是独立语义、全遮挡或时序稳定性认证。',
        '仅当前Linux CPU依赖环境实际验证；包不含Python/依赖二进制和原始PLY。']
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-22T07:42:47.619070+09:00')).total_seconds()/60
    artifacts=['PROTOCOL.json','SELECTION_RECIPE.json','SELECTION_FREEZE.json','assets/authored','assets/edited','metrics/SELECTION.json',
        'metrics/REAL_ASSET_TEST.json','metrics/LOCALITY.json','metrics/VISUAL_REVIEW.json','media/source_reference_all_views.png','media/full_object_before_after.png',
        'media/selection_all_views.png','media/chair_orbit.mp4','media/chair_zoom.mp4','browser/BROWSER_VALIDATION.json','cold_browser/BROWSER_VALIDATION.json',
        'metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','PACKAGE_README_ZH.md','source_snapshot','UNIT020_DIFF.patch','EVIDENCE_SHA256.json']
    status=dict(stage='UNIT_COMPLETE_MANUAL_SEAT_EXAMPLE',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS',scientific_verdict='H1_H2_H5_NOT_TESTED; OPTIONAL_MANUAL_ARTISTIC_CONTROL_ONLY',demo_progress=progress,
        artifacts=artifacts,tests=dict(real_asset_tests=2,TDD='No material algorithm changed; existing algorithms exercised on real saved Chair without artificial red',
            actual_Firefox=True,command_receipts={k:dict(returncode=v['returncode'],path='logs/'+k+'.receipt.json') for k,v in sorted(receipts.items())}),
        blockers=[],limitations=limits,scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='完整对象、座面局部修改、保存和冷重开已可用。划区本身的意外笔触重排是实际可复现的小瓶颈，修复它可使后续局部编辑更直观，不需增加模型或扫参。',
        estimated_next_minutes=30,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    command_rows='\n'.join(f"| {k} | {v['returncode']} | {v['seconds']:.3f} |" for k,v in sorted(receipts.items()))
    table='\n'.join(f"| {v['camera']['azimuth']} | {v['coverage']['authored']['selection_ink']:.3f} → {v['coverage']['edited']['selection_ink']:.3f} | {100*v['coverage']['authored']['support_fraction']:.3f}% → {100*v['coverage']['edited']['support_fraction']:.3f}% | {v['angle_delta']['target_interior']['L1']:.3f} | {v['angle_delta']['far_other']['L1']:.1f} / {v['angle_delta']['far_background']['L1']:.1f} |" for v in loc['views'])
    author_delta=[sum(x['L1'] for x in v['authoring_delta'].values()) for v in loc['views']]
    report=f'''# Unit020：真实Chair座面局部选区可编辑、可保存、可冷重开

执行状态 **completed**（工程范围），视觉仍 **partial**；约{elapsed:.1f}分钟。新增可选目录示例 `chair_seat_patch`，原四默认与既有示例未变。实际完成原GS四视角、三状态共12张整椅输出、浏览器局部编辑/撤销/导出、新服务冷导入、18帧完整解码与冷重绘、最终tar迁移后重新划区/改角/导出。没有H1/H2/H5成功结论。

## 判断与冻结

完整读取BRIEF和851行原大纲，读取P1 unit010/P2实际源、报告和NEXT，查看unit019实际全对象与原GS对照。旧P1 NO_GO、P2零物理边界余量/不可辨识保持。本轮不继承旧单单元授权限制，也未调用嵌套模型。unit019额外局部平滑整椅尺度几乎无收益；其region2包含座面、扶手和部分椅背，统一改角影响过大。本轮优先分出更小人工编辑区，沿用原默认Chair代理，所有几何不变。

协议SHA `{sha(U/'PROTOCOL.json')}` 在构建前冻结；选区配方SHA `{sha(U/'SELECTION_RECIPE.json')}` 在任何改角输出前冻结。construction仅查看az0/180、elev65、distance4.7代理图，手工放置两个矩形[182,217,324,341]和[193,204,332,281]，没有看结果后重选。第一视图2531面，第二视图额外173面，共2704/17768个原region2面，区域4名为Manual seat surface patch。只选前景可见整三角形，不补隐藏面；不是完整语义座垫或自动语义理解。

原资产 `{ASSET}`；输入逐文件SHA见PROTOCOL。原PLY `{p['original']['original_ply']}`，SHA `{p['original']['sha256']}`，256690原高斯。实际CPU SH3/EWA重绘四曝光相机az17/107/197/287、elev25、distance4.7；CPU库来源/哈希见source_model/LIBRARY_PROVENANCE.json。原GS不是独立表面真值或GPU等价认证。四组原图/代理/高度区/排线见media/source_reference_all_views.png。

## 实际结果与局限

原顶点/索引面精确保留；区域1/3文件逐字节不变；region2的5491个未选路径段（points/bary/face/stroke_id）精确保留，移出1577段。划区重生成区域4原角度95笔触157条/1611段，总长19.321349；改角65后153条/1494段，总长19.403897。原spacing .045、length .22、width1、默认ink .8、xy切面和显示设置不变。路径ID属于代理路径，不是高斯索引；改角目标路径是新版本。

划区本身不是无操作：原始→划区相机总L1分别为{', '.join(f'{x:.3f}' for x in author_delta)}，来自原工具对目标间断位置的重生成；四视角远其他/背景均0。没有把这部分变化算作angle65贡献。

| Az | 共同选区掩码内墨量95→65 | 选区hatch>.1覆盖95→65 | 目标内部L1 | 远其他/背景L1 |
|---:|---:|---:|---:|---:|
{table}

改角四视角mesh/depth/regions/contour、全部非目标路径/样式/layers精确。分区为固定2px边界带、目标内部、远其他、远背景，全部像素分区无排除；原始分母、边界L1、blank-distance、整图墨量见metrics/LOCALITY.json。同代理标签不等于独立语义标签；覆盖不是均匀间距/艺术偏好评分。正面变稀、侧面变密，不是保墨改善。

实际检查media/full_object_before_after.png和selection_all_views.png：新方向局限于座面局部，原扶手/下椅背/裙边外观保持，局部控制比改整个高度区更实用。矩形/锯齿边缘、侧后细碎面、原座面隆起/波纹、薄杆缺损仍可见；只将它作为可选人工局部控制示例，不晋级整体画质，不替换默认。全12旋转+6缩放接触表已检查，弱侧/背视图全部保留。

## 真实测试、浏览器和迁移

两项真实资产测试rc0：两视图可见面并集/第二视图非零增量、错误checksum拒绝、顶点/索引面精确、未选段逐字段精确、冷载入重心锚点、目标角度更改与非目标文件/样式保留。没有更改既有材料算法，因此未制造TDD红灯；现有源逐文件与source_before一致。新增驱动/测试/文档有source_snapshot和UNIT020_DIFF.patch。

真实Firefox从保存选区angle95执行65→撤销→刷新→65，旋转/缩放后回原相机，下载资产ZIP、PNG、orbit ZIP、zoom ZIP。PNG及全部分层数组与CLI精确。停止原服务与浏览器后另起新服务/新Firefox导入ZIP，scene/styles/camera/display/selected_region、PNG和全部数组精确；再改95及撤销成功。两个进程清理收据和最终PID不存在检查见metrics/OWN_PROCESS_CLEANUP.json。

浏览器导出12 orbit+6 zoom真实帧。FFV1全部18帧解码RGB精确，MP4全部18帧解码计数通过；两独立新进程串行冷重绘PNG和全部数组精确。有限18帧不是持续笔触独立对应或完整时序/遮挡证据。

最终tar解压至final_archive后，文档入口实际运行：optional example冷绘、从原默认重放两视图author、region4 edit65、指定相机export；保存的mesh/所有路径/selection及PNG精确。解压目录目录服务直接打开新示例并导入浏览器ZIP，PNG和状态精确。实际命令、cwd、起止时间、返回码见logs/*.receipt.json和REPRODUCE_ZH.md。

| Command | Return code | Seconds |
|---|---:|---:|
{command_rows}

全部执行阶段rc0，无科学重试/参数扫选。准备阶段大小写/路径猜测错误保留于logs/PREPARATION_READ_ERRORS.json；组合命令内未知子返回码明确未知，未伪造。全程数值串行、两核、线程1、无GPU/credentials/environment dump/嵌套模型/push/merge，orchestration只读。最终包仅当前Linux依赖环境实测，不含Python二进制或原始PLY。

## 交付与后续

入口：`cd {U/'portable_demo'} && ./run.sh viewer --scene chair --example chair_seat_patch`。运行/导入/重建选区/视频/冷重放命令见PACKAGE_README_ZH.md。portable_demo.tar.gz包含四模型资产、可选座面示例、源码、完整预览与视频；原默认和原示例逐文件保持。

只封存验证过的工程证据，scientific_seal=false，reported_not_independently_verified。NEXT=continue：{next_step}
'''
    (U/'REPORT_ZH.md').write_text(report)
    reproduce='# 实际执行命令与返回码\n\n工作目录：`'+str(Path.cwd())+'`。每项详细命令为JSON argv，不做shell拼接。\n\n'
    for k,v in sorted(receipts.items()):reproduce+='## '+k+'\n\n```json\n'+json.dumps(v,indent=2,ensure_ascii=False)+'\n```\n\n'
    (U/'REPRODUCE_ZH.md').write_text(reproduce)
    root_readme=f'''# 可运行真实旧模型Demo：unit020\n\n最新单元：`{U}`。工程completed，视觉partial；四默认模型保留，新增人工座面局部示例，不宣称语义/几何/时序科学成功。\n\n```bash\ncd {U/'portable_demo'}\n./run.sh viewer --scene chair --example chair_seat_patch --port 8765\n```\n\n打开 http://127.0.0.1:8765 。资产、图片和实际轨迹可导出；重新启动目录viewer后可上传保存ZIP继续编辑。\n\n完整说明：`{U/'PACKAGE_README_ZH.md'}`。可移植包：`{U/'portable_demo.tar.gz'}`。报告：`{U/'REPORT_ZH.md'}`。整椅对比：`{U/'media/full_object_before_after.png'}`。\n\n新原GS四视角、真实Firefox编辑/导出和新服务导入、18帧完整解码/冷重绘、最终tar迁移重建选区/改角/出图均已执行。当前只验证Linux CPU依赖环境。座面是人工局部选区，边缘/波纹/细杆缺损保留；原四默认和既有示例未变。\n\n下一步：{next_step}\n'''
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(root_readme)
    (SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(root_readme)
    prior_readme=(U/'docs_before/DEMO_README_ZH.md').read_text()
    with (U/'UNIT020_DIFF.patch').open('a') as f:
        f.write(''.join(difflib.unified_diff(prior_readme.splitlines(keepends=True),root_readme.splitlines(keepends=True),
            fromfile='a/docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md',tofile='b/docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md')))
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(updated_utc=now(),latest_unit='unit_020',execution_state='completed',scientific_verdict=status['scientific_verdict'],
        demo_progress=progress,portable_package=str(U/'portable_demo.tar.gz'),readme=str(U/'PACKAGE_README_ZH.md'),report=str(U/'REPORT_ZH.md'),
        next_action='continue',recommended_next_step=next_step,scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    # Only stable artifacts: never seal browser profiles, live sessions, temp files or runtime model responses.
    files=[]
    for n in ('PROTOCOL.json','SELECTION_RECIPE.json','SELECTION_FREEZE.json','selection_faces.npz','STATUS.json','NEXT.json','REPORT_ZH.md','REPRODUCE_ZH.md','PACKAGE_README_ZH.md','SOURCE_BEFORE.json','SOURCE_FINAL.json','UNIT020_DIFF.patch','portable_demo.tar.gz'):
        files.append(U/n)
    for folder in ('assets','renders','construction','source_model','metrics','media','source_snapshot'):
        files.extend(f for f in (U/folder).rglob('*') if f.is_file())
    for folder in ('browser','cold_browser'):
        files.extend(f for f in (U/folder).iterdir() if f.is_file() and f.suffix in ('.json','.png','.zip'))
    files.extend(f for f in (U/'logs').iterdir() if f.is_file())
    manifest={str(f.relative_to(U)):sha(f) for f in sorted(set(files))}
    js(U/'EVIDENCE_SHA256.json',dict(utc=now(),scope='Hash inventory of validated finite engineering evidence and its source/receipts; NOT a scientific success seal',scientific_seal=False,files=manifest))
    assert all(sha(U/n)==v for n,v in manifest.items())
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,sealed_engineering_files=len(manifest),scientific_seal=False,next_action='continue',package=str(U/'portable_demo.tar.gz'))))

if __name__=='__main__':main()
