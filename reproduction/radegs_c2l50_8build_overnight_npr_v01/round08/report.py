from env import *
def main():
 tests=(R/'logs/12_regression.txt').read_text();assert 'Ran 20 tests' in tests and tests.rstrip().endswith('OK')
 js(R/'TEST_RESULTS.json',dict(new_tests_passed=20,groups=dict(features=8,protocol=8,audit=4),red_logs=['logs/01_features_RED.txt','logs/03_protocol_RED.txt','logs/07_audit_RED.txt'],green_logs=['logs/02_features_GREEN.txt','logs/04_protocol_GREEN.txt','logs/08_audit_GREEN.txt','logs/12_regression.txt'],red_scope='3 vertical API/module missing failures then minimal implementation GREEN; not 20 independent red executions',inherited_tests_counted_as_new=0,tolerance_relaxed=False))
 gates=dict(overall='PARTIAL',precise_partition='NO_GO',engineering='GO',scenes=dict(scan24=dict(state='NO_GO',A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',why='Gray roof/platform/background still one class; brighter color separation is not subject recovery.'),scan65=dict(state='PARTIAL',A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',why='Visible dark cranial coverage improves, but teeth/cheek/table still mix in 0036; no certified subject.'),ficus=dict(state='NO_GO',A='INHERITED_GO_PROXY',B='NO_GO',C='NOT_RUN',D='NOT_RUN',why='Pot class absent in all four views, trunk mostly UNKNOWN, no mutual qualified pair.')))
 js(R/'STAGE_GATES.json',gates)
 seen=['figures/ficus/train_r_80/FULL.jpg','figures/scan24/0000/FULL.jpg','figures/scan65/0000/FULL.jpg','figures/scan24/0036/FULL.jpg','figures/scan65/0036/FULL.jpg','figures/ficus/test_r_14/FULL.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ficus_FOUR_VIEWS.jpg']
 js(R/'VISUAL_AUDIT.json',dict(actual_image_tool_inspection=True,files={n:sha(R/n) for n in seen},native_dimensions=dict(scan24=[777,581],scan65=[777,581],ficus=[800,800]),overview_padding_only=True,post_result_crops_not_algorithm_masks=True,judgement=gates))
 nxt='检验局部RGB纹理的方向/尺度布局是否提供单像素颜色缺失的材料证据：固定小patch梯度结构张量/方向能量，比较保留RGB原强对照与同patch颜色多重集但空间打乱的null。沿用原proxy seeds和历史相机，不调颜色门，不恢复错误硬seed，不把纹理类当物理部件。先解析同色直条纹/交织与真实Ficus盆横纹、纵干、叶群小pilot；若无独立增益则停止该机制。此方向本轮未运行，下一轮必须另冻配置及资格。'
 js(R/'NEXT_REVIEW.json',dict(next_hypothesis=nxt,next_allowed=True,not_executed=True,distinct_from=['r03 per-pixel RGB density','r04/05 graph propagation and seed constraints','r06 binary negative-space morphology','r07 source SH angle counterfactual','r08 scalar-intensity quotient'],risk='Screen texture viewpoint dependent, false line/leaf holes; cannot bypass A/B gates.',latest_start_JST='07:40',deadline_JST='08:00'))
 (R/'REPORT_ZH.md').write_text('''# r08：明暗归一化有局部作用，但不能代替结构身份

本轮实际完成三场景、四个冻结视角、四臂，共12个密度模型、48幅原尺寸分类数据及15组Ficus双向区域资格检查。总体记 **PARTIAL（局部机制观察）**；作为可用于多风格NPR的精确分块方案仍 **NO_GO**。头骨阴影区域有可见改善，建筑主体门仍失败，Ficus盆/干分类明显退化。没有新GS模型、源核标签或NPR演示；原C8/joint完全保留。

## 为什么换这个机制
r07真实SH反事实证明了颜色的视角项会影响判断：DC减少Ficus盆高光被判木，但并不能得到完整盆—干—冠。本轮进一步检验的是**像素整体明暗**，不是再删SH、换K、改平滑、增加图传播或调seed。输入回到原封存source RGB，保持原几何、相机、mask及代理seed不变。执行前已写METHOD_FREEZE_ZH/CONFIG并记录源码SHA，reserved只在模型和BUILD图审后一次运行。

令x=(R,G,B)，c=x/(R+G+B)。对正标量a，资格不变时c(ax)=c(x)。这只是一条代数性质，不是恢复albedo，也不保证输入RGB为线性辐射。加性高光、彩色照明、透明混合不满足这一简化。尤其不同亮度的灰材质都变成(1/3,1/3,1/3)，因此屋顶、地台等可能变得更难区分。该反例在真实运行前已测试/冻结。

## 四臂如何隔离变量
1. raw_rgb：严格重放r03原RGB likelihood，同UV、类别、每view/class质量及原mask。
2. rgb_floor：仅增加与主臂相同的资格门，RGB特征不变。
3. chromaticity：同资格门，加c(x)变换。
4. shuffled_chromaticity：每BUILD内对合格seed特征做固定1729排列，保持原UV/labels、类别数量及整体特征多重集，目标像素仍用真实c(x)。这是破坏关联的null。

资格统一为finite、通道非负、最大通道>=.02；无scene特调。低值全部UNKNOWN，mask不删，不填背景。该数是数值稳定代理，不是测得的相机噪声。分类器仍是16³直方图、.75bin平滑、每类自身5%密度门、posterior>=.65、margin>=.2，无新graph/语义网络。特征压到二维单纯形后仍使用同16³网格和平滑，这是本轮固定实现的重要限制：失败否定这一**特定描述子+估计器**，不证明所有亮度不变量方法不可用，也不证明所有明暗变化都无影响。

三新臂的seed预算与资格相同；原RGB与floor在10/12幅图的最终labels完全相同。scan24/0036另有7817像素、Ficus/test_r_79有3像素由已知转UNKNOWN，须归因于资格门，不能算chroma特征收益。因此建筑0036的黑背景变化包含floor作用；Ficus盆/干大范围退化与头骨阴影变化则需与同floor臂比较，不能由raw直接归因。COUNTS同时记录relative_to_same_floor。恢复核查时发现并更正了未封存草稿的“12幅一致”错误，原草稿与CORRECTION_RECEIPT保留，科学数组和冻结参数不变。raw全部3模型、12幅labels/probability/density/UV/mask均逐数组重放r03，避免换基线。

## 输入条件与视角
scan24/65为原native RaDe RGB/alpha/camera-z，777×581、fx/fy不等；Ficus为vanilla3DGS+CPU条件平面深度代理，800×800。世界单位非米。DEV/AUX分别0000/0024和train_r_80/train_r_7；reserved为0012/0036和test_r_14/test_r_79。全历史曝光，DTU为source GS训练视角，不是blind或GS-heldout。本轮每个目标视角使用自己的原RGB推断，不是纯从DEV标签无图像迁移。

DTU两类沿用外围水平/中心非水平的旧代理seed，不能叫前景GT，更不能把两色当屋顶/墙或颅/颌物理部件。Ficus三类盆/木/冠亦是原粗几何代理，不是人工GT。source索引与line parent不同，C8线不参与此次颜色分类。图中原C8 xray和true joint来自封存CPU fullSH/EWA参考，明确为只读context；本轮未重新渲染它们，未把2D着色当joint GS修改。

## 三场景实图结论
**scan24：A NO_GO。** 明暗归一化使屋顶和红砖外观更整齐，并使0036部分黑背景由错误橙类转UNKNOWN；这是可观察的小变化。但灰屋顶、白地台、窗框仍归同一蓝类。主体与背景身份根本未解决。0024/0012也如此。蓝色多不代表真实屋面被识别。B/C/D均NOT_RUN。

**scan65：局部PARTIAL，A仍NO_GO。** 0000/0012及0036暗颅侧较原RGB被保留，0036颅顶和部分下颌可见连续性改善。全有效场景UNKNOWN由176343降至80707，但新增已知包含大量桌面，不是“恢复95636骨骼像素”，不能当准确率。0036牙列、颧部/眼窝、骨与桌面接触边仍混杂；0024/0012细牙仍不可靠，部分黑背景又出现橙块。r05图传播在部分图更连贯，也会填错洞。没有证据授权颅/面颌正式部件分组。B/C/D均NOT_RUN。

**Ficus：B NO_GO且明显退化。** 四图盆类像素全为0；主干只剩395/634/177/13个木类像素，整盆及大部分主干转UNKNOWN，叶冠也大块不确定。train80主体UNKNOWN由15998/75408增到62367/75408；test14由16514/69003增到62804/69003；test79由14647/79309增到64849/79309。原mask和叶间负空间并未删除，但这些UNKNOWN不能驱动可靠风格。原RGB/r05和r07DC在盆/干完整性上更好。不能把弱彩色线条减少说成干净分区。

## 可解释负结果与跨视角
Ficus训练代理类的归一密度重叠量Σmin(h_i,h_j)：盆/木由0.04561升至0.75888，盆/冠0.06331升至0.43658，木/冠0.26146升至0.43356。这个数是冻结估计器上的分布重叠，不是GT混淆率。亮度信息既是潜在干扰，也携带区分盆/枝的信号；统一去掉导致后验缺少足够margin。DTU代理两类重叠也升高（建筑.1200→.1918；头骨.1786→.3255），同时局部阴影骨像素可以更完整，说明聚合重叠不能替代全图判读。

Ficus使用完全不变的2p深度/1.5px循环/3p世界资格，遮挡不负票。raw及floor DEV→AUX/test14/test79分别1/2/2个互配，chroma与shuffled都0/0/0；r05为2/2/2。原互配仍仅木/冠，没有认证盆，不能把原强基线包装成精确成功。null全图UNKNOWN说明随机破坏关联无法提供类别证据，但“优于null”不足以使主方法成功。无新source-ID软成员，无物理primitive。

## 真实检查与交付
20项新测试通过，分features8/protocol8/audit4；三次RED是各垂直API缺实现失败，随后最小实现GREEN，非20项各独立RED。无容差放宽，灰材质/高光反例保留。独立只读verify重拟12模型、重算48预测和15匹配；原RGB exact检查另列。继承source渲染/all-N工程校准未冒充本轮新执行；此次不改renderer且不生成source责任，因此没有新增全N责任实验。

完整图在figures/<scene>/<view>/FULL.jpg，CONTEXT.jpg为原C8/true joint及r07DC；Ficus另有v02强RGB-only图。delivery包含三场景FOUR_VIEWS、全局OVERVIEW和坏例ROI。图块保持原像素尺度，跨scene总览仅加白边，固定gain；ROI是结果后解释，未作为算法mask。所有预测NPZ保留标签、概率、密度、UNKNOWN、资格及source_uv（图像坐标而非GS ID），所有原候选范围可追溯。没有修改source几何/fullSH/filter/+Inf、线核或旧工作树。

本轮建议不替换原C8/joint，不将chroma直接投入Ficus分块。保留头骨暗区局部收益作为机制证据。下一轮若仍有时间，可另冻结“局部纹理空间布局”而不是再换颜色阈值：横纹盆、纵干和交织叶群在同色统计下可能有不同局部方向结构。需要同patch颜色多重集但打乱布局的null、尺度/视角反例；它尚未执行，不保证语义成功。只允许runner下一次resume决定，本调用不启动r09。07:40开始收尾、08:00硬停止规则不变。
''')
 (R/'FORMAT_ZH.md').write_text('''# 数据格式与只读限制
models/<scene>/<arm>/MODEL.npz: hist[K,16,16,16] float64、threshold[K]、classes；SEEDS含原UV/labels/raw_rgb，eligible[N]，合格features/labels及排列索引。shuffled的permutation作用在合格feature行上，UV与label不换。
inference/<scene>/<arm>/<view>/RESULT.npz: labels[H,W] uint8（0拒绝）；unknown bool；probability/density[H,W,K]；inference_mask/feature_eligible；source_uv[N,2]整数像素xy。source_uv不是原GS source_index，不生成原核语义标签。outside mask labels0，unknown保留原上层未知。
Ficus labels1/2/3为pot/wood/crown proxy；DTU1/2为peripheral-horizontal/central-nonhorizontal prior，非foreground GT。固定原图gain，不修改SH或source模型；颜色覆盖仅诊断显示。
evaluation保存逐点uv/target_uv/state/target_label，state0未知、1几何可比较、2遮挡、3画外、4前方不合、5循环失败（见geometry.py），不可把occlusion当反票。
SEAL.json与RESULTS_MANIFEST采用{members:{relative:{sha256}}}。runtime AGENT_LAUNCH/ASTRA_RUNTIME_FINAL不封存。verify --readonly --replay不改封存结果；只读旧依赖路径见SOURCE_MANIFEST。包不含原GS或旧环境。
''')
 (CODE/'README.md').write_text('''# Round 08 scalar-intensity quotient
Run only after METHOD_FREEZE: `experiment.py --phase pilot`, then fit, review, reserved. New r08 only; original RGB and C8/source read-only. `verify.py --readonly --replay` checks all models, predictions, matches, exact r03 baseline, hashes and old worktrees. Use existing official_code_fix_v01/env/bin/python -B. No GPU/network/new models. No export of styled GS or labels as physical primitives. See output REPORT_ZH and METHOD_FREEZE_ZH. Do not rerun freeze or overwrite sealed units.
''')
 cmds=['freeze.py','test_features.py (RED before features.py; GREEN after)','test_protocol.py (RED before protocol.py; GREEN after)','experiment.py --phase pilot','experiment.py --phase fit','test_audit.py (RED before audit_metrics.py; GREEN after)','experiment.py --phase reserved','evaluation.py','delivery.py','python -B -m unittest discover -s round08 -p test_*.py -v','verify.py --readonly --replay','report.py','local commit new round08 only','finish.py (after clean commit; receipt outside r08)']
 (R/'RUN_COMMANDS.md').write_text('# Actual command ledger\n\nInterpreter: `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B`\n\nCode: `reproduction/radegs_c2l50_8build_overnight_npr_v01/round08`\n\n'+ '\n'.join('- '+x for x in cmds)+'\n\nExact outcomes and RED/GREEN in logs/. No package installation, GPU, training or source rendering this round. verify is readonly; prerequisite caches and old worktree locations are in SOURCE_MANIFEST.json.\n')
 review('04_visual_delivery_GO','已用image tool实看三DEV、三困难reserved和三FOUR_VIEWS全部12图。允许交付证伪成果：Ficus NO_GO、建筑A NO_GO、头骨局部PARTIAL但A仍NO_GO；不向C/D/NPR推进。20测试和12/48/15 replay须完成才封存；所有负例保留。',[R/'delivery/scan24_FOUR_VIEWS.jpg',R/'delivery/scan65_FOUR_VIEWS.jpg',R/'delivery/ficus_FOUR_VIEWS.jpg',R/'STAGE_GATES.json'])
if __name__=='__main__':main()
