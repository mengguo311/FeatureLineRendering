# FeatureLineRendering — 当前研究汇总入口

**推荐查看分支：`research-progress-summary-v1`。** 以最新三场景实验 `c873fb8` 为基点，保留主线历史，补齐两条并行负结果快照，并首次发布真实交互demo与历史综合报告。没有删除历史分支、强推、改默认分支或把不同算法代码强行合并。

## 从这里开始

- **[最新进展与科学结论](docs/PROGRESS_ZH.md)**
- **[所有分支的用途与固定SHA](docs/BRANCHES_ZH.md)** · [机器盘点](docs/BRANCH_INVENTORY.json)
- **[Lego / Chair / tree=Ficus代表性选核](artifacts/representative_edge_gaussians_three_v1/REPORT_ZH.md)**
- **[Mic / Materials代表性选核](artifacts/representative_edge_gaussians_v1/REPORT_ZH.md)**
- **[最初Gaussian贡献回溯](artifacts/gaussian_edge_attribution_v1/REPORT_ZH.md)**
- **[交互Gaussian检查demo（真实数据）](artifacts/gaussian_edge_demo_v1/README.md)**
- **[历史32页综合PDF](artifacts/npr_progress_report_sol_v1/REPORT_ZH.pdf)**（形成于2026-10-04，不含后来的联合选择实验）

## 当前结论

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
