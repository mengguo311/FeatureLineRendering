# GitHub分支导航与保留策略

盘点GitHub远端 **38 个现有分支**；盘点后新增 `research-progress-summary-v1` 作为统一入口。没有删除、重命名、强推历史分支，没有更改默认分支。

分支名是实验标签，不代表科学成功。commit subject仅为历史元数据，不视为重新验证的结论；结论请读对应冻结报告。

## 快速入口

- `research-progress-summary-v1`：当前汇总入口、全部主线结果、两条并行负结果快照、历史综合报告与真实交互demo。
- `representative-edge-gaussians-three-v1`：最新Lego/Chair/Ficus三场景实验，147姿态。
- `representative-edge-gaussians-v1`：Mic/Materials联合选核实验，98姿态。
- `gaussian-edge-attribution-v1`：最初固定ID贡献回溯，Mic/Materials，TOP4限制。

## 完整远端盘点（按用途分组）

### 当前贡献核主线

- [`gaussian-edge-attribution-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/20f85a15c3d3c382b94b83e8b6aa501c72009e70) — `20f85a15c3d3`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/gaussian_edge_attribution_v1/FINAL.json](https://github.com/mengguo311/FeatureLineRendering/blob/20f85a15c3d3c382b94b83e8b6aa501c72009e70/artifacts/gaussian_edge_attribution_v1/FINAL.json) · [artifacts/gaussian_edge_attribution_v1/REPORT_ZH.md](https://github.com/mengguo311/FeatureLineRendering/blob/20f85a15c3d3c382b94b83e8b6aa501c72009e70/artifacts/gaussian_edge_attribution_v1/REPORT_ZH.md)
- [`representative-edge-gaussians-three-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/c873fb87ec0f0ce13dcb1d7f2b9b4d4737bb894e) — `c873fb87ec0f`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/representative_edge_gaussians_three_v1/FINAL.json](https://github.com/mengguo311/FeatureLineRendering/blob/c873fb87ec0f0ce13dcb1d7f2b9b4d4737bb894e/artifacts/representative_edge_gaussians_three_v1/FINAL.json) · [artifacts/representative_edge_gaussians_three_v1/REPORT_ZH.md](https://github.com/mengguo311/FeatureLineRendering/blob/c873fb87ec0f0ce13dcb1d7f2b9b4d4737bb894e/artifacts/representative_edge_gaussians_three_v1/REPORT_ZH.md)
- [`representative-edge-gaussians-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/d5265b4b71f635bac6563ad12466e4abcd2e1ffb) — `d5265b4b71f6`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/representative_edge_gaussians_v1/FINAL.json](https://github.com/mengguo311/FeatureLineRendering/blob/d5265b4b71f635bac6563ad12466e4abcd2e1ffb/artifacts/representative_edge_gaussians_v1/FINAL.json) · [artifacts/representative_edge_gaussians_v1/README.md](https://github.com/mengguo311/FeatureLineRendering/blob/d5265b4b71f635bac6563ad12466e4abcd2e1ffb/artifacts/representative_edge_gaussians_v1/README.md) · [artifacts/representative_edge_gaussians_v1/REPORT_ZH.md](https://github.com/mengguo311/FeatureLineRendering/blob/d5265b4b71f635bac6563ad12466e4abcd2e1ffb/artifacts/representative_edge_gaussians_v1/REPORT_ZH.md)

### 同源渲染与方法来源

- [`hao-mukai-rade-foundation`](https://github.com/mengguo311/FeatureLineRendering/tree/1f0a9e667675495236cec8753869fd63d7e9f519) — `1f0a9e667675`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/hao_mukai_rade_foundation/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/1f0a9e667675495236cec8753869fd63d7e9f519/artifacts/hao_mukai_rade_foundation/REPORT.md)
- [`hao-mukai-rade-native-f1`](https://github.com/mengguo311/FeatureLineRendering/tree/8dd29e1c68feae723e6d17417eea381251bf1e5f) — `8dd29e1c68fe`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/hao_mukai_rade_native_f1/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/8dd29e1c68feae723e6d17417eea381251bf1e5f/artifacts/hao_mukai_rade_native_f1/REPORT.md)
- [`hao-mukai-source-2026-repro`](https://github.com/mengguo311/FeatureLineRendering/tree/1730def5e2844cc0df215d9db2c37a57513b58c2) — `1730def5e284`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/hao_mukai_source_2026_repro/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/1730def5e2844cc0df215d9db2c37a57513b58c2/artifacts/hao_mukai_source_2026_repro/REPORT.md)
- [`hybrid-dense-ink-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/e9b7e59ab109097aca46c374a3544c0eea3b93ab) — `e9b7e59ab109`；该tip已在最新实验的提交祖先中。
- [`hybrid-raster-evidence-v2`](https://github.com/mengguo311/FeatureLineRendering/tree/f2a618450e0d0d142a059794149021fe3c2644ab) — `f2a618450e0d`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/hybrid_raster_evidence_v2/FINAL.json](https://github.com/mengguo311/FeatureLineRendering/blob/f2a618450e0d0d142a059794149021fe3c2644ab/artifacts/hybrid_raster_evidence_v2/FINAL.json) · [artifacts/hybrid_raster_evidence_v2/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/f2a618450e0d0d142a059794149021fe3c2644ab/artifacts/hybrid_raster_evidence_v2/REPORT.md)
- [`hybrid-raster-extra-models-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/fef9b8566b9fc3aa42a8639b336987b302041c99) — `fef9b8566b9f`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/hybrid_raster_extra_models_v1/FINAL.json](https://github.com/mengguo311/FeatureLineRendering/blob/fef9b8566b9fc3aa42a8639b336987b302041c99/artifacts/hybrid_raster_extra_models_v1/FINAL.json) · [artifacts/hybrid_raster_extra_models_v1/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/fef9b8566b9fc3aa42a8639b336987b302041c99/artifacts/hybrid_raster_extra_models_v1/REPORT.md) · [artifacts/hybrid_raster_extra_models_v1/source_audit/README.md](https://github.com/mengguo311/FeatureLineRendering/blob/fef9b8566b9fc3aa42a8639b336987b302041c99/artifacts/hybrid_raster_extra_models_v1/source_audit/README.md)
- [`hybrid-raster-trained-models-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/59b6b3e49e14f758032a5e0079fe9405511bc148) — `59b6b3e49e14`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/hybrid_raster_trained_models_v1/FINAL.json](https://github.com/mengguo311/FeatureLineRendering/blob/59b6b3e49e14f758032a5e0079fe9405511bc148/artifacts/hybrid_raster_trained_models_v1/FINAL.json) · [artifacts/hybrid_raster_trained_models_v1/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/59b6b3e49e14f758032a5e0079fe9405511bc148/artifacts/hybrid_raster_trained_models_v1/REPORT.md) · [artifacts/hybrid_raster_trained_models_v1/acquisition/README.md](https://github.com/mengguo311/FeatureLineRendering/blob/59b6b3e49e14f758032a5e0079fe9405511bc148/artifacts/hybrid_raster_trained_models_v1/acquisition/README.md)

### 基础与固定资产可行性

- [`3dgs-field-visualization`](https://github.com/mengguo311/FeatureLineRendering/tree/bcf8260ac194191a9d9c1b28e21d3c82a5c3f0a0) — `bcf8260ac194`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/3dgs_field_visualization/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/bcf8260ac194191a9d9c1b28e21d3c82a5c3f0a0/artifacts/3dgs_field_visualization/REPORT.md)
- [`adaptive-mass-layered-line-probe`](https://github.com/mengguo311/FeatureLineRendering/tree/4ba72d38f15aff5370faf0ce6448a72e98884ae9) — `4ba72d38f15a`；该tip已在最新实验的提交祖先中。
- [`curve-correspondence-foundation`](https://github.com/mengguo311/FeatureLineRendering/tree/962b786bffd9a19f4cae5bea5d6c6ee65a1bd4f3) — `962b786bffd9`；该tip已在最新实验的提交祖先中。
- [`density-ridge-lines`](https://github.com/mengguo311/FeatureLineRendering/tree/e4695a498a055ae056ef649f8700ea31b59b6a5e) — `e4695a498a05`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/density_ridge_lines/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/e4695a498a055ae056ef649f8700ea31b59b6a5e/artifacts/density_ridge_lines/REPORT.md)
- [`density-ridge-threshold-sweep`](https://github.com/mengguo311/FeatureLineRendering/tree/9313e537bb2a7a4f998f75ae202a4a13872eb1ea) — `9313e537bb2a`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/density_ridge_threshold_sweep/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/9313e537bb2a7a4f998f75ae202a4a13872eb1ea/artifacts/density_ridge_threshold_sweep/REPORT.md)
- [`direct-curve-global-fit-probe`](https://github.com/mengguo311/FeatureLineRendering/tree/345d5905dc8ce02fef4b8f8c09e84f10ac7f4b60) — `345d5905dc8c`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/direct_curve_global_fit_probe/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/345d5905dc8ce02fef4b8f8c09e84f10ac7f4b60/artifacts/direct_curve_global_fit_probe/REPORT.md)
- [`mic-persistent-line-feasibility-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/d5c6d4d114b6b80ec5edb9c1717111e89a191eda) — `d5c6d4d114b6`；该tip已在最新实验的提交祖先中。
  - 冻结入口：[artifacts/mic_persistent_line_feasibility_v1/FINAL.json](https://github.com/mengguo311/FeatureLineRendering/blob/d5c6d4d114b6b80ec5edb9c1717111e89a191eda/artifacts/mic_persistent_line_feasibility_v1/FINAL.json) · [artifacts/mic_persistent_line_feasibility_v1/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/d5c6d4d114b6b80ec5edb9c1717111e89a191eda/artifacts/mic_persistent_line_feasibility_v1/REPORT.md) · [artifacts/mic_persistent_line_feasibility_v1/historical_blocker/FINAL.json](https://github.com/mengguo311/FeatureLineRendering/blob/d5c6d4d114b6b80ec5edb9c1717111e89a191eda/artifacts/mic_persistent_line_feasibility_v1/historical_blocker/FINAL.json)
- [`multiscene-foundation`](https://github.com/mengguo311/FeatureLineRendering/tree/5c5837ff5de68498d1c0388269808a30041a8774) — `5c5837ff5de6`；该tip已在最新实验的提交祖先中。
- [`multiscene-foundation-corrected`](https://github.com/mengguo311/FeatureLineRendering/tree/42158159a037fee1b14c5ba2d8a7e5271ec1bc36) — `42158159a037`；该tip已在最新实验的提交祖先中。
- [`persistent-boundary-feasibility-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/e3caf113a478a99ac6a6dd3abc9c3b27741ca34f) — `e3caf113a478`；该tip已在最新实验的提交祖先中。
- [`point-feature-foundation`](https://github.com/mengguo311/FeatureLineRendering/tree/6b098a5cb538fc4fc09d48d927dc97b77acc0b28) — `6b098a5cb538`；该tip已在最新实验的提交祖先中。
- [`topk-layered-line-probe`](https://github.com/mengguo311/FeatureLineRendering/tree/062d7ce73a740e1a817c82e57e516b395e45f417) — `062d7ce73a74`；该tip已在最新实验的提交祖先中。

### 并行负结果（独立合同）

- [`independent-rgbd-asset-probe`](https://github.com/mengguo311/FeatureLineRendering/tree/999a71bf53c717b4e04adc037b38476d3d5f5111) — `999a71bf53c7`；tip不是最新实验祖先；保留独立分支，不假称已代码合并。
  - 冻结入口：[artifacts/independent_rgbd_asset_probe/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/999a71bf53c717b4e04adc037b38476d3d5f5111/artifacts/independent_rgbd_asset_probe/REPORT.md)
- [`temporal-depth2d-video-probe`](https://github.com/mengguo311/FeatureLineRendering/tree/5aa1a14b4b7cbce95fb620377bfff48154ed5c63) — `5aa1a14b4b7c`；tip不是最新实验祖先；保留独立分支，不假称已代码合并。
  - 冻结入口：[artifacts/temporal_depth2d_video_probe/REPORT.md](https://github.com/mengguo311/FeatureLineRendering/blob/5aa1a14b4b7cbce95fb620377bfff48154ed5c63/artifacts/temporal_depth2d_video_probe/REPORT.md)

### 历史分支／专门诊断

- [`aggressive-linking`](https://github.com/mengguo311/FeatureLineRendering/tree/6b05516912444d12a0ee3851dd3dca9c8206bdd2) — `6b0551691244`；该tip已在最新实验的提交祖先中。
- [`evidence-frontier`](https://github.com/mengguo311/FeatureLineRendering/tree/d3d24a9d564b9ec10c609959559e02615e15ffd4) — `d3d24a9d564b`；该tip已在最新实验的提交祖先中。
- [`expose-splat-radius`](https://github.com/mengguo311/FeatureLineRendering/tree/e3c331f033c41a18ff06d3e3e5feb5e1e02de0bd) — `e3c331f033c4`；tip不是最新实验祖先；保留独立分支，不假称已代码合并。
- [`gap-recovery`](https://github.com/mengguo311/FeatureLineRendering/tree/e0293bd5c847698b9dbe67175ef1cc96a8243df1) — `e0293bd5c847`；该tip已在最新实验的提交祖先中。
- [`geo-line-extraction`](https://github.com/mengguo311/FeatureLineRendering/tree/3fbc930371ba80ec2e3185109b562d0bef644837) — `3fbc930371ba`；该tip已在最新实验的提交祖先中。
- [`geometric-angular-scenes`](https://github.com/mengguo311/FeatureLineRendering/tree/7878f6abbefeb8bf3fe6e9581079472dd0b348bc) — `7878f6abbefe`；tip不是最新实验祖先；保留独立分支，不假称已代码合并。
- [`m1b-milestone`](https://github.com/mengguo311/FeatureLineRendering/tree/0f40d02d2fec6ad11b9548bafff9f5fe98fac89c) — `0f40d02d2fec`；tip不是最新实验祖先；保留独立分支，不假称已代码合并。
- [`main`](https://github.com/mengguo311/FeatureLineRendering/tree/777cb548c6ddbe15be3e243017d10c8a41888b41) — `777cb548c6dd`；tip不是最新实验祖先；保留独立分支，不假称已代码合并。
- [`raster-state-candidates`](https://github.com/mengguo311/FeatureLineRendering/tree/3a10d3908173e35d359d41eec1469f5adaac4e56) — `3a10d3908173`；该tip已在最新实验的提交祖先中。
- [`retrain-falsify`](https://github.com/mengguo311/FeatureLineRendering/tree/6b05516912444d12a0ee3851dd3dca9c8206bdd2) — `6b0551691244`；该tip已在最新实验的提交祖先中。
- [`stroke-organization`](https://github.com/mengguo311/FeatureLineRendering/tree/fc27b3e01085cb35edc8418c5e9b1be33ed5d067) — `fc27b3e01085`；该tip已在最新实验的提交祖先中。
- [`tier1-research`](https://github.com/mengguo311/FeatureLineRendering/tree/2beba1dfce8ec75dc7a7e295b8b47cc169dde41e) — `2beba1dfce8e`；该tip已在最新实验的提交祖先中。
- [`visual-stroke-render`](https://github.com/mengguo311/FeatureLineRendering/tree/acd4ab9530fb4e5f654f2198c239bf6ddb62095e) — `acd4ab9530fb`；该tip已在最新实验的提交祖先中。
- [`vrss-experiment`](https://github.com/mengguo311/FeatureLineRendering/tree/9e643c2408954dffcfa8b298d5204e7314863a91) — `9e643c240895`；该tip已在最新实验的提交祖先中。

## 特别说明

- `aggressive-linking` 与 `retrain-falsify` 在本次盘点时tip完全相同；保留两个标签，不因为重复tip删除其研究语义。
- 最新实验分支不是仓库的全部历史自动合并：`main`、`m1b-milestone`、`expose-splat-radius`、`geometric-angular-scenes`以及两条并行实验均有独立tip。汇总通过固定SHA索引和明确快照补齐，未做潜在冲突代码大合并。
- `independent_rgbd_asset_probe` 与 `temporal_depth2d_video_probe` 两个完整Git跟踪结果目录从各自固定SHA逐blob复制，来源记录在 `artifacts/research_progress_summary_v1/IMPORTED_RESULT_SNAPSHOTS.json`；原始服务器out大视频/模型不因快照而自动进入Git。
- `npr-progress-report-sol-v1` 是服务器本地报告工作树标签，不在此次GitHub远端分支清单；历史报告已在本汇总首次出版，不宣称旧分支早已推送。
- 本次是保留历史的导航整理，不是分支数量清理。若要删除/重命名或把汇总设为默认分支，应另行明确。
