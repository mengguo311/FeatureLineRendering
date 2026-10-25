"""Write Chinese handoff from completed saved results; no scientific reruns."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now
from pathlib import Path
import json,datetime

AUTHORIZED='2026-10-25T13:02:28.723079+09:00'
def load(name):return json.loads((UNIT/name).read_text())
def main():
    a=load('asset/ASSET.json');d=load('DIRECTION_READBACK.json');f=a['field'];audit=load('AUDIT.json')
    match=load('BUILD_MATCH.json');rows=[x for x in load('SUMMARY.json') if x['kind']=='dev'];far=load('FAR_READBACK.json');attr=load('attribution/SUMMARY.json')
    assert audit['status']=='pass' and load('cached_global_replay/REPLAY_RECEIPT.json')['all_equal']
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['global_RED']['child_returncode']==1
    assert all(r['child_returncode']==0 for k,r in commands.items() if k!='global_RED')
    nextstep='下一次只读Astra审查与父级冻结后，优先做H的交叉角混杂控制：冻结本轮H第0层场与路径，仅替换第1层。对每个原载体面，以同一个切平面旋转R把F0第0层无向方向映到H第0层，令J第1层=R作用于F0第1层；因此逐面保留F0两层夹角，而H第0层及其路径逐字节保持。该旋转从已存场直接确定，不选择新角度、不扫描、不重新求场或改载体。第1层沿原种子/请求长度和同一行走器重新生成新身份；保留F0及原H对照，重新按四BUILD固定各臂全局可见墨预算，检查完整前后linked/ungated、支持长度、分层变化与远区绝对损伤。若局部顺线收益在恢复原交叉角后消失或弱后侧继续退化，就不把本轮观感改善归于可推广的全局场优势。此为解决已观察到的风格混杂，不是角度调优；仍不能独立证明物理载体噪声或自动方向估计优越。'
    why='H真实降低归一化图内方向能量且前侧局部线束更顺，但最大分量1486面、73.8146%目标面积把锚面2.768896°的近平行夹角传播到整片；低于15°面积从17.0964%升至78.8601%。这直接混杂了场一致性与交叉风格，弱后侧支持长度也下降。保持第一层不变、逐面恢复原两层夹角是由本轮实际证据提出的单项反证，优先于继续调锚点、角度、平滑权重或立即转UI。'
    nxt=dict(action='continue',recommended_next_step=nextstep,why=why,estimated_minutes=25,requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00')
    js(UNIT/'NEXT.json',nxt)
    visual=dict(verdict='partial_local_improvement_with_cross_layer_confound; no whole-object promotion',
        inspected=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','dev/orbit_61_24_5.3/COMPARISON.png','dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_61_24_5.3/INK_LAYERS.png','dev/orbit_241_24_5.3/INK_LAYERS.png'],
        front='H的线束更直顺、斜面局部走向较一致，前侧实际可见墨量和支持长度也增加；局部收益可见，不能仅用整体负结论抹去。',
        rear='后侧格状交叉减少，呈较平行斜短线，但碎线、空白和照片残留仍在，弱后侧实际支持长度和覆盖下降；不能把少交叉直接当作完整形体改善。',
        confound='两层几何夹角大幅趋同；保留全部380条身份并不等于保留了原交叉风格。自然/配平及同预算ungated均有这一现象。',
        scope='有限目视检查，无独立用户偏好、真实表面或时序认证。')
    js(UNIT/'VISUAL_REVIEW.json',visual)
    verdict='partial: normalized graph coherence and front local readability improve; cross-layer angle collapse and weaker rear support prevent whole-object causal quality claim; default not promoted'
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(AUTHORIZED)).total_seconds()/60
    status=dict(unit='unit_006',execution_state='completed',stage='actual_F0_H_comparison_visual_audit_replay_complete',scientific_verdict=verdict,
        gaussian_link_progress='Original310475 rows/geometry/fullSH/opacity and order, paper41058/ink21006 weights,M1/UNKNOWN195279 unchanged. New proxy paths use original-ID regional S; no new per-path Gaussian ownership certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,
        tests=dict(expected_red='global_RED',green='global_GREEN_001',audit='audit',replay='cached_global_replay'),
        artifacts=['PROTOCOL.json','asset/ASSET.json','asset/FIELDS.npz','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','DIRECTION_READBACK.json','TENSOR_READBACK.json','TRANSITION_READBACK.json','COMPONENT_READBACK.json','WALKER_GUARD_RECORD.json','FAR_READBACK.json','VISIBLE_INTERVENTION.json','VISUAL_REVIEW.json','AUDIT.json','cached_global_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json','EXECUTION_RECORDS.json','HANDOFF_SOURCE_LOCK.json','ARTIFACT_MANIFEST.json'],
        blockers=[],candidate_limitations=['Relative tensor amplitude median0.04429; normalization does not certify confidence.','Two layers below15deg on78.86% target area; dominant anchor nearly parallel.','One inherited walker zero_step_cycle retained.'],execution_authorized_jst=AUTHORIZED,elapsed_minutes_from_authorization=elapsed,finished_utc=now())
    js(UNIT/'STATUS.json',status)
    L0=sum(a['paths']['F0_'+part]['length'] for part in ('old','added'));LH=sum(a['paths']['H_'+part]['length'] for part in ('old','added'))
    report=['# Unit006：全局传输减少图内方向跳变，但交叉角塌缩混杂了局部收益','',
        '**实际F0/H比较完成；科学结论为局部PARTIAL，整物体优势未建立，不升级默认。execution_state=completed，scientific_seal=false，父级验证待完成，NEXT=continue。**','',
        '已检查四DEV完整自然/配平图、前后独立墨层、同预算ungated和231/241/251后侧相机序列。H前侧线束较直顺，局部走向更一致；后侧格状交叉减少，但碎线、空白和照片残留仍在。局部可见改善保留为PARTIAL，不能称整物体突破，也不能忽略显著的交叉风格变化。本观察不是用户偏好实验。','',
        '## 冻结机制与保持项','',
        'F0仍是原切片场normalize(n×q)，q来自冻结unit010基底及35°/95°。H沿用unit003的2483对共享边传输图；同旧/新增分区且无向二面角不超过60°，311对锐边被排除于场求解，但仍可被原行走器跨越。每个连通分量选最大面积三角形、同面积取最小面ID，固定该面F0两层切向。用切平面内对称无迹张量Q表示无向场，最小化sum((area_i+area_j)/2)*||Q_i−T_ij Q_j T_ij^T||²，一次稀疏分解同时求两层；不含逐面原始场保真项，不扫描权重或迭代次数。取正主特征线；相对幅值sqrt(2)||coeff||≤1e-12才回退同面F0，规则在生成前冻结。','',
        '同一原16543顶点/29999面、380个种子、逐笔触原请求长度、原行走器和保护停止保持。原310475 Gaussian行/顺序、原PLY/中心/协方差/opacity/完整SH、41058纸底与21006墨权重、195279 UNKNOWN/M1、2121作者目标面、旧2030/新增91分区、1px/AA2、0.004遮挡容差和2px评价带保持。新F0/H ID分别为父ID+900000000000/1000000000000，存face/bary，不表示Gaussian所有权。没有改载体、补孔、重排种子、放宽遮挡或新增目标。','',
        '## 图内相干性、幅值衰减和风格混杂','',
        f"传输图有{f['components']}个分量。归一化后图内方向能量{f['normalized_graph_energy_F0']:.9f}→{f['normalized_graph_energy_H']:.9f}，所以收益并非只来自未归一化张量变小。独立张量驻点残差{audit['tensor_audit']['stationarity_residual_max']:.3g}，锚向与实际图均核对通过。目标方向变化中位数/P95/最大={f['selected_change_degrees_quantiles'][0]:.3f}°/{f['selected_change_degrees_quantiles'][2]:.3f}°/{f['selected_change_degrees_quantiles'][3]:.3f}°。退化回退0。",
        '但是相对张量幅值最小0.0003094、中位数0.0442897，存在明显幅值衰减；大于数值回退阈值不代表可靠方向。被排除锐边的两层连接能量0.366469/0.281841→0.363871/0.305855，未同步改善，不能称全表面相干。','',
        '最重要的混杂：最大分量1486面，占目标面积73.8146%，锚面3102的F0两层夹角只有2.768896°；该角度在H整个分量保持近乎常数。另一83面分量的锚角1.960896°也被传播。目标面积加权平均交叉角49.895273°→13.151954°，小于15°的面积17.0964%→78.8601%。因此H更像平行排线；380条数量不变不能证明原交叉风格保持。此为按冻结锚规则得到的真实结果，未换锚、调角或回填协议。','',
        '## 路径与实际跨边事件','',
        f'两臂均380条笔触，内部存储断点0。总长度{L0:.9f}→{LH:.9f}，减少{100*(1-LH/L0):.3f}%；128条笔触有大于1e-6长度损失。H双向端点613达到请求长度、127遇作者边界、19遇网格边界、1触发zero_step_cycle。F0长度来自已被原生成器截断的路径，全部requested_length不能说明原基线没有边界截断。','',
        '| 分区 | 世界跨面转角中位数F0/H | P95 F0/H | 总长度F0/H |','|---|---:|---:|---:|']
    for part in ('old','added'):
        x,y=d['paths'][part+'_F0'],d['paths'][part+'_H'];report.append(f"| {part} | {x['shared_edge_turn_degrees_quantiles'][0]:.3f}°/{y['shared_edge_turn_degrees_quantiles'][0]:.3f}° | {x['shared_edge_turn_degrees_quantiles'][2]:.3f}°/{y['shared_edge_turn_degrees_quantiles'][2]:.3f}° | {x['length']:.9f}/{y['length']:.9f} |")
    report+=['','主分区实际路径的图内展开转角中位数3.245°→0.461°、P95 39.645°→5.597°；排除锐边上的P95却92.468°→121.682°，钝角事件12→20。图内钝角9→1，新增分区图内P95 35.726°→6.817°。统计按实际存储的非零线段读取，所有跨面边都归类，未删除困难锐边。行走器H事件计数22与存储非零段读回21不完全一致：零步转换可以计入行走事件但不留下线段。','',
        '保护停止保留在WALKER_GUARD_RECORD.json：父stroke14500000040，新ID1014500000040，seed_face2442，第1层minus端zero_step_cycle，请求0.12、实际0.108510429、20段。没有删去该笔触、延长它或调保护阈值；这不使其他有效锚点无效，但禁止称全部路径完整积分。','',
        '## BUILD预算和完整DEV','',
        '四BUILD自然目标墨RGB L1：'+json.dumps(match['natural_totals'],ensure_ascii=False)+'。',
        f"公共预算{match['budget']:.6f}；全局系数"+json.dumps(match['scales'])+'。实际合成读回在浮点误差内配平，自然强度同时保存，无DEV/逐帧拟合。BUILD相等不保证每个DEV墨量相等。','',
        '| DEV相机 | 目标像素 | 目标墨L1 F0/H | 覆盖F0/H | 内部覆盖F0/H |','|---|---:|---:|---:|---:|']
    for r in rows:
        x,y=r['F0_linked'],r['H_linked'];report.append(f"| {r['view']} | {r['target_pixels']} | {x['ink_L1']:.3f}/{y['ink_L1']:.3f} | {100*x['coverage']:.2f}%/{100*y['coverage']:.2f}% | {100*x['interior_coverage']:.2f}%/{100*y['interior_coverage']:.2f}% |")
    report+=['','两前侧目标覆盖增加，两后侧下降；弱241°/24°由35.36%降至32.12%，同预算ungated也由40.57%降至36.97%。前侧更顺的线束同时带有更多可见墨和交叉角塌缩，不能纯归因于场一致性；后侧格状交叉变少同时支持下降，也不能单独当作更干净。S仍为可选原ID区域连接，未建立其NPR质量贡献。','',
        '四DEV目标RGB L1差≥0.05的像素比例为'+', '.join(f"{100*r['target_changed_fraction_005']:.2f}%" for r in far[:4])+'，确有大幅可见干预。1°场差、0.05墨或图像差仅为沿用描述口径，不是新增通过门槛。','',
        '## 自身可见支持、深度与S','',
        '| 相机/臂 | 代理可见长度px | pre-S自身缺失px | linked配平自身缺失px | linked支持长度px |','|---|---:|---:|---:|---:|']
    for r in attr:report.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    report+=['','前侧linked支持长度854.642→985.513px，确有局部支持增长；弱后侧720.578→665.518px。后侧缺失分子虽变小，可见长度也下降，因此不称连续性修复。曲线方向改变、投影和分段求积都影响这些量；采样每条stroke自身墨层，不借重叠笔触，但可见性仍依赖原代理，非独立物理真值。深度拒绝含正确背面/真实遮挡，不能全部当渲染错误；完整分区和深度拒绝保留在attribution及VISIBLE_INTERVENTION。','',
        '## 远区绝对损伤','',
        '| DEV相机 | linked远其他源差L1 F0/H | linked背景源差L1 F0/H | H ungated远其他源差L1 |','|---|---:|---:|---:|']
    for r in rows:
        x,y=r['F0_linked'],r['H_linked'];report.append(f"| {r['view']} | {x['far_other']:.9f}/{y['far_other']:.9f} | {x['background']:.9f}/{y['background']:.9f} | {r['H_ungated']['far_other']:.9f} |")
    report+=['','表中包含原纸底已有损伤。六个不同评估相机H−F0 linked远区最大单像素L1=4.93973494e-06；弱后视角1个非零像素，超过1/255的远区像素合计0。不能称严格零，未扩评价带、改目标或删困难像素。','',
        '## 验证、复放和范围','',
        '预期RED因缺global_field模块rc1；5组GREEN全部rc0，覆盖平面恒等、可展开曲面共享边、噪声曲面、反绕序、分离片/分区/孤立面、基线路径恢复、face/bary、真实同标签前景遮挡及零S。真实派生、BUILD、DEV/arc、归因、审计、复放及保存结果诊断全部rc0。',
        f"独立审计检查{audit['input_files_checked']}份冻结输入、源码快照、原行权重、传输图/锚选择、张量驻点与归一化场；380×2个种子误差0，锚点误差{audit['max_anchor_error']:.3g}，F0端点误差{audit['max_F0_endpoint_error']:.3g}。F0所有实际自然墨图逐值恢复旧A，{audit['pngs_decoded_and_checked']}张PNG完整解码并核验。新进程实际重画弱后侧墨层，30数组逐值一致。",'',
        '```bash','/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/global_field_unit/replay_global.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_006/user_replay_001 --view orbit_241_24_5.3','```','',
        '输出须为unit006内不存在的新目录。复用哈希固定GS source/paper/S，实际重栅格化新路径；不是再次冷GS或独立便携包。unit001一次冷重放成功范围保持。沿用既有依赖，CPU两核亲和、数值线程1、串行、CUDA为空，无安装、下载、GPU、训练或嵌套模型。冻结科学代码未改；事后诊断/报告源码另列HANDOFF_SOURCE_LOCK。','',
        '四DEV与三后侧arc合计六个不同评估相机，241°/24°明确复用；均为EXPOSED，三帧序列不是连续视频或时序稳定认证。Lego是已有冻结GS资产，不是本轮新采集真实物体，代理也不是真值。当前是CPU原GS纸底加原ID区域门控代理墨，不是原生Gaussian排线、完整语义部件或逐路径原ID认证。','',
        'v05稀疏任务far8.044%、31像素腐蚀目标、4.49%作者区域变化失败，v06及v07 unit001至005全部负结果保持。本轮不能排除全部载体噪声或证明载体必为主因；也不能把图内相干性成功扩成全物体NPR成功。','',
        '## 下一步','',nextstep,'',why,'',
        f'本次仅完成unit006；报告时从授权计约{elapsed:.2f}分钟。下一科学单元仍须只读审查与父级冻结。14:25禁启新单元、14:45科学收尾、15:00硬停止。']
    (UNIT/'REPORT_ZH.md').write_text('\n'.join(report)+'\n')
    js(UNIT/'EXECUTION_RECORDS.json',commands)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(HERE/name):sha(HERE/name) for name in ('read_diagnostics.py','finish_global.py')}))
    print(json.dumps(dict(execution_state='completed',scientific_verdict=verdict,next='continue',elapsed_minutes=elapsed),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
