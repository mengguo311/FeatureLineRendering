"""Finalize honest engineering delivery from observed immutable evidence only."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import json,datetime,shutil,subprocess
from unit024_run import U,PREV,SOURCE,protocol,hashes

def main():
    p=protocol();timing=json.loads((U/'metrics/TIMINGS_FINAL.json').read_text())
    static=json.loads((U/'metrics/STATIC.json').read_text())
    regressions=json.loads((U/'metrics/REGRESSIONS.json').read_text())
    cold=json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
    integrity=json.loads((U/'metrics/PACKAGE_INTEGRITY.json').read_text())
    assert sha(U/'portable_demo.tar.gz')==integrity['archive_sha256']==cold['archive_sha256']
    assert hashes(U/'source_snapshot')==hashes(SOURCE)
    for name in ('browser','cold_browser'):
        assert json.loads((U/name/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
        assert json.loads((U/name/'CLEANUP.json').read_text())['own_child_groups_only']
    receipts={f.stem.removesuffix('.receipt'):dict(returncode=json.loads(f.read_text())['returncode'],path=str(f.relative_to(U))) for f in sorted((U/'logs').glob('*.receipt.json'))}
    assert all(v['returncode']==0 for k,v in receipts.items() if k not in ('tdd_red','reference','regressions'))
    assert receipts['tdd_red']['returncode']==1 and receipts['reference']['returncode']==1
    assert receipts['final_cache_tests']['returncode']==0 and receipts['relocated_ZIP_cold_editor']['returncode']==0
    med=timing['medians']
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],newly_rendered_model='chair',
        original_PLY_newly_rendered=True,original_gaussians=256690,original_GS_views=4,complete_static_states=8,
        manual_regions=[dict(region=4,faces=2704,source='two inherited visible rectangles; partial seat'),dict(region=5,faces=3055,source='inherited world box; partial upper back, includes hidden faces')],
        automatic_semantics=False,legacy_renderer_PNG_arrays_exact_views=4,other_region_layers_exact=True,all_binary_asset_files_preserved=True,
        same_camera_ink_reuses_supersampled_coverage=True,content_camera_width_path_label_cross_invalidation_tested=True,zero_ink_restore_exact=True,
        actual_browser_local_ink_edit=True,fresh_server_ZIP_import_exact=True,relocated_ZIP_first_draw_without_cache=True,
        orbit_frames=12,zoom_frames=6,decoded_lossless_exact_frames=18,decoded_MP4_frames=18,relocated_cold_replay_exact_frames=18,
        default_models_preserved=4,inherited_examples_preserved=7,optional_examples_now=8,
        timing_medians_seconds=med,render_speedup=timing['render_speedup'],full_editor_speedup=timing['editor_speedup'],cache_array_bytes=timing['cache']['bytes'],
        visual_quality='partial; inherited proxy ripples, thin-part defects and partial authored regions unchanged',
        reasoning='The existing real-model editor now changes local ink using exact cached 2x visibility coverage, with substantially shorter same-view waits. Saved assets remain cache-independent; four-model catalog, cold ZIP and full motion replay work.')
    limitations=[
        '旧vanilla GS的CPU衍生代理，不是GT、RaDe-GS重新训练或独立实测表面；路径/面ID不是原Gaussian行号。',
        '2704面部分座面与3055面上部椅背为人工选区；波纹、碎线、薄腿缺损及不完整部件未改善。',
        '缓存只加速同视点墨色/轮廓合成；转动、几何、标签、路径、宽度或交叉开关变化需完整重绘。单条缓存数组18MiB，128MiB上限，切换会话释放覆盖。',
        '速度为本机CPU2/512²/2xAA的3次配对测量；完整编辑还包含文件树容量检查，未承诺实时或跨平台性能。',
        '局部性掩码来自同一代理，固定2px目标边界带；旧unit022单像素残差不被本轮重写。',
        '四静态视图、18帧解码和冷重放不等于全时序或几何/语义认证；H1/H2/H5未测，P1 NO_GO/P2不可辨识保留。',
        '冷浏览器与后续回归外层各rc143；冷浏览器主返回码UNKNOWN，回归收据随后确认rc1（12项测试OK后的辅助烟测异常）。未由PASS倒填rc0。最终缓存4测试有独立rc0。',
        '参照输入路径错误rc1后恢复；继承测试之后四模型烟测遇缺省viewer_camera KeyError，补用Editor相同默认值后仅重跑该烟测，rc0。',
        'GUI部分控件需滚动，原页面秒数是绘制保存阶段；包不含解释器/依赖二进制/原PLY，仅当前Linux验证。']
    elapsed=(datetime.datetime.fromisoformat(now())-datetime.datetime.fromisoformat(p['started_utc'])).total_seconds()/60
    status=dict(stage='UNIT_COMPLETE_EXACT_INK_RENDER_CACHE',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS_WITH_RETAINED_INTERRUPTION_AND_RECOVERED_HELPER_FAILURES',scientific_verdict='H1_H2_H5_NOT_TESTED; ENGINEERING_PERFORMANCE_ONLY',
        demo_progress=progress,artifacts=['PROTOCOL.json','metrics/PROFILE.json','metrics/TIMINGS_FINAL.json','metrics/STATIC.json','metrics/REGRESSIONS.json',
            'browser/BROWSER_VALIDATION.json','cold_browser/BROWSER_VALIDATION.json','metrics/FINAL_ARCHIVE_REPLAY.json','media/full_object_ink.png',
            'media/source_reference_all_views.png','media/chair_orbit.mp4','media/chair_zoom.mp4','portable_demo.tar.gz','PACKAGE_README_ZH.md',
            'source_snapshot','UNIT024_DIFF.patch','EVIDENCE_SHA256.json'],
        tests=dict(cache_tests=4,inherited_tests_log_OK=12,default_models_smoke=4,command_receipts=receipts,
            TDD='Actual Chair Editor ink-only change ray_surface call count 2 vs expected 1 failed rc1; cache implementation passes with frozen legacy equality and invalidation.'),
        retained_interruptions=['logs/COLD_BROWSER_OUTER_INTERRUPTION.json','logs/REGRESSION_OUTER_INTERRUPTION.json'],blockers=[],limitations=limitations,
        scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    next_step='整理真实Demo的主要编辑流程：把Render & save、Undo和下载按钮放到无需长距离滚动即可看到的位置，并显示包含资产保存的实际操作耗时。固定现有几何与默认资产，在Chair/Lego各完成一次局部编辑→ZIP保存→冷导入验证；保留慢速转动提示，不展开新模型或几何参数扫描。'
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='完整对象、局部编辑、冷加载与四模型已有真实证据；同视点墨色编辑已提速，剩余直接可见的使用阻力是控件滚动与耗时说明。小范围交互整理比第五模型或重复证明更接近交付。',estimated_next_minutes=15,
        no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    table=[]
    for v in static['views']:
        l=v['locality'];table.append(f"| {v['camera']['azimuth']} | {l['target_interior']['L1']:.4f} | {l['boundary']['L1']:.4f} | {l['far_other']['L1']:.4f} | {l['far_background']['L1']:.4f} | exact |")
    commands=[]
    for name,v in receipts.items():
        r=json.loads((U/v['path']).read_text());commands.append(f"| {name} | {r['returncode']} | {r['seconds']:.3f} |")
    report=f'''# Unit024：保持描画精确的同视点墨色编辑加速

工程completed，视觉partial；本轮约{elapsed:.1f}分钟。真实Chair完整对象的局部墨色修改，纯渲染中位数{med['full_render_seconds']:.3f}→{med['warm_render_seconds']:.3f}秒（{timing['render_speedup']:.1f}倍），包含验证、容量检查、资产保存与PNG/NPZ输出的Editor操作{med['full_editor_seconds']:.3f}→{med['warm_editor_seconds']:.3f}秒（{timing['editor_speedup']:.2f}倍）。这是三次本机配对测量，非实时性能承诺。

完整阅读BRIEF和原始大纲，复核P1最新完成unit010与中断unit011、P2源/报告/NEXT。实际查看unit023完整四视角、原GS/代理/区域对照、全部orbit接触表及当前渲染/编辑源码。四模型已可用，部分座面及椅背人工区域可保存恢复，主要可用性问题之一是等待。相较第五模型或继续小幅平滑，选择有实测依据的缓存加速。实际旧CATALOG为四默认模型、七可选示例，本轮新增墨色示例后八个，按实际文件计数。

紧凑协议SHA `{sha(U/'PROTOCOL.json')}` 在TDD和候选前冻结。源资产 `{p['asset']}`，源Chair PLY `{p['original']['original_ply']}`，SHA `{p['original']['sha256']}`。本轮原256690高斯重新执行CPU SH3/EWA四视图渲染；库与adapter/C++来源hash核验。本轮新冻结相机43/133/223/313°、仰角28°、距离4.9、512²/2xAA。模型及人工选区已有曝光，不称盲测。

唯一外观变量是部分座面region4墨色.80→.35；所有路径坐标、ID、二进制资产、其他区域样式不变。缓存保存逐区域、逐方向层的原2x可见覆盖，用原float32赋值、max合成再降采样。没有使用低分辨率层的近似合成。内容哈希包含网格/标签/法线/路径/支持掩码/相机/采样率及除墨色外的样式；HTML显式默认交叉参数规范化。零墨色不丢覆盖，宽度、交叉开关、相机或任何支持变化失效。单条缓存数组18MiB，128MiB上限；切换模型/示例时释放，不写入ZIP。冷加载仍做一次完整渲染。

真实TDD先在Chair Editor中观察到重复ray_surface计算（2次而非1次），rc1；实现后通过。最终4项真实资产测试覆盖旧渲染全字段精确、0墨色和显示修改、返回数组污染隔离、原地路径/掩码/标签/几何变化失效、相机/线宽/采样率失效、Lego交叉开关及缓存容量上限。12项继承墨色/交叉层/例子隔离测试日志OK。四默认模型均实际重绘并与旧渲染一致，八个可选例子都加载成功。

四视角共8个完整对象状态，5种PNG和保存全部数组与冻结旧渲染逐值相同；非目标层、深度、标签与轮廓保持相同。目标变化非零，同代理mask、固定2px带分区如下，完整分母见metrics/STATIC.json。

| Az | 目标内部L1 | 边界带L1 | 远其他L1 | 远背景L1 | 缓存/旧渲染 |
|---:|---:|---:|---:|---:|---|
{chr(10).join(table)}

实际Firefox完成墨色.35→0→.35、宽度变化失效、Undo、刷新、旋转和缩放、PNG与ZIP下载。新服务器/新浏览器导入ZIP，首次无缓存完整渲染与保存图像/数组一致，随后墨色命中缓存；真实按钮导出12帧orbit及6帧zoom。18帧无损视频完整RGB核验，MP4完整解码计数。最终tar解压后，逐条执行文档中的冷图片、改深、再改浅以及18帧运动重放，并在另一个新进程导入实际浏览器ZIP、首次无缓存Editor绘制；所有PNG/数组/二进制路径检查通过，子命令有真实rc0。

实际查看四视角前后对照、原GS/代理/区域图、浏览器墨色图及全部18帧接触表。座面局部变浅可见，但前沿碎线、座面波纹、侧后视图的轮廓重复、细腿缺损与人工区域边界仍在。速度收益不改变视觉partial，也不证明H1/H2/H5。

保留所有失败：reference辅助脚本初次误用source_reference而非source_model读取旧库来源，rc1且尚未渲染，改正后rc0。两次外层工具session93320/17487返回143，冷浏览器主返回码UNKNOWN，仍继续完成行为、导出及清理。回归主进程的收据随后确认rc1：12项测试OK后，四模型烟测遇viewer_camera缺省KeyError；只修辅助烟测使用Editor相同缺省相机，重新烟测rc0。第一次收尾因发现这个迟到的非零收据而断言失败rc1，未写完成状态或seal；更新收据事实后重新打包与冷检，初版包/快照/冷检证据保留。没有覆盖旧日志或把PASS当返回码。后续命令将收据写入者放在独立自有worker，实际冷重放收据齐全。空补丁和一次未匹配的报告补丁均被工具拒绝，无文件改动。历史unit023及更早的失败不改写。

| Command | Return code | Seconds |
|---|---:|---:|
{chr(10).join(commands)}

准确argv/cwd/UTC/返回码见logs/*.receipt.json；冷浏览器缺失主返回码和外层中断见独立记录。source_snapshot/、SOURCE_SNAPSHOT.json与UNIT024_DIFF.patch支持重放；最终包源与工作源码核验。CPU两核、数值线程1、串行，无GPU、凭据、环境转储、嵌套模型、push/merge。只封存已核对的工程证据、真实失败和限定说明；scientific_seal=false，reported_not_independently_verified。

启动：`cd {U}/portable_demo && ./run.sh viewer --scene chair --example chair_ink_preview --port 8765`。完整操作见PACKAGE_README_ZH.md，压缩包portable_demo.tar.gz含四模型、八例子、源码、实际预览/视频与ZIP。

'''+ '\n'.join('- '+x for x in limitations)+f'\n\nNEXT=continue：{next_step}\n'
    (U/'REPORT_ZH.md').write_text(report)
    reproduce=['# 实际执行收据\n','所有命令数值工作串行，解释器先导入runtime限制CPU/禁用CUDA。\n']
    import shlex
    for name,v in receipts.items():
        r=json.loads((U/v['path']).read_text());reproduce.append(f"\n## {name}\n\nrc={r['returncode']}，{r['seconds']:.3f}s，cwd={r['cwd']}\n\n```bash\n{shlex.join(r['command'])}\n```\n")
    reproduce.append('\n外层143不伪造子返回码，详情见logs/*INTERRUPTION.json。\n')
    (U/'REPRODUCE_ZH.md').write_text(''.join(reproduce))
    output_guard(U)
    resources=dict(root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
        output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),cpu=2,numeric_threads=1,gpu=False)
    js(U/'metrics/RESOURCES_FINAL.json',resources)
    evidence={}
    folders=('assets','renders','source_reference','media','metrics','source_snapshot')
    for folder in folders:
        for n,h in hashes(U/folder).items():evidence[folder+'/'+n]=h
    for folder in ('browser','cold_browser'):
        for n in ('BROWSER_VALIDATION.json','CLEANUP.json','SAVED_STATE.json','chair_edited.zip','chair_edited.png'):
            if (U/folder/n).is_file():evidence[folder+'/'+n]=sha(U/folder/n)
    for f in (U/'logs').iterdir():
        if f.is_file():evidence[str(f.relative_to(U))]=sha(f)
    for n in ('STATUS.json','REPORT_ZH.md','NEXT.json','PROTOCOL.json','PACKAGE_README_ZH.md','REPRODUCE_ZH.md','SOURCE_SNAPSHOT.json','UNIT024_DIFF.patch','portable_demo.tar.gz'):
        evidence[n]=sha(U/n)
    js(U/'EVIDENCE_SHA256.json',dict(schema='validated_engineering_evidence_v1',created_utc=now(),files=evidence,
        scientific_seal=False,scope='Validated engineering outputs and explicitly retained failures; browser profiles, mutable runtime/codex responses excluded.'))
    assert all(sha(U/n)==h for n,h in evidence.items())
    shutil.copy2(U/'PACKAGE_README_ZH.md',OUTPUT_ROOT/'DEMO_README_ZH.md')
    shutil.copy2(U/'PACKAGE_README_ZH.md',SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md')
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(unit='unit_024',execution_state='completed',updated_utc=now(),demo_progress=progress,
        package=str(U/'portable_demo.tar.gz'),package_sha256=sha(U/'portable_demo.tar.gz'),readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),
        report=str(U/'REPORT_ZH.md'),status=str(U/'STATUS.json'),next=str(U/'NEXT.json'),limitations=limitations,scientific_seal=False,
        supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,evidence_files=len(evidence),package_bytes=integrity['bytes'],next_action='continue')))

if __name__=='__main__':main()
