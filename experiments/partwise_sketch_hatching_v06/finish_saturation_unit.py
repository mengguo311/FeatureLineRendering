"""Post-result handoff only; frozen scientific sources/results are not changed."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT,js,sha,now
from pathlib import Path
import datetime,json,shutil
from run_saturation_unit import protocol

def main():
    p=protocol();s=json.loads((UNIT/'SUMMARY.json').read_text());val=json.loads((UNIT/'VALIDATION.json').read_text())
    media=json.loads((UNIT/'MEDIA_VALIDATION.json').read_text());replay=json.loads((UNIT/'cold_replay_001/REPLAY_CHECK.json').read_text())
    visual=json.loads((UNIT/'VISUAL_REVIEW.json').read_text());assert visual['all_four_DEV'] and visual['all_nine_arc_frames']
    assert all(media['all_frames_decoded_exact']) and replay['all_links_zero_equals_original_GS']
    b=s['build'];dev=[r for r in s['records'] if r['kind']=='dev'];assert len(dev)==4 and len(s['records'])==13
    lines=[];damages=[];effects=[]
    for r in dev:
        pr=r['paper_residual'];w=pr['weighted_raw']['target_interior'];n=pr['saturated_raw']['target_interior'];m=pr['saturated_matched']['target_interior']
        lines.append(f"| {r['view']} | {r['coverage']['target']['pixels']}/{w['pixels']} | {w['clipped_L1_mean']:.6f}/{n['clipped_L1_mean']:.6f}/{m['clipped_L1_mean']:.6f} | {(1-n['clipped_L1_mean']/w['clipped_L1_mean'])*100:.2f}% | {r['coverage']['target']['ink_fraction']*100:.2f}% |")
        old=r['metrics']['weighted_raw'];new=r['metrics']['saturated_raw'];matched=r['metrics']['saturated_matched']
        damages.append(f"| {r['view']} | {old['far_other']['raw_L1_sum']:.6f}/{new['far_other']['raw_L1_sum']:.6f} | {old['far_background']['raw_L1_sum']:.6f}/{new['far_background']['raw_L1_sum']:.6f} | {matched['far_other']['raw_L1_sum']+matched['far_background']['raw_L1_sum']:.6f} | {r['far_readback']['new_far_sum']:.6f} |")
        ink=r['ink'];change=r['changes']['raw']['target_full']
        effects.append(f"| {r['view']} | {ink['weighted_raw']['target_full']['raw_L1_sum']:.3f}/{ink['saturated_raw']['target_full']['raw_L1_sum']:.3f}/{ink['saturated_matched']['target_full']['raw_L1_sum']:.3f} | {change['raw_L1_mean']:.6f}/{change['raw_L1_sum']:.3f} | {change['useful_fraction_0_05']*100:.2f}% |")
    worst=max(r['far_readback']['max_new_raw_L1'] for r in s['records']);pixels=sum(r['far_readback']['new_visible_pixels'] for r in s['records'])
    dt=datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-23T11:43:42.993363+00:00')
    minutes=dt.total_seconds()/60
    nxt=visual['next_step'];why=visual['next_why']
    report=f'''# Unit009：同一原行许可满强度纸底，容量增加但整体优势未建立

**冻结实验完成。相同41058个原Gaussian行的满强度替换减少照片残留；同源编辑预算下结果混合，远区绝对损伤增加，完整物体的排线形体与干净度优势仍未建立。不升级默认，scientific_seal=false。**

本轮唯一主变量是纸底强度映射：旧unit008.completed_strength对同一非零集合的strength=1。作者目标2121面、375条stroke/2004段、21006行墨责任及其原权重、195279个UNKNOWN、全部可见性和unit008.new_raw_alpha固定。原310475行身份、顺序、中心、协方差、opacity、完整SH和原PLY不变；满强度是渲染时完整SH求值后的颜色副本，不写源模型。20052个仅获外观许可的UNKNOWN行原已为1，本轮不增加任何核或标签。

协议SHA256 `{sha(UNIT/'PROTOCOL.json')}`。50份输入以及协议、源码、相机均在分解与渲染前冻结；DEV结果没有用于修改规则。四BUILD用于一次全局源RGB效果配平，四DEV和九后侧短弧均已曝光。

## 有符号残留与支持集端点

在每个保存trace采样点，以白背景和纸色p=(.95,.95,.95)重建：旧纸底-p = 已许可原行的w(1-s)(RGB-p) + 未许可原行的w(RGB-p) + 剩余透射(1-p)。满强度仅移除第一项。各项先按RGB向量相加，再取L1；各分量范数不能相加当作损伤归因。颜色可超过纸色，饱和不是任意RGB的最优残留下界，取消项已由小夹具检验。

四DEV目标像素均完整包含在trace内，目标外仅稀疏采样。因此分解只用于目标解释，远区指标来自实际完整GS渲染。弱241°/24°内部三项的平均分量L1约0.096547、0.175082、0.000069；向量合成后的旧/饱和残留为0.271514/0.175053，并与实际完整GS结果相符。剩余照片残留主要来自未许可原行；这只描述当前固定支持集，不是否定所有原GS局部外观控制。

## 实际完整物体结果

{visual['observation_chinese']}

表中残留为clipped纸底RGB到固定纸色的L1；同预算旧臂系数为1，所以配平旧值等于自然旧值。墨覆盖采用固定alpha>0.05，所有臂严格相同。

| DEV视角 | 全目标/内部像素 | 内部残留旧自然/饱和自然/饱和配平 | 自然残留下降 | 固定目标墨覆盖 |
|---|---:|---:|---:|---:|
{chr(10).join(lines)}

四视角自然强度残留均下降，但配平后的两个前侧内部残留升高，两个后侧仅小幅下降；不支持稳定的同预算优势。纸底平均残留与源编辑量存在耦合，不能仅凭该指标选默认。所有完整/腐蚀目标、边界、远其他部件和背景的mean/sum/可见变化已保存。

四BUILD自然完整源编辑raw RGB L1：旧{b['natural_source_L1']['weighted']:.6f}，饱和{b['natural_source_L1']['saturated']:.6f}，增加{(b['natural_source_L1']['saturated']/b['natural_source_L1']['weighted']-1)*100:.3f}%。公共预算{b['budget']:.6f}；旧/饱和全局系数{b['scales']['weighted']:.10f}/{b['scales']['saturated']:.10f}，实际完整GS重渲染配平，无DEV或逐帧拟合。源效果配平不等于DEV逐视角相等，也不等于墨RGB预算配平。墨alpha固定，纸底变白引起的实际墨对比度变化如下。

| DEV视角 | 目标墨RGB L1旧/饱和自然/饱和配平 | 自然两臂目标混合图差mean/sum | 目标差L1≥.05比例 |
|---|---:|---:|---:|
{chr(10).join(effects)}

## 远区代价与短弧

| DEV视角 | 远其他L1旧/饱和自然 | 背景L1旧/饱和自然 | 饱和配平远区合计 | 自然两臂远区图像差L1 |
|---|---:|---:|---:|---:|
{chr(10).join(damages)}

自然强度四DEV的远其他部件与背景绝对损伤均增加。13条记录的最大新增远区单像素raw L1={worst:.8f}，超过1/255的远区像素计数合计{pixels}；重复相机不作为独立样本。原固定2px带、目标掩码和背景分类没有扩张或重画。最终源差与两臂之间图像差分别报告，避免颜色抵消或分母变化造成错误解释。

九帧为231°–251°、仰角24°、距离5.3的真实相机短弧；使用同一3D路径与逐相机冻结墨alpha。全部帧实际解码并与PNG逐像素一致。前侧新增面在此轨迹不可见，不能认证其旋转稳定性。4DEV+9arc为12个不同相机配置，全部已曝光；无独立语义、几何或时序真值。

## 验证与失败保留

三项针对性测试验证同支持集与输入范围、RGB抵消和背景分解、真实非连续原行的满强度及零编辑控制。预期缺模块RED rc1保留。首次真实夹具读错相机元数据位置，tdd_green_001 rc1；在冻结前只修正从CAMERAS.json读取，tdd_green_002三项通过。

四BUILD及13DEV/arc的旧纸底/混合图逐值恢复unit008自然结果。独立审计核对50份输入、完整原行、同许可集合、M1/UNKNOWN、固定墨alpha和原行责任；从完整已接受alpha×T trace与完整SH重建四种纸底，读回全部预算及区域指标。弱角度独立冷重放实际执行6次完整GS：原源/责任、四种纸底、全零许可；四混合结果一致，零墨等于纸底，全部许可置零等于原GS。CPU replica不是原生CUDA认证。

arc_3_001启动命令误拼Python目录，外层rc1，子进程未启动、无科学输出；包装器未生成退出回执，原start JSON及空log保留，原因见ENGINEERING_FAILURES.json。新名称arc_3_002正确启动并完成rc0，未修改冻结源码、协议或参数。其余科学阶段均完成rc0。旧v05的8.044%远区失败、4.49%作者区域变化，以及v06单位001–008负结果和中断全部保留。

交付是原GS颜色替换纸底与原ID关联代理墨层，不是原生Gaussian排线或H1/H2/H3证明。相对v05稀疏路径任务，区域操作范围早已显式改变，本轮不能倒算旧门槛成功。实际源码、SOURCE_LINK、独立纸底/墨层/混合图、原始数组与可冷重放入口随单元保存；原PLY、本地Python及历史锁定输入仍为外部依赖。

## 下一步

NEXT=continue：{nxt}

理由：{why}

本轮执行约{minutes:.2f}分钟；只完成unit009，未执行下一科学单元。后续仍须新的A阶段审查及父级授权，并遵守21:20不启动新单元、21:45科学收尾。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    py='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
    (UNIT/'README_ZH.md').write_text(f'''# Unit009：固定原行支持集的纸底满强度对照

结果：自然强度减少照片残留，但同预算结果混合、远区代价增加，完整NPR优势未建立。默认未升级，全部失败保留。

- [报告](REPORT_ZH.md)
- [自然强度完整物体](ALL_DEV_VIEWS.png)
- [同源编辑预算](ALL_DEV_MATCHED.png)
- [全部短弧帧](ALL_ARC_FRAMES.png)
- [视频](media/same_support_saturation_arc_ffv1.mkv)
- [原行连接](asset/SOURCE_LINK.npz)

冷重放（6次完整GS，输出目录必须不存在；不会改原PLY或旧结果）：

```bash
V06_UNIT_DIR={UNIT} CUDA_VISIBLE_DEVICES='' {py} -B {UNIT}/source_snapshot/audit_saturation_unit.py replay --out {UNIT}/replay_user_001
```

使用冻结source_snapshot内runtime，串行CPU最多2核，无GPU。unit009/scratch已存在，编译临时文件与输出均在HDD。需要锁定的原PLY、本地Python及unit008缓存，详细路径见INPUT_LOCK.json；不是可独立移动包。新运行目录会拒绝覆盖。

SOURCE_LINK的source_index是原PLY行；代理stroke/face不是Gaussian ID。目标与路径引用见asset/REFERENCES.json，其哈希锁在INPUT_LOCK。FRAME中的alpha是固定原ID关联墨，所有条件相同；paper和hybrid分开保存。权重与强度的对照不重标UNKNOWN，不扩展许可集合。只在已曝光视角和有限后侧短弧验证。
''')
    progress=dict(actual_advance='Same41058 original-row permission endpoint rendered and signed residual decomposition verified; natural paper residual falls, matched-budget and whole-object benefit not established.',
        original_rows=310475,paper_rows_unchanged=41058,ink_rows_unchanged=21006,UNKNOWN_unchanged=195279,
        target_faces_unchanged=2121,strokes_unchanged=375,segments_unchanged=2004,
        weak_interior_residual_old=.27151363001741685,weak_interior_residual_saturated=.1750532347227987,
        weak_interior_residual_matched=.26217040566847327,visible_outcome=visual['observation_chinese'],representation=p['scope'])
    receipts=[]
    for f in sorted((UNIT/'logs').glob('*.receipt.json')):receipts.append(dict(name=f.name,**json.loads(f.read_text())))
    artifacts={n:str(UNIT/n) for n in ('REPORT_ZH.md','README_ZH.md','PROTOCOL.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json','SUMMARY.json','VALIDATION.json','decomposition/SUMMARY.json','ALL_DEV_VIEWS.png','ALL_DEV_MATCHED.png','ALL_ARC_FRAMES.png','MEDIA_VALIDATION.json','cold_replay_001/REPLAY_CHECK.json','asset/SOURCE_LINK.npz','VISUAL_REVIEW.json','ENGINEERING_FAILURES.json')}
    status=dict(execution_state='completed',stage='fixed_support_saturation_handoff',scientific_verdict=visual['scientific_verdict'],
        gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,variant_retained='diagnostic endpoint only',
        completed_utc=now(),elapsed_minutes=minutes,artifacts=artifacts,tests_and_actual_commands=receipts,
        blockers=[],next_action='continue',parent_monitor_verification='pending',
        preserved_failures=json.loads((UNIT/'ENGINEERING_FAILURES.json').read_text())['failures'])
    js(UNIT/'STATUS.json',status);js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=nxt,why=why,
        preserve='All old scientific negatives, targets, source rows and interruptions remain immutable; next stage requires fresh review.'))
    backup=UNIT/'delivery_previous';backup.mkdir(exist_ok=False);backups={}
    for name in ('DELIVERY_STATUS.json','DEMO_README_ZH.md'):
        f=OUTPUT_ROOT/name
        if f.exists():shutil.copy2(f,backup/name);backups[name]=sha(f)
    js(UNIT/'DELIVERY_PREVIOUS_LOCK.json',dict(files=backups))
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(latest_unit=str(UNIT),execution_state='completed',scientific_verdict=status['scientific_verdict'],
        gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,variant_retained='diagnostic endpoint only',
        readme=str(UNIT/'README_ZH.md'),report=str(UNIT/'REPORT_ZH.md'),next_action='continue',old_delivery_backup=str(backup),parent_monitor_verification='pending',utc=now()))
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text('''# v06：最新unit009固定支持集纸底端点结果

同一41058个原行满强度替换减少照片残留，但同预算结果混合、远区代价增加，完整NPR优势未建立。默认未升级，旧失败保留。

- [报告](units/unit_009/REPORT_ZH.md)
- [完整自然视角](units/unit_009/ALL_DEV_VIEWS.png)
- [同预算视角](units/unit_009/ALL_DEV_MATCHED.png)
- [数据与冷重放命令](units/unit_009/README_ZH.md)

这是原GS纸底加原ID关联代理墨，不是原生Gaussian排线；与v05稀疏路径任务范围不同，不能倒算旧门槛通过。unit008可见前侧补选变体仍保留；前版交付说明备份在unit009/delivery_previous。
''')
    hand=UNIT/'handoff_source';hand.mkdir(exist_ok=False);shutil.copy2(Path(__file__),hand/Path(__file__).name)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={Path(__file__).name:sha(Path(__file__))}))
    print('HANDOFF completed, no default promotion, NEXT continue',minutes,'minutes',flush=True)

if __name__=='__main__':main()
