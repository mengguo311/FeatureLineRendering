"""Seal finite, validated manual-region engineering evidence only."""
import runtime
from runtime import js,sha,now,output_guard,OUTPUT_ROOT
from pathlib import Path
import argparse,json,shutil,subprocess,datetime,shlex

def finish(unit):
    unit=output_guard(unit);work=Path(__file__).resolve().parents[2]
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    p=json.loads((unit/'PROTOCOL.json').read_text());v=json.loads((unit/'metrics/VALIDATION.json').read_text())
    browser=json.loads((unit/'browser_complete/BROWSER_VALIDATION.json').read_text())
    assert v['status']==browser['status']=='PASS'
    for name in ('EXPORT_REPLAY','PORTABLE_REPLAY'):
        assert json.loads((unit/f'metrics/{name}.json').read_text())['status']=='PASS'
    videos=json.loads((unit/'media/VIDEO_VALIDATION.json').read_text())['videos']
    assert sum(row['frames'] for row in videos)==18 and all(row['all_decoded_frames_exact'] for row in videos)
    # Recheck immutable prior evidence without touching the prior unit.
    old=Path(p['source_unit']);old_manifest=json.loads((old/'SHA256_MANIFEST.json').read_text())
    for row in old_manifest['files']:assert sha(old/row['path'])==row['sha256'],row['path']
    for path,h in p['input_sha256'].items():assert sha(path)==h
    old_protocol=json.loads((old/'PROTOCOL.json').read_text())
    input_checks={path:h for path,h in old_protocol['inputs_sha256'].items()
                  if path.startswith('/home/u00134/3dgs_line/tier1/') or path.endswith('EXISTING_MODEL_INPUTS.json')}
    for path,h in input_checks.items():assert sha(path)==h
    # Inspect only PID/comm for child IDs recorded by this unit.
    pids=[json.loads(f.read_text())['pid'] for f in (unit/'logs').glob('*.start.json')]
    for folder in ('browser','browser_complete'):
        cleanup=json.loads((unit/folder/'CLEANUP.json').read_text())
        pids.extend(row['pid'] for row in cleanup['children'])
    check=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid=,comm='],capture_output=True,text=True)
    assert not check.stdout.strip(), 'a recorded child PID is still present; inspect before sealing'
    js(unit/'metrics/FINAL_AUDIT.json',dict(utc=now(),prior_sealed_files_unchanged=len(old_manifest['files']),
        original_input_hashes_unchanged=len(input_checks),current_input_hashes_unchanged=len(p['input_sha256']),
        own_recorded_child_PIDs=pids,ps_command=['ps','-p','<recorded own PIDs>','-o','pid=,comm='],
        present_children=[],root_free_bytes=shutil.disk_usage('/').free,
        hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
        task_output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),
        CPU_affinity=[0,1],numeric_threads=1,serial=True,GPU=False,nested_agents=False))
    js(unit/'VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent, not independent human preference study',
        inspected=['media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png',
                   'media/orbit_all_frames.png','media/zoom_all_frames.png',
                   'browser_complete/02_selection_preview.png','browser_complete/07_reload_export.png',
                   'renders/static_baseline/frame_003_region_rgb.png','renders/static_edited/frame_003_image.png'],
        positive='Front bucket and neighboring tip/support faces have a separate persistent color/ID; roof and body stay unchanged under the angle edit. Complete objects remain visible in all recorded views.',
        negatives=['Manual box includes nearby lifting support; no exact semantic bucket mask.',
                   'Proxy holes and missing thin rods persist, especially side/rear views.',
                   'Ground hatching is wavy/crowded; cabin and arms retain broken/short lines.',
                   'World-coordinate numeric boxes require familiarity; no click/brush picker.',
                   'Offline short orbit and zoom do not establish all-path temporal or occlusion correctness.'],
        quality='partial',no_candidate_sweep=True))
    receipts=[]
    for file in sorted((unit/'logs').glob('*.receipt.json')):
        r=json.loads(file.read_text());receipts.append(dict(path=str(file.relative_to(unit)),returncode=r['returncode'],seconds=r['seconds']))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    start=datetime.datetime.fromisoformat('2026-10-21T18:18:57.154692+00:00')
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()/60
    progress=dict(scene='lego',genuinely_ran_old_model=True,available_models=['chair','lego'],
        original_gaussians=v['original_gaussians'],proxy_vertices=v['vertices'],proxy_faces=v['faces'],
        editable_regions=4,selected_faces=v['selected_faces'],manual_selection_source='authored AABB on existing upper-region face centroids',
        geometry_unchanged=True,retained_donor_segments=v['source_segments_retained'],
        target_paths_before=207,target_paths_after=207,non_target_paths_and_layers_exact=True,
        complete_object_views=8,far_edit_delta_all_views=0.,
        browser_preview_create_edit_undo_orbit_zoom_export=True,cold_reload_exact=True,
        exported_zip_cold_reload_exact=True,relocated_package_cold_reload_exact=True,
        orbit_frames=12,zoom_frames=6,all_video_frames_decoded_exact=True,
        visual_quality='partial',
        reasoning='旧Lego高度区把铲斗和车顶绑定；现在能预览并保存实际面ID的人工区域，独立编辑前部，导出并冷加载。完整对象和非目标保持能力已实际验证。',
        remaining='coarse proxy, short/crowded hatching, approximate manual selection, numeric box UI, no full temporal/semantic validation')
    next_step='在Chair/Lego均可运行且Lego人工区域编辑已验证的基础上，短时检查Drums原检查点/相机，用同一CPU提取和多区域入口做第三真实模型的完整对象、局部编辑与冷加载。先完成一组真实输出；细杆/鼓沿缺失如实列为partial，不因精确语义或完美代理而停留在toy门槛。若短时库存显示Drums无可靠可用输入，则回到现有Lego底板/车体排线可读性做一个冻结候选。'
    status=dict(stage='UNIT004_HANDOFF',execution_state='completed',completed_utc=now(),elapsed_minutes=elapsed,
        scientific_verdict='H1_H2_NOT_TESTED; historical P1 NO_GO and P2 ZERO_HEADROOM unchanged',
        engineering_validation='PASS for manual face-region authoring, local style edit, actual browser, export and cold/relocated reload',
        genuinely_ran_old_model=True,demo_progress=progress,source_commit=commit,
        artifacts=['portable_demo.tar.gz','portable_demo/run.sh','REPRODUCE_ZH.md',
            'assets/baseline/asset.json','assets/baseline/selection_4.npz','assets/edited/asset.json',
            'media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv',
            'media/editor_02_selection_preview.png','media/editor_07_reload_export.png',
            'metrics/VALIDATION.json','metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json',
            'browser_complete/BROWSER_VALIDATION.json','metrics/FINAL_AUDIT.json'],
        tests_and_command_receipts=receipts,blockers=[],
        limitations=json.loads((unit/'VISUAL_REVIEW.json').read_text())['negatives'],
        failure_records=['EXECUTION_AMENDMENT.json','logs/freeze.receipt.json','logs/tdd_red.receipt.json',
                         'logs/tdd_label_red.receipt.json','logs/browser.receipt.json'],
        next_action='continue',recommended_next_step=next_step,
        supervisor_verification='reported_not_independently_verified',
        seal_scope='validated finite engineering artifacts and explicit failure receipts; not full scientific certification',
        resources=dict(cpu_affinity=[0,1],numeric_threads=1,serial=True,gpu=False,nested_models=False,
                       new_dependencies=False,servers_stopped=True,extra_recovery_extension=False))
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='完整对象、局部编辑、冷加载与基本可用区域作者工具已在两个旧模型上打通；可先拓展第三模型而不追求当前代理完美。',
        ranked_alternatives=['bounded Drums real-model transfer','one Lego hatch readability candidate','click/brush selection UI'],
        estimated_next_minutes=35,deadline_jst='2026-10-22T10:00:00+09:00',
        no_new_science_after_jst='2026-10-22T09:20:00+09:00',science_wrap_jst='2026-10-22T09:45:00+09:00'))
    rows='\n'.join(f"| {r['view']} | {r['target_edit_L1']:.2f} | {r['far_edit_L1']:.1f} | {r['target_ink_before']:.1f} → {r['target_ink_after']:.1f} | {r['proxy_source_alpha_iou']:.5f} |" for r in v['views'])
    report=f'''# Unit004 — Saved manual regions on the real Lego model

本轮工程执行 **completed**；整体 demo 外观仍 **partial**，H1/H2未测试。用时 {elapsed:.1f} 分钟。源码提交 `{commit}`。完整读取 BRIEF、原大纲、最新可用 P1(unit010)/P2 报告与 NEXT 及相关源；unit011报告路径不存在的只读查询失败保留在阅读记录。实际审阅unit003全部完整对象图，选择解决“铲斗/车顶同高度区被绑定”的操作性问题，未扩展toy验证或扫描几何参数。

## Frozen inputs and one intervention

原始 Lego PLY `{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，310,475高斯。本轮重新加载该检查点并串行CPU渲染8视角。继承unit003的16,543顶点/29,999面TSDF代理，顶点和面索引逐元素不变；这是同模型估计表面，不是GT/独立测量/RaDe重训练。本轮不重复完整PLY→TSDF构建，unit003的完整构建证据保持原状。

`PROTOCOL.json`在新候选输出前冻结。一条人工world box：xyz min=(-0.70,-1.20,0.45)，max=(0.70,-0.35,1.10)，只从原region3按面中心选择，3,001/5,040面保存为region4。它覆盖前铲斗及相邻支撑，不是准确语义铲斗分割。无GT标签或人工几何补洞，无候选扫选。所有历史视角已曝光；新增虚拟静态41/131/221/311°、orbit12和zoom6在输出前冻结，不称盲测。

区域作者保留region1/2文件，保留region3未选中的1,237段points/bary/face/stroke_id；选择边界会截短原路径，不能称每条旧路径完整不变。新region4继承xz切平面及原风格，生成207条路径。随后仅角度-25°→35°，仍207条但坐标属于新版本；其余三区域2,194个路径ID与文件不变。风格方向平面显式保存，避免新region ID偷偷改变轴向。

## Actual evidence

| View | Target edit L1 | Far delta | Target ink before → after | Proxy/source alpha IoU |
|---|---:|---:|---:|---:|
{rows}

8视角的非目标三个图层、轮廓、深度精确相同；固定2px边界带外变化全0，目标变化均非零。作者分区操作的远区变化也全0，目标内有小幅路径截断/重排，未伪称分区完全无视觉变化。相对代理重心附着最大2.22e-16，只证明实现贴在自身代理；同模型深度残差/IoU不是独立几何精度。分母与覆盖/墨量在metrics/VALIDATION.json中保留。

实际查看完整8组RGB/代理/旧新区域/排线、8组局部编辑及全部12旋转/6缩放接触图。车顶和车身在前区域编辑时保持，侧后方孔洞、细杆缺失、底板拥挤波浪线和车体短线仍明显；新区域包含相邻举升支撑。18轨迹帧全部不同、整个代理在框内，FFV1全部解码与源PNG逐帧精确；不是全路径时序认证。

真实Firefox软件渲染完成：包围盒预览→保存第4区→独立角度编辑→间距/长度/线宽编辑→撤销精确复原→orbit/zoom→刷新→下载。浏览器作者结果与CLI四个区域路径文件精确一致；缺少新预览的保存请求返回422。下载ZIP保存选择文件、四区路径、当前相机与选中区域；关闭服务器后新CLI冷加载PNG/全部数组精确。tar搬移解压后的 `./run.sh preview` 也精确，保存资产不需原PLY。

15项必要行为测试通过；第4区域真实网格测试先rc1失败后通过。补充3项实际资产测试覆盖空/非法/全吞并选择和选择文件损坏拒绝。没有重复跑历史巨量审计。源码快照、哈希、命令和返回码见SOURCE_LOCK、REPRODUCE_ZH与logs。

## Failure records and limits

freeze首次错误使用metadata键path（rc1），在冻结前改为original_ply。新模块缺失及旧mesh只接受3个region的TDD rc1保留。主批处理外层143、原因/发送方UNKNOWN；prepare至validate全部已启动子阶段rc0，media尚未开始。只补运行未开始的media（rc0），没有改参数或重渲染已完成阶段。首浏览器测试在预览成功后，WebDriver读取页面lexical变量pending触发HTTP500/rc1；改测试为通过实际UI及HTTP检验缺少新预览的拒绝，新browser_complete rc0。原日志、截图和清理收据保留，未把失败尝试当作完整通过。

`EXECUTION_AMENDMENT.json`保留所有失败/恢复；没有额外延长本轮时限。{len(old_manifest['files'])}个前单元封存文件及原PLY/相机/RGB输入哈希复核一致。两核、数值单线程、串行，无GPU、安装、凭据、嵌套模型、push或merge；自身服务器/浏览器子进程已关闭。

数值包围盒仍需理解模型坐标，没有点击刷选；撤销历史只在当前服务器会话，导出保留最终资产；32个region ID是工程上限，仅Lego第4区实际验证。纸面可读性、精确语义、独立遮挡/时序与更复杂多次拆分未完成。封存是有限工程证据，不能升级成科学成功。NEXT=continue，优先有界Drums真实模型迁移，必要时回到Lego一次排线可读性改进。完整交互入口见portable_demo/run.sh与根DEMO_README_ZH.md。
'''
    (unit/'REPORT_ZH.md').write_text(report)
    commands=[]
    for file in sorted((unit/'logs').glob('*.receipt.json')):
        r=json.loads(file.read_text());commands.append(f"## {file.stem}\n\nreturncode={r['returncode']}; wall={r['seconds']:.3f}s\n\n```bash\n{shlex.join(r['command'])}\n```\n")
    (unit/'REPRODUCE_ZH.md').write_text('# Unit004 — Actual commands and return codes\n\n以下为实际运行命令，按各receipt时间查看执行顺序。输出目录不可重复覆盖；重放时改用新的任务内目录。冻结科学参数见PROTOCOL。外层143另见EXECUTION_AMENDMENT；恢复仅继续未启动阶段。\n\n'+ '\n'.join(commands))
    readme=work/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md'
    shutil.copy2(readme,OUTPUT_ROOT/'DEMO_README_ZH.md');shutil.copy2(readme,unit/'DEMO_README_ZH_SNAPSHOT.md')
    delivery=dict(updated_utc=now(),latest_unit=str(unit),execution_state='completed',visual_quality='partial',
        genuinely_ran_old_models=['chair','lego'],latest_demo=str(unit/'portable_demo/run.sh'),
        portable_package=str(unit/'portable_demo.tar.gz'),portable_sha256=sha(unit/'portable_demo.tar.gz'),
        scene='lego',demo_progress=progress,scientific_verdict=status['scientific_verdict'],next_action='continue',
        report=str(unit/'REPORT_ZH.md'),other_demo=str(OUTPUT_ROOT/'units/unit_002/portable_demo/run.sh'))
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',delivery);js(unit/'DELIVERY_STATUS_SNAPSHOT.json',delivery)
    source=unit/'source_snapshot';source.mkdir()
    source_rows={}
    for f in sorted(Path(__file__).parent.iterdir()):
        if f.suffix in ('.py','.cpp','.html'):
            shutil.copy2(f,source/f.name);source_rows[f.name]=sha(f)
    js(unit/'SOURCE_LOCK.json',dict(commit=commit,worktree=str(work),source_sha256=source_rows,protocol_sha256=sha(unit/'PROTOCOL.json')))
    diff=subprocess.check_output(['git','diff','2a3bdbbdb1b9ca6e134d5775cad343bf6b940f46','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04'])
    (unit/'SOURCE_DIFF.patch').write_bytes(diff)
    # Exclude browser profiles, mutable scratch/test work, and console responses.
    files=[]
    for f in sorted(unit.rglob('*')):
        if not f.is_file():continue
        rel=f.relative_to(unit);parts=rel.parts
        if parts[0] in ('test_work','portable_relocated'):continue
        if parts[0] in ('browser','browser_complete'):
            if len(parts)>2 and parts[1]!='session':continue
        if f.name in ('SHA256_MANIFEST.json','ENGINEERING_SEAL.json'):continue
        if len(parts)==1 and f.suffix not in ('.json','.md','.patch','.gz'):continue
        files.append(dict(path=str(rel),sha256=sha(f),bytes=f.stat().st_size))
    js(unit/'SHA256_MANIFEST.json',dict(utc=now(),scope=status['seal_scope'],files=files))
    js(unit/'ENGINEERING_SEAL.json',dict(utc=now(),manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),
        file_count=len(files),source_commit=commit,execution_state='completed',visual_quality='partial',
        scientific_claim='NONE',scope=status['seal_scope']))
    print(json.dumps(dict(execution_state='completed',visual_quality='partial',elapsed_minutes=elapsed,
                         files=len(files),next_action='continue',source_commit=commit)),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unit',type=Path,required=True);finish(parser.parse_args().unit)
