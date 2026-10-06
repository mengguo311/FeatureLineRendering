# FeatureLineRendering — 当前研究汇总入口

**推荐查看分支：`research-progress-summary-v1`。2026-10-06 已补齐后续九阶段实验与导师会议材料；新研究暂停。** 保留原三场景基点、并行负结果、demo与历史报告，精确提交导入新的协议/代码/证据快照。没有删除历史分支、强推、改默认分支或强合并不同算法。

## 从这里开始

- **[导师会议：通俗原理讲解、海报对比、真实图与讨论问题](docs/ADVISOR_MEETING_PRINCIPLES_ZH.md)**
- **[2026-10-06 后续九阶段方法与结果](docs/UPDATE_20261006_ZH.md)**
- **[最新全原核黑墨容量：Lego](artifacts/gaer_attribution_capacity_v02/media/lego/fourview_known_target_capacity.jpg)** · **[Chair](artifacts/gaer_attribution_capacity_v02/media/chair/fourview_known_target_capacity.jpg)**

- **[最新进展与科学结论](docs/PROGRESS_ZH.md)**
- **[所有分支的用途与固定SHA](docs/BRANCHES_ZH.md)** · [机器盘点](docs/BRANCH_INVENTORY.json)
- **[Lego / Chair / tree=Ficus代表性选核](artifacts/representative_edge_gaussians_three_v1/REPORT_ZH.md)**
- **[Mic / Materials代表性选核](artifacts/representative_edge_gaussians_v1/REPORT_ZH.md)**
- **[最初Gaussian贡献回溯](artifacts/gaussian_edge_attribution_v1/REPORT_ZH.md)**
- **[交互Gaussian检查demo（真实数据）](artifacts/gaussian_edge_demo_v1/README.md)**
- **[历史32页综合PDF](artifacts/npr_progress_report_sol_v1/REPORT_ZH.pdf)**（形成于2026-10-04，不含后来的联合选择实验）

## 当前结论

原核全 N 连续强度能形成可辨线结构，证明固定小核集合失败不等于表示不可行；但这是已知目标容量诊断，不是自动算法或泛化成绩，细线完整性、部分近最优认证和时间稳定仍未成立。GAER 支撑变化与海报核心明显重叠；区别在指定线归因到原核及原核实际墨迹容量，尚不宣称创新/优越。下一方向只讨论，未启动。

### 旧五场景结论（历史保留）

五场景联合选核：贡献需求覆盖增加，但非边缘泄漏也增加；**尚不支持同时保留主要边界并减少面内泄漏的总体成功**。数学完整归因仍UNDETERMINED，独立人类视觉验收PENDING。工程完成不是科学GO。Chair原float64审计失败与实际存储精度补充验证均保留，不宣称原检查全部通过。

## 直接看五场景完整对照视频

- [Lego](artifacts/representative_edge_gaussians_three_v1/media/lego/arc33_telegram1600.mp4)
- [Chair](artifacts/representative_edge_gaussians_three_v1/media/chair/arc33_telegram1600.mp4)
- [Ficus / tree](artifacts/representative_edge_gaussians_three_v1/media/ficus/arc33_telegram1600.mp4)
- [Mic](artifacts/representative_edge_gaussians_v1/media/mic/arc33_telegram1600.mp4)
- [Materials](artifacts/representative_edge_gaussians_v1/media/materials/arc33_telegram1600.mp4)

每段完整33帧、相同相机与原增益、非等墨量。贡献核投影不是几何线段。

## 运行交互demo

```bash
git clone --branch research-progress-summary-v1 https://github.com/mengguo311/FeatureLineRendering.git
cd FeatureLineRendering/artifacts/gaussian_edge_demo_v1
npm ci
npm test
npm start
```

访问 `http://127.0.0.1:8765`。Node20+；Mic/Materials各3缓存视图，TOP4 ROI归因与真实Gaussian几何检查，不是五场景native实时3DGS渲染器。`node_modules`不进入Git。

## 保留历史与复现边界

[main原根目录README](docs/LEGACY_ROOT_README.md)按`777cb548`原字节保留（最新实验基点没有根README）。[来源与策展验收](artifacts/research_progress_summary_v1/README.md)区分原提交继承、独立分支结果快照与本地新发布资产。大型服务器模型/CSR/out缓存并非全部Git上传；按各报告REPRODUCE与SOURCE_MAP获取。海报作者方法、第三方RaDe、我们的独立重建/贡献插桩与核群方法分别归属。mesh与TEST不进入当前方法。
