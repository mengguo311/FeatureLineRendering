"""Record only validated engineering delivery; preserve scientific limitations."""
import runtime
from runtime import js, sha, now, output_guard, OUTPUT_ROOT
from pathlib import Path
import json, os, shutil, subprocess
from unit026_run import U, PREV, SOURCE, hashes


def main():
    protocol = json.loads((U/'PROTOCOL.json').read_text())
    browser = json.loads((U/'browser/BROWSER_VALIDATION.json').read_text())
    cold = json.loads((U/'cold_browser/BROWSER_VALIDATION.json').read_text())
    replay = json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
    assert browser['status'] == cold['status'] == 'PASS'
    assert replay['archive_sha256'] == sha(U/'portable_demo.tar.gz')
    assert hashes(SOURCE) == json.loads((U/'SOURCE_SNAPSHOT.json').read_text())
    assert all(json.loads((U/'metrics/PRESERVATION.json').read_text()).values())
    for details in protocol['inputs'].values():
        assert hashes(Path(details['asset'])) == details['files']
        assert sha(details['original']['original_ply']) == details['original']['sha256']
    records = {f.stem.removesuffix('.receipt'): json.loads(f.read_text())
               for f in sorted((U/'logs').glob('*.receipt.json'))}
    required = ('tdd_red', 'tdd_green', 'browser', 'cold_browser', 'media',
                'package_build', 'package_check', 'packaged_viewer')
    assert all(name in records for name in required)
    for name, receipt in records.items():
        assert receipt['returncode'] == (1 if name == 'tdd_red' else 0), name
    children = []
    for name in ('layout_red', 'layout_green', 'browser', 'cold_browser'):
        cleanup = json.loads((U/name/'CLEANUP.json').read_text())
        assert cleanup['own_child_groups_only']
        for child in cleanup['children']:
            assert child['returncode'] is not None
            result = subprocess.run(['ps', '-p', str(child['pid']), '-o', 'pid=,comm='],
                                    capture_output=True, text=True)
            assert not result.stdout.strip(), result.stdout
            children.append(child)
    previous_exact = {}
    for scene in ('chair', 'lego'):
        for arm in ('baseline', 'edited'):
            frame = U/'browser'/(scene+'_'+arm)
            assert json.loads((frame/'frame_000.json').read_text())['bounds']['all_proxy_vertices_inside']
            previous_exact[scene+'_'+arm] = sha(frame/'frame_000_image.png') == sha(PREV/'browser'/(scene+'_'+arm)/'frame_000_image.png')
    assert all(previous_exact.values())
    js(U/'metrics/PRIOR_RENDER_PRESERVATION.json', previous_exact)
    package_files = json.loads((U/'portable_demo/PACKAGE_FILES.json').read_text())['files']
    assert all(sha(U/'portable_demo'/name) == digest for name, digest in package_files.items())
    visual = json.loads((U/'metrics/VISUAL_REVIEW.json').read_text())
    assert visual['actually_inspected']
    output_guard(U)
    js(U/'metrics/RESOURCES_FINAL.json', dict(utc=now(), affinity=sorted(os.sched_getaffinity(0)),
        root_free_bytes=shutil.disk_usage('/').free, hdd_free_bytes=shutil.disk_usage(U).free,
        total_task_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),
        unit_bytes=sum(f.stat().st_size for f in U.rglob('*') if f.is_file()),
        browser_children_exited=children))
    locality = [e for e in browser['events'] if e['action'].startswith('real local ink edit')]
    layouts = [e for e in browser['events'] if e.get('label', '').endswith('_top')]
    progress = dict(genuinely_ran_old_model=True, available_models=['chair', 'lego', 'drums', 'ficus'],
        newly_run_models=['chair', 'lego'], new_original_PLY_renders=False,
        geometry_source='CPU-derived proxies of original SHA-verified vanilla GS checkpoints; not GT',
        default_assets_preserved=4, optional_examples_preserved=8,
        first_screen_region_and_ink_desktop=True, top_bar_ZIP_dialog=True,
        advanced_groups_actual_click_test=True,
        actual_viewports=[dict(width=e['layout']['width'], height=e['layout']['height']) for e in layouts],
        mobile_device_tested=False, full_object_baseline_edited_states=4,
        browser_local_edit_undo_PNG_ZIP_models=2, fresh_server_browser_ZIP_import_exact_models=2,
        packaged_entrypoint_cold_ZIP_import_exact_models=2,
        all_NPZ_assets_unchanged_by_ink_edit=True, non_target_layers_exact=True,
        unit025_baseline_and_edited_PNGs_exact=previous_exact,
        orbit_frames=12, zoom_frames=6, lossless_exact_decode_frames=18,
        MP4_decoded_frames=18, relocated_cold_replay_exact_frames=18,
        visual_quality='partial: inherited proxy ripples, gaps in thin geometry and incomplete manual regions',
        automatic_semantics=False,
        reasoning='Region and ink editing now fit the desktop first screen, and reopening saved ZIPs is a visible primary action. Both real-model workflows and the relocated package ran successfully. Geometry and scientific claims are unchanged.')
    limitations = [
        '只改善操作组织。旧vanilla GS衍生代理、规则粗区域和人工局部选区保持原样；不是GT、独立实测表面或自动语义。',
        '本轮实际绘制旧模型的保存代理，核验原PLY SHA，但没有重新渲染原PLY；包内原GS参照继承历史结果并标注来源。',
        'Chair波纹、碎轮廓和薄腿缺损，Lego平台噪线和细结构不足仍在；完整入画不代表几何完整。',
        '局部性只在两幅冻结历史已曝光视点、同代理掩码和固定2px边界带测量；有限冷重放及视频解码不等于独立几何或全时序认证。',
        '实测Firefox视口1280×714、1024×682、500×758；390px请求实际为500px，没有真机移动端测试。窄屏区域控件在预览下方，需滚动；高级控件需展开。',
        '没有H1/H2/H5科学比较；P1完整视觉NO_GO、P2不可辨识及历史失败不改写。09:20之后只做工程交付。',
        '便携包不含解释器、依赖二进制或原PLY，仅当前Linux/Firefox验证。资产冷绘制无需原PLY。',
        'TDD原始失败rc1保留；布局修复后rc0。历史读取时两条缺失路径报错，改用真实unit_010/unit_011路径完成只读检查，无历史文件修改。']
    artifacts = ['PROTOCOL.json', 'browser/BROWSER_VALIDATION.json', 'cold_browser/BROWSER_VALIDATION.json',
        'media/two_model_edit_cold.png', 'media/two_model_proxy_regions.png', 'media/chair_orbit.mp4',
        'media/chair_zoom.mp4', 'metrics/FINAL_ARCHIVE_REPLAY.json', 'metrics/VISUAL_REVIEW.json',
        'portable_demo.tar.gz', 'PACKAGE_README_ZH.md', 'source_snapshot', 'SOURCE_SNAPSHOT.json',
        'UNIT026_DIFF.patch', 'EVIDENCE_SHA256.json']
    status = dict(stage='usable_real_model_demo_delivery', execution_state='completed', finished_utc=now(),
        scientific_verdict='NOT_TESTED_H1_H2_H5; engineering complete, visual partial; inherited P1 NO_GO/P2 unidentifiable retained',
        demo_progress=progress, artifacts=artifacts,
        tests=dict(command_receipts={name:dict(returncode=r['returncode'], path='logs/'+name+'.receipt.json') for name,r in records.items()},
                   browser_locality=locality, TDD='Real browser first-screen controls fail before layout edit and pass afterwards'),
        blockers=[], limitations=limitations, scientific_seal=False,
        supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json', status)
    step = '在09:45前仅做交付整理：把现有Chair/Lego真实before/after保存帧制作短操作说明或两状态编辑视频，明确不是连续实时录屏；不改模型或参数，不开新科学比较。若临近收尾，保留本包并停止。'
    js(U/'NEXT.json', dict(action='continue', recommended_next_step=step,
        reason='四模型入口、完整对象、局部编辑和冷重载已经可运行；剩余独立有用动作是用已有真实结果说明操作与保存流程，减少首次使用成本。',
        demo_progress=progress, estimated_next_minutes=6, wrap_jst='2026-10-22T09:45:00+09:00'))
    lines = [
        '# Unit026：首屏区域与墨色、顶部ZIP打开入口', '',
        '工程 completed，视觉 partial。完整读取BRIEF和851行原大纲，复核P1 unit010/中断unit011及P2报告、NEXT和相关源码；实际查看unit025完整对象修改/冷导入、代理/区域图与桌面截图。旧模型已能运行，主要问题是常用控件被长说明挤出首屏，因此选择小范围界面整理。未开展新的科学比较。', '',
        '唯一产品代码变化是viewer.html：区域与墨色前置；示例说明、笔触形状/交叉层、相机、恢复、轮廓和人工选区分组折叠；顶部Open saved ZIP打开原导入功能的对话框。已有选择草稿重载时自动展开人工工具。保存/渲染/几何/路径算法与参数不变。', '',
        '冻结协议：'+protocol['frozen_utc']+'；SHA `'+sha(U/'PROTOCOL.json')+'`。Chair输入unit025/portable_demo/examples/chair_ink_preview，region4墨色.35→.65，相机43/28/4.9；Lego为lego_bucket_cross，region4墨色.8→.35，相机-127/30/5.1。输入资产与原PLY路径/SHA完整保存于PROTOCOL.json。人工座面/铲斗区域和历史已曝光视点保持，不是盲测。', '',
        '真实Firefox TDD原失败rc1：1280×714视口中inkStrength的y=914.4且不可见，Open ZIP按钮尚不存在。布局修复后rc0；1280×714、1024×682中区域/墨色可见且点击命中，500×758中主要操作栏在页面顶/底可见且无水平溢出。真实点击验证ZIP弹窗和高级分组打开/关闭。', '',
        'Chair和Lego均通过实际浏览器局部墨色修改、撤销、再次修改、刷新、转动、缩放、相机恢复、PNG/ZIP下载。全部NPZ路径不变，非目标层、深度、区域与轮廓精确保持；四张baseline/edited完整对象PNG与unit025逐字节相同，证明界面改动没有改变本次绘制结果。局部量如下（同代理掩码、固定2px带）：', '',
        '| Model | Target interior L1 | Boundary L1 | Far other L1 | Far background L1 |',
        '|---|---:|---:|---:|---:|']
    for entry in locality:
        m = entry['locality']
        lines.append(f"| {entry['scene']} | {m['target']['L1']:.4f} | {m['boundary']['L1']:.4f} | {m['far_other']['L1']:.4f} | {m['far_background']['L1']:.4f} |")
    lines += ['', '全新服务器/Firefox通过顶部ZIP弹窗分别导入两份实际下载资产，首次绘制cache miss，PNG及全部数组、路径、样式与相机一致，继续编辑可精确返回。Chair真实浏览器导出12帧orbit和6帧zoom，MP4及FFV1完整解码18帧，FFV1全部逐像素一致；完整接触表实际查看，弱视点保留。', '',
        'portable_demo.tar.gz包含四默认模型、八示例、本次两编辑资产/ZIP、源码、预览、参照来源与运动包。最终压缩包解压后实际运行文档中的两模型冷PNG、Chair逆向墨色修改和PNG、orbit/zoom重放，均精确；另通过解压副本run.sh viewer启动新进程，导入两份ZIP首次无缓存且一致。服务与浏览器子进程均已退出。source_snapshot及UNIT026_DIFF.patch提供精确回放源码。', '',
        '视觉审阅：区域/墨色现在与完整对象同时可见，保存与重新打开入口直接可达。Chair和Lego只发生冻结局部墨色变化；几何波纹、碎线与不完整人工区域无改善。界面可用性与有限工程重放不能写成新的科学成功。', '',
        '| Command receipt | Return code | Seconds |', '|---|---:|---:|']
    lines += [f"| {name} | {r['returncode']} | {r['seconds']:.3f} |" for name,r in records.items()]
    lines += ['', '准确argv、cwd、UTC和退出码见logs/*.receipt.json。所有数值任务串行、affinity两核、数值线程1、CUDA禁用；无嵌套模型/agents、凭据、环境转储、push或merge。orchestration只读，scratch仅临时使用。', '',
              *['- '+value for value in limitations], '',
              '启动：`cd '+str(U/'portable_demo')+' && ./run.sh viewer --scene chair --example chair_ink_preview --port 8765`。浏览器打开http://127.0.0.1:8765；完整命令见PACKAGE_README_ZH.md。', '',
              'NEXT=continue：'+step, '', '仅封存验证过的有限工程证据；scientific_seal=false，reported_not_independently_verified。']
    (U/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    readme = (U/'PACKAGE_README_ZH.md').read_text()
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(readme)
    (SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(readme)
    delivery = dict(unit='unit_026', execution_state='completed', updated_utc=now(), demo_progress=progress,
        package=str(U/'portable_demo.tar.gz'), package_sha256=sha(U/'portable_demo.tar.gz'),
        readme=str(U/'PACKAGE_README_ZH.md'), report=str(U/'REPORT_ZH.md'), scientific_seal=False, limitations=limitations)
    js(U/'DELIVERY_STATUS.json', delivery); js(OUTPUT_ROOT/'DELIVERY_STATUS.json', delivery)
    targets = ['PROTOCOL.json', 'STATUS.json', 'REPORT_ZH.md', 'NEXT.json', 'PACKAGE_README_ZH.md',
               'DELIVERY_STATUS.json', 'SOURCE_SNAPSHOT.json', 'UNIT026_DIFF.patch', 'portable_demo.tar.gz']
    for folder in ('source_snapshot', 'metrics', 'media'):
        targets += [str(f.relative_to(U)) for f in (U/folder).rglob('*') if f.is_file()]
    targets += [str(f.relative_to(U)) for f in (U/'logs').glob('*') if f.is_file() and not f.name.startswith('finalize.')]
    for folder in ('layout_red', 'layout_green', 'browser', 'cold_browser'):
        targets += [str(f.relative_to(U)) for f in (U/folder).iterdir() if f.is_file() and f.suffix in ('.json', '.png', '.zip')]
        targets += [str(f.relative_to(U)) for f in (U/folder).glob('*/frame_000*') if f.is_file()]
    manifest = {name:sha(U/name) for name in sorted(set(targets))}
    js(U/'EVIDENCE_SHA256.json', dict(scope='Validated finite engineering evidence and preserved failures, not a scientific seal',
                                   scientific_seal=False, files=manifest))
    assert all(sha(U/name) == digest for name,digest in manifest.items())
    print(json.dumps(dict(execution_state='completed', evidence_files=len(manifest), unit=str(U), next_action='continue')))


if __name__ == '__main__':
    main()
