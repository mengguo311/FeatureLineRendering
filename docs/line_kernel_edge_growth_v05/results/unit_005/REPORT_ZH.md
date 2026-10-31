# unit_005：ficus 第二轮拓扑合并

交付完成，科学结论 **PARTIAL**。Parent 实际数值子进程 returncode=0、reason=null，运行于 07:13:34–07:16:14 JST；runner 报告约160.05秒。已保存并冷载完整285956行 M3 membership、有限载体、支持区间、版本谱系、候选/拒绝记录和双相机原始核全景。不是内存进度或 launcher 返回值。分析阶段没有拟合、重跑、渲染、测试、参数调整或源码修改。

本单元从 unit002 封存的 ficus M2 恢复，只执行一轮 M3；没有初始化或池化。沿用全部冻结参数，辅助载体的 many-to-one 支持与 degree-two 拓扑分离。原核位置、协方差、宽度、不透明度、数量和顺序保持不变。所有有效 UNKNOWN 仍可候选；无效源保持 UNKNOWN，失败旧载体保留分配并冻结。scan24、scan65、M4 在本单元 NOT_RUN；不覆盖旧单元的已保存结果，v04 仍为历史 PARTIAL。

| ficus 阶段 | 已分配核 | UNKNOWN | 主组数 |
|---|---:|---:|---:|
| 强v03/L0 | 95951 | 190005 | 3318 |
| L1 两次 containment pooling | 106399 | 179557 | 3289 |
| M2 一轮拓扑 | 109052 | 176904 | 3243 |
| M3 两轮累计 | 112533 | 173423 | 3281 |

M3 比 M2 增加3481个已分配核，覆盖率39.35%。组数增加包含 dormant 载体激活，既不是更大边的证明，也不能仅凭此判为失败。本轮25884次拟合，未耗尽30000预算；4402个 accepted events 包含未激活的载体，不能当作4402个新主边。候选仍受截断：candidate_cap44772、sample_query_saturated41299；因此“未耗尽fit预算”不等于搜索完备。拒绝包含 endpoint_gap45916、residual14361、parallel1128、branch23、ambiguous2206 等，统计口径沿用原实现，不宜简单相加为独立样本。

8组通过冻结增长公式，全部为 polyline，0组为 line；8组的域外支持都超过4p。其中4组有至少两个实质原parent，1组有至少三个实质L1片段。五组数值增长门槛已达到，但更严格的“五组实质跨原parent”以及本轮新增直线证据未达到。分类为 polyline 本身不证明曲率；必须结合实际图片。

| 组 | 核数 | 最大M2前驱支持p → M3并集p | 域外支持p | 最长连续段p | 总/最大间隙p | 解释 |
|---|---:|---:|---:|---:|---:|---|
| 79171 | 104 | 12.411 → 20.468 | 7.859 | 3.353 | 4.217 / 0.376 | 三实质L1、两实质原parent |
| 204470 | 77 | 8.627 → 16.227 | 7.629 | 3.164 | 4.924 / 1.295 | 两实质原parent |
| 34551 | 70 | 8.636 → 16.554 | 8.034 | 1.755 | 5.353 / 1.115 | 两实质原parent，原生像素很少 |
| 55091 | 62 | 9.386 → 13.668 | 4.306 | 1.792 | 6.206 / 1.255 | 两实质原parent |
| 57769 | 160 | 19.049 → 35.239 | 16.187 | 1.729 | 16.085 / 0.404 | 仅一个实质原parent |

79171 的 M2 贡献为68+36核；L1贡献为48+36+20核，各自达到实质支持门槛。双视图可见浅弧，M2两色被M3统一，原parent贡献覆盖不同部分。它是目前实质逐级合并的具体例子。其有限载体长24.702p，而去重支持20.468p、最长连续段仅3.353p；不能把整条载体当作连续观测。贡献支持可重叠，不能直接相加。204470的双视图和parent颜色也支持曲线片段的组合，但不提供独立物理身份真值。

固定大组21870、21927、20007投影接近直线，却均无M3域外支持，不能把继承的大组冒充新增延伸。跟踪曲线34448新增4核，支持仅增加0.0366p、域外0；跟踪直线36790保持52核且增量0。57769虽然新增支持明显，但原parent3698贡献150/160核，其余均不足实质门槛，不作为强跨parent证据。

实际保存246张PNG，本次直接检查40张：两张完整资产、固定大组、增长/跟踪组、同成员M2/M3及parent色、六类精确负例的双视图。完整检查清单见 VISUAL_REVIEW.json。parallel、branch、crossing/tangent、gap、ambiguity和最差接受例虽有图，原生仅少量像素；冻结的4倍最近邻裁剪没有创造新信息，无法充分排除深度重叠或分支误吞。最差接受例切向29.9992249°非常接近30°，图片也无法独立验证其合法性。未发现足以从现有图明确判定的新巨型吞并，但这不是所有接受的视觉认证。

可直接打开的实际图：

- [全景 test_r_1](scenes/ficus/stages/M3_MERGE_ONLY/test_r_1_FULL.png)、[全景 test_r_79](scenes/ficus/stages/M3_MERGE_ONLY/test_r_79_FULL.png)
- [79171 M2](scenes/ficus/stages/M3_MERGE_ONLY/diagnostics/CROP_79171_test_r_1_GROUP_79171_M2_test_r_1.png)、[M3](scenes/ficus/stages/M3_MERGE_ONLY/diagnostics/CROP_79171_test_r_1_GROUP_79171_M3_test_r_1.png)、[另一视图M3](scenes/ficus/stages/M3_MERGE_ONLY/diagnostics/CROP_79171_test_r_79_GROUP_79171_M3_test_r_79.png)、[原parent色](scenes/ficus/stages/M3_MERGE_ONLY/diagnostics/CROP_79171_test_r_1_GROUP_79171_PARENTS_test_r_1.png)
- [204470原parent色](scenes/ficus/stages/M3_MERGE_ONLY/diagnostics/CROP_204470_test_r_79_GROUP_204470_PARENTS_test_r_79.png)、[最差接受例](scenes/ficus/stages/M3_MERGE_ONLY/diagnostics/CROP_CONTEXT_accepted_worst_margin_test_r_1_CONTEXT_accepted_worst_margin_test_r_1.png)

图片来自固定相机、白背景、floor0.0144、原协方差/宽度/opacity的实际原始LINE kernels；UNKNOWN灰色。没有RGB source GS、拟合线替代图或补画间隙。支持并集、有限载体长度、bbox、间隙和贡献分别保存在 GROUPS/CARRIERS；物理身份全部暂定，无独立held-out或泛化主张。

溯源与完整性：CONFIG SHA256 为 `2221d81f5e1726660ce428804981a26d484fa8716cc3c60ee1c774cb23fd99be`，DECISION SHA256 为 `135c5ce8d39a171629686132e4af2ebd30fe2f7cb28c7595b5bbcb574a079dba`。按 Parent 的 immutable_source_snapshot 验证26个源码快照、全部输入引用、26个helper引用（含4个获准外部helper）、5个检查点；验证285956行映射、载体归属、所有前驱已分配成员保留、六个非颜色原始字段哈希、诊断完整行集合及输入版本。全部通过，详见 ANALYSIS_AUDIT.json。诊断行列表不必排序，但集合精确；主资产行顺序单独逐行核对。

PROVENANCE.json 保存完整哈希和实际 runner argv：批准venv的python、`-B`、`continuation_scene.py --config unit_005/CONFIG.json`。未来工作树HEAD变化不影响本单元快照。BUILD真实测试10项、returncode0，日志及RED收据保留；小型真实回归只证明其覆盖范围内等价，不当作全资产增长证据。Parent实际EXIT单独引用并哈希，不改写。静态 SEAL 仅涵盖已关闭的本单元文件，不纳入外部实时API或监督日志。

NEXT=continue：下一独立单元将完整scan65的封存M2推进恰好一轮M3，沿用本单元参数、预算、原始核和双相机；不重跑旧场景、不初始化、不池化。scan24和ficus已有两轮，scan65尚只有一轮，这一步先完成同配置比较。ficus当前fit预算未耗尽，暂无依据单纯提高cap。下一步仍经决策冻结→BUILD→Parent compute→ANALYSIS；本分析未启动它。NEXT.json给出状态哈希、1800秒阶段预算和视觉否证条件。所有science须在12:35JST前结束，12:00后不开新单元。
