"""Report actual frozen elevation results without promoting a default arm."""
import runtime
from runtime import ROOT as UNIT,js,sha
import json,datetime

def main():
    n=json.loads((UNIT/'REPORT_NUMBERS.json').read_text());audit=json.loads((UNIT/'READBACK.json').read_text())
    replay=json.loads((UNIT/'replay/REPRO_006_A/REPLAY_CHECK.json').read_text())
    s=n['temporal']['natural'];matched=n['temporal']['matched']
    report='''# Unit004：条件性 H1 在高仰角过渡中的实际对照

**15个科学相机、13帧连续抬高轨迹及双向评价完成；科学结论PARTIAL。** 原U三维路径在本次过渡中保留条件性时序优势，24个有向相邻对的共同像素误差和union归一化误差均低于冻结二维B0。但共同可见支持减少、两臂覆盖和生成方式不同，B1自身也有缺墨；没有证明纯锚定因果优势、整物体质量赢家或Gaussian特有贡献。

[整物体关键帧](media/KEYFRAMES.png) · [全部自然帧](media/natural_ALL_FRAMES.png) · [独立墨层](media/WHOLE_LAYERS.png) · [自然影片](media/natural_orbit.png) · [BUILD匹配影片](media/matched_orbit.png) · [复现](REPRODUCE.md)

## 实际整图与冻结条件

已目视检查自然/匹配关键帧、全部13帧自然联系图、独立结构与排线层，以及BUILD、006、009至012原尺寸对照。中段二维背部排线较稀且碎，三维仍保留较长的笔触；高角两者均挤成细窄带。整椅、扶手和座面仍可辨，但开放左返回、扁平内框、背下孔洞、座背空白及高后侧结构零合成增量保持。传统代理表达相同主要形体。没有独立感知偏好试验或真人播放器认证。

父级DECISION原样保留。B0直接采用unit002修复边缘种子遗漏后的screen_hatch.py和原RAW_FIELD/CONFIG/BUILD_MATCH，生成器字节保持，不重算BUILD标定。它使用投影原方向场、冻结部件位置/朝向锚点、固定相位与像素间距/长度，在每个合法掩码/深度连续片段内放种子，0.5px中点积分，.035深度断层停止；没有每帧随机重置或人工修线。unit002最初中心在外就漏画的失败仍保存，未作为主基线。

B1是原U，未应用H2的S/D。原256690行及顺序、geometry/covariance/opacity/fullSH、UNKNOWN170281、27873行座面责任、网格/粗标签、原路径、169段结构ON、全局.95纸底、非目标区域、1px/AA2/.004可见性容差保持。两臂仍有种子、积分和像素尺度/透视压缩差异，因此只是标签条件的两个生成系统比较，不能归为纯坐标锚定、自动二维/三维分割或最佳二维NPR比较。

轨迹000–012固定方位241°，仰角24°至60°每3°一帧；另BUILD151°/36°、BACK196°/36°，距离5.1、384×384。全部相机已在旧输出曝光，未称留出或训练未见。15个相机使用逐值冻结的unit003同相机source/paper/S缓存；每帧重新求native与AA首交、生成B0并光栅化两臂。主实验没有冒称15次冷GS重算。所有相机B1恢复unit003自然U；BUILD/BACK/000/012两臂两模式还逐数组恢复unit002对应结果。

自然强度与固定BUILD匹配均保存。因子B0=0.9476143419888103、B1=0.9999999701831257，直接继承，目标BUILD作用量约758.252；不逐帧重匹配。必要内部沿用H1固定2px腐蚀，不扣H2引导带；因此不直接混用unit003的必要覆盖数值。

## 实际墨量与必要覆盖

| 帧/仰角 | 自然RGB作用 B0/B1 | 匹配RGB作用 B0/B1 | 必要覆盖 B0/B1 | 内部像素 |
| --- | ---: | ---: | ---: | ---: |
'''
    for key in ('BUILD','000','003','006','009','012'):
        r=n['frames'][key];e=r['rgb_effect'];c=r['necessary_coverage']
        report+=f"| {key}/{r['camera'][1]} | {e['natural']['B0']:.3f}/{e['natural']['B1']:.3f} | {e['matched']['B0']:.3f}/{e['matched']['B1']:.3f} | {c['B0']:.3%}/{c['B1']:.3%} | {r['necessary_pixels']} |\n"
    report+='''
等BUILD预算并不等于等DEV墨量/覆盖。二维屏幕路径条数随裁断变化，不是持久三维ID数；006有38段输出路径、58次端点深度断层停止，009有40段、77次停止。没有为改善高角表现调整间距、相位或深度阈值；二维更碎/少画本身也不是更干净的证据。

## 双向实际输出时序与分母

双方共用exact-native首交深度/标签对应和.004容差，双线性深度不跨无效孔洞。两种方法各自的中心线以不超过0.5px采样，检查源帧实际自身AA墨、共同首交和目标实际自身墨；B1额外按真实线段深度排除隐藏投影。不是只检查存储坐标，也不只在B1锚点取样。没有LOD、计划裁剪或明暗切换。

| 24个方向对累计（自然） | B0二维 | B1三维 |
| --- | ---: | ---: |
'''
    for label,key in [('每共同像素墨L1','L1_per_common_pixel'),('逐对平均union归一化L1','mean_pair_union_normalized_L1'),('共同可见且源有墨中心线长度px','common_centerline_length_px'),('至目标实际自身墨距离px','centerline_to_actual_ink_mean_px'),('共同长度中目标无墨px','common_centerline_without_destination_ink_length_px'),('源代理可见长度px','source_visible_length_px'),('源代理可见却无自身墨px','source_visible_without_own_ink_length_px')]:
        report+=f"| {label} | {s['B0'][key]:.6f} | {s['B1'][key]:.6f} |\n"
    report+=f'''
共同像素为{n['common_pixel_observations']}/{n['source_target_pixel_observations']}（{n['common_fraction']:.3%}），两臂逐对使用相同像素分母；中心线分母则不同。BUILD匹配的每共同像素误差为{matched['B0']['L1_per_common_pixel']:.6f}/{matched['B1']['L1_per_common_pixel']:.6f}。24/24方向对的自然像素L1和union误差都偏向B1，故本次没有观察到该时序指标的反转；这仍不等于等覆盖质量胜利。旧方位轨迹的采样步长/运动方向不同，不能用跨轨迹原始数值比例给性能退化归因。

自然强度的墨→空为1600/6137与31/8609像素观测。B0/B1共同中心线无目标墨的累计长度分别1764.313/39.388px；源代理可见却无自身墨为1.000/71.487px，B1该失败不能被较小warp误差覆盖。源有墨条件会排除这些缺墨，故必须同时报告。最近自身墨可能来自相邻笔触，中心线距离并非逐ID对应精度；二维路径可能重叠，长度不等于去重墨面积。

自身墨仍在而合成增量跌落的像素观测为37/38；源自身有墨但合成增量不足为194/443。它们和自身缺墨、代理遮挡拒绝分开记录，不能统称笔触消失。相邻方向对/像素不是独立物体样本；代理首交不是独立物理真值，未作显著性或无闪烁认证。

## FAR反例与原Gaussian来源

15相机所有臂/模式相对原彩色GS的远其他绝对L1范围{n['far_absolute_ranges']['far_other'][0]:.3f}–{n['far_absolute_ranges']['far_other'][1]:.3f}，远背景{n['far_absolute_ranges']['far_background'][0]:.3f}–{n['far_absolute_ranges']['far_background'][1]:.3f}；包含全局纸底和有意的其他区域墨，不能用方法差分抵消。

006=241°/42°，固定输出区域图将像素(157,185)记为region4。B1上背自身墨为0.1125，B0为0；自然/匹配B0相对自然U的FAR-other差分L1均为0.310501635。该点相对原彩色GS的绝对L1为B0 0.221492、B1 0.384027，因此这是去掉既有亚像素足迹的非零差异，并非新增远区损伤的证明。没有扩大掩码、改图或把非零门槛重标为通过；其余FAR增量为0也不是独立语义零泄漏认证。见FAR_OBSERVATIONS和REPORT_NUMBERS。

{audit['accepted_trace_events']}个继承的原行接受事件按原source_index重建fullSH RGB与座面S，最大误差{audit['full_SH_RGB_max_error']:.4g}/{audit['S_max_error']:.4g}，T链最大误差{audit['T_chain_max_error']:.4g}。它们是缓存来源核验，不冒充新增接受事件采集。006另从原PLY真实冷重算source/paper/S，三者逐值恢复缓存；954个新采样接受事件核验通过。随后同一新进程从保存配置生成B0并光栅化两臂，9份数组文件逐值恢复科学结果。

上背和结构仍proxy-only；没有新增路径Gaussian所有权、独立语义/物理真值或native CUDA逐ID一致性证据。传统3D参考确实使用原座面墨，不乘S，5个检查相机经独立代理AA重渲染核对。

## 实际验证、历史失败与后续

实际TDD：001因缺elevation模块RED rc1，002八项GREEN rc0，覆盖相机身份/缓存形状/非有限拒绝、旧输出与DECISION写保护、二维确定性/无向方向、掩码与分离片停止、真实遮挡对应和中心在外合法片段。15相机135张策略/传统PNG逐值对应数组，自然/匹配APNG各13帧全部解码且逐值等于整图面板。8fps只是播放速度，末尾回起点是播放重置，不是连续360°。

本轮实际科学渲染及分析、审计、冷重算命令均串行完成。READBACK记录写入时010审计自身回执尚未生成，保留该原快照；FINAL_READBACK另核对实际最终rc0，不将历史UNKNOWN改写为成功。旧unit003的143/UNKNOWN、错误零FAR审计、H2的S四视角覆盖损失、D36/37覆盖损失及匹配FAR非零，unit002最初二维遗漏和路径失败，v08墨跌落、调度重叠、孔洞等均保留原义。

本轮使用两核亲和、单数值线程、CUDA空，无GPU/训练/下载/安装/嵌套模型或push/merge。科学源码、协议、输入和父级决策锁保持；事后报告/复现代码另锁。工程核验不等于研究胜利，父级独立核验仍待完成。

H1本轮RUN且条件性；新的H2政策/第二物体NOT_RUN。unit001/003已完成的U/S/D/sham及PARTIAL不被本轮二臂结果替代，也不升级默认资产。

NEXT=continue：转入BRIEF要求的最终联合交付，整合现有H2三臂/sham、两条H1轨迹、真实命令、必要资产/来源清单和失败索引，写根级DEMO_README_ZH.md/DELIVERY_STATUS.json并核对入口依赖。沿用已完成冷核验，避免重复大归档、重复轨迹或参数扫描；这属于交付收尾，不伪装为新的科学单元。尚未冻结新的独立科学问题；任何新科学路线仍须先只读审查并在15:20前启用，15:45科学收尾、16:00硬停。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    reproduce='''# Unit004 本机复现

主实验为同相机GS缓存加真实两臂排线生成/光栅化；并已做一次原PLY冷核验。下面是实际执行通过的保存源码入口。再次使用时请换一个尚不存在的output-name，入口拒绝覆盖科学结果。

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_004/source/h1_elevation/replay_h1.py --reference-key 006 --output-name REPRO_006_B
```

实际已执行output-name=REPRO_006_A，logs/011_cold_replay006.json，replay/REPRO_006_A/REPLAY_CHECK.json。该命令从原PLY冷重算选定相机source/paper/S并逐值核对缓存，再用同值缓存重生成B0、渲染两臂；不是15相机全部冷重算。reference-key可为BUILD、BACK、000至012。禁止直接运行source/base中继承的旧producer CLI；只使用本单元新入口。

首次科学生产入口run_h1.py prepare冻结输入/源码/相机/协议；随后render --keys BUILD BACK、000 001 002 003、004 005 006 007、008 009 010、011 012。这些目录已经存在，不能原位覆盖。完整argv及真实rc见logs/003至008。analyze_h1.py产生24个有向相邻对；audit_h1.py读取实际数组核对PNG/影片/来源；summarize_h1.py只汇总，均已执行。

CONFIG.json、RAW_FIELD.npz、BUILD_MATCH.json来自unit002最终版本，B0生成器也按原科学锁核对；相机来自unit003精确相机，缓存路径/哈希记录在CAMERAS/IMPORT。inputs/assets/on与inputs/data/chair保留原PLY、标签、路径、结构及source_index责任配置。各帧保存B0_PATHS、CENTERLINES、COMMON、TRACE、两模式两臂FRAME及生成停止记录。源码副本source/h1_elevation、source/base及最终HANDOFF_SOURCE_LOCK，科学锁SOURCE_LOCK，输入锁INPUT_LOCK，父级决策/协议锁PROTOCOL_LOCK。

所有入口先限定两核亲和、单数值线程、CUDA空；输出guard限制unit004，编译/缓存/重放均在本单元HDD目录。依赖使用现有只读Python/Open3D/Pillow/SciPy，无安装或跨机器可移植认证。
'''
    (UNIT/'REPRODUCE.md').write_text(reproduce)
    next_step=dict(action='continue',recommended_next_step='Final integrated delivery of completed unit001/003 H2 U/S/D/sham and unit002/004 conditional H1: root DEMO_README_ZH.md and DELIVERY_STATUS.json, actual saved-source commands, required assets/source/weights/path/guide/config manifests, full-object media and immutable failure index. Check entry dependencies using existing cold-replay evidence; no new parameter scan or replay-only science unit.',why='The frozen elevation question is answered with scoped partial evidence. Required joint delivery is still an independent useful task before16:00; no new scientific hypothesis has been frozen. New science requires a separate read-only decision before15:20, wrap15:45.')
    js(UNIT/'NEXT.json',next_step)
    start=datetime.datetime.fromisoformat('2026-10-28T05:58:44.395843+00:00')
    status=dict(execution_state='completed',stage='15_camera_13_frame_H1_elevation_render_temporal_media_cold_check_and_saved_source_replay_complete',
        scientific_verdict='PARTIAL: B1 has lower actual warp L1 and union-normalized error in24/24 directed pairs; unequal coverage/generators,79.76% common support and nonzero B1 own-ink loss prevent pure-anchor or whole-object superiority. FAR nonzero footprint difference preserved.',
        gaussian_link_progress='Original256690 rows/order/geometry/covariance/opacity/fullSH,UNKNOWN170281 and seatS27873 unchanged.15 exact-camera GS caches;15930 inherited trace events reconstructed. One real originalPLY cold source/paper/S check at241/42 with954 new sampled events, exact cache and9-file hatch replay. Upper-back/structure proxy-only; no new ownership/nativeCUDA parity.',
        H1='RUN; conditional elevation robustness only',H2='No new policies in unit004; unit001/003 complete U/S/D/sham PARTIAL preserved',second_object='NOT_RUN',
        artifacts=['PROTOCOL.json','CONFIG.json','RAW_FIELD.npz','BUILD_MATCH.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json','TEMPORAL.json','SUMMARY_METRICS.json','REPORT_NUMBERS.json','FAR_OBSERVATIONS.json','READBACK.json','REPORT_ZH.md','REPRODUCE.md','media/KEYFRAMES.png','media/WHOLE_LAYERS.png','media/natural_orbit.png','media/matched_orbit.png','replay/REPRO_006_A/REPLAY_CHECK.json'],
        commands_tests=[str(p.relative_to(UNIT)) for p in sorted((UNIT/'logs').glob('*.json')) if '.start.' not in p.name],blockers=[],
        preserved_failures=['B1 source-visible own-ink missing71.4868px accumulated;B0 1.0px','unequal coverage/common support79.76%','006 FAR-other difference0.310501635 from absent existing U footprint','all unit001/002/003 and v08 failures remain'],
        decision_sha256=sha(UNIT/'DECISION.json'),parent_verification='pending independent parent read',scientific_seal=False,
        resources=dict(affinity=sorted(runtime.os.sched_getaffinity(0)),numerical_threads=1,CUDA_VISIBLE_DEVICES='',serial=True),
        elapsed_minutes=(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()/60,completed_utc=runtime.now(),next='continue')
    js(UNIT/'STATUS.json',status)
    print(json.dumps(dict(state=status['execution_state'],verdict=status['scientific_verdict'],elapsed_minutes=status['elapsed_minutes'],next=next_step)),flush=True)

if __name__=='__main__':main()
