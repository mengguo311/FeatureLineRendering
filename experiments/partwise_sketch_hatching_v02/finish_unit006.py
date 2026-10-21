"""Summarize only actual current-unit evidence; no scientific rerender or gate tuning."""
from common import *
import shutil,subprocess,platform
from datetime import datetime,timezone
import PIL,scipy
U=OUT.parent/'unit_006';D=WORK/'docs/partwise_sketch_hatching_v02'

def main():
    v=json.loads((U/'INDEPENDENT_VALIDATION.json').read_text());g=json.loads((U/'GENERATION.json').read_text())
    visual=json.loads((U/'VISUAL_REVIEW.json').read_text());hist=json.loads((U/'HISTORICAL_SEAL_AUDIT.json').read_text())
    cold=json.loads((U/'COLD_REPLAY.json').read_text());lock=json.loads((U/'SOURCE_LOCK.json').read_text())
    recovery=json.loads((U/'VALIDATION_RECOVERY.json').read_text())
    go=recovery['verdict']=='RECOVERED_WITH_LOCAL_UINT8_CAMERA_ADAPTER' and recovery['all_other_original_checks_passed'] and visual['go'] and hist['valid'] and cold['rgb_exact']
    times=np.array([f['render_and_save_seconds'] for f in g['frames']]);now=datetime.now(timezone.utc).isoformat()
    blockers=[
      'No verified trained RaDe-GS lamp or reconstructed main proxy. CPU-only disallows training; dataset readiness does not establish reconstruction.',
      'Inherited unit004 density NO_GO: orbit frame19 az285 stem ink ratio0.7521462443170939 >0.75; unit004/005 preview remains DIAGNOSTIC_PREVIEW_ONLY.',
      'Inherited17 hidden-profile observations, rim-depth outliers and limited nine-ID temporal evidence remain unresolved; this RGB-input unit does not validate NPR motion.',
      'Current part-edit CLI only supports width and saved-path replay; direction/spacing/length/crossing generators still need explicit lineage and isolated edits.',
      'Authored axisymmetric texture-poor geometry, GT labels and synthetic local-Lambert materials are diagnostic. Real/click-assisted labels, real reconstruction and H1/H2 remain untested.',
      'Unmodified official camera reader fails with signed RGB under current Pillow (original rc1/INVALID retained). Compatibility GO requires the disclosed local np.uint8 adapter; future full scene loading/training needs that fix in an authorized writable source copy.'
    ]
    progress='已把完整三部件GT台灯接到实际生成的36训练/12开发/72测试RGB＋相机输入，隔离GT oracle，并经全部图像解码、独立投影/划分/加载故障测试、本地适配相机读取和全视图目视检查。后续重建不再缺灯具输入与坐标接口；训练、重建代理和完整P1仍未完成。'
    if not go:progress='已实际生成并保留120视图输入，但冻结验证存在失败，不能晋级输入就绪。具体失败和原始输出保留。'
    verdict='SYNTHETIC_INPUT_READY_WITH_LOCAL_ADAPTER_RECONSTRUCTION_BLOCKED' if go else 'INPUT_BRIDGE_NO_GO'
    status=dict(stage='completed_single_reconstruction_input_bridge',execution_state='complete',scientific_verdict=verdict,
      tests=dict(initial_validation=v['verdict'],original_validation_returncode=1,recovery_validation=recovery['verdict'],validated_frames=len(v['frame_metrics']),checks_passed=sum(x['passed'] for x in v['checks'].values()),checks_total=len(v['checks']),fault_controls=len(v.get('evidence',{}).get('isolated_loader_and_fault_controls',{}).get('faults',{})),cold_RGB_replay=cold['rgb_exact'],historical_manifest_files=hist['files_checked'],historical_manifest_valid=hist['valid'],visual_review=visual['go']),
      artifacts=['PROTOCOL.json','PROTOCOL_INITIAL.json','PRE_EVALUATION_REFINEMENT.json','SOURCE_LOCK.json','RECONSTRUCTION_INVENTORY.json','INPUT_PROVENANCE.json','dataset/DATASET.json','dataset/train','dataset/evaluation/dev','dataset/evaluation/test','oracle_only/ORACLE.json','GENERATION.json','INDEPENDENT_VALIDATION.json','ENGINEERING_RECOVERY.json','RECOVERY_LOCK.json','VALIDATION_RECOVERY.json','COLD_REPLAY.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json','figures/train_all_views.png','figures/dev_all_views.png','figures/test_all_views.png','inherited_failures/FROZEN_GATE_FAILURES.json','REPORT_ZH.md'],
      blockers=blockers,outline_milestone='P1 / W1 RGB-camera input bridge; complete-object synthetic diagnostic',p1_progress=progress,
      claim_status=dict(coding='COMPLETE',software='GO_SYNTHETIC_INPUT_WITH_LOCAL_ADAPTER' if go else 'NO_GO',visual='GO_INPUT_COVERAGE' if visual['go'] else 'NO_GO',unmodified_official_reader='NO_GO_PILLOW_SIGNED_RGB',reconstructed_input='BLOCKED',full_P1='PARTIAL_NOT_COMPLETE',H1_H2='NOT_TESTED',inherited_density='NO_GO_RETAINED'),
      session_started_jst='2026-10-21T18:05:07.542148+09:00',completed_utc=now,initial_protocol_commit='e6a54645',protocol_implementation_commit=lock['git_commit'])
    write_json(U/'STATUS.json',status)
    next_step='One bounded whole-lamp rendered temporal audit on the named unit003 baseline asset: freeze the saved paths, 24-frame512 orbit and a small zoom sequence, then use independent analytic visibility with per-stroke isolated actual RGB/ink renders for a stratified sample of shade/stem/base including short/occluded paths. Measure common-visible alignment and abnormal missing/reappearance with fixed eligibility, ambiguity and visible-length coverage; inject no-edit/drift/dropout controls. Preserve the inherited17 hidden-profile cases and all original density failures. Do not tune TEST, promote unit004, train or start H2. Prioritize evidence on all three parts over anchor-hash equality.'
    if not go:next_step='Diagnose only the retained unit006 input/visual failure under original frozen controls; preserve outputs and revise only demonstrable engineering defects, with explicit protocol/source amendment before replay.'
    nxt=dict(action='continue',recommended_next_step=next_step,
      hypothesis='With RGB/camera handoff now explicit but training blocked, the largest independent P1 validation gap is whether actual rendered persistent strokes behave correctly over camera motion, particularly the short stem and occluded regions.',
      fixed_controls=['Keep unit006 RGB/angle/material/light recipe and train/dev/test/oracle isolation sealed; no test RGB or GT proxy used as reconstruction','Use one explicitly named existing asset and fixed paths; original unit003 baseline to avoid promoting unit004 density NO_GO','Freeze cameras, sample IDs, visible-length coverage, ambiguity rules and thresholds before opening temporal results','CPU<=2, no GPU, no historical writes, no parameter sweep'],
      go_no_go=dict(go='Useful bounded temporal evidence on actual full-object renders with nonzero eligible coverage in each part and sensitive drift/dropout controls; report failures without upgrading full P1',no_go='Unidentifiable stroke output, self-referential visibility, metric-insensitive controls or unreported exclusions; preserve raw data and do not claim temporal success'),
      blockers=blockers,evidence_paths=['STATUS.json','INDEPENDENT_VALIDATION.json','VALIDATION_RECOVERY.json','dataset/DATASET.json','VISUAL_REVIEW.json','RECONSTRUCTION_INVENTORY.json','inherited_failures/FROZEN_GATE_FAILURES.json',str(U.parent/'unit_005/STATUS.json')],
      p1_distance_reduced=progress+' 下一步在CPU限制内补全实际排线时序可见性的证据，直接检验完整对象P1的旋转/缩放展示，而不重复平面数值证明。',estimated_next_minutes=30,estimated_range_minutes=[25,35],updated_utc=now)
    write_json(U/'NEXT.json',nxt)
    write_json(U/'TIMING_SUMMARY.json',dict(frames=len(times),render_save_total_seconds=float(times.sum()),render_save_median_seconds=float(np.median(times)),render_save_p95_seconds=float(np.percentile(times,95)),scope='Includes RGB render, center oracle raster and PNG/NPZ save per frame; CPU offline, not interactive FPS'))
    usage=dict(root_free_bytes=shutil.disk_usage(WORK).free,hdd_free_bytes=shutil.disk_usage(U).free,unit_bytes=sum(x.stat().st_size for x in U.rglob('*') if x.is_file()),task_unit_bytes=sum(x.stat().st_size for x in U.parent.rglob('*') if x.is_file()),cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False)
    assert usage['root_free_bytes']>=2**30 and usage['hdd_free_bytes']>=10*2**30 and usage['task_unit_bytes']<20*2**30
    write_json(U/'RESOURCES_FINAL.json',usage)
    write_json(U/'DEPENDENCIES.json',dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,Pillow=PIL.__version__,interpreter=PYTHON,dependencies='Existing read-only shared environment; no install/upgrade/download',GPU=False))
    report=f'''本单元完成唯一推荐步骤：完整台灯重建输入桥接。结论为 **{verdict}**，不是RaDe-GS重建或完整P1成功。

先完整读取BRIEF、原大纲851行，以及round001/002/016的报告、协议、NEXT和unit005交接。限域盘点9,045目录未发现可核验的灯具训练资产；六个历史DTU修改版RaDe-GS的scientificdone=false仍保留，29顶点/22面的scan63代理未准入。没有把vanilla PLY或GT台灯称为训练重建。

初始协议提交e6a54645；任何RGB生成前，源码审查发现官方ndc2Pix主点约定，保留PROTOCOL_INITIAL并将256修正为255.5，详见PRE_EVALUATION_REFINEMENT。最终协议/实现提交{lock['git_commit']}，SOURCE_LOCK在渲染前绑定源码、输入、官方相机/FOV/像素函数及快照。没有看到新图后调整角度、材料、光照或门槛。

实际生成36训练＋12开发＋72测试，共120张512×512 RGB；仰角10/25/40度，训练30m度、开发7.5+90m度、测试3.75+15m度，精确互斥。RGB为固定世界光照的三材质局部Lambert表面图，不含NPR排线。每个视图均保存原始PNG；网格和每视图光轴深度、世界法线、部件及AA覆盖只放在oracle_only。GT来自已曝光人工作成网格，不是新盲测物体。轴对称、无纹理、无投影阴影等简化会影响未来重建，输入就绪不保证训练质量。

训练source目录dataset/train只有36张RGB和相机；官方transforms_test为空。开发与测试在evaluation独立目录，通用loader默认train，评估必须明确purpose=evaluate；训练输入不含测试RGB、GT标签、深度、网格或初始化点云。读取器的跨split正确性由独立全局验证负责，普通单split加载只检查该输入的路径、字段、哈希与相机。

初始独立验证保留{v['verdict']}及rc1：{len(v['frame_metrics'])}张PNG完整解码，{sum(x['passed'] for x in v['checks'].values())}/{len(v['checks'])}项记录通过；9项故障控制检查held-out访问、路径逃逸、oracle字段、非PNG、非有限焦距、矛盾矩阵、重合角度和相机翻转。其中7项作用于自有loader，2项作用于全局验证；重合角度首先被冻结角度集合检查拒绝，未单独测试集合交集分支。它不导入生成器/渲染器，用独立球面三角公式核验相机与投影。唯一失败为原始官方相机函数把RGB转np.byte，当前Pillow拒绝signed RGB。随后先提交适配器616f2780和恢复协议3485b408，再评测仅np.byte→np.uint8的本地AST适配，结果{recovery['verdict']}。全部120图与原PNG及原signed数组的底层字节相同；相机/光栅映射最大投影误差{recovery['maximum_absolute_errors']['projection_px']:.3g}px，所有RGB/oracle/相机哈希不变。外部官方源码、原validator、原INVALID与rc1不改写；不能称原版官方读取成功。ndc2Pix仅做CPU公式核验，没有CUDA运行。三部件每视图最小可见像素：{v['minimum_visible_pixels_by_part']}；全体顶点最小画面余量{v['minimum_projected_margin_px']:.6f}px。部件掩码由生产器输出，因此它们不是独立重建真值；相机/网格界限独立验证不代表光度正确性。

逐一检查三套全视图接触图和各split原尺寸首/中/尾，结论为{visual['verdict']}。具体观察与限制见VISUAL_REVIEW/DELEGATED_VISUAL_REVIEW。实际图像的完整性、部件可辨和可用隔离输入是主门槛；单帧新进程重放像素/PNG相同仅作次要确定性检查。

每帧渲染及保存中位{np.median(times):.6f}s，P95 {np.percentile(times,95):.6f}s，120帧合计{times.sum():.6f}s；包含RGB、oracle中心采样及保存。非24FPS或交互延迟承诺。CPU affinity[0,1]，数值线程1，无GPU、下载、训练、push或merge；旧结果和orchestration只读。unit005完整{hist['files_checked']}项seal文件校验为{hist['valid']}，当前task units占用{usage['task_unit_bytes']/2**20:.2f}MiB，磁盘底线通过。

报告编辑辅助命令曾因系统无python别名返回127，未执行脚本体或改变科学输出，单独保留AUXILIARY_COMMAND_FAILURE.json。原始退出码保留于EXECUTION_*.json、原始日志在runtime且不纳入科学manifest。继承unit004 frame19支杆墨量比0.7521462443170939超过0.75的NO_GO及原图已复制保留；本单元没有修复或晋级该预览。旧rc1/143/UNKNOWN、round004/012/013 NO_GO、rim离群、17个hidden-profile观察、九ID时序覆盖缺口均未改写。

{progress}

下一步仅推荐25–35分钟的三部件实际排线时序审计：固定命名unit003资产及视角，独立可见性、明确ID、实际输出和覆盖统计检查旋转/缩放，保留漂移/删线敏感性控制与失败；CPU训练阻塞下仍能缩短完整P1的验证距离。不启动H2、不做参数扫选、不靠坐标哈希宣称稳定。STATUS/NEXT/SEAL和SHA256_MANIFEST位于本单元根目录。
'''
    (U/'REPORT_ZH.md').write_text(report);(D/'REPORT_unit006_ZH.md').write_text(report)
    receipts=[]
    for f in sorted(U.glob('EXECUTION_*.json')):
      if f.name.endswith('_START.json'):continue
      r=json.loads(f.read_text());receipts.append(dict(name=f.stem,**r))
    text='本记录是已执行命令/原始退出码；封存目录禁止覆盖重跑。新生产必须迁移到新授权unit并保留本结果。\n\n'
    for r in receipts:
      import shlex
      text+=f"{r['name']}: rc={r['returncode']}, wall={r['wall_seconds']:.6f}s\n\n```bash\n{shlex.join(r['command'])}\n```\n\n"
    text+='所有命令均通过receipt_unit006.py约束CPU affinity[0,1]、数值线程1、CUDA不可见、590秒超时，TMPDIR使用已指定scratch。stdout/stderr只在runtime，科学seal仅收据绑定其SHA。\n'
    (U/'REPRODUCE.md').write_text(text)
    print(json.dumps(native(dict(verdict=verdict,frames=len(times),resources=usage)),ensure_ascii=False))
if __name__=='__main__':main()
