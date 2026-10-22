"""Finalize only after actual packaged cold runs; seal finite engineering evidence."""
import runtime
from runtime import js,sha,now,output_guard,OUTPUT_ROOT
from pathlib import Path
import datetime,json,os,shutil,subprocess
from unit025_run import U,PREV,SOURCE,hashes

def main():
    p=json.loads((U/'PROTOCOL.json').read_text())
    browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text())
    cold=json.loads((U/'cold_browser/BROWSER_VALIDATION.json').read_text())
    replay=json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
    assert browser['status']==cold['status']=='PASS'
    assert replay['archive_sha256']==sha(U/'portable_demo.tar.gz')
    assert hashes(SOURCE)==json.loads((U/'SOURCE_SNAPSHOT.json').read_text())
    for scene,d in p['inputs'].items():assert hashes(Path(d['asset']))==d['files']
    preservation=json.loads((U/'metrics/PRESERVATION.json').read_text());assert all(preservation.values())
    for name in ('browser','cold_browser'):
        cleanup=json.loads((U/name/'CLEANUP.json').read_text());assert cleanup['own_child_groups_only']
        for c in cleanup['children']:
            assert c['returncode'] is not None
            result=subprocess.run(['ps','-p',str(c['pid']),'-o','pid=,comm='],capture_output=True,text=True)
            assert not result.stdout.strip(),result.stdout
    records={f.stem.removesuffix('.receipt'):json.loads(f.read_text()) for f in sorted((U/'logs').glob('*.receipt.json'))}
    for name,r in records.items():assert r['returncode']==(1 if name=='tdd_red' else 0),(name,r['returncode'])
    assert all(name in records for name in ('tdd_red','tdd_green','browser','cold_browser','package_build','package_check','packaged_viewer'))
    package=json.loads((U/'portable_demo/PACKAGE_FILES.json').read_text())['files']
    assert all(sha(U/'portable_demo'/f)==v for f,v in package.items())
    operation=[r for r in browser['events'] if r['action']=='real local ink edit; all NPZ paths and non-target layers preserved']
    timings=[r for r in browser['events'] if r['action']=='#apply']
    for scene in ('chair','lego'):
        for arm in ('baseline','edited'):
            frame=json.loads((U/'browser'/(scene+'_'+arm)/'frame_000.json').read_text())
            assert frame['bounds']['all_proxy_vertices_inside']
    output_guard(U)
    resources=dict(utc=now(),affinity=sorted(os.sched_getaffinity(0)),root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(U).free,
        total_task_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),unit_bytes=sum(f.stat().st_size for f in U.rglob('*') if f.is_file()),owned_browser_groups_exited=True)
    js(U/'metrics/RESOURCES_FINAL.json',resources)
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],newly_run_models=['chair','lego'],new_original_PLY_renders=False,
        existing_proxy_source='original checkpoint SHA verified; saved model-derived proxies actually rendered',default_assets_preserved=4,optional_examples_preserved=8,
        fixed_primary_actions=True,actual_viewport_widths=[1280,1024,500],actual_viewport_heights=[714,682,758],mobile_device_tested=False,
        full_object_baseline_edited_states=4,actual_browser_local_edit_undo_PNG_ZIP_models=2,fresh_server_browser_ZIP_import_exact_models=2,
        packaged_entrypoint_cold_ZIP_import_exact_models=2,all_NPZ_assets_unchanged_by_ink_edit=True,non_target_layers_exact=True,
        timing_includes_asset_save=True,timing_browser_image_decode=True,first_apply_server_seconds={s:next(x['operation_seconds'] for x in timings if x['scene']==s) for s in ('chair','lego')},
        orbit_frames=12,zoom_frames=6,full_lossless_exact_decode_frames=18,MP4_decoded_frames=18,relocated_cold_replay_exact_frames=18,
        visual_quality='partial: inherited proxy ripples, thin geometry defects and incomplete manual regions',automatic_semantics=False,
        reasoning='The existing real-model demo now keeps save, undo and downloads visible, reports complete save/render latency, and has two-model browser ZIP round trips plus a cold-run portable delivery. No geometry or scientific improvement is claimed.')
    limitations=[
        '旧vanilla GS的CPU衍生代理；本轮未重渲染原PLY，仅核验其SHA。历史原GS对照明确标注来源。不是GT、独立实测表面或新的RaDe-GS训练。',
        'Chair局部座面和Lego铲斗为继承人工选区；原区域规则、几何、路径未变。波纹、碎线、薄部件缺损、不完整选区仍在，视觉partial。',
        '局部性仅在两幅冻结视点用同一代理标签与固定2px带测量；非目标图层/路径精确不等于独立几何真值。',
        '浏览器计时含提交到图像解码；服务器计时含验证、资产保存和绘图，排除传输及最后计时元数据写入。少量本机操作观测，不是新性能基准或实时保证。',
        'Firefox实际视口为1280×714、1024×682、500×758；390px窗口请求被限制为500，没有真机移动端验证。细风格参数、导入和视频仍需滚动。',
        '18帧完整解码和冷重放是有限工程证据，不是全时序稳定认证。H1/H2/H5未测，P1 NO_GO/P2不可辨识与历史失败保持原状。',
        '包不含解释器、依赖二进制或原PLY；仅当前Linux/Firefox实际验证。离线资产绘制不需原PLY。',
        '冷浏览器第一次启动的收据包装器拒绝--name参数，rc2且浏览器未启动；改用argparse.REMAINDER后完整运行rc0，原失败保留。TDD预期失败rc1保留。']
    artifacts=['PROTOCOL.json','browser/BROWSER_VALIDATION.json','cold_browser/BROWSER_VALIDATION.json','media/two_model_edit_cold.png','media/two_model_proxy_regions.png','media/chair_orbit.mp4','media/chair_zoom.mp4','metrics/FINAL_ARCHIVE_REPLAY.json','metrics/PACKAGE_INTEGRITY.json','metrics/VISUAL_REVIEW.json','portable_demo.tar.gz','PACKAGE_README_ZH.md','source_snapshot','SOURCE_SNAPSHOT.json','UNIT025_DIFF.patch','EVIDENCE_SHA256.json']
    status=dict(stage='usable_real_model_demo_delivery',execution_state='completed',scientific_verdict='NOT_TESTED_H1_H2_H5; engineering complete, visual partial; inherited P1 NO_GO/P2 unidentifiable retained',finished_utc=now(),demo_progress=progress,artifacts=artifacts,
        tests=dict(TDD='Real Chair missing full operation timer fails rc1; implementation includes delayed save and passes rc0',command_receipts={n:dict(returncode=r['returncode'],path='logs/'+n+'.receipt.json') for n,r in records.items()},browser_locality=operation),blockers=[],limitations=limitations,scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    step='将常用区域/墨色控件和打开ZIP入口前置，压缩示例说明、折叠高级人工选区工具，减少首屏到实际风格编辑的滚动；固定现有模型与参数，仅做一次从启动到局部编辑/下载/重新打开的真实流程验证。09:20后只做工程交付，不开新科学比较，09:45前收尾。'
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=step,reason='完整对象、局部编辑、两模型冷导入和便携入口均已运行；主要操作栏解决了保存按钮难找的问题，实际界面仍把常用墨色控件放在长说明下方。此独立小改动比扩展模型或参数扫描更接近易用交付。',demo_progress=progress,estimated_next_minutes=12,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00'))
    report=['# Unit025：主要操作可见、真实耗时与两模型冷交付','',
        '工程 completed，视觉 partial。已完整读取BRIEF和851行原大纲，复核P1 unit010报告/NEXT及中断unit011状态、P2源码/报告/NEXT。旧限制由当前用户授权替代；只在指定分支/工作树与unit025输出目录工作。',
        '实际检查unit024四视角完整对象修改、原GS/代理/区域图和全部18运动帧。四模型已经可运行，重建波纹和薄部件不足仍在；选择把保存、撤销、资产ZIP/PNG下载和状态放在固定顶部操作栏，桌面控件可独立滚动、预览随窗口高度缩放。本轮不改变几何/排线算法，未扩展第五模型。',
        '协议SHA：`'+sha(U/'PROTOCOL.json')+'`，冻结于 '+p['frozen_utc']+'。Chair输入为unit024的chair_ink_preview，region4墨色.35→.65，相机43°/28°/4.9；Lego为lego_bucket_cross，region4墨色.8→.35，相机见PROTOCOL输入（-127°/30°/5.1）。都是历史已曝光人工区域，非盲测试。原PLY路径与SHA、全部输入资产SHA见PROTOCOL.json。',
        '真实Chair TDD先发现operation_seconds缺失，rc1；增加覆盖验证、保存、绘图和保存输出的计时后，包含受控保存延迟的真实资产测试rc0。浏览器另测提交至图像decode完成的ready in。操作栏和状态实际在三个视口、页面顶部/底部通过可见性及点击命中检查；请求390px但Firefox实际500px，原数据如实保存。',
        '实际Firefox在Chair和Lego中选择示例、局部修改、撤销、再次修改、刷新、旋转、缩放、恢复相机、下载PNG与ZIP。修改前后全部NPZ文件字节不变，非目标图层/深度/标签/轮廓精确保持。所有完整对象静态状态的代理顶点入画。局部量使用同代理标签和固定2px带：','',
        '| Model | Target interior L1 | Boundary L1 | Far other L1 | Far background L1 | Save + render seconds |','|---|---:|---:|---:|---:|---:|']
    for row in operation:
        s=row['scene'];loc=row['locality'];report.append(f"| {s} | {loc['target']['L1']:.4f} | {loc['boundary']['L1']:.4f} | {loc['far_other']['L1']:.4f} | {loc['far_background']['L1']:.4f} | {progress['first_apply_server_seconds'][s]:.3f} |")
    report+=['','实际两次浏览器显示ready in均约1.09秒；这只是本机单次操作读数，不声称新速度收益。保存阶段明显超过仅绘图约.23/.25秒，因此本轮修正了过去显示范围偏小的问题。',
        '新服务器/新Firefox分别导入实际下载的Chair和Lego ZIP，首次绘制均cache miss，PNG与全部保存数组精确相同，资产路径和样式恢复；继续改墨色后也可精确返回。Chair真实按钮导出12帧orbit和6帧zoom，两种视频均完整解码计数，FFV1全部18帧逐像素一致；全部接触表已实际查看，弱侧后视图不隐藏。',
        '最终portable_demo.tar.gz解压到final_archive后，实际运行文档中的两模型冷PNG、Chair逆向墨色编辑与PNG、12+6帧运动重放，全部PNG/数组一致。另通过解压副本run.sh viewer启动全新服务器，分别导入实际ZIP，首帧无缓存且一致，服务SIGINT正常退出rc0。包包含四默认资产、八原样示例、本轮两编辑资产/ZIP、源码、预览、运动视频与历史参照来源记录；source_snapshot和UNIT025_DIFF.patch给出本轮可重放源码。',
        '实际视觉：Chair座面变深、Lego铲斗变浅可辨；没有改变Chair波纹/碎轮廓和薄腿不足，Lego平台、细支架仍有噪线。工具改善的是操作可达性和计时真实性，不能写成几何恢复、语义理解或H1/H2/H5成功。',
        '保留原失败：收据包装器第一次转发--name cold_browser被argparse拒绝rc2，无浏览器子进程启动；只修包装器后原计划冷流程rc0。logs/cold_browser_launch_failure.json保留准确argv和错误。TDD预期rc1也保留。没有覆盖unit024或更早失败。','',
        '| Command | Return code | Seconds |','|---|---:|---:|']
    report += [f"| {n} | {r['returncode']} | {r['seconds']:.3f} |" for n,r in records.items()]
    report+=['','准确argv/工作目录/UTC/返回码见logs/*.receipt.json；浏览器子进程清理由各CLEANUP.json记录，最终确认其PID已退出。CPU affinity[0,1]，数值线程1，串行；无GPU、凭据、环境转储、嵌套模型、push或merge。','',*['- '+x for x in limitations],'',
        '启动：`cd '+str(U/'portable_demo')+' && ./run.sh viewer --scene chair --example chair_ink_preview --port 8765`。完整操作见PACKAGE_README_ZH.md。','',
        'NEXT=continue：'+step,'',
        '仅封存已核验的有限工程证据。scientific_seal=false；reported_not_independently_verified。']
    (U/'REPORT_ZH.md').write_text('\n\n'.join(report)+'\n')
    readme=(U/'PACKAGE_README_ZH.md').read_text()
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(readme)
    (SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(readme)
    delivery=dict(unit='unit_025',execution_state='completed',updated_utc=now(),demo_progress=progress,package=str(U/'portable_demo.tar.gz'),package_sha256=sha(U/'portable_demo.tar.gz'),readme=str(U/'PACKAGE_README_ZH.md'),report=str(U/'REPORT_ZH.md'),scientific_seal=False,limitations=limitations)
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',delivery);js(U/'DELIVERY_STATUS.json',delivery)
    targets=['PROTOCOL.json','STATUS.json','REPORT_ZH.md','NEXT.json','PACKAGE_README_ZH.md','DELIVERY_STATUS.json','SOURCE_SNAPSHOT.json','UNIT025_DIFF.patch','portable_demo.tar.gz']
    targets += [str(f.relative_to(U)) for folder in ('source_snapshot','metrics','media') for f in (U/folder).rglob('*') if f.is_file()]
    targets += [str(f.relative_to(U)) for f in (U/'logs').glob('*') if f.is_file() and not f.name.startswith('finalize.')]
    for folder in ('browser','cold_browser'):
        targets += [str(f.relative_to(U)) for f in (U/folder).iterdir() if f.is_file() and f.suffix in ('.json','.png','.zip')]
        for f in (U/folder).glob('*/frame_000*'):
            if f.is_file():targets.append(str(f.relative_to(U)))
    manifest={name:sha(U/name) for name in sorted(set(targets))}
    js(U/'EVIDENCE_SHA256.json',dict(scope='Validated finite engineering evidence, real failures and limitations; not a full scientific seal',scientific_seal=False,files=manifest))
    assert all(sha(U/name)==digest for name,digest in manifest.items())
    print(json.dumps(dict(execution_state='completed',evidence_files=len(manifest),package_sha256=delivery['package_sha256'],unit=str(U),next_action='continue')))

if __name__=='__main__':main()
