"""Finalize validated engineering evidence, then seal only immutable unit files."""
import runtime
from runtime import js,sha,now,output_guard,OUTPUT_ROOT
from pathlib import Path
import argparse,json,shutil,subprocess,difflib,datetime,shlex,os
from unit015_run import UNIT as U,PREVIOUS,SOURCE,protocol

def finish():
    output_guard(U);p=protocol()
    assert sha(p['original']['original_ply'])==p['original']['sha256']
    assert {f.name:sha(f) for f in Path(p['asset']).iterdir() if f.is_file()}==p['inputs']
    assert sha(U/'PROTOCOL.json')==sha(Path('docs/partwise_sketch_hatching_v04/UNIT015_PROTOCOL.json'))
    lock=json.loads((U/'metrics/INPUT_LOCK.json').read_text())
    for scene,files in lock['default_assets'].items():
        assert files=={f.name:sha(f) for f in (PREVIOUS/'portable_demo/assets'/scene).iterdir() if f.is_file()}
    required=['tdd_green','cached_cross_test','candidate','original_lego','static_views','browser_recovery','stage','cold_orbit_recovery','cold_zoom_recovery','recovery_audit','package','final_archive_check']
    receipts={}
    for file in sorted((U/'logs').glob('*.receipt.json')):
        record=json.loads(file.read_text());receipts[file.name.removesuffix('.receipt.json')]=dict(returncode=record['returncode'],path=str(file.relative_to(U)))
    assert all(receipts[name]['returncode']==0 for name in required)
    assert receipts['tdd_red']['returncode']==1 and receipts['browser']['returncode']==-2
    browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text());assert browser['status']=='PASS'
    cold=json.loads((U/'metrics/COLD_REPLAY.json').read_text());assert sum(r['frame_count'] for r in cold.values())==18
    assert all(r['all_png_exact'] and r['all_arrays_exact'] for r in cold.values())
    final=json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text());assert final['CLI_PNG_exact'] and final['cold_viewer_PNG_exact']
    geom=json.loads((U/'metrics/REFINEMENT.json').read_text());loc=json.loads((U/'metrics/LOCALITY.json').read_text())
    own_pids=[]
    for root in ('browser','browser_interrupted'):
        for item in json.loads((U/root/'OWN_CHILDREN.json').read_text())['children']:own_pids.append(item['pid'])
    own_pids.append(json.loads((U/'logs/FINAL_VIEWER_CHILD.json').read_text())['pid'])
    alive=[]
    for pid in own_pids:
        try:os.kill(pid,0);alive.append(pid)
        except ProcessLookupError:pass
    assert not alive,alive
    js(U/'metrics/FINAL_GUARDS.json',dict(utc=now(),own_pids_checked=own_pids,own_processes_remaining=alive,
        original_ply_unchanged=True,input_asset_files_unchanged=True,default_four_assets_unchanged=True,protocol_unchanged=True,
        affinity=sorted(os.sched_getaffinity(0)),gpu=False,final_validated_numeric_serial=True,original_schedule_overlap_preserved='EXECUTION_AMENDMENT.json',
        root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_SNAPSHOT.json',dict(utc=now(),files={f.name:sha(f) for f in sorted((U/'source_snapshot').iterdir()) if f.is_file()},
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
        note='Full replay source; preexisting dirty worktree retained. source_before is protocol-freeze time, including the new runner and red tests.'))
    diff=[]
    names={f.name for f in (U/'source_before').iterdir() if f.is_file()}|{f.name for f in SOURCE.iterdir() if f.is_file()}
    for name in sorted(names):
        a=U/'source_before'/name;b=SOURCE/name
        before=a.read_text().splitlines(True) if a.exists() else [];after=b.read_text().splitlines(True) if b.exists() else []
        diff.extend(difflib.unified_diff(before,after,fromfile='protocol_freeze/'+name,tofile='unit015/'+name))
    (U/'UNIT015_DIFF.patch').write_text(''.join(diff))
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-22T06:31:57.669731+09:00')).total_seconds()/60
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],scene='lego',original_PLY_render_this_unit=True,
        original_gaussians=310475,proxy_faces=geom['faces'],manual_bucket_faces=2030,moved_vertices=geom['moved_vertices'],
        max_displacement=geom['displacement_max'],displacement_bbox_fraction=geom['displacement_bbox_fraction'],
        non_target_geometry_and_path_files_exact=True,manual_selection_and_face_labels_exact=True,topology_unchanged=True,
        target_paths_before=351,target_paths_after=339,roughness_mean_degrees=[geom['target_roughness_before']['mean_angle_degrees'],geom['target_roughness_after']['mean_angle_degrees']],
        geometry_revision_saved=True,cached_disabled_cross_reanchored_and_reenabled=True,full_object_static_views=4,states_per_view=3,
        actual_browser_downloads=4,motion_frames=18,lossless_video_frames_exact=18,mp4_frames_decoded=18,cold_replay_png_arrays_exact=18,
        portable_cli_refine_and_local_edit=True,cold_viewer_png_exact=True,defaults_unchanged=True,default_promoted=False,
        strict_pixel_locality=dict(scope='four frozen cameras, baseline proxy masks fixed2px band; geometry and local style probe reported separately',
            geometry_far_other=sum(v['baseline_mask']['far_other']['L1'] for v in loc['views']),geometry_far_background=sum(v['baseline_mask']['far_background']['L1'] for v in loc['views']),
            style_far_other=sum(v['style_probe']['far_other']['L1'] for v in loc['views']),style_far_background=sum(v['style_probe']['far_background']['L1'] for v in loc['views']),
            geometry_non_target_layer_L1_including_changed_occlusion=sum(sum(v['non_target_layer_L1'].values()) for v in loc['views'])),
        visual_quality='partial; modest broad bucket surface improvement, tooth/rim noise and thin surfaces remain; global platform/body clutter unchanged',
        scientific_seal=False,reasoning='Existing real-model demo now supports a separately versioned local geometry refinement while keeping selected-part editing, cached layers, saved provenance, downloads and cold replay usable. Geometry benefit is limited and exploratory.')
    limits=['No independent surface truth: smoothing lowers its own roughness measure; no reconstruction accuracy or H1/H2/H5 claim.',
        'Original model-derived proxy has holes/thin parts. Open/region boundary pinning limits smoothing; tooth/rim and weak side-view noise persists.',
        'Manual2030-face bucket selection is reused, not learned or guaranteed complete semantics; old screen recipe stays bound to its old mesh.',
        'Target path count and arclength decrease with geometry change; rendered ink/coverage reported, no equal-ink aesthetic comparison.',
        'Non-target path bytes are exact but geometry changes nearby occlusion; aggregate non-target layer L1 is nonzero and explicitly reported.',
        '18 decoded/replayed frames and four static views do not certify continuous temporal stability or independent visibility.',
        'Current Linux relocation tested; interpreter/dependencies not bundled.']
    js(U/'STATUS.json',dict(stage='UNIT_COMPLETE_WITH_VISUAL_LIMITATIONS',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS_AFTER_PRESERVED_BROWSER_INTERRUPTION_AND_SCHEDULE_RECOVERY',scientific_verdict='H1_H2_H5_NOT_TESTED_EXPLORATORY_LOCAL_PROXY_REVISION',
        demo_progress=progress,artifacts=['PROTOCOL.json','PACKAGE_README_ZH.md','assets/refined','assets/style_probe','media/full_object_before_after.png',
        'media/source_proxy_regions_edit.png','media/bucket_detail_supplement.png','media/lego_refined_orbit.mp4','media/lego_refined_zoom.mp4',
        'browser/BROWSER_VALIDATION.json','metrics/REFINEMENT.json','metrics/LOCALITY.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json',
        'portable_demo.tar.gz','source_snapshot','UNIT015_DIFF.patch'],tests=dict(real_model_behavior_tests=4,actual_Firefox=True,TDD_red_preserved=True,command_receipts=receipts),
        blockers=[],limitations=limits,failures_preserved=['logs/tdd_red.receipt.json','logs/tdd_red.log','logs/browser.receipt.json','browser_interrupted','logs/cold_orbit.receipt.json','logs/cold_zoom.receipt.json','attempt_schedule_overlap','EXECUTION_AMENDMENT.json'],
        scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    recommended='增加一个保持几何和所有3D路径不变的分区墨色强度控件，默认完全复现原0.80墨色；仅用一次预冻结的Lego底板region1=0.40候选，其他区域仍0.80。通过完整对象/弱视角、逐层墨量与局部性、保存/撤销/冷重开验证底板能否退后，避免再次扩大局部平滑或新增模型。保留原版，透明披露这是艺术明暗控制而非几何改善，不做扫参或同墨量审美优越结论。'
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=recommended,demo_progress=progress,
        reason='Core real-model editing/export/cold-reload is working. This bounded proxy change has only modest whole-object effect; all regions currently share hard-coded0.80 ink, and dense platform lines remain a prominent readable-demo bottleneck. A local tone control is independently useful without changing anchors.',
        estimated_next_minutes=30,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    table='\n'.join(f"| {v['camera']['azimuth']} | {v['baseline_mask']['target_interior']['L1']:.3f} | {v['target_visible_pixels']['baseline']}→{v['target_visible_pixels']['refined']} | {v['target_layer_ink']['refined']/v['target_layer_ink']['baseline']:.4f} | {sum(v['non_target_layer_L1'].values()):.3f} | {v['style_probe']['target_interior']['L1']:.3f} |" for v in loc['views'])
    report=f'''# Unit015：真实Lego铲斗局部代理修订与可重放Demo

执行状态 **completed**（本轮工程范围），整体视觉 **partial**。从用户给定开始时间计约{elapsed:.1f}分钟。实际原PLY CPU参考、四全对象视角×三状态、真实Firefox局部编辑/四次下载、18运动帧全解码和冷重放、可迁移CLI重新执行局部修订均已完成。原四默认资产未替换；候选作为opt-in例子。H1/H2/H5未测试。

## 审阅与冻结

完整读取BRIEF/851行大纲、P1完成unit010及P2相关报告/NEXT/源，实际审阅unit014四整对象视角和原GS对照。交叉层已有可用性，剩余波折主要来自代理；选择单次局部平滑，不增加模型、不重做手工选面。历史NO_GO和H2零余量原样保留，见READING_REVIEW_ZH。

协议冻结{p['frozen_utc']}，SHA `{sha(U/'PROTOCOL.json')}`。输入`{p['asset']}`；原PLY SHA `{p['original']['sha256']}`（310475高斯），源mesh SHA `{geom['source_mesh_sha256']}`，候选mesh SHA `{geom['mesh_sha256']}`。原vanilla GS深度的CPU融合代理16543顶点/29999面，不是GT或RaDe训练结果；沿用三次手工矩形选面region4共2030面。

## 实际几何与路径变化

仅一个预冻结候选：10轮正/负步(.5,-.53)，位移≤.018，面/标签/选面不变，非目标所用顶点、区域边界、开边和非流形边固定。移动647顶点，固定15896；最大位移.018（bbox对角线0.6009%），12次顶点提案恢复，全部原面法向内积>0且面积≥原20%。这不保证全局无自交或几何准确。

目标2682条真实共享边的平均相邻法线夹角28.1789°→19.9087°，P95 80.3749°→69.6067°。此指标由平滑直接驱动，不是独立重建收益。基础路径199→194、长度16.5169→15.8204；交叉152→145、长度12.2806→11.5150，最长仍≤.12+数值误差。目标路径是明确的新修订，不宣称坐标/ID含义跨修订不变；其他region1/2/3路径文件字节精确，手工选择与历史精确。

原风格保持35°/xz、spacing.060、length.12、width1、cross+60°/.075；另固定angle50°检查候选仍可局部编辑。相机233/323/53/143°、仰角30°、距离5.1、512²/2xAA/轮廓1，全部对象在画内。

| 方位 | 几何编辑目标内部L1 | 目标可见像素原→新 | 目标hatch墨量新/旧 | 非目标layer L1含遮挡改变 | 后续angle编辑目标内部L1 |
|---:|---:|---:|---:|---:|---:|
{table}

固定2px边带、基线mask和前后并集mask两种口径都保存；四视图几何编辑及后续风格编辑远其他/远背景L1均0。**几何编辑的非目标分层L1合计17.600001**，来自目标附近可见性改变，不能写成全部非目标渲染精确。风格编辑在候选固定网格上则depth/regions/contour与region1/2/3层精确。mask来自同一代理，非独立语义GT。墨量和可见面积减少如表，不以少画自动判美观成功。

实际查看全对象、proxy/regions/原GS面板、补充铲斗图和全部18运动接触图：323°宽面局部更平顺，233/143°变化较细微；53°齿边/薄侧面仍碎，固定开边限制改善；原履带、平台、驾驶室和杆件的孔洞/线团仍在。整体收益有限，候选不提升为默认，不作盲审美或真实形状保真结论。

## 测试、交互与冷重开

TDD真实红灯rc1：旧refine用rmin=4导致同一Lego目标改名region7就改变结果；新asset wrapper尚不存在。修复初值为整数上界并实现局部保存后，3项真实行为测试rc0；补充关闭状态的缓存交叉层重锚/再开启测试rc0，共4项。验证非目标几何/文件、位移/面翻转、同标签改名、非法设置拒绝、加载不重生成和局部编辑。

Firefox实际加载修订资产、angle35→50、保存、Undo、刷新、Orbit/Zoom，图像与冻结CLI精确；实际下载资产ZIP/PNG/12帧orbit/6帧zoom四文件。FFV1全18帧RGB精确，MP4全解码计数通过。新Python进程从下载资产+相机重放18/18 PNG和分层数组精确；有限帧不等于全时序认证。

最终tar解压到新目录，使用文档run.sh refine从原版再生全部mesh/路径字节精确；CLI export PNG与浏览器精确，CLI angle50再生路径与冻结探针精确；冷viewer恢复选区4、手工历史、相机/风格/显示和PNG精确。只验证当前Linux依赖环境，未捆绑解释器/依赖。

## 中断与恢复

首个browser wrapper收到外部SIGTERM，11.633秒后退出143，child=-2；原因未知。第二次信号打断原finally，留下本测试两个记录PID；仅终止这些自有进程组，确认消失后重试。原log/receipt/部分目录保留browser_interrupted。仅加固清理时忽略重复信号且WebDriver DELETE限3秒；同协议新目录重试rc0，候选/风格/相机没有重选。EXECUTION_AMENDMENT记录原退出，未把部分浏览器输出算完整证据。

原首轮cold_orbit尚未退出就误启动cold_zoom，两个数值进程重叠1.834727秒，违背串行要求；两者仍在相同两核affinity/单数值线程内。发现后仅终止自己的zoom组（child=-15，wrapper241），orbit原rc0保留；两原目录移到attempt_schedule_overlap，不作为有效调度证据。随后等待明确退出再依次串行重放相同orbit/zoom，并与原有帧逐文件对照，未改变科学候选或参数。不能声称初始调度从未失误。

最终纳入证据的数值阶段串行、数值线程1、两核affinity，无GPU/安装/凭据/环境dump/嵌套模型/push/merge。最终自有viewer/WebDriver均退出，原PLY/输入/四默认资产/协议哈希复核不变。完整精确命令和returncodes见REPRODUCE_ZH及logs。

## 交付和下一步

`cd {U}/portable_demo && ./run.sh viewer --scene lego --asset "$PWD/examples/lego_bucket_refined"`，浏览器127.0.0.1:8765。完整说明PACKAGE_README_ZH，交付portable_demo.tar.gz；SOURCE_SNAPSHOT包含可回放源码，UNIT015_DIFF相对于协议冻结时快照，继承dirty未清理。

只封存已检查工程证据，scientific_seal=false，parent仍reported_not_independently_verified。NEXT=continue：{recommended}
'''
    (U/'REPORT_ZH.md').write_text(report)
    commands=['# 实际命令与退出记录\n\n以下是实际执行收据，不将预期TDD红灯或外部中断改写为成功。\n']
    for name,row in receipts.items():
        record=json.loads((U/row['path']).read_text());commands.append(f"\n## {name}\n\nreturncode={record['returncode']}，耗时{record.get('seconds','unknown')}秒。\n\n```bash\n{shlex.join(record['command'])}\n```\n")
    (U/'REPRODUCE_ZH.md').write_text(''.join(commands))
    readme=Path('docs/partwise_sketch_hatching_v04/UNIT015_DEMO_README_ZH.md')
    shutil.copy2(readme,Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md'))
    shutil.copy2(readme,OUTPUT_ROOT/'DEMO_README_ZH.md')
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(latest_unit='unit_015',execution_state='completed',updated_utc=now(),demo_progress=progress,
        package=str(U/'portable_demo.tar.gz'),readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),report=str(U/'REPORT_ZH.md'),next_action='continue',
        scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,demo_progress=progress)))

def seal():
    assert json.loads((U/'STATUS.json').read_text())['execution_state']=='completed'
    selected=[]
    dirs=['source_snapshot','metrics','assets/refined','assets/style_probe','renders','source_model','media']
    for name in dirs:selected.extend(f for f in (U/name).rglob('*') if f.is_file())
    for name in ['PROTOCOL.json','STATUS.json','REPORT_ZH.md','NEXT.json','READING_REVIEW_ZH.md','PACKAGE_README_ZH.md',
                 'REPRODUCE_ZH.md','SOURCE_SNAPSHOT.json','UNIT015_DIFF.patch','EXECUTION_AMENDMENT.json','VISUAL_REVIEW.json','portable_demo.tar.gz',
                 'browser/BROWSER_VALIDATION.json','browser/EXPORT_STATE.json','browser/CLEANUP.json','browser/lego_asset.zip',
                 'browser/lego_image.png','browser/02_refined_bucket.png','browser/03_local_angle_edit.png','browser/05_export_complete.png',
                 'browser_interrupted/MANUAL_CLEANUP.json']:
        selected.append(U/name)
    for kind in ('orbit','zoom'):
        selected.append(U/'browser'/('lego_'+kind)/'VIDEO_RECEIPTS.json')
    selected.extend(f for f in (U/'logs').glob('*.receipt.json'))
    selected.extend(U/'logs'/name for name in ('tdd_red.log','tdd_green.log','cached_cross_test.log','browser.log','FINAL_VIEWER_CLEANUP.json'))
    files={str(f.relative_to(U)):sha(f) for f in sorted(set(selected))}
    js(U/'ENGINEERING_MANIFEST.json',dict(utc=now(),files=files,scope='Validated finite engineering evidence plus explicitly retained failure receipts; excludes runtime profiles, mutable package runs and final sealing process output.',scientific_seal=False))
    assert all(sha(U/name)==digest for name,digest in files.items())
    js(U/'ENGINEERING_SEAL.json',dict(utc=now(),manifest='ENGINEERING_MANIFEST.json',sha256=sha(U/'ENGINEERING_MANIFEST.json'),files=len(files),
        validated_engineering_only=True,scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(manifest_files=len(files),manifest_sha256=sha(U/'ENGINEERING_MANIFEST.json'))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['finish','seal']);a=p.parse_args();globals()[a.phase]()
