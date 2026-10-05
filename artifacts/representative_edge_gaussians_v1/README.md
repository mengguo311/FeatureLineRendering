# 代表性固定原始 Gaussian ID 实验

实际结果见 [中文报告](REPORT_ZH.md)、[FINAL](FINAL.json)。本轮 `gpt-6.1-sol / xhigh`；历史基点保持 `gpt-6-astra / ultra`。

图组在 `figures/`，完整Telegram1600视频在 `media/{mic,materials}/`。`assets/*/selected_ids.json` 包含五个arm的原始PLY行号、有序前缀、三档预算和仅F确定的coverage匹配点，可供浏览器demo读取；未改写旧demo。

大数组、全部姿态/预算图、native视频、CPU/native日志保留于 `/home/u00134/3dgs_line/representative_edge_gaussians_v1/out/representative_edge_gaussians_v1`，每文件散列与精确路径见 `SOURCE_MAP.json`。

运行 [run.sh](run.sh)，复现与续跑要求见 [REPRODUCE](REPRODUCE.md)。S0、F选择封条不可重写，C/arc不能用于调整证据、归一化、预算或λ。
