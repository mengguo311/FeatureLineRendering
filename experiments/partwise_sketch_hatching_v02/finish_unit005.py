"""Report and seal the executed explicit-asset editing slice, preserving failures."""
from common import *
import argparse
import platform
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
import PIL
import scipy
from run_unit005 import UNIT, resources, check_lock


def read(relative):
    return json.loads((UNIT/relative).read_text())


def finish():
    check_lock()
    metrics=read('METRICS.json'); validation=read('INDEPENDENT_VALIDATION.json')
    video=read('VIDEO_VALIDATION.json'); visual=read('VISUAL_REVIEW.json')
    delegated=read('DELEGATED_VISUAL_REVIEW.json')
    history=read('HISTORICAL_SEAL_AUDIT.json')
    commands={}
    for name in ('prepare','freeze','tests','baseline','edited','cold_replay','named_unit003_baseline','validation','media','history'):
        commands[name]=read(f'EXECUTION_{name}.json')
    assert all(r['returncode']==0 for r in commands.values())
    assert validation['verdict']=='VALID'
    rows=metrics['stills']
    assert len(rows)==4 and all(r['quantitative_go'] for r in rows)
    assert video['decoded_frames']==24 and video['all_rgb_exact'] and history['valid']
    assert visual['width_edit_visual_verdict'].startswith('GO')
    named=read('outputs/named_unit003_baseline/asset.json')
    named_receipt=read('outputs/named_unit003_baseline/EDIT.json')
    old3=json.loads((UNIT.parent/'unit_003/STATUS.json').read_text())
    named_check=dict(name=named['name'],path_count=named_receipt['saved_path_count'],
        source_mesh_sha_exact=sha(UNIT/'outputs/named_unit003_baseline/mesh.npz')==sha(UNIT.parent/'unit_003/inputs/lamp_mesh.npz'),
        source_paths_sha_exact=sha(UNIT/'outputs/named_unit003_baseline/strokes.npz')==sha(UNIT.parent/'unit_003/inputs/selected.npz'),
        retained_scientific_verdict=named['verdict_metadata']['scientific_verdict'],
        rendered_az30_png_sha_exact=sha(UNIT/'outputs/named_unit003_baseline/renders/030.png')==sha(UNIT.parent/'unit_003/stills/candidate_030.png'))
    named_check['passed']=bool(named_check['path_count']==458 and named_check['source_mesh_sha_exact'] and named_check['source_paths_sha_exact']
        and named_check['rendered_az30_png_sha_exact'] and named_check['retained_scientific_verdict']==old3['scientific_verdict'])
    write_json(UNIT/'NAMED_ASSET_CHECK.json',named_check)
    assert named_check['passed']
    timings={}
    for name in ('baseline','edited','cold_replay','named_unit003_baseline'):
        record=read(f'outputs/{name}/EDIT.json')
        timings[name]=dict(external_command_wall_seconds=commands[name]['wall_seconds'],
            module_entry_to_first_preview_seconds=record['command_to_first_preview_seconds'],
            module_entry_to_all_previews_seconds=record['command_to_all_previews_seconds'],
            per_view_seconds=record['per_view_seconds'],regenerated_parts=record['regenerated_parts'])
    write_json(UNIT/'TIMING_SUMMARY.json',dict(timings=timings,
        scope='External command wall includes interpreter startup, input loading/checking/copying, config edit/save, all actual renders and receipt output. First-preview timer starts at module entry. Width edit requires no path regeneration. No repeated benchmark or FPS claim.'))
    write_json(UNIT/'COLD_REPLAY.json',dict(command=commands['cold_replay']['command'],
        returncode=commands['cold_replay']['returncode'],source='Frozen source_snapshot in fresh interpreter',
        saved_bundle='outputs/edited/asset.json',views={str(r['azimuth']):r['cold_replay'] for r in rows},
        scope='Saved-config/mesh/path replay only; width does not regenerate geometry'))
    write_json(UNIT/'DEPENDENCIES.json',dict(python=platform.python_version(),numpy=np.__version__,
        scipy=scipy.__version__,Pillow=PIL.__version__,interpreter=PYTHON,ffmpeg=FFMPEG,
        ffmpeg_sha256=sha(FFMPEG),environment='Existing shared read-only Python environment; no installation/upgrade',gpu=False))
    resource=resources();write_json(UNIT/'RESOURCES_FINAL.json',resource)
    progress='已把完整三部件GT台灯从固定脚本输出推进为显式选资产、选部件、改屏幕线宽、保存并冷重放的可操作资产。unit003基线和unit004诊断预览分别命名，418路径未退回旧608路径；四视角真实局部响应/独立掩码隔离/覆盖及24帧编辑展示经过验证。unit004密度NO_GO、真实重建和时序阻塞仍保留；完整P1未完成。'
    blockers=[
        'Unit004 stem density NO_GO retained: frame19 az285 ratio0.7521462443170939 exceeds frozen0.75. Preview remains DIAGNOSTIC_PREVIEW_ONLY; shade width success does not promote it.',
        'No verified reconstructed lamp. Authored GT geometry/parts and manual directions remain diagnostic; CPU-only prohibits new RaDe-GS training.',
        'Inherited17 hidden-profile observations, rim-depth outliers and limited nine-ID temporal evidence remain unresolved; this discrete edit is not temporal visibility validation.',
        'Visible shade stacking/raster irregularities and base front-edge crossings/uneven patches remain. No polished NPR or perceptual preference claim.',
        'Bounded CLI supports width edits and saved-path replay only. Direction,spacing,length,crossing edits require explicit modern generators/config lineage; inherited generator counts are stale.',
        'This CLI output authorization is pinned to unit005; later authorized units must migrate the explicit output boundary without modifying historical results.']
    status=dict(stage='completed_explicit_asset_width_edit_and_saved_config_replay',execution_state='complete',
        scientific_verdict='EXPLICIT_ASSET_WIDTH_EDIT_GO_INHERITED_DENSITY_NO_GO',
        tests=dict(cli_contracts=dict(tests=4,passed=4,returncode=commands['tests']['returncode']),
            artifact_validation=validation['verdict'],artifact_checks=len(validation['checks']),
            actual_image_pairs=4,all_four_image_pairs_go=True,metric_controls=True,cold_saved_config_replay=True,
            edit_video_decoded_frames=24,edit_video_all_rgb_exact=True,named_unit003_baseline=named_check['passed'],
            historical_manifest_files=sum(r['files'] for r in history['checks']),historical_manifests_valid=True),
        artifacts=['PROTOCOL.json','SOURCE_LOCK.json','inputs/unit003_baseline.asset.json','inputs/unit004_diagnostic_preview.asset.json',
            'outputs/edited/asset.json','outputs/edited/EDIT.json','METRICS.json','INDEPENDENT_VALIDATION.json',
            'COLD_REPLAY.json','TIMING_SUMMARY.json','NAMED_ASSET_CHECK.json','VISUAL_REVIEW.json','DELEGATED_VISUAL_REVIEW.json',
            'figures/full_lamp_comparison.png','figures/shade_comparison.png','figures/edit_all_frames.png',
            'videos/edit.mkv','previous_snapshot/unit004_diagnostic_preview/FROZEN_GATE_FAILURES.json','REPORT_ZH.md'],
        blockers=blockers,outline_milestone='P1 complete-object GT engineering slice: explicit part-width editing,asset persistence and replay',
        p1_progress=progress,claim_status=dict(coding='COMPLETE_FOR_FROZEN_SCOPE',software='GO_WIDTH_EDIT_SAVE_REPLAY',
            visual='GO_BOUNDED_COMPLETE_LAMP_EDIT_PREVIEW',inherited_density_contract='NO_GO',candidate_promotion='DIAGNOSTIC_PREVIEW_ONLY',
            full_P1='PARTIAL_NOT_COMPLETE',reconstructed_input='BLOCKED',independent_temporal='NOT_ESTABLISHED',H1_H2='NOT_TESTED'),
        historical_failures='Original rc1/143/UNKNOWN,round004/012/013 NO_GO,rim outliers and unit001/002 visual NO_GO retained. Expected FFmpeg header-only rc1 explicitly recorded; decode rc0.',
        session_started_jst='2026-10-21T17:53:23.094613+09:00',completed_utc=datetime.now(timezone.utc).isoformat(),
        protocol_commit='840e74c3',protocol_source_commit=read('SOURCE_LOCK.json')['git_commit'])
    write_json(UNIT/'STATUS.json',status)
    next_step=dict(action='continue',
        recommended_next_step='One reconstruction-input bridge unit: perform a bounded read-only recheck of known scientific roots for a genuinely trained RaDe-GS lamp and its training provenance (<=5min); if still absent, prepare a clearly labeled synthetic lamp RGB+camera dataset for later reconstruction with fixed disjoint train/dev/test angles, plus a loader/provenance manifest. GT mesh/parts/depth stay in a separate oracle-only directory, never as the claimed reconstructed main proxy. Freeze resolution/frame counts/lighting/materials/cameras before rendering, inspect all contact sheets and test split disjointness/camera projection. Do not train on CPU, substitute vanilla PLY, start H2, or optimize the current density failure.',
        hypothesis='With the current whole-lamp editing/save/replay slice usable, explicit reconstruction inputs and strict train/test/oracle separation remove the next concrete handoff gap toward RGB-derived P1 without pretending CPU-only can produce a trained reconstruction.',
        fixed_controls=['Preserve both named assets and unit004 density NO_GO; current width edit does not promote preview',
            'Inventory only authorized known scientific roots; trained provenance must be verified, no credentials/env/GPU access',
            'If synthetic preparation:36train/12dev/72test RGB at512,3 declared elevations,azimuths30m/7.5+90m/3.75+15m with exact disjointness assertions; no test-driven material/camera tuning',
            'Keep RGB/camera dataset separate from oracle mesh/parts/depth; never feed test RGB or GT proxy into a claimed reconstruction',
            'Freeze CPU practical renderer/lighting/materials/camera conventions; preserve all generated views and explicit data/source hashes'],
        go_no_go=dict(go='Actual complete dataset or provenance-verified existing trained lamp input, split/loader validation and all-view visual coverage documented. Call it input readiness only until real reconstructed geometry exists.',
            no_go='Missing or mislabeled provenance, overlapping angles, clipped/missing views or oracle contamination. Preserve failure and do not claim reconstruction or H1/H2 success.'),
        blockers=blockers,evidence_paths=['STATUS.json','METRICS.json','outputs/edited/asset.json','COLD_REPLAY.json','TIMING_SUMMARY.json','figures/full_lamp_comparison.png','videos/edit.mkv',
            str(WORK/'docs/partwise_sketch_hatching_v02/P1_ROADMAP_ZH.md')],
        p1_distance_reduced=progress+' 下一步把只依赖GT的应用切片连接到可训练的RGB/camera输入，缩短真实重建P1的资料与接口距离；训练本身仍明确阻塞。',
        estimated_next_minutes=30,estimated_range_minutes=[25,35],updated_utc=datetime.now(timezone.utc).isoformat())
    write_json(UNIT/'NEXT.json',next_step)
    summary=dict(min_target_inside_L1=min(r['edit']['inside_delta'] for r in rows),
        max_target_inside_L1=max(r['edit']['inside_delta'] for r in rows),
        max_far_other_fraction=max(r['edit']['far_other_parts_fraction'] for r in rows),
        max_far_background_fraction=max(r['edit']['far_background_fraction'] for r in rows),
        edit_external_wall_seconds=timings['edited']['external_command_wall_seconds'],
        edit_module_entry_first_preview_seconds=timings['edited']['module_entry_to_first_preview_seconds'])
    write_json(UNIT/'SUMMARY.json',summary)
    table='\n'.join(f"| {r['azimuth']}° | {r['edit']['inside_delta']:.6f} | {100*r['edit']['boundary_band_fraction']:.6f}% | {100*r['edit']['far_other_parts_fraction']:.6f}% | {100*r['edit']['far_background_fraction']:.6f}% |" for r in rows)
    report=f'''# Unit005：显式整灯资产编辑与保存重放

本轮完成唯一工作包：按 unit004 NEXT，建立显式资产 CLI，并固定验证灯罩屏幕线宽1.0→1.5px。结论为 **局部线宽编辑／保存重放软件 GO，完整灯具预览视觉有界 GO；继承密度契约仍 NO_GO，完整 P1 未完成**。协议提交840e74c3先于测试和渲染；实现与冻结源码提交{read('SOURCE_LOCK.json')['git_commit']}。未运行平面审计、H2或新训练。

已完整阅读BRIEF、851行原大纲、round001/002/016报告及原参数/NEXT，执行上一轮推荐。所有新重输出在 `{UNIT}`；历史和orchestration未写入。

## 实际接口与资产

CLI 为 `experiments/partwise_sketch_hatching_v02/asset_cli.py`，用法见 `docs/partwise_sketch_hatching_v02/ASSET_CLI_ZH.md`。`preview`/`edit` 必须指定资产清单和新输出目录，`replay` 必须指定保存后的包和新输出目录。选定shade/stem/base并改width，保存配置、原始网格与路径、清单、实际PNG和渲染层。错误输入在输出前拒绝；渲染异常会保留部分结果。

unit003基线458路径与unit004诊断预览418路径分别命名并保留原判定。unit003另实际渲染az30，与历史图完全一致。编辑实验的before是unit004预览，不是unit003基线。260灯罩、8支杆、150底座路径始终来自选定包，未退回608条旧路径。所有路径ID/part/face/bary/ink不变，仅灯罩width字段变化；这些是辅助软件证据，应用门槛来自整灯实际图像。

继承CONFIG的部分生成数量仍是旧参数，因此保存路径被明确声明为权威，禁止用旧配置重生成当前子集。保存包使用相对路径，保留原provenance和verdict_metadata；编辑成功不会覆盖原来的NO_GO。

## 实际图像与独立掩码

固定512×512、2倍AA、visible_centerline、0.006深度容差、0.8px轮廓、0.65px实体环，仰角20°、距离4.5。四视角均为已曝光诊断视角，不是盲测。连续解析旋转面独立射线求交给出掩码，与三角网格渲染分开；仍共享人工GT几何定义。

| 方位 | 目标内L1 | 外侧2px边界带比例 | 远其他部件 | 远背景 |
|---|---:|---:|---:|---:|
{table}

四视角目标内L1均>10，固定2px带外的其他部件／背景各≤2%；全部三部件排线支持非空、完整形体留在画面中。原始掩码/区域分别保存于references。no-edit得到零变化且非零门槛失败；固定16个远部件黑点注入得到100%远部件变化；3px漂移使L1增大。这些是指标敏感性控制，不是新时序证据。原支杆密度比0.7521462443170939>.75失败保留，未套用到灯罩线宽也未修改门槛。

实际检查四组完整前后图、灯罩局部、全部24编辑帧接触图与首中末。灯罩变粗加重可见，三种部件风格保持可辨，未见新增明显跨部件干扰。az300的灯罩原墨量较浅，变化较细微。已有灯罩叠线/栅格不均、底座前缘交叉与局部杂乱仍在；不宣称精致手绘质量。独立协作者也检查了实际图片，见DELEGATED_VISUAL_REVIEW。

## 冷重放、媒体与延迟

在新Python进程从冻结source_snapshot启动，直接加载保存的edited包重放四视角；四张PNG的字节与像素、六类保存渲染层均相同。它证明保存配置和路径可重放，不是重新生成几何的独立确定性实验。

编辑视频为24帧、12fps、512×512、FFV1无损，前12帧1.0px、后12帧1.5px，无插值。全部24帧解码RGB与源PNG一致，恰好两个实际状态。接触图及完整解码不证明动态无闪烁。本轮不重跑orbit/zoom；前轮结果只作为继承证据，旧时序限制不变。

编辑命令完整外层wall为{summary['edit_external_wall_seconds']:.3f}秒，包含解释器启动、读取/校验、保存、四次实际预览和收据。模块入口到第一张PNG为{summary['edit_module_entry_first_preview_seconds']:.3f}秒（此计时不含解释器启动）。width操作无需重生成路径。其余逐视角/命令时长见TIMING_SUMMARY；没有24FPS或实时交互声明。

4项CLI契约测试通过，独立输出检查{len(validation['checks'])}项有效，四图应用门槛全过；unit003和004合计{sum(r['files'] for r in history['checks'])}项历史清单文件校验通过。全部实际命令/返回码在EXECUTION文件。FFmpeg仅检查输入头时rc1是预期无输出参数行为，编码和全解码均rc0；旧科学/工程失败没有改写。

## P1距离、限制与下一步

{progress}

下一步只推荐一个约30分钟（25–35分钟）重建输入桥接单元：在已知科学根目录有界复核真实RaDe-GS灯具来源，若仍无则准备分离的合成RGB/camera train/dev/test与oracle目录，冻结相机划分、验证加载和全部视图。只称输入准备，不把GT网格替换成重建主输入；CPU不训练、不声称H1/H2。详见NEXT.json。

资源：CPU affinity[0,1]、数值/ffmpeg单线程、串行计算、无GPU/下载/共享环境修改；根盘余量{resource['root_free_bytes']/2**30:.2f}GiB、HDD余量{resource['hdd_free_bytes']/2**30:.2f}GiB、任务输出{resource['task_output_bytes']/2**20:.2f}MiB。新代码/文档仅授权分支；没有push或merge。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    (WORK/'docs/partwise_sketch_hatching_v02/REPORT_unit005_ZH.md').write_text(report)
    lines=['# Actual unit005 commands and return codes','',f'Working directory: `{WORK}`','',
        'Each child inherited CPU affinity0,1, numeric threads1, CUDA disabled and the required task scratch TMPDIR. Raw stdout/stderr are retained outside the science manifest and SHA-bound by receipts.','']
    for name,record in commands.items():
        lines += [f'## {name}', '', '```bash',shlex.join(record['command']),'```',f"Return code: {record['returncode']}; wall seconds: {record['wall_seconds']:.6f}",'']
    (UNIT/'REPRODUCE.md').write_text('\n'.join(lines))
    print(json.dumps(native(summary)))


def seal():
    check_lock();assert not (UNIT/'SEAL.json').exists()
    status=read('STATUS.json');assert status['execution_state']=='complete'
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-p1-v02'
    assert Path.cwd().resolve()==WORK.resolve()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    files=[]
    for path in sorted(UNIT.rglob('*')):
        if not path.is_file() or 'runtime' in path.relative_to(UNIT).parts:continue
        if path.parent==UNIT and path.name in ('SHA256_MANIFEST.json','SEAL.json'):continue
        files.append(dict(root='unit',path=str(path.relative_to(UNIT)),bytes=path.stat().st_size,sha256=sha(path)))
    sources=list((WORK/'experiments/partwise_sketch_hatching_v02').glob('*unit005.py'))
    sources += [WORK/'experiments/partwise_sketch_hatching_v02/asset_cli.py',WORK/'docs/partwise_sketch_hatching_v02/ASSET_CLI_ZH.md']
    sources += list((WORK/'docs/partwise_sketch_hatching_v02').glob('*unit005*'))
    for path in sorted(sources):
        files.append(dict(root='worktree',path=str(path.relative_to(WORK)),bytes=path.stat().st_size,sha256=sha(path)))
    manifest=dict(source_commit=commit,created_utc=datetime.now(timezone.utc).isoformat(),
        roots=dict(unit=str(UNIT),worktree=str(WORK)),files=files,
        exclusions=['runtime stdout/stderr, bound in execution receipt hashes','manifest and seal self references'])
    write_json(UNIT/'SHA256_MANIFEST.json',manifest)
    result=dict(manifest_path=str(UNIT/'SHA256_MANIFEST.json'),manifest_sha256=sha(UNIT/'SHA256_MANIFEST.json'),
        file_count=len(files),total_bytes=sum(f['bytes'] for f in files),source_commit=commit,
        protocol_source_commit=read('SOURCE_LOCK.json')['git_commit'],scientific_verdict=status['scientific_verdict'],
        created_utc=datetime.now(timezone.utc).isoformat(),
        verification='Producer seal after independent image/mask validation,full media decode and actual delegated visual review. Parent monitor remains independent.')
    write_json(UNIT/'SEAL.json',result);print(json.dumps(native(result)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['finish','seal'])
    globals()[parser.parse_args().stage]()
