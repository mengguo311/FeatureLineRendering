"""Summarize validated finite evidence; no scientific gate or result is changed."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import argparse,json,shutil,os
import numpy as np

def read(p):return json.loads(Path(p).read_text())

def finish(unit):
    protocol=read(unit/'PROTOCOL.json');scenes={s:read(unit/'results'/s/'SUMMARY.json') for s in ('chair','lego')}
    validations={s:read(unit/f'VALIDATION_{s}.json') for s in scenes}
    assert all(v['region_binding_all_rows_recomputed_exact'] and v['path_binding_all_rows_recomputed_exact'] for v in validations.values())
    checks={};bounds=[];recovery_equal={}
    for filename,root,key in [('INTERRUPTED_CHAIR_LOCK.json',unit/'interrupted_chair','files'),
                              ('INTERRUPTED_LEGO_LOCK.json',unit/'interrupted_lego_start','files')]:
        lock=read(unit/filename);bad=[name for name,h in lock[key].items() if sha(root/name)!=h]
        assert not bad;checks[filename]=dict(files=len(lock[key]),unchanged=True)
    prev=OUTPUT_ROOT/'units/unit_001';pl=read(prev/'EVIDENCE_LOCK.json')
    assert all(sha(prev/name)==v['sha256'] for name,v in pl['files'].items())
    checks['previous_unit']=dict(files=len(pl['files']),unchanged=True)
    for name in ('BASELINE_MEMBER_LOCK.json','OLD_SEALS_BEFORE.json'):
        lock=read(OUTPUT_ROOT/'orchestration'/name)
        bad=[p for p,h in lock.items() if sha(p)!=h]
        assert not bad,(name,bad);checks[name]=dict(files=len(lock),unchanged=True)
    for old in (unit/'interrupted_chair').rglob('*.npz'):
        other=unit/'results/chair'/old.relative_to(unit/'interrupted_chair')
        with np.load(old,allow_pickle=False) as a,np.load(other,allow_pickle=False) as b:
            exact=set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
            assert exact,old;recovery_equal[str(old.relative_to(unit/'interrupted_chair'))]=exact
    for scene,s in scenes.items():
        for e in s['evaluation']:
            c=e['camera'];folder=unit/'results'/scene/c['view']
            with np.load(folder/'baseline.npz') as z:
                alpha=z['alpha'];yy,xx=np.nonzero(alpha>.05)
                bounds.append(dict(scene=scene,view=c['view'],alpha_gt_005_bbox=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],
                    border_alpha_max=float(max(alpha[0].max(),alpha[-1].max(),alpha[:,0].max(),alpha[:,-1].max()))))
    replays={}
    for folder in unit.glob('replay_*'):
        r=read(folder/'REPLAY.json');assert all(all(v.values()) for v in r['checks'].values())
        replays[folder.name]=r['checks']
    video=read(unit/'media/VIDEO_VALIDATION.json')
    assert all(x['encoded_frames']==x['decoded_frames'] for x in video['videos'])
    receipts={p.name.removesuffix('.receipt.json'):read(p) for p in (unit/'logs').glob('*.receipt.json')}
    assert all((unit/'logs'/(p.name.removesuffix('.start.json')+'.receipt.json')).exists() or read(p)['pid']==os.getpid() for p in (unit/'logs').glob('*.start.json'))
    audit=dict(utc=now(),immutable_inputs_and_failures=checks,recovery_all_original_npz_arrays_exact=recovery_equal,
        cold_replay_all_arrays_exact=replays,whole_object_bounds=bounds,no_unfinished_numerical_command_receipts=True,current_reporter_excluded_from_finished_receipt_check=True,
        visual_review='Viewed both complete three-view comparison sheets, Chair controls and all14 motion frames. Source objects stay in frame; proxy ripples/fragmented hatches and missing thin structures remain. Opacity changes are visually weak, especially Lego; motion fidelity is not edit-quality success.')
    js(unit/'FINAL_AUDIT.json',audit)
    next_step='Use the saved BUILD traces to measure each candidate original kernel\'s full-footprint responsibility inside versus outside the frozen path capsules. Freeze a specificity-aware selection or abstention rule, then repeat actual source tint/opacity with the same visible-effect budget, nearest-path and shuffled controls on Chair rear views and Lego. Preserve unit002 locality failures; do not loosen gates or add UI.'
    progress=dict(previous_gap='unit001 had region-level actual source tint and passive path CSR, but no path-driven source edit or second scene',
        actual_advance='Executed bounded saved-path-driven original-GS tint and true opacity rerender on Chair and Lego, with per-row UNKNOWN, complete accepted events, effect-matched controls and cold replay.',
        milestones=dict(M1_region_original_binding=dict(state='partial',scope='Two original row universes with locked soft region evidence, exposure/conflict/UNKNOWN; Chair exactly reproduces unit001 and Lego is new.'),
            M2_path_original_support=dict(state='partial',scope='Fixed sampled saved segments map face/bary/stroke IDs to all accepted original-ID alpha*T; duplicates counted once per pixel/view for selection; rejected and occluded anchors retained.'),
            M3_actual_linked_control=dict(state='engineering_demonstrated_scientific_locality_failed',scope='Both source tint and opacity copies actually rendered in three evaluation views per scene. Path locality tint passes1/6, opacity0/6; no general advantage over nearest-path.'),
            M4_reusable_asset_demo=dict(state='partial',scope='Persisted original-ID bindings, selections, source-only CLI, per-anchor CSV query and four exact cold replays. External original PLY and existing CPU environment required. No UI or native-Gaussian hatching.')),
        scenes={s:{k:v[k] for k in ('source_count','source_binding_unknown','region4_supported','path_selected_original_ids','sampled_segments','sampled_stroke_ids')} for s,v in scenes.items()},
        reasoning='Real source-kernel linkage is now active at path level and portable to a second scene, but broad kernel footprints, sparse cross-view support and weak opacity effect prevent a narrow-path local-control claim.')
    gates={s:{op:sum(e['arms'][op+'_path_linked']['path_intent']['intent_locality_gate'] for e in v['evaluation']) for op in ('tint','opacity')} for s,v in scenes.items()}
    assert gates=={'chair':{'tint':0,'opacity':0},'lego':{'tint':1,'opacity':0}},gates
    status=dict(unit='unit_002',stage='path_driven_original_GS_control_and_second_scene',execution_state='partial',updated_utc=now(),
        scientific_verdict='UNCERTIFIED_CPU_MAPPING; frozen narrow-path locality NO_GO across all required views',scientific_seal=False,
        gaussian_link_progress=progress,path_locality_pass_counts=gates,
        tests=dict(focused_trace_membership_path_tests=10,resume_equivalence_test=1,first_TDD_red_returncode=1,
            original_ID_acceptance_T_RGB_and_UNKNOWN_readback='passed both scenes',cold_replay_views=4,all_replay_arrays_exact=True,
            actual_camera_arc_frames=8,actual_opacity_levels=6,full_video_decode=True,lossless_frames_exact=True),
        original_failure_evidence=dict(unit001_unchanged=True,ficus_NO_GO_unchanged=True,historical_CPU_depth_discrepancy_unchanged=True,
            interrupted_commands={k:dict(returncode=v['returncode'],signals=v['interrupt_signals']) for k,v in receipts.items() if v['returncode']!=0},
            interrupted_bytes_preserved_in=['interrupted_chair','interrupted_lego_start']),
        artifacts=dict(protocol='PROTOCOL.json',source_binding='results/<scene>/SOURCE_BINDING.npz',path_binding='results/<scene>/PATH_BINDING.npz',
            selection='results/<scene>/EDIT_SELECTION.npz',contributors='results/<scene>/<view>/path_support.npz',
            source_panels='results/<scene>/ALL_EVALUATION_VIEWS.png',CLI='delivery_source/run_path.sh',validation=['VALIDATION_chair.json','VALIDATION_lego.json','FINAL_AUDIT.json']),
        limitations=['No independent native CUDA per-ID calibration or semantic reference','Same proxy intent mask is not physical attachment truth',
            'Chair23 represented stroke IDs after bounded sampling from24 frozen IDs; Lego24','Opacity mean target change is below .02 in every evaluation view',
            'Many original rows and occluded anchors remain UNKNOWN','No H1/H2/H3 proof, geometry repair or native-Gaussian hatching'],
        blockers_for_stronger_claim=['Full-footprint locality and cross-view path coverage','Independent native/physical/semantic calibration'],
        resource_discipline=dict(serial=True,cpu_affinity=2,numeric_threads=1,GPU=False,nested_models=False,push_or_merge=False),
        source_PLY_geometry_and_original_SH_unchanged=True,next_action='continue',evidence_seal_scope='validated finite engineering evidence only')
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,
        recommended_next_step_zh='利用已保存BUILD责任值量化每个候选原核在固定路径内外的完整footprint质量，冻结带特异性约束的选择／弃权，再按相同可见效果预算与最近路径、打乱对照比较；优先Chair背视角和Lego，保留本轮负结果，不放宽门槛。',
        gaussian_link_progress=progress,reasoning='A passive contributor list has become actual two-operation source control on two scenes. The next useful question is why accepted kernels spill outside the selected paths and whether footprint specificity helps at equal effect.',
        stop_only_if=['safety','quota','no useful independent action','deadline'],deadlines_jst=dict(no_new_science='2026-10-22T21:20:00+09:00',wrap='2026-10-22T21:45:00+09:00',hardstop='2026-10-22T22:00:00+09:00')))
    lines=['# Unit002：固定路径驱动原始 Gaussian 控制与 Lego 第二场景','',
        '**状态 partial；科学范围 UNCERTIFIED_CPU_MAPPING。** 本轮已实际执行 Chair／Lego 原核路径改色和 opacity 衰减，完成同预算对照、逐ID责任值验证和冷加载重放。窄路径局部性总体失败：linked改色仅1/6视角通过，opacity为0/6；不能宣称优于简单空间选择。','',
        '完整读取BRIEF、大纲M1/贡献追踪/代理附着/比较矩阵，复核实际v04适配器、接受位置、代理锚点和编辑代码。unit001原始7视角、每行membership和实际改色均独立复算通过，旧证据锁保持不变。旧Ficus源代码采用另一个q<=9/.999 cap/1e-5 stop近似，不能套用为本轮渲染器的逐ID校准；其357/284835支持核、reserved几乎全UNKNOWN及NO_GO结论保留。旧PartField k3是无语义聚类，未完成reserved原GS部件编辑；没有拿它冒充当前路径绑定。','',
        '协议在2026-10-22 17:20 JST冻结。每场景4个BUILD、3个仅对本次binding保留的评估相机，384px、固定stride3网格；Chair评估视点已在unit001曝光，底层GS训练覆盖未独立审计。没有盲测或独立语义GT。人工region4分别是座面patch和bucket surfaces，不保证完整语义部件。','',
        '| Scene | 原始行数 | M1 UNKNOWN | region4支持行 | 路径控制原核 | 段/实际stroke IDs |',
        '|---|---:|---:|---:|---:|---:|']
    for scene,s in scenes.items():lines.append(f'| {scene} | {s["source_count"]} | {s["source_binding_unknown"]} | {s["region4_supported"]} | {s["path_selected_original_ids"]} | {s["sampled_segments"]}/{s["sampled_stroke_ids"]} |')
    lines += ['', '预先均匀冻结24个保存stroke ID，再限制最多128个原段；Chair最终128段只覆盖23个ID，Lego93段覆盖24个。这个范围在评估前已记录，未按效果删样本。所有锚点保留原segment_index、stroke_id、face/bary、世界点、相机、完整CSR原ID/alpha×T、接受深度、保留/拒绝质量与UNKNOWN。相同像素/原ID的重复锚点在每视角选择累积中仅计一次。M1仍使用原6通道规则，Lego第5通道不用；Chair所有M1数组与unit001精确相同。','',
        '路径选择只作用于M1支持region4的原行；至少两视角、接受质量>=.02、保留比例>=.7，强度为fraction×min(accepted/.1,1)。其余保留UNKNOWN/拒绝原因。权重是渲染曝光证据，不是校准语义概率，更不是物理同面证明。','',
        '改色在完整SH3评估和下界clamp之后混合蓝色；原SH数组不写回，剩余(1-strength)部分保留全部高阶视角依赖。opacity编辑仅在副本中执行opacity_i×(1-strength_i)，重新渲染完整模型、重算T与接受列表。均值、协方差、旋转、原始行数/顺序与源PLY全部不变。selected-only单独存图，重算T，不能当作完整模型贡献。','',
        '最近路径控制按核中心到冻结段中点的距离取相同核数；这只是空间控制，不作为表面绑定。shuffle在BUILD曝光十分位内以seed1729置换强度。改色按BUILD固定网格真实未裁剪RGB L1线性匹配；opacity用实际完整源渲染做10步有界匹配，要求目标误差<=1%，评估相机不再调强度。PNG显示裁剪到0–1，原始指标另保存clipped结果。','',
        '| Scene | BUILD tint L1（三臂相同） | BUILD opacity L1 linked/nearest/shuffle | opacity目标最大相对误差 |',
        '|---|---:|---|---:|']
    for scene,v in validations.items():lines.append(f'| {scene} | {v["actual_BUILD_tint_L1"]["path_linked"]:.9f} | '+ '/'.join(f'{v["actual_BUILD_opacity_L1"][k]:.9f}' for k in ('path_linked','nearest_path','shuffled'))+f' | {v["opacity_matching_max_relative_error"]:.4%} |')
    lines += ['', '窄路径目标是冻结3D段的可见3px半径capsule，代理深度容差.02；固定2px边界带。下表保留三臂目标变化及远变化比例。门槛为目标内部mean L1>=.02且far<=2%；属于同一作者代理的意图自洽，不是语义正确率。完整region意图指标也保存在SUMMARY中，不能用宽region通过替代窄路径失败。','',
        '| Scene/view | Operation/arm | Target mean L1 | Far other mean L1 | Far background mean L1 | Far fraction | Total L1 | Gate |',
        '|---|---|---:|---:|---:|---:|---:|---|']
    for scene,s in scenes.items():
        for e in s['evaluation']:
            for arm,v in e['arms'].items():
                q=v['path_intent'];lines.append(f'| {scene}/{e["camera"]["view"]} | {arm} | {q["target_interior"]["L1_mean"]:.7f} | {q["far_other"]["L1_mean"]:.7f} | {q["far_background"]["L1_mean"]:.7f} | {q["far_non_target_fraction"]:.3%} | {q["total_L1"]:.4f} | {q["intent_locality_gate"]} |')
    lines += ['', 'Chair linked改色远泄漏14.1%–19.0%，最近路径约1.0%–2.1%；opacity linked为16.9%–22.8%。Lego linked改色3.09%/12.78%/1.22%，仅102度通过；opacity目标mean L1约0.00048/0.01405/0.00126，变化明显弱于.02门槛。不存在“几乎没改而低损伤即成功”的解释。Lego局部个别视角linked较好，不能覆盖Chair与其他视角的失败。','',
        '| Scene/view | Supported/attempted | Proxy-visible | Visible retained mass | UNKNOWN |',
        '|---|---:|---:|---:|---:|']
    for scene,s in scenes.items():
        for view,q in s['path_checks'].items():lines.append(f'| {scene}/{view} | {q["supported"]}/{q["attempted"]} | {q["proxy_visible"]} | {q["visible_retained_fraction"]:.2%} | {q["unknown"]} |')
    lines += ['', '10项针对性trace/membership/path测试通过，其中新功能先RED(rc1模块未实现)后GREEN；另1项断点匹配等价测试通过。两场景独立读回核验原ID剔除/排序映射、接受alpha阈值、完整T链、质量和完整SH RGB；所有M1及路径分布逐行重算一致。新opacity trace独立重建编辑RGB/alpha；Chair linked新增接受像素–ID对为1242/571/268，Lego为104/202/99。原生CUDA逐ID校准仍不可用；历史CPU median/expected depth偏差原样保留，协方差平面深度不是物理真值。','',
        'Chair长命令收到SIGTERM(-15)，Lego首次启动也收到SIGTERM(-15)，信号来源未确定；不把它们归因于科学失败。原始目录逐字节封存于interrupted_chair和interrupted_lego_start，退出码单独保留。工程恢复仅缓存同一opacity effect调用和恢复已完成数组，未改阈值/相机/选择；Chair原中断目录全部npz数组与恢复结果一致。随后保持命令等待并分段运行正常完成；没有隐藏第一次非零退出。','',
        '已实际查看两场景全部三视图面板、Chair对照和14帧接触表：原GS对象完整入画，代理波纹、碎排线、薄结构缺损仍在。8个不同相机矩阵构成40度短arc；固定相机6级opacity真实重渲染。两条视频完整解码，FFV1逐帧完全一致；这不证明全时序稳定性或局部编辑质量。四个独立冷进程（两场景、两操作、含Chair弱背视点）与保存数组完全一致。query_lego段0列出60个原核，保留质量0.927101、拒绝0.072799；CSV包含所有事件，不把单个原核当一条线。','',
        'M1两场景软分布partial；M2有限路径支撑partial；M3路径驱动真实原GS两种诊断已执行，但科学局部性失败；M4持久化/CLI重放partial。没有UI工作、新训练、GPU、环境转储、凭据访问、嵌套模型、push/merge。数值串行、两核亲和、数值线程1。orchestration及旧证据未写；仅封存验证过的有限工程证据，scientific_seal=false。','',
        '**NEXT=continue。** '+next_step,'',
        '重点文件：`results/<scene>/SOURCE_BINDING.npz`、`PATH_BINDING.npz`、`EDIT_SELECTION.npz`、各视角`trace/path_support`及opacity新trace、`VALIDATION_chair.json`、`VALIDATION_lego.json`、`FINAL_AUDIT.json`。完整图见`results/<scene>/ALL_EVALUATION_VIEWS.png`，复现见`REPRODUCE_ZH.md`。']
    (unit/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    reproduce=f'''# Unit002 复现

以下入口已用交付副本在四个新进程实际执行，数组与结果一致。输出目录必须尚不存在。

```bash
cd {unit}/delivery_source
./run_path.sh replay --unit {unit} --scene chair --view orbit_223_28_4.9 --operation opacity --output {unit}/runs/chair_replay_new
./run_path.sh replay --unit {unit} --scene lego --view orbit_102_28_5.1 --operation tint --output {unit}/runs/lego_replay_new
./run_path.sh query --unit {unit} --scene lego --segment 0 --output {unit}/runs/lego_query_new
```

`--arm nearest_path`和`--arm shuffled`可重放控制。`query`保留eligible=false事件；原ID始终为原PLY行i。源重放不使用代理栅格，读取完整原PLY、锁定原ID强度和相机。实际诊断仅改渲染副本，源PLY不写。

依赖现有只读CPU解释器与原始PLY，不打包环境或源checkpoint；可以用V05_PYTHON指定兼容解释器。仅当前本机验证。路径与模型SHA在PROTOCOL.json中。

完整实验来源是source_snapshot/run_path_unit.py。SIGTERM恢复的等价分段实现位于delivery_source/run_staged_path_unit.py（重复调用直到SUMMARY.json出现）；每次最多计算12个新的opacity预算点，退出rc0也可能只是保存预算断点，须检查SUMMARY。工程改动与原失败见ENGINEERING_AMENDMENT.json及INTERRUPTED_*_LOCK.json。禁止用已存在结果目录启动新的不同协议实验。

本单元只认证工程一致性，UNCERTIFIED_CPU_MAPPING。视频是8帧40度arc及6级opacity；不是360转台、实时性能或局部性成功认证。详见REPORT_ZH.md中的负结果。
'''
    (unit/'REPRODUCE_ZH.md').write_text(reproduce)
    docs=Path(__file__).resolve().parents[2]/'docs/partwise_sketch_hatching_v05'
    shutil.copy2(unit/'REPORT_ZH.md',docs/'UNIT002_REPORT_ZH.md')
    (docs/'UNIT002_LINKS.md').write_text(f'Unit002 evidence: `{unit}`\n\nReplay: `{unit}/delivery_source/run_path.sh`\n\nStatus partial; UNCERTIFIED_CPU_MAPPING. Path locality failed across required views; see UNIT002_REPORT_ZH.md.\n')
    print(json.dumps(dict(status='partial',gates=gates,immutable_checks=checks,archive_npz_equal=len(recovery_equal),replays=len(replays)),default=runtime.json_default))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);finish(p.parse_args().unit)
