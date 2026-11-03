# unit_003：端点合并未产生新增归组

**工程执行完成；本机制本轮为零收益，整体长曲线恢复仍为PARTIAL。** 父级实际子进程rc=0、reason=null，18:14:00.661253至18:15:41.996470 JST；RUN_RESULT记录100.949秒。两个完整阶段NO_MERGE与MERGE_FINAL均已保存285956行、520模型及两张原核全景。分析仅读取保存结果，没有重跑、拟合、渲染或编辑源码。

本轮真正增加的是动态有限模型合并、共同重拟合及全局能量接受。原核可逐颗改投第三模型或UNKNOWN，旧M4/v05/v06不是不可拆原子。**实际五个提案均在试验重新归属之前失败，故不能宣称已验证全局能量接受的科学效果，更不能归因某个求解器。**

|提案|实际拒绝|是否完成试验全核重竞争/能量|
|---|---|---|
|2/5|length_cap|否|
|4/5|length_cap|否|
|386/499|拟合后window_turn|否|
|515/646|拟合后vertex_turn|否|
|513/517|拟合后vertex_turn|否|

539760个四端点组合均有保存，只有5个满足本轮端点屏幕，全部尝试；未触及64次预算，无未尝试合格提案。两个长度容量拒绝不等于做过成功拟合。三个拟合后几何拒绝也不等于物理上确定是不同边。SEARCH_RESULT的complete仅限当前模型版本及端点候选族，不代表发现了全部真实曲线。55/441的四种端点关系均不合格：最小间距2.699113p，相关连接角158.614°；没有为重点案例扩大范围。

## 实际归属与得失

两臂均assigned=56213、UNKNOWN=229743；其中228033无几何候选，1710因竞争/UNKNOWN margin弃权。独立读取保存NPZ确认原行号0…285955，NO_MERGE与MERGE_FINAL所有membership字段（含替代关联）、模型文件和两张全景逐字节相同。E同为240886.3417603029，其中数据项240366.3417603029、模型惩罚520；所有trial的after=null，**没有任何实际能量下降**。

相对unit002末状态新增28个归属、损失0、拆分0，完全来自NO_MERGE的一次重竞争，不能计为合并收益。相对旧参考如下；“新增/丢失”只是assigned状态转变，拆分为旧组对应多个新主组，均不是准确率。数字ID变化不能当作身份准确性。

|参考|旧assigned|新增assigned|丢失assigned|旧组拆分|
|---|---:|---:|---:|---:|
| v05_M4 | 118470 | 9697 | 71954 | 43 |
| v05_M5 | 121965 | 9118 | 74870 | 44 |
| v06_overlap_joint | 121883 | 8648 | 74318 | 42 |
| v06_common_joint | 119860 | 9577 | 73224 | 44 |
| unit001_STATIC | 4577 | 53557 | 1921 | 4 |
| unit001_ADAPTIVE | 6184 | 52367 | 2338 | 6 |
| unit002_STATIC | 53176 | 3326 | 289 | 19 |
| unit002_ADAPTIVE | 56185 | 28 | 0 | 0 |

逐核自由是真实的：例如旧M4片段31251的部分核位于模型55、另一部分位于441；旧片段31215也分散到这两个模型。此类重排主要继承前轮，不是本轮新合并。完整变更清单在MERGE_FINAL/COMPARISONS.json；旧分配保留不是优化目标，丢失仍须接受视觉审查。

## 已实际查看的图与限制

两张全景均保持大范围灰色UNKNOWN和零散局部彩色边；右/左侧仍有长彩色尖刺。固定几何无法清除原尖刺；将尖刺统一成一条身份也不代表正确。

![原核全景test_r_1](scenes/ficus/stages/MERGE_FINAL/test_r_1_FULL.png)
![原核全景test_r_79](scenes/ficus/stages/MERGE_FINAL/test_r_79_FULL.png)

查看了7/11/15、旧144和旧482的同核双视图，以及7/144的竞争上下文、13054损伤和16931/18768、33117/201172负例上下文。图7和11有可辨的局部浅弧/弯曲，15更接近浅弯线段；它们均继承unit002。7含356核、5个实质M4贡献，支持代理38.810924p；但单一旧284665已覆盖整个代理域。11为255核/5贡献/33.466079p，旧32707已覆盖整个域；15为212核/3贡献/33.587728p，旧65959已覆盖整个域。跨片段重复观测池化是存在的，**未出现相对最大输入的新外延**。

![继承曲组7第一视图](figures/PRIOR_UNIT002_CURVED_7/MERGE_FINAL_test_r_1_GROUP_CROP4.png)
![继承曲组7第二视图](figures/PRIOR_UNIT002_CURVED_7/MERGE_FINAL_test_r_79_GROUP_CROP4.png)

旧unit001弧144的198个原核仍为55:150、441:47、UNKNOWN:1；双视图可见颜色分段，没有恢复成同一身份。旧直例482同核图可见直段，但属于单parent5872/单M4片段148857，不能作为新实质跨片段直线证据。15个保存案例中没有新增曲线或新增实质直线案例，不能补造成功图。

![旧弧144仍分段](figures/PRIOR_CURVED_144/MERGE_FINAL_test_r_79_GROUP_CROP4.png)
![旧直例482](figures/PRIOR_STRAIGHT_482/MERGE_FINAL_test_r_1_GROUP_CROP4.png)
![旧13054已撤回为UNKNOWN](figures/PRIOR_UNIT002_DAMAGED_13054/MERGE_FINAL_test_r_1_GROUP_CROP4.png)

旧13054的96核和9969的87核仍全部UNKNOWN；37737的90核中87 UNKNOWN、3归175。30个案例/视图联合bbox均非空，但负例在原生上下文中仍很小；非空不等于平行、分支或深度安全已证实。没有为五个拒绝提案另存专门隔离渲染，故不对它们作物理正/负判定。原始全景无源表面遮挡；本轮未生成连续相机帧，未验证时间稳定性。没有辅助曲线或无支持桥作为最终墨迹。

支持均为协方差半宽投影区间代理；即使7/11/15的union、最长代理段相等且代理gap=0，也不能据此宣布真实连续观测或物理边完整。所有身份provisional，未验证held-out，旧parent不是GT。

## 来源、保存与下一步

已核验父级冻结映射中的18个source_snapshot文件、两个只读renderer/helper、CONFIG/DECISION绑定及两个完整阶段checkpoint全部文件hash。几何审计记录means/covariance/opacity/原colors/primitive_id/internal_piece_id/arc_t逐字段不变；分析没有再次加载完整原资产重新做几何科学计算。以保存快照为准，不要求以后工作树HEAD仍相同。

- DECISION SHA256：`58b60925666956479d9fb581b4b219d8bff69f3a3594c844d37848940cbca1fe`
- CONFIG SHA256：`8231ab7ff396c30c7e359fd139c53b2cf65f92d6092d97dd81d1ce6eee59e256`
- 最终MEMBERSHIP：`1d544bc84345ae8e8f268c2009d277c7d9ecf5019409bb775d39fd9b1842ea20`
- 最终MODELS：`e990caaa4a47272a8285da8453400b231ffe575df53493557040fb9bf95e4ef3`，与输入unit002模型一致。
- 输入原核/control/相机与所有旧参考的精确绑定见CONFIG.input_files；源快照和两个helper的具体SHA见PARENT_RUN_FROZEN.json及STATUS.json。真实退出见父级COMPUTE_EXIT.json，不改写为wrapper状态。
- 父级实际入口：批准venv的`python -B reproduction/line_kernel_free_reassignment_v07/merge_runner.py --config <本单元>/CONFIG.json`；此次分析不执行该命令。

下一步建议独立评审**共享兼容核支持的动态重叠曲线合并与单调共同参数化**：端点族只有5个可尝试提案，尚未给全局能量提供有效模型；应改变提案的关系与共同参数域，不扫描gap/turn/λ或扩大预算。以NO_MERGE为对照，完整几何兼容关系必须包含全部竞争模型，不能只依赖top2替代引用。55/441是否共享足够支持尚未核实。若没有共同证据就保存负结果，不强连重点弧。保持所有核自由竞争与原守卫/能量，单列重复池化与真正外延。具体规则须下一review重新冻结；本分析未启动任何新实验。当前窗口仍可继续，19:15停新单元、19:38停science。
