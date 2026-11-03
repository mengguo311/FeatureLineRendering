本轮工程执行完成，科学结论仍为 **PARTIAL：恢复了一批局部旧来源片段，未恢复满足门槛的实质跨片段长曲线**。不是全局归组成功，也不是自由重归属方向已被彻底证伪。

父进程实际子进程退出为0，reason=null，运行于2026-11-01 18:55:57.413886至19:01:01.417861 JST；runner记303.593秒。共保存NO_BIRTH、15个接受阶段及BIRTH_FINAL，17份完整285956行检查点；对照和最终阶段均有test_r_1/test_r_79原生全景，25组案例、50个非空联合裁剪框。非空框不等于单组可辨或安全。分析仅查看保存结果，没有重跑、拟合、渲染或改源码。

本轮latent object是从位置—无向切向观测图得到的有限路径及其辅助曲线。1p voxel内保留多个方向模式，图状态只是提案证据，不是固定旧片段；新曲线可以吸收UNKNOWN或夺取已有模型成员。原核几何不变、旧归属允许撤销。路径证据、方向表示与候选搜索同时改变，不能把结果单独归因于Dijkstra或全局能量。

实际图包含102910 voxel、131891方向模式、263782有向状态和344798边，全部285956有效原核参与模式构建。58026候选种子中覆盖选择64个，覆盖8463/88386个含UNKNOWN的空间voxel；57962种子未选。64个搜索结果中32个少于6 voxel，32条进入试验，路径几何长约3.415–17.439p。完整图和所选路径库已保存，但这不是全场景所有长曲线都已搜索。32次试验接受15次，拒绝8次window_turn、1次vertex_turn、8次出生模型无有效单片支持；这8次存活列表均为空，不能误称发生了多片分裂或能量拒绝。未用放宽阈值救场。

NO_BIRTH精确保留unit004最终状态。最终assigned 56222→56762，UNKNOWN 229734→229194；增加540核、丢失0核。另有3个旧已归属核从模型199转入722，199的88核成为199:85、722:3，表明旧标签确实可拆。543个新模型成员中540个原为UNKNOWN；并非大规模旧组重排。模型519→534，没有接受后的支持死亡/分裂事件。E由240874.001485降至240384.944691，其中数据项240355.001485→239850.944691、模型惩罚519→534。降低目标不证明物理身份。

最终UNKNOWN理由为无几何候选227497、竞争/UNKNOWN margin 1697。相对旧参考的得失如下，数字是覆盖和标签诊断，绝非准确率；跨命名空间的numeric ID变化也不能当身份错误率。

| 参考 | 原assigned | 新获分配 | 丢失分配 | 旧组拆分数 |
|---|---:|---:|---:|---:|
| v05_M4 | 118470 | 9797 | 71505 | 43 |
| v05_M5 | 121965 | 9205 | 74408 | 45 |
| v06_overlap_joint | 121883 | 8748 | 73869 | 42 |
| v06_common_joint | 119860 | 9677 | 72775 | 44 |
| unit001_ADAPTIVE | 6184 | 52883 | 2305 | 7 |
| unit002_ADAPTIVE | 56185 | 581 | 4 | 2 |
| unit004_OVERLAP_FINAL | 56222 | 540 | 0 | 1 |

完整逐组撤回、重排和UNKNOWN记录保存在[COMPARISONS](scenes/ficus/stages/BIRTH_FINAL/COMPARISONS.json)及[配对比较](NO_BIRTH_COMPARISON.json)。允许旧组拆分不意味着可以隐瞒大量相对v05/v06的标签损失。

实际全景仍以灰色碎线为主，原有外伸长尖刺清楚可见；本轮没有清理这些原几何。全对象highlight中的新目标非常小，不能据此宣称整体视觉明显改善。

![最终全景1](scenes/ficus/stages/BIRTH_FINAL/test_r_1_FULL.png)
![最终全景79](scenes/ficus/stages/BIRTH_FINAL/test_r_79_FULL.png)

15个新组中12个只有一个原parent；所有新组的实质M4贡献者至多1个，没有达到三个片段各≥12核且≥4p支持代理的门槛。代表病例：

| 新组 | 核数 | 支持union/最长段代理p | 证据判断 |
|---|---:|---:|---|
| 722 | 55 | 5.581/5.581 | 52个旧UNKNOWN+199的3核；原parent4个、实质2个；M4原本全UNKNOWN。相对199域外代理4.698p只挂靠3核，不能据此称长曲线恢复。 |
| 717 | 64 | 17.673/17.673 | 全为旧UNKNOWN，单parent3723；52核来自M4片段95409，其余12核M4 UNKNOWN。两视图为短浅弯/近直线。 |
| 720 | 47 | 15.826/15.826 | 单parent5303，只有1个实质M4片段；程序累计转角89度不等于可见大曲线。 |
| 716 | 36 | 12.807/12.807 | 短直线可见，但单parent6394及单M4片段163277，不是跨片段直边统一。 |
| 726 | 53 | 6.420/6.420 | 3个parent但仅2个实质来源，只有1个实质M4片段；无专用隔离图，视觉证据缺失。 |

722两视图都近似微小点团，深度/平行/分支关系不可辨。其完整当前模型竞争为199与722；当前模型集合之外的物理解释并未穷尽。717、720、716在对照中没有兼容模型，最终分别仅有自身模型，说明主要填补旧模型覆盖空白；不能用“只有一个竞争者”反证物理歧义。717同核在v05_M5已有来源分组，当前恢复不等于超越旧强参考。

[722原对照](figures/CURVED_722/NO_BIRTH_test_r_1_GROUP_CROP4.png)、[722视图1](figures/CURVED_722/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)、[722视图79](figures/CURVED_722/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)、[722竞争上下文](figures/CURVED_722/BIRTH_FINAL_test_r_79_CONTEXT.png)。

[717视图1](figures/CURVED_717/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)、[717视图79](figures/CURVED_717/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)、[717全对象highlight](figures/CURVED_717/BIRTH_FINAL_test_r_79_WHOLE_HIGHLIGHT.png)；[720视图1](figures/CURVED_720/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)、[720视图79](figures/CURVED_720/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)；[716视图1](figures/STRAIGHT_716/BIRTH_FINAL_test_r_1_GROUP_CROP4.png)、[716视图79](figures/STRAIGHT_716/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)。

上述新组保存的支持代理均覆盖各自有限域，union等于最长代理段、代理gap为0；这是协方差半宽区间投影，不是连续照片观测或真实无间隙证明。14个新组没有已有模型贡献者，outward_reference_missing=true；其输出0是缺参考占位，不能解释为已测得零外延。

原unit001弧144的198行仍分为55:150、441:47、UNKNOWN:1；本轮没有接回它。[同核弧图](figures/PRIOR_CURVED_144/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)。unit002曲组7的356行仍属7，unit004小组712的57行仍属712；均为继承结果。旧损失13054的96行仍全部UNKNOWN。模型199的3行转投是真实重排，但[受损组图](figures/DAMAGED_199/BIRTH_FINAL_test_r_79_GROUP_CROP4.png)过小，不能独立判定转投是否正确。

固定负例11/80709仍是很淡小灰段，33117/201172呈局部黄色弧；这些只是未解上下文，不能称安全真值。没有逐一检查25个案例的全部参考视图，也没有每个拒绝提案的单独渲染。平行、分支、深度与错误尖刺吸收的全面安全性未验证；没有源表面遮挡、时间帧或held-out验证。实际final ink仅原核，不画辅助路径或桥。

本次核验30个source_snapshot文件、全部17个闭合stage checkpoint文件SHA及两个renderer依赖；保存的17份GEOMETRY_AUDIT均报告原字段精确一致。本分析没有重新加载原始资产重做几何计算。CONFIG SHA256 `10423a1d233148eeb0a106563edad79a25feedf82e666ce10f347182424aba77`，decision SHA256 `d9a2faeec8d4d45eaff533b293bfcde790595234adede596f8473b94c1212293`。最终MEMBERSHIP SHA256 `bbcdc8457c99c14d183370584e82bad93df9cd8add83eda527cca26f1f920ebd`；MODELS SHA256 `1c79b11b25a7e88baf1342575d5a0274a807377e13f02b1c50e46f8949ac58c5`。输入资产、相机、旧状态及helper的完整SHA见[CONFIG](CONFIG.json)，源码归属见[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)。renderer.py SHA256 `ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93`，libjoint.so SHA256 `033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0`。

父进程实际命令为：

```text
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/line_kernel_free_reassignment_v07/reproduction/line_kernel_free_reassignment_v07/graph_birth_runner.py --config /mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101/units/unit_005/CONFIG.json
```

源码后续可能变化，追溯以本单元冻结snapshot哈希为准，不以将来的工作区HEAD代替。78项构建测试和退出0仅证明相应工程执行，不能替代上述视觉判据。

下一步建议为一个新的、尚未运行的机制：真实多视图边缘观测支持的可撤销核级关联与长曲线提案。先核实已有原图、标定及可见性输入；当前并未证明这些输入就绪。若可用，再冻结完整竞争邻域和同库去除图像证据的对照；若不可用则明确NOT_READY，不能用线核自渲染循环证明。仍在当前新单元窗口内，不因局部负结果停止研究；不再扩展本轮半径、种子数或拟合预算。详见[NEXT](NEXT.json)。
