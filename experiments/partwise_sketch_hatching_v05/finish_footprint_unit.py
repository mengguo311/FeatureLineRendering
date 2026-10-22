"""Report only executed, independently validated original-kernel evidence."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json,subprocess,shutil,csv
import numpy as np
from PIL import Image
from run_footprint_unit import load,ARMS
from run_path_unit import read_npz
from run_unit import panel

def finish(unit):
    p=load(unit);scenes={};rows=[];coverage_rows=[];opacity_rows=[];total_pass={k:0 for k in ARMS}
    for scene,s in p['scenes'].items():
        root=unit/'results'/scene
        selection=json.loads((root/'SELECTION.json').read_text());audit=json.loads((root/'PRIOR_RAW_AUDIT.json').read_text())
        validation=json.loads((root/'VALIDATION.json').read_text());budget=json.loads((root/'BUDGET_MATCH.json').read_text())
        assert validation['all_footprint_rows_and_UNKNOWN_recomputed'] and validation['source_count_order_and_PLY_unchanged']
        assert budget['valid']
        evaluations=[];panels=[];controls=[];differences=[]
        for c in [v for v in s['cameras'] if v['split']=='evaluation']:
            e=json.loads((root/c['view']/'EVALUATION.json').read_text());evaluations.append(e)
            for arm in ARMS:
                v=e['arms'][arm];total_pass[arm]+=int(v['intent_locality_gate'])
                rows.append(f'| {scene}/{c["view"]} | {arm} | {v["target_interior"]["pixels"]} | {v["target_interior"]["L1_mean"]:.6f} | {100*v["far_non_target_fraction"]:.3f}% | {v["total_L1"]:.3f} | {v["intent_locality_gate"]} |')
            cv=e['coverage'];coverage_rows.append(f'| {scene}/{c["view"]} | {cv["specific"]["attempted"]} | {cv["specific"]["proxy_visible"]} | {cv["specific"]["original_supported"]} | {cv["specific"]["anchors_with_edit_mass_above_001"]} | {cv["previous_path"]["anchors_with_edit_mass_above_001"]} | {cv["specific"]["retained_fraction"]:.3%} |')
            v=e['opacity_diagnostic'];opacity_rows.append(f'| {scene}/{c["view"]} | {v["target_interior"]["L1_mean"]:.6f} | {v["far_non_target_fraction"]:.3%} | {v["intent_locality_gate"]} | {e["opacity_check"]["newly_accepted_pixel_ID_pairs"]} |')
            panels.append(root/c['view']/'comparison.png');controls.append(root/c['view']/'controls.png')
            base=read_npz(root/c['view']/'baseline.npz')['rgb'];heats=[]
            for arm in ARMS:
                edit=read_npz(root/c['view']/('tint_'+arm+'.npz'))['rgb']
                intensity=np.clip(np.abs(edit-base).sum(2)/.3,0,1)
                heat=np.ones_like(base);heat[:,:,1:]=1-intensity[:,:,None];heats.append(heat)
            diff=root/c['view']/'difference_diagnostics.png'
            panel(diff,[base]+heats,['Original GS','Specific | RGB L1 / 0.3','Previous | RGB L1 / 0.3','Nearest | RGB L1 / 0.3','Shuffled | RGB L1 / 0.3'],
                scene+' '+c['view']+' | Actual rendered differences, fixed red heat scale; these panels are NOT source renders')
            differences.append(diff)
        for name,files in [('ALL_EVALUATION_VIEWS.png',panels),('ALL_CONTROLS.png',controls),('ALL_DIFFERENCES.png',differences)]:
            ims=[Image.open(f).convert('RGB') for f in files];sheet=Image.new('RGB',(ims[0].width,sum(i.height for i in ims)),'white');y=0
            for im in ims:sheet.paste(im,(0,y));y+=im.height
            sheet.save(root/name)
        scenes[scene]=dict(source_count=s['source_count'],M1_unknown=audit['unknown'],selection=selection,
            primary_tint_pass_counts=validation['locality_pass_counts'],budget=budget,
            displayed_BUILD_L1=validation['clipped_display_BUILD_L1'],display_budget_ratio=validation['display_budget_max_min_ratio'],
            evaluation_artifacts='results/'+scene+'/<view>/EVALUATION.json',source_assets_and_arrays_locked=True)
    replays={};query_checks={}
    for scene in scenes:
        for op in ('tint','opacity'):
            result=json.loads((unit/f'replay_{scene}_{op}'/'RECEIPT.json').read_text())
            assert all(result['all_arrays_exact'].values());replays[scene+'_'+op]=result
        query=json.loads((unit/f'query_{scene}'/'RECEIPT.json').read_text());assert query['no_weak_or_occluded_records_pruned']
        ps=read_npz(unit/'results'/scene/query['camera']['view']/'path_support.npz')
        anchors=read_npz(unit/f'query_{scene}'/'ALL_ANCHORS.npz')
        for k,v in anchors.items():np.testing.assert_array_equal(v,ps[k])
        with (unit/f'query_{scene}'/'path_original_ID_support.csv').open() as f:records=list(csv.DictReader(f))
        assert len(records)==len(ps['weight'])==query['rows']
        np.testing.assert_array_equal([int(row['source_index']) for row in records],ps['source_index'])
        np.testing.assert_array_equal([float(row['alpha_T']) for row in records],ps['weight'])
        np.testing.assert_array_equal([row['depth_eligible']=='True' for row in records],ps['eligible'])
        query_checks[scene]=dict(CSV_original_ID_weight_and_eligibility_exact=True,all_anchor_fields_exact=True,rows=len(records),anchors=len(ps['state']))
    js(unit/'QUERY_VALIDATION.json',query_checks)
    video=json.loads((unit/'media/VIDEO_VALIDATION.json').read_text());assert video['all_frames_decoded'] and video['FFV1_frames_exact']
    previous=Path(p['prior_unit']);lock=json.loads((previous/'EVIDENCE_LOCK.json').read_text())
    errors=[k for k,v in lock['files'].items() if sha(previous/k)!=v['sha256']];assert not errors
    js(unit/'PREVIOUS_FINAL_SEAL_AUDIT.json',dict(utc=now(),members=len(lock['files']),mismatches=errors,old_evidence_unchanged=True))
    source=Path(__file__).parent;delivery=unit/'delivery_source'
    shutil.copytree(source,delivery,ignore=shutil.ignore_patterns('__pycache__'))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    js(unit/'SOURCE_COMMIT.json',dict(commit=commit,branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
        source_hashes={f.name:sha(f) for f in delivery.iterdir() if f.is_file()},protocol_core_unchanged=True))
    progress=dict(previous_gap='unit002 accepted original-ID path anchors but did not bound each selected kernel full off-path footprint; Chair locality 0/3 and Lego1/3.',
        actual_advance='All-pixel alpha*T per-original-row inside/band/far and depth-compatible evidence; frozen exclusion; actual effect-matched four-arm source tint and real source-opacity rerenders on Chair and Lego.',
        milestones={
            'M1_region_original_binding':dict(state='partial',scope='Two original-row universes; every inherited soft membership, exposure, conflict and UNKNOWN reconstructed exactly; no new semantic claim.'),
            'M2_path_original_support':dict(state='partial',scope='Raw stroke/segment/face/bary original-ID responsibilities retained; full-footprint per-row specificity and UNKNOWN now saved; unpruned CLI query.'),
            'M3_actual_linked_control':dict(state='validated_finite_CPU_diagnostic',scope=f'Actual original-GS source tint passes {total_pass["specific"]}/6 exposed evaluation views; all four arms use matched BUILD full-image RGB effect; opacity rerender is a separate fixed-strength diagnostic.'),
            'M4_reusable_asset_demo':dict(state='partial',scope='Saved original-ID bindings, footprint masses and selections; source-only replay/query CLI; four cold replays; actual camera arc and edit ramp. External source PLY/CPU environment required.' )},
        scene_counts={k:dict(source_count=v['source_count'],M1_unknown=v['M1_unknown'],selected_original_IDs=v['selection']['counts']['specific'],prior_selected_IDs=v['selection']['counts']['previous_path'],path_query_unknown=v['selection']['unknown']) for k,v in scenes.items()},
        reasoning='Off-path source responsibilities are now measured and drive reversible source edits. Finite locality and coverage are reported separately; exposed views and proxy masks cannot establish native calibration or physical/semantic ownership.')
    failures={f.stem:json.loads(f.read_text())['returncode'] for f in (unit/'logs').glob('*.receipt.json') if json.loads(f.read_text())['returncode']!=0}
    status=dict(unit='unit_003',stage='full_footprint_original_kernel_specificity_and_source_control',execution_state='partial',updated_utc=now(),
        scientific_verdict=f'UNCERTIFIED_CPU_MAPPING; proposed finite path-locality gate {total_pass["specific"]}/6; no general semantic/native/physical certification',
        scientific_seal=False,gaussian_link_progress=progress,primary_tint_pass_counts=total_pass,scenes=scenes,
        tests=dict(footprint_fixtures=2,prior_raw_views_reconstructed=14,full_pixel_real_BUILD_views=8,
            independent_fixed_grid_per_ID_checks=2,actual_matched_BUILD_rerenders=8,cold_replays=4,all_cold_replay_arrays_exact=True,unpruned_path_query_roundtrips=2,
            source_opacity_acceptance_RGB_T_reconstructed_views=6,actual_arc_cameras=4,actual_tint_levels=4,video_full_decode=True),
        original_failure_evidence=dict(unit002_lock_unchanged=True,unit001_Ficus_and_historical_depth_failures_unchanged=True,own_nonzero_receipts=failures,
            interrupted_Lego_evaluation='INTERRUPTED_EVALUATION_LOCK.json; original rc -15/SIGTERM, source undetermined; incomplete bytes preserved separately'),
        artifacts=dict(protocol='PROTOCOL.json',clarification='PROTOCOL_CLARIFICATION.json',bindings='results/<scene>/FOOTPRINT_BINDING.npz',
            original_region_binding='results/<scene>/SOURCE_BINDING.npz',original_path_binding='results/<scene>/PATH_BINDING.npz',
            selection='results/<scene>/EDIT_SELECTION.npz',validation='results/<scene>/VALIDATION.json',
            panels='results/<scene>/ALL_EVALUATION_VIEWS.png',controls='results/<scene>/ALL_CONTROLS.png',CLI='delivery_source/run_footprint.sh',motion='media/VIDEO_VALIDATION.json'),
        limitations=['All evaluation cameras previously exposed; no blind test','Same authored proxy intent masks, not independent semantics or surface truth',
            'M1 remains sparse/UNKNOWN; strict path query abstains on most original rows','Proxy holes, roughness and thin-structure loss are unchanged','Primary budget matches raw full-SH CPU RGB; clipped-display budgets separately audited',
            'Opacity diagnostic not matched across controls','No H1/H2/H3 proof or native-Gaussian hatching'],
        resource_discipline=dict(serial=True,CPU_affinity=2,numeric_threads=1,GPU=False,nested_models=False,no_push_or_merge=True),
        source_PLY_geometry_order_and_original_SH_unchanged=True,code_commit=commit,next_action='continue',
        evidence_seal_scope='validated finite engineering outputs and preserved failure receipts only')
    js(unit/'STATUS.json',status)
    next_step='Freeze genuinely new azimuth/elevation cameras and a fixed path-coverage/effect budget before looking at results. Test whether full-footprint selection retains locality under view change on both scenes; inspect failing or unsupported anchors and kernel depth/covariance, keep unit002/unit003 evidence unchanged, no UI or threshold loosening.'
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,
        recommended_next_step_zh='冻结未用于本轮判断的新方位／仰角及路径覆盖与编辑强度预算，复验全footprint选择在两场景的跨视角局部性；分析失败／无支持锚点的深度与核形状，保留旧证据，不放宽门槛或转做UI。',
        gaussian_link_progress=progress,reasoning='A real source-responsibility failure mechanism has an executable intervention. Fresh-view transfer and retained path coverage are useful independent questions, while native/physical calibration remains unavailable.',
        stop_only_if=['safety','quota','no useful independent action','deadline'],deadlines_jst=dict(no_new_science='21:20',wrap='21:45',hardstop='22:00')))
    lines=['# Unit003：完整 footprint 约束的原始 Gaussian 路径控制','',
        f'**execution_state=partial；UNCERTIFIED_CPU_MAPPING。** 新选择的原始GS改色在既定6个评估视角中通过{total_pass["specific"]}/6；上轮路径选择{total_pass["previous_path"]}/6，最近路径{total_pass["nearest_path"]}/6，打乱ID {total_pass["shuffled"]}/6。这是实际源GS CPU渲染的有限意图自洽结果，不是独立语义、原生CUDA或物理附着认证。','',
        '已完整阅读BRIEF和原大纲，检查v04原始SH3/协方差适配器、C++接受位置、代理锚点和编辑实现，并逐视角复算unit002实际数据。上轮14个视角的ID、alpha×T、排序、深度与完整SH RGB重建通过；两场景M1每行分布/UNKNOWN和路径绑定完全一致。旧Ficus实现使用q<=9、.999 cap、1e-5 stop，与当前接受逻辑不同；其NO_GO不改变。PartField k3明确只是无语义聚类、没有reserved原GS编辑，也未拿来冒充本轮绑定。','',
        '上轮只在路径锚点记录支持；同一核在其他像素的责任值不受约束。本轮在原C++实际接受位置累加**所有像素**的原核总质量、3px路径capsule内质量、固定2px边界带、远区质量与深度一致内部质量。原RGB/alpha/depth算术和阈值不变；全图聚合不保存巨量逐像素表，原稀疏查询仍保存全部接受事件，无topK。目标沿用Chair的128段/23个stroke和Lego的93段/24个stroke，均来自冻结人工region4，不等同整个座面或铲斗的语义范围。','',
        '协议在评估前冻结，PROTOCOL_CLARIFICATION明确继承的旧matching字段仅作历史元数据；本轮以footprint字段为准。保留上轮路径强度的条件：BUILD总far/total<=2%，有曝光视角的最差far/total<=5%，至少两视角深度一致支持，内部深度一致比例>=.7；其他原行保留弃权理由，不提升旧UNKNOWN。未按评估结果改阈值。','',
        '| Scene | 原始行数 | M1 UNKNOWN | 旧路径核 | 新路径核 | BUILD旧加权far | BUILD新加权far |','|---|---:|---:|---:|---:|---:|---:|']
    for scene,v in scenes.items():
        z=v['selection'];lines.append(f'| {scene} | {v["source_count"]} | {v["M1_unknown"]} | {z["counts"]["previous_path"]} | {z["counts"]["specific"]} | {z["old_selected_weighted_far_fraction"]:.3%} | {z["proposed_weighted_far_fraction"]:.3%} |')
    lines+=['','四臂都实际渲染完整原模型。最近路径按中心到冻结段中点距离取与新选择相同核数；打乱在BUILD曝光十分位内置换；上轮选择保留原核数。主改色在完整SH3求值和下界clamp后混合蓝色，原SH不写回，其余部分保留高阶视角变化。按四个BUILD完整图像的原始RGB L1配平，固定比例后才评估；源PLY、均值、协方差、旋转、行数／顺序不变。','',
        '| Scene | 四臂同一BUILD raw RGB L1 | 裁剪显示预算 max/min |','|---|---:|---:|']
    for scene,v in scenes.items():lines.append(f'| {scene} | {v["budget"]["target"]:.6f} | {v["display_budget_ratio"]:.8f} |')
    lines+=['','PNG裁剪到0–1；raw与clipped指标分别保存。上表显示预算差异单列，不把raw配平冒充完全相同的截图墨量。评估相机已在unit002曝光；本轮仅未用于选择和预算拟合，不是盲测。','',
        '| Scene/view | Arm | 目标内部像素 | 目标内部 mean L1 | 远区变化占比 | 全图 L1 | 原局部性门槛 |','|---|---|---:|---:|---:|---:|---|',*rows,'',
        '原门槛保持目标内部mean L1>=.02且远区占比<=2%。目标来自同一作者代理，衡量意图自洽；完整对象视角及最差结果都保存，不能用窄路径诊断图声称完整干净素描。旧代理的波纹、孔洞及薄结构缺失没有修复。ALL_DIFFERENCES.png以统一RGB L1/0.3红色热度显示实际渲染差值，明确标为差值诊断而非源渲染。','',
        '| Scene/view | 锚点总数 | 代理可见 | 原支持锚点 | 新编辑mass>.01锚点 | 旧编辑mass>.01锚点 | 新编辑加权mass/原保留mass |','|---|---:|---:|---:|---:|---:|---:|',*coverage_rows,'',
        '上表按实际配平强度计算；权重不是语义概率，仍保留遮挡、拒绝及零事件锚点。覆盖不足不能被低泄漏掩盖。M1 UNKNOWN是区域证据未知；FOOTPRINT_BINDING的UNKNOWN是此次特定路径查询弃权，两者含义不同。','',
        '另执行新选择opacity×(1-.5×未缩放强度)，真实重新计算全模型T和接受列表，保留新增背层贡献。此项是单臂机制诊断，没有配平控制，不能据此宣称优于其他选择。','',
        '| Scene/view | opacity目标mean L1 | far占比 | 原门槛 | 新接受像素-ID对 |','|---|---:|---:|---|---:|',*opacity_rows,'',
        '针对性验证包括：2项先RED后GREEN测试；非连续原ID、近裁剪、排序、混合深度/背层、全像素质量分区与弃权；8个真实BUILD视角全图统计；2场景逐原ID固定网格独立求和精确一致；原CPU五数组及事件精确不变；6个opacity trace重建；8次固定预算强度BUILD实际重渲染；24个主改色结果独立指标复算。4次冷加载原GS重放全部数组精确一致。','',
        'media保存4个真实相机位置的30°短弧与4级实际改色，逐帧原始数组及相机齐全；视频完整解码，FFV1逐像素精确。不是360°转台或时序质量认证。','',
        '最初TDD模块未实现返回1；一次生成C++时误用不存在的python命令返回127，随后编译测试返回1。改用python3生成后测试通过，原日志与退出码保留。Lego第三评估视角曾收到来源未确定的SIGTERM(rc=-15)；6个已写文件及原退出记录保存在interrupted_lego_evaluation_2和INTERRUPTED_EVALUATION_LOCK.json，按原冻结协议单独重跑，没有调整选择或门槛。unit002证据锁在开始和结束重新验证，原中断／失败和负结论字节不变。','',
        '交付：`results/<scene>/SOURCE_BINDING.npz`、`PATH_BINDING.npz`保留继承绑定；`FOOTPRINT_BINDING.npz`保存所有原行的全图质量、逐视角证据和弃权；`EDIT_SELECTION.npz`保存实际强度。`query_<scene>/`保存完整锚点表及原ID支持CSV；`delivery_source/run_footprint.sh`可冷重放与查询；`REPRODUCE_ZH.md`给出命令。','',
        '四里程碑均有明确范围：M1两场景软区域绑定已复算；M2加入完整footprint的路径原核支持；M3完成实际原GS改色/opacity与公平主对照；M4有CLI、持久化与冷重放，但依赖外部源PLY和现有CPU环境。没有UI工作、原生Gaussian排线或H1/H2/H3结论。只封存验证通过的有限工程证据，scientific_seal=false。','',
        '**NEXT=continue。** '+next_step,'']
    (unit/'REPORT_ZH.md').write_text('\n'.join(lines))
    repro=f'''# Unit003 原始GS链接重放

固定入口：`{delivery}/run_footprint.sh`。CPU两核／数值线程1／CUDA禁用；需要现有只读Python环境与原始PLY，源SHA在协议中校验。输出目录必须不存在，均在unit003内。

```bash
{delivery}/run_footprint.sh {unit} replay --scene chair --index 2 --operation tint --output {unit}/new_replay_chair
{delivery}/run_footprint.sh {unit} replay --scene lego --index 2 --operation opacity --output {unit}/new_replay_lego_opacity
{delivery}/run_footprint.sh {unit} query --scene chair --index 2 --output {unit}/new_query_chair
{delivery}/run_footprint.sh {unit} validate --scene lego --output {unit}/new_validation_lego.json
```

replay加载原始全SH3 GS以及逐原行权重，实际完整源渲染并与本轮数组逐项比较；query保留所有原始锚点和所有接受支持，不静默删除UNKNOWN/遮挡。`--arm previous_path/nearest_path/shuffled`支持改色对照重放。opacity仅有specific单臂诊断。

完整执行次序和精确参数在`logs/*.receipt.json`；协议核心源码在`source_snapshot/`，最终CLI和独立验证器在`delivery_source/`。没有打包原始PLY或Python解释器。
'''
    (unit/'REPRODUCE_ZH.md').write_text(repro)
    js(unit/'ENGINEERING_NOTES.json',dict(nonzero_receipts=failures,additional_generation_command_failure=dict(command='python - [local source generator]',returncode=127,reason='python executable unavailable; used python3, no model or environment changes'),recovery='new C++ generated; original failed test logs retained; focused tests pass; protocol gates unchanged'))
    print(json.dumps(dict(execution_state='partial',passes=total_pass,report=str(unit/'REPORT_ZH.md')),default=runtime.json_default),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);finish(output_guard(ap.parse_args().unit))
