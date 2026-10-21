"""Package validated unit002 engineering evidence, preserving negative results."""
import runtime
from runtime import js,sha,now,output_guard,OUTPUT_ROOT
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tarfile


def read(path):return json.loads(path.read_text())


def stage(unit):
    out=unit/'source_snapshot';out.mkdir()
    files={}
    for p in sorted(Path(__file__).parent.iterdir()):
        if p.suffix in ('.py','.cpp','.html'):
            shutil.copy2(p,out/p.name);files[p.name]=sha(p)
    js(unit/'SOURCE_LOCK.json',dict(utc=now(),files=files,
        note='actual source snapshot; protocol frozen before candidate; no historical source imported for writes'))
    doc=Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md')
    shutil.copy2(doc,unit/'REPRODUCE_ZH.md')
    shutil.copy2(doc,OUTPUT_ROOT/'DEMO_README_ZH.md')
    for name in ('01_loaded','02_angle_edit','03_orbit_zoom','04_regions','05_reloaded'):
        shutil.copy2(unit/f'browser_complete/{name}.png',unit/f'media/editor_{name}.png')
    js(unit/'VISUAL_REVIEW.json',dict(utc=now(),reviewer='same executing assistant, not blind or independent human',
        reviewed=['media/refinement_historical_views.png','media/refinement_new_views.png',
                  'media/local_edit_all_views.png','media/orbit_all_frames.png','media/zoom_all_frames.png',
                  'browser_complete/01_loaded.png','browser_complete/05_reloaded.png'],
        positive='Seat/back hatch kinks are visibly reduced in the complete-object views; geometry appears smoother; whole objects remain framed.',
        negative='Side and overhead hatch crowding remains. Lower legs stay sparse/noisy. Holes and ornament loss remain. Region cuts cross the back and arms; edited angle95 creates wide blank patches.',
        selection='Deliver bounded smooth asset as an appearance option with original included; no geometry accuracy improvement claim.',
        quantitative_tradeoff='Source-model depth residual and silhouette agreement worsen in all 8 views; ink is retained.'))
    print(json.dumps(dict(source_files=len(files),stage='ready for packaging')))


def archive(unit):
    package=unit/'portable_demo'
    files={str(p.relative_to(package)):sha(p) for p in sorted(package.rglob('*')) if p.is_file()}
    js(package/'PACKAGE_MANIFEST.json',dict(files=files))
    target=unit/'portable_demo.tar.gz'
    with tarfile.open(target,'w:gz') as tar:
        for p in sorted(package.rglob('*')):
            if p.is_file():tar.add(p,arcname=str(Path('portable_demo')/p.relative_to(package)),recursive=False)
    destination=unit/'portable_relocated';destination.mkdir()
    with tarfile.open(target,'r:gz') as tar:
        for member in tar.getmembers():
            assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            data=tar.extractfile(member).read()
            p=destination/member.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            p.chmod(member.mode)
    relocated=destination/'portable_demo'
    for name,expected in files.items():assert sha(relocated/name)==expected
    js(unit/'metrics/PACKAGE_VALIDATION.json',dict(utc=now(),status='PASS',files=len(files),
       archive_sha256=sha(target),archive_bytes=target.stat().st_size,
       all_extracted_files_exact=True,relocated_path=str(relocated)))
    print(json.dumps(dict(archive=str(target),bytes=target.stat().st_size,files=len(files))))


def finish(unit):
    p=read(unit/'PROTOCOL.json');v=read(unit/'metrics/REFINEMENT_VALIDATION.json')
    for phase in ('BUILD','EXPORT','PORTABLE'):
        assert read(unit/f'metrics/{phase}_REPLAY.json')['status']=='PASS'
    assert read(unit/'metrics/PACKAGE_VALIDATION.json')['status']=='PASS'
    assert read(unit/'browser_complete/BROWSER_VALIDATION.json')['status']=='PASS'
    assert len(read(unit/'metrics/VIEWER_SMOKE.json')['actual_http_edit_tests'])==6
    assert all(x['all_decoded_frames_exact'] for x in read(unit/'media/VIDEO_VALIDATION.json')['videos'])
    lock=read(unit/'SOURCE_LOCK.json')
    for name,h in lock['files'].items():
        assert sha(unit/'source_snapshot'/name)==h==sha(Path(__file__).parent/name)
    for path,h in p['inputs_sha256'].items():assert sha(path)==h
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    receipts=[]
    for path in sorted((unit/'logs').glob('*.receipt.json')):
        d=read(path);receipts.append(dict(path=str(path.relative_to(unit)),returncode=d['returncode'],seconds=d['seconds']))
    ratios=[r['candidate_hatch_ink']/r['original_hatch_ink'] for r in v['views']]
    turns={r:1-v['paths']['candidate'][r]['turning_radians_per_world_length']/v['paths']['original'][r]['turning_radians_per_world_length'] for r in ('2','3')}
    next_step=('复用已验证的CPU适配器与可搬移编辑器，扩展第二个真实Lego检查点。先按其模型坐标冻结粗风格区域和完整对象相机，'
               '运行一套原始代理/固定3D排线、局部参数编辑、导出冷加载与短轨迹。保留Chair两个版本，不把本轮平滑当成几何提升，也不继续扫平滑参数。')
    progress=dict(scene='chair',genuinely_ran_old_model=True,complete_object_comparison_views=8,
        saved_assets=['original','baseline','edited'],original_gaussians=256690,
        geometry_refinement='one bounded option; topology/labels/lower geometry preserved',
        middle_turn_per_length_reduction=turns['2'],upper_turn_per_length_reduction=turns['3'],
        total_hatch_ink_ratio_range=[min(ratios),max(ratios)],
        actual_browser_test=True,actual_http_controls=6,page_reload_camera_fixed=True,
        cold_reload_exact=True,exported_zip_cold_reload_exact=True,relocated_package_cold_reload_exact=True,
        full_original_model_rebuild_exact=True,full_rebuild_seconds=read(unit/'metrics/BUILD_REPLAY.json')['seconds'],
        orbit_frames=12,zoom_frames=6,all_video_frames_exact=True,
        reasoning='在已运行真实Chair上减少了可见路径折痕，补齐真实浏览器操作/刷新、下载资产冷加载和搬移包重放；下一步可验证跨模型可用性。',
        remaining='sparse lower legs, holes/ornament loss, side crowding, manual height cuts, tiny strict-locality residual, geometry agreement tradeoff')
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-22T02:39:33.193498+09:00')).total_seconds()/60
    status=dict(stage='UNIT002_HANDOFF',execution_state='partial',completed_utc=now(),elapsed_minutes=elapsed,
        scientific_verdict='H1_H2_NOT_TESTED; historical P1 NO_GO/P2 ZERO_HEADROOM unchanged; no geometry accuracy gain',
        genuinely_ran_old_model=True,demo_progress=progress,source_commit=commit,
        visual_quality='partial; smoother appearance with measured source-geometry tradeoff',
        geometry_provenance=p['geometry'],region_provenance=p['region_provenance'],
        artifacts=['portable_demo.tar.gz','portable_demo/run.sh','REPRODUCE_ZH.md','assets/baseline/asset.json',
                   'assets/original/asset.json','assets/edited/asset.json','media/refinement_historical_views.png',
                   'media/refinement_new_views.png','media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv',
                   'media/editor_05_reloaded.png','metrics/REFINEMENT_VALIDATION.json','metrics/BUILD_REPLAY.json',
                   'metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','browser_complete/BROWSER_VALIDATION.json'],
        tests_and_command_receipts=receipts,
        failure_records=['EXECUTION_AMENDMENT.json','logs/tdd_red.log','logs/freeze.log',
                         'logs/browser_red.log','logs/browser_ui_red.log','logs/browser_green.log',
                         'logs/end_to_end_rebuild.log','replay_end_to_end/raw_source/proxy/BUILD_PROGRESS.json'],
        limitations=['source-depth and silhouette agreement worsen in all eight views',
                     'one train_r_32 far-other pixel retains 0.2 gray L1 outside fixed 2px band',
                     'finite self-proxy attachment/locality, no independent temporal or semantic truth',
                     'headless browser tested in software mode; not a user study or real-time demo',
                     'Firefox snap version wrapper printed XDG reassignment messages; automatic file effects not audited'],
        blockers=[],recommended_next_step=next_step,next_action='continue',
        supervisor_verification='reported_not_independently_verified',
        seal_scope='validated engineering artifacts and explicit negative evidence; no full scientific certification',
        resources=dict(cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False,nested_models=False,
                       serial=True,new_dependencies=False,servers_stopped=True))
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='Chair已经具备完整对象/局部编辑/真实浏览器/导出与冷加载；第二真实模型比追求完美去噪或重启GT门槛更接近通用可用demo。',
        ranked_alternatives=['next genuine model: Lego','later improve coarse region authoring or hatch crowding'],
        estimated_next_minutes=35,deadline_jst='2026-10-22T10:00:00+09:00',
        no_new_science_after_jst='2026-10-22T09:20:00+09:00',science_wrap_jst='2026-10-22T09:45:00+09:00'))
    table=[]
    for r in v['views']:
        g=r['geometry']
        table.append(f"| {r['view']} | {r['candidate_hatch_ink']/r['original_hatch_ink']:.4f} | "
                     f"{g['original']['source_alpha_silhouette_iou']:.5f} → {g['candidate']['source_alpha_silhouette_iou']:.5f} | "
                     f"{g['original_depth_residual']['mean']:.6f} → {g['candidate_depth_residual']['mean']:.6f} |")
    report=f'''# Unit002 — Chair bounded refinement and usable demo

**执行状态 `partial`，工程交付可运行。** 完整读取 BRIEF、851行原大纲、最新P1/P2报告/NEXT及相关源代码，并实际审阅unit001完整对象输出。本轮选择一个受限代理平滑候选，保持原基线，同时补齐真实浏览器与导出包冷加载。没有重启GT台灯、训练、GPU或参数扫选。

## Frozen change and actual model

原Chair PLY：`{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，256,690高斯。几何仍是vanilla 3DGS协方差平面估计深度的TSDF代理，不是独立测量或RaDe-GS训练结果。原模型CPU EWA/SH在8个冻结相机真实重渲染，见 `source_model/MODEL_IMPORT.json` / `SOURCE_RENDER.json`。没有使用旧失败ink资产或GT替代模型。

协议 `PROTOCOL.json` 先于候选输出冻结。唯一外观候选为8对Taubin正负步（0.5/-0.53），最大位移0.012世界单位；共享索引边邻接，固定开放/非流形边界、区域边界与全部下区域顶点，保留三角拓扑和面regionIDs。17,058顶点/30,000面中9,273顶点移动，7,783顶点固定；最大位移0.012，P95=0.010416。面朝向为正且面积至少原20%，保留6,210开放边，无补洞。下区所有顶点及212路径精确不变。

修复读取器以使用保存的face_regions；若继续按新面中心高度重算，将有12面改变标签。标签来源仍是unit001人工z阈值，并未增加语义知识。新mesh SHA定义新的资产版本；跨版本相同数字stroke_id不代表同一坐标路径。

## Appearance versus geometry

中区路径转角/总弧长从46.0022降至28.6296（描述性下降{turns['2']:.1%}），上区29.7947→16.6460（{turns['3']:.1%}）。这包含真实形状曲率，且不是匹配路径审美指标。中/上区总弧长83.6065→79.0285、44.8850→43.3655；路径数782→753、390→383，很多短线依然存在。8视角实际总hatch墨量保留为原{min(ratios):.2%}–{max(ratios):.2%}，没有靠清空排线取得平顺结果；逐region固定原可见mask覆盖、墨量与空白距离在验证JSON中。

| View | Candidate/original hatch ink | Source-alpha silhouette IoU | Mean source-depth residual |
|---|---:|---:|---:|
{chr(10).join(table)}

深度残差使用相同整数像素中心射线、共同合格源深度与两代理可见交集；每视角分母及缺失像素另列。**8视角源几何一致性均变差，因此不宣称几何精度提升。** 这是共享原检查点的模型深度诊断，不是独立真值。旧4个参考RGBA轮廓分数也保留。静态前4视角历史已曝光；新4视角及12/6轨迹在候选前冻结，不能称盲评。

已查看全部8个对照视角、8个编辑对照、12 orbit和6 zoom接触表。座面/椅背折痕减轻，侧面/俯视仍拥挤；腿部稀疏，孔洞、雕花/薄结构损失未解。95°中区编辑仍有不自然大空白。候选作为外观选项交付，原资产同包保留。

## Actual editing, browser and reload

8视角中区45°→95°编辑真实非零；非目标region_1/3文件、图层、深度、标签和轮廓精确相同。代理重心附着误差接近浮点量级。train_r_32仍有一个远其他区域像素0.2灰度L1残差，固定2px带未扩宽；其他7视角为0。严格零残差保持partial，非独立语义泄漏结论。

10项行为测试先红后绿，覆盖真实Chair粗糙度响应、位移/面朝向/固定下区、保存标签，以及原7项相机/深度/附着/遮挡测试。真实Firefox无头软件渲染完成角度编辑、Orbit、Zoom、区域显示与刷新截图。实际发现刷新图像不变但相机滑条复位；修复HTML初始化并将server camera字段限定为3个相机值后通过。初次WebDriver读取page lexical state失败，以及中间camera对象额外style字段导致的断言失败均保留，没有改写成通过。`browser_complete/`是真实浏览器证据，非人工UI研究。

HTTP角度/间距/长度/线宽/orbit/zoom六操作再次通过；invalid spacing返回422。真实下载ZIP解包后，服务器关闭，在独立CLI进程冷加载，PNG与全部数组精确复现。保存edited资产冷加载与搬移后的tar包 `./run.sh preview` 也精确。完整原PLY→24视角→原代理→受限平滑→路径→首图重建用时{progress['full_rebuild_seconds']:.2f}s，mesh、三个路径文件、PNG/NPZ和原代理都精确复现。实际命令/时间/rc见 `logs/*.receipt.json`，启动器见 `REPRODUCE_ZH.md`。

12 orbit+6 zoom均逐相机真实渲染同一固定3D资产，18帧各异、完整对象在框内，FFV1全解码与PNG精确；无全路径时序、遮挡正确性或实时性能认证。

## Failures and delivery

首个freeze因猜测旧SEAL文件名rc1，改为实际ENGINEERING_SEAL后才冻结。首个整流程重建外层rc143，在12/24视角中断，child subcode UNKNOWN，原因未确定，部分输出与日志保留；PID/comm检查无任务Python残留。唯一不改科学参数的恢复运行rc0。命令runner增加child PID/group收据、进度与自身组信号清理。Firefox最初的snap版version探测打印XDG目录自动重分配信息，文件级副作用未知、未手工回改；实际测试均直接使用snap内二进制及unit-local新profile，没有手工修改全局配置。详见 `EXECUTION_AMENDMENT.json`。

交付：`portable_demo.tar.gz`、`assets/{{original,baseline,edited}}`、`media/refinement_*_views.png`、`media/local_edit_all_views.png`、`media/editor_05_reloaded.png`、`media/{{orbit,zoom}}.mkv`、`metrics/`、源快照与哈希。源码提交 `{commit}`；变更只在授权分支/目录，原PLY、旧单元、orchestration证据输入哈希复核未变。CPU两核/数值单线程/串行/无GPU/无新依赖/无嵌套模型，实际浏览器与服务器已终止。仅封存验证工程产物及明确的失败证据，不把失败重建数组封为成功科学证据。

NEXT=`continue`：{next_step} 旧P1 NO_GO、P2 ZERO_HEADROOM/UNIDENTIFIABLE_FOR_H2不改写，外部监督状态保持reported_not_independently_verified。
'''
    (unit/'REPORT_ZH.md').write_text(report)
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(latest_unit='units/unit_002',execution_state='partial',
       updated_utc=now(),demo_progress=progress,readme='DEMO_README_ZH.md',package='units/unit_002/portable_demo.tar.gz',
       report='units/unit_002/REPORT_ZH.md',next_action='continue',recommended_next_step=next_step,
       supervisor_verification='reported_not_independently_verified'))
    groups=['source_snapshot','assets','renders','source_model','proxy','media','metrics','logs','red_source']
    paths=[]
    for group in groups:paths += [f for f in (unit/group).rglob('*') if f.is_file()]
    paths += [f for f in unit.glob('*.json') if f.name not in ('SHA256_MANIFEST.json','ENGINEERING_SEAL.json')]
    paths += [unit/'REPORT_ZH.md',unit/'REPRODUCE_ZH.md',unit/'portable_demo.tar.gz']
    for name in ('BROWSER_VALIDATION.json','CAPABILITIES.json','CLEANUP.json','RELOAD_CAMERA.json'):
        paths.append(unit/'browser_complete'/name)
    manifest={str(f.relative_to(unit)):sha(f) for f in sorted(set(paths))}
    js(unit/'SHA256_MANIFEST.json',dict(files=manifest))
    for name,h in manifest.items():assert sha(unit/name)==h
    js(unit/'ENGINEERING_SEAL.json',dict(utc=now(),kind='partial_engineering_integrity_seal',
        manifest='SHA256_MANIFEST.json',manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),files=len(manifest),
        execution_state='partial',source_commit=commit,
        validated_scope=['exact old-model execution','bounded candidate and measured negative tradeoffs',
                         'local edit with one-pixel residual','browser actions and page refresh',
                         'full original-model rebuild recovery','export and relocated cold replay','all video frames decoded'],
        exclusions=['scientific H1/H2 seal','independent geometry/temporal truth','browser profiles and mutable runs',
                    'initial interrupted rebuild arrays','automatic snap version-probe side effects'],
        supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='partial',files_sealed=len(manifest),source_commit=commit,
                         next_action='continue',elapsed_minutes=elapsed)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True)
    p.add_argument('phase',choices=['stage','archive','finish']);a=p.parse_args();output_guard(a.unit)
    {'stage':stage,'archive':archive,'finish':finish}[a.phase](a.unit)
