"""Finalize verified unit021 engineering evidence and the runnable handoff."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from unit021_run import U,PREV,SOURCE,ASSET,protocol,hashes
from pathlib import Path
import datetime,difflib,json,os,shutil,subprocess


def main():
    output_guard(U);p=protocol()
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert Path.cwd()==SOURCE.parents[1]
    assert hashes(ASSET)==p['inputs']
    required=['tdd_green','final_author_tests','asset_tests','regressions','reference','candidate','static','stage','browser','cold_browser','media_stage','cold_orbit','cold_zoom','package_build','package_check']
    receipts={f.name.removesuffix('.receipt.json'):json.loads(f.read_text()) for f in (U/'logs').glob('*.receipt.json')}
    assert all(receipts[n]['returncode']==0 for n in required)
    assert receipts['tdd_behavior_red']['returncode']==receipts['cross_empty_red']['returncode']==1
    assert 'FAILED (failures=2)' in (U/'logs/tdd_behavior_red.log').read_text()
    assert 'FAILED (failures=1)' in (U/'logs/cross_empty_red.log').read_text()
    assert 'Ran 6 tests' in (U/'logs/dtype_final_tests.log').read_text()
    assert all(receipts[n]['returncode']==0 for n in ['dtype_final_tests','stage_dtype','media_stage_dtype','cold_orbit_dtype','cold_zoom_dtype','package_build_dtype','package_check_dtype'])
    real=json.loads((U/'metrics/REAL_ASSET_TEST.json').read_text())
    loc=json.loads((U/'metrics/LOCALITY.json').read_text())
    reference=json.loads((U/'source_model/RECEIPT.json').read_text())
    reg=json.loads((U/'metrics/REGRESSIONS.json').read_text())
    assert reference['original_gaussians']==256690 and len(reference['views'])==4
    assert all(sum(x['L1'] for x in v['authoring_delta'].values())==0 for v in loc['views'])
    assert all(v['angle_delta']['target_interior']['L1']>0 and v['angle_delta']['far_other']['L1']==0 and v['angle_delta']['far_background']['L1']==0 for v in loc['views'])
    assert json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())['archive_sha256']==sha(U/'portable_demo.tar.gz')
    cold=json.loads((U/'metrics/COLD_REPLAY.json').read_text())
    assert sum(v['frame_count'] for v in cold.values())==18 and all(v['all_png_exact'] and v['all_arrays_exact'] for v in cold.values())
    package=U/'portable_demo'
    assert hashes(package/'assets')==p['inherited_catalog_inputs']['assets']
    assert all(sha(package/'examples'/f)==v for f,v in p['inherited_catalog_inputs']['examples'].items())
    assert all(sha(SOURCE/f.name)==sha(f) for f in (package/'source').iterdir() if f.is_file())
    children=[]
    for folder in ('browser','cold_browser'):
        assert json.loads((U/folder/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
        children+=json.loads((U/folder/'CLEANUP.json').read_text())['children']
    children.append(json.loads((U/'logs/relocated_viewer_cleanup.json').read_text()))
    for r in children:
        try:os.kill(r['pid'],0)
        except ProcessLookupError:pass
        else:raise AssertionError('owned child still exists: '+str(r['pid']))
    js(U/'metrics/OWN_PROCESS_CLEANUP.json',dict(utc=now(),all_recorded_child_PIDs_absent=True,children=children))
    js(U/'metrics/RESOURCES.json',dict(utc=now(),cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,serial_numerical_execution=True,gpu_used=False,nested_models=False,root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,task_output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file())))
    recovery=json.loads((U/'RECOVERY.json').read_text());recovery.update(end_utc=now(),execution_state='completed',tests='dtype_red rc1 real render TypeError; dtype_final_tests rc0, six tests; rebuilt package/cold motion/relocated replay passed',unchanged_original_unsigned_assets=True);js(U/'RECOVERY.json',recovery)
    next_step='为人工区域增加可持久保存的“恢复创建时笔触”操作：当前95→65后再输95会重生成间断位置，只有会话内Undo能精确回到继承路径。复用本轮父段映射和固定座面选区，保存一份明确的区域初始路径/样式，验证局部改角→导出→新进程导入→仅重置区域4，非目标及几何原样。作为可用性改进，不启动新模型或几何扫参。'
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],newly_rendered_model='chair',original_PLY_newly_rendered=True,original_gaussians=256690,original_GS_views=4,complete_static_states=12,additional_cold_edit_reference_views=1,
        manual_selection=dict(region=4,faces=2704,source_region_faces=17768,rectangle_steps=2,semantic_completeness=False,geometry_exact=True,selected_parent_segments_transferred=1577,unselected_source_segments_retained=5491),
        authored_same_style_is_noop=True,author_only_image_hatch_contour_depth_exact_views=4,
        author_only_image_L1=[sum(x['L1'] for x in v['authoring_delta'].values()) for v in loc['views']],
        local_style_edit='Angle95->65 only in manual seat patch; region1/2/3 paths/styles/layers exact',
        target_interior_L1=[v['angle_delta']['target_interior']['L1'] for v in loc['views']],far_other_L1=[v['angle_delta']['far_other']['L1'] for v in loc['views']],far_background_L1=[v['angle_delta']['far_background']['L1'] for v in loc['views']],
        actual_browser_pointer_author_noop=True,actual_browser_edit_undo_save=True,cold_new_server_browser_import_exact=True,
        motion_frames=18,lossless_video_decoded_exact_frames=18,mp4_decoded_frames=18,cold_replay_PNG_arrays_exact_frames=18,relocated_tar_CLI_author_edit_export_and_import=True,
        defaults_and_inherited_examples_unchanged=True,legacy_renderer_defaults_pixel_exact=4,optional_example='chair_seat_preserved',visual_quality='partial; unchanged proxy ripples/thin-part defects and incomplete manual seat selection',
        reasoning='Creating a local editable region now preserves its existing appearance. Real Chair pointer authoring, local edit, export, cold import and relocated recipe replay work. This removes an observed usability surprise while keeping all four previous models available; geometry/scientific quality is not upgraded.')
    limits=['旧vanilla GS的CPU深度融合代理，含继承平滑；本轮顶点和索引面完全不变。不是独立实测表面或原高斯ID。',
        '两个旧人工可见面矩形及2704面选区固定，只有部分座面；背面碎片、矩形边界、波纹、缺孔和薄杆缺损仍在。',
        '保留笔触的visibility_mask明确继承分区前的线宽覆盖；线帽可跨新标签。不是严格逐像素语义裁剪。新生成层回到当前region裁剪，固定深度容差.004未变；宽线/任意编辑的全部边界行为未认证。',
        '95→65→95会重生成目标间断位置；参数相同不代表回到继承路径。仅无操作95→95和会话Undo保证该次路径保留。跨会话恢复初始路径留待下一步。',
        '无现成base笔触的选区及会清空启用cross层的分割拒绝保存；不为了创建空白区域偷偷生成新线。',
        '四静态视角、两次浏览器会话和18运动帧是有限工程证据。局部性使用同代理标签及固定2px带，不是独立语义/几何/时序验证。',
        '改角墨量随视图变化，未作匹配墨量审美试验；H1/H2/H5未测试，旧P1 NO_GO与P2不可辨识不变。',
        '只在当前Linux CPU依赖环境运行；包不含Python/依赖二进制或原PLY，非实时帧率承诺。']
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-22T07:54:57.470590+09:00')).total_seconds()/60
    artifacts=['PROTOCOL.json','SELECTION_RECIPE.json','assets/authored','assets/edited','assets/regenerated95','metrics/SELECTION.json','metrics/REAL_ASSET_TEST.json','metrics/REGRESSIONS.json','metrics/LOCALITY.json','metrics/VISUAL_REVIEW.json','media/source_reference_all_views.png','media/full_object_before_after.png','media/selection_all_views.png','media/chair_orbit.mp4','media/chair_zoom.mp4','browser/BROWSER_VALIDATION.json','cold_browser/BROWSER_VALIDATION.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','PACKAGE_README_ZH.md','source_snapshot','UNIT021_DIFF.patch','EVIDENCE_SHA256.json']
    status=dict(stage='UNIT_COMPLETE_APPEARANCE_PRESERVING_AUTHORING',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,engineering_execution='PASS',scientific_verdict='H1_H2_H5_NOT_TESTED; ENGINEERING_AUTHORING_FIX_ONLY',demo_progress=progress,artifacts=artifacts,
        tests=dict(final_authoring_behavior_tests=6,real_asset_tests=2,inherited_cross_tests=reg['cross_tests'],legacy_default_raster_comparisons=4,TDD='Real Chair path/raster failures rc1 -> pass; enabled-cross-empty split failure rc1 -> reject before output. Initial scratch output-guard error separately retained, not counted as behavior red.',actual_Firefox=True,command_receipts={k:dict(returncode=v['returncode'],path='logs/'+k+'.receipt.json') for k,v in sorted(receipts.items())}),
        blockers=[],limitations=limits,engineering_recovery='RECOVERY.json',scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,reason='完整对象/局部编辑/冷加载已可用，下一步解决已观察到的跨会话精确恢复问题，避免只恢复数值却改变笔触。',estimated_next_minutes=25,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    commands='\n'.join(f"| {k} | {v['returncode']} | {v['seconds']:.3f} |" for k,v in sorted(receipts.items()))
    table='\n'.join(f"| {v['camera']['azimuth']} | {sum(x['L1'] for x in v['authoring_delta'].values()):.1f} | {v['angle_delta']['target_interior']['L1']:.3f} | {v['angle_delta']['boundary_band']['L1']:.3f} | {v['angle_delta']['far_other']['L1']:.1f} / {v['angle_delta']['far_background']['L1']:.1f} |" for v in loc['views'])
    report=f'''# Unit021：创建人工局部区域时保留原有笔触与画面

工程执行 **completed**，视觉质量仍 **partial**；耗时约{elapsed:.1f}分钟。实际修复并运行了真实Chair选区→局部改角→浏览器保存→冷导入→可移植包重放，新增可选示例 `chair_seat_preserved`。不是计划性完成，也不宣称H1/H2/H5成功。

完整读取BRIEF、851行原大纲、P1/P2源/报告/NEXT，查看unit020真实整对象和原GS对照。unit020已完成四模型目录、局部编辑和冷加载；其选区保存会在相同angle95下重生成目标路径，旧四视图L1为32–467.8。相比再加模型或继续收益很弱的局部平滑，本轮修复这一可复现的编辑意外。旧P1 NO_GO、P2零物理边界余量/不可辨识保持；未调用任何嵌套模型。

协议SHA `{sha(U/'PROTOCOL.json')}` 在测试/输出前冻结。源资产 `{ASSET}`，逐文件hash见PROTOCOL；复用unit020两个矩形，不改选区、不调几何、不扫参数。2704/17768个region2面划入region4，仍只是人工部分座面。新静态相机az29/119/209/299、elev28、distance4.9在结果前固定；模型和框选已曝光，不是盲测重建视角。

原PLY `{p['original']['original_ply']}`，SHA `{p['original']['sha256']}`。实际CPU SH3/EWA重绘256690原高斯的四幅RGB；CPU库与adapter逐文件验证继承，见source_model/LIBRARY_PROVENANCE.json。原GS/代理/区域/排线并列图在media/source_reference_all_views.png；原GS不充当独立几何真值。

实现将1577个选中父段及其points/bary/face/stroke_id直接转移到新区域，保留5491个未选父段；selection_4.npz新增父段数组索引、父路径ID和方向层映射。全部顶点/索引面精确，region1/3文件不变。为了防止新标签裁掉原有线帽，每段保存明确的visibility_mask；重复划区只扩展已有父标签支持，不建立新空间邻接。深度容差.004与线宽不变。主动改角的新层按当前所属region生成并裁剪；其他层不改。父ID是代理笔触ID，不是原Gaussian行号。

同样参数创建区域，在四幅512²整椅输出中image/hatch/contour/depth逐数组精确，图像L1均0；region调试颜色按设计改变。95→95无操作保留路径文件；改65产生新的目标几何版本，region1/2/3路径文件、样式与渲染层精确。

| Az | 仅划区图像L1 | 改角目标内部L1 | 固定2px边界L1 | 远其他/背景L1 |
|---:|---:|---:|---:|---:|
{table}

每像素划分为目标内部、固定2px带、远其他和远背景，无排除；原始分母、墨量、覆盖和blank-distance在metrics/LOCALITY.json。这个mask来自同一代理，不是独立语义真值。新继承线帽允许跨新标签，不得把零远区变化称为严格语义裁剪或全遮挡证明。改角墨量随视图变化，未做保墨审美比较。

实际检查整椅三状态、四视图代理/选区、原GS对照、Firefox输出、全部12旋转+6缩放接触图。仅划区的原笔触外观保持；改角仍是有用的局部艺术控制。座面波纹、前裙边杂线、侧后零碎人工选区和薄杆缺损没有改善。保存为可选示例，四默认及旧四可选示例逐文件保持，不升级整体视觉或几何结论。

真实TDD：修复前选中段1611 vs 原1577，画面1012像素不相同，两个断言真实失败rc1；修复后通过。进一步发现启用cross时选走全部cross面会留下不能冷加载的源区域，真实失败后增加写入前拒绝。最终6项作者行为测试、2项真实资产测试、7项继承cross测试通过；后者显式把测试输出重定向到本unit，历史目录只读。四默认模型用新/旧renderer实际逐数组比较完全相同。没有机械全历史测试。

Firefox实际执行两个pointer矩形、跨视图合并、保存region4（PNG未变且路径与CLI一致）、改角65/Undo/刷新/再改、旋转缩放、下载资产ZIP/PNG/两条运动ZIP。停止服务器及浏览器后，在新服务和新Firefox上传ZIP，PNG/全部数组及scene/styles/camera/display/selected_region精确；再改95和Undo成功。改回95对照的是独立保存的regenerated95，不冒称可恢复原继承断点；仅Undo恢复原资产。

两视频合计18帧完整解码：FFV1逐帧RGB精确，MP4完整计数通过；两独立新进程串行冷重绘所有PNG和数组精确。最终tar解压迁移后，文档入口实际重建选区、局部改角、导出PNG、打开新目录示例并导入ZIP，逐文件/PNG/状态一致。可复现命令见REPRODUCE_ZH.md与logs/*.receipt.json。有限工程证据不等于完整时序认证，未做实时帧率宣称。

| Command | Return code | Seconds |
|---|---:|---:|
{commands}

初次TDD夹具把输出放在orchestration/scratch，被既有output_guard拒绝rc1；这是夹具错误，修正到当前unit后才得到两个真实行为红灯。该记录与两个预期行为失败保留，不伪称全部首次通过。两次准备只读路径错误rc2/rc1也保留，详见logs/PREPARATION_READ_ERRORS.json和READ_ATTEMPT_2.json。首次完成后只读兼容性检查发现signed int64 mask虽可通过load校验却不能与uint64标签位做运算；真实Chair冷载入渲染复现TypeError(rc1)。将所有原379份hash证据完整保留并核验于pre_dtype_recovery/，做一次有界工程恢复：visibility_masks统一转为uint64；6项测试、18帧冷重绘、最终tar迁移重放再次通过。原科学候选/选区/样式不变，原失败不覆盖，RECOVERY.json记录起止。所有修复后正式运行/测试rc0。CPU两核、数值线程1、数值任务串行、无GPU/credentials/environment dump/嵌套模型/push/merge；自有浏览器/服务子进程均退出。

启动：`cd {package} && ./run.sh viewer --scene chair --example chair_seat_preserved --port 8765`。完整说明PACKAGE_README_ZH.md，包portable_demo.tar.gz包含四真实模型资产、旧示例、新示例、源码、框选配方、预览和视频。仅当前Linux依赖环境实际验证，不含原PLY或解释器。

{chr(10).join('- '+x for x in limits)}

只哈希已核验的工程证据和真实失败记录，scientific_seal=false，reported_not_independently_verified。NEXT=continue：{next_step}
'''
    (U/'REPORT_ZH.md').write_text(report)
    reproduce='# 实际命令/返回码\n\n每项为准确JSON argv；cwd、UTC起止和耗时均在收据。\n\n'
    for k,v in sorted(receipts.items()):reproduce+='## '+k+'\n\n```json\n'+json.dumps(v,indent=2,ensure_ascii=False)+'\n```\n\n'
    (U/'REPRODUCE_ZH.md').write_text(reproduce)
    readme=f'''# 可运行真实旧模型Demo：unit021\n\n工程completed，画质partial。创建人工区域现在保留原有笔触外观；真实Chair已验证局部修改、浏览器导出/冷导入、18帧解码/冷重绘和最终包迁移运行。四默认模型与旧示例保留。\n\n```bash\ncd {package}\n./run.sh viewer --scene chair --example chair_seat_preserved --port 8765\n```\n\n打开 http://127.0.0.1:8765 。选择区域修改样式，导出保存ZIP，重启目录viewer后上传继续编辑。\n\n完整说明：[{U/'PACKAGE_README_ZH.md'}]({U/'PACKAGE_README_ZH.md'})。可移植包：[{U/'portable_demo.tar.gz'}]({U/'portable_demo.tar.gz'})。报告：[{U/'REPORT_ZH.md'}]({U/'REPORT_ZH.md'})。整对象：[{U/'media/full_object_before_after.png'}]({U/'media/full_object_before_after.png'})。\n\n局限：模型衍生粗代理与人工部分座面，波纹/薄杆缺损仍在。新标签保留原线帽覆盖；参数改回原角度会重生成，Undo才精确回到上一状态。只验证当前Linux CPU环境，不宣称H1/H2/H5或独立几何/完整时序成功。\n\n下一步：{next_step}\n'''
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(readme)
    doc=SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md';doc.write_text(readme)
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(updated_utc=now(),latest_unit='unit_021',execution_state='completed',scientific_verdict=status['scientific_verdict'],demo_progress=progress,portable_package=str(U/'portable_demo.tar.gz'),readme=str(U/'PACKAGE_README_ZH.md'),report=str(U/'REPORT_ZH.md'),next_action='continue',recommended_next_step=next_step,scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    before=json.loads((U/'SOURCE_BEFORE.json').read_text());current=hashes(SOURCE)
    changed=[n for n in before if before[n]!=current.get(n)]
    js(U/'SOURCE_FINAL.json',dict(source_files=current,changed_preexisting_sources=changed,added_sources=sorted(set(current)-set(before)),packaged_runtime_source_exact=True))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'),dirs_exist_ok=True)
    patch=''
    for n in sorted(set(current)|set(before)):
        a=(U/'source_before'/n).read_text().splitlines(keepends=True) if n in before else []
        b=(SOURCE/n).read_text().splitlines(keepends=True) if n in current else []
        if a!=b:patch+=''.join(difflib.unified_diff(a,b,fromfile='a/experiments/partwise_sketch_hatching_v04/'+n,tofile='b/experiments/partwise_sketch_hatching_v04/'+n))
    for n in ('UNIT021_PROTOCOL.json','UNIT021_DEMO_README_ZH.md'):
        f=doc.parent/n;patch+=''.join(difflib.unified_diff([],f.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/docs/partwise_sketch_hatching_v04/'+n))
    patch+=''.join(difflib.unified_diff((U/'docs_before/DEMO_README_ZH.md').read_text().splitlines(keepends=True),readme.splitlines(keepends=True),fromfile='a/docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md',tofile='b/docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md'))
    (U/'UNIT021_DIFF.patch').write_text(patch)
    files=[U/n for n in ('PROTOCOL.json','SELECTION_RECIPE.json','selection_faces.npz','STATUS.json','NEXT.json','REPORT_ZH.md','REPRODUCE_ZH.md','PACKAGE_README_ZH.md','SOURCE_BEFORE.json','SOURCE_FINAL.json','UNIT021_DIFF.patch','portable_demo.tar.gz','RECOVERY.json')]
    for folder in ('assets','renders','source_model','metrics','media','source_snapshot'):
        files.extend(f for f in (U/folder).rglob('*') if f.is_file())
    for folder in ('browser','cold_browser'):
        files.extend(f for f in (U/folder).iterdir() if f.is_file() and f.suffix in ('.json','.png','.zip'))
    files.extend(f for f in (U/'logs').iterdir() if f.is_file())
    manifest={str(f.relative_to(U)):sha(f) for f in sorted(set(files))}
    js(U/'EVIDENCE_SHA256.json',dict(utc=now(),scope='Validated finite engineering artifacts and exact retained failure/command provenance. Not a scientific-success seal. Excludes mutable browser profiles/sessions, scratch and orchestration.',scientific_seal=False,files=manifest))
    assert all(sha(U/n)==v for n,v in manifest.items())
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,engineering_files_hashed=len(manifest),scientific_seal=False,next_action='continue',package=str(U/'portable_demo.tar.gz'))))

if __name__=='__main__':main()
