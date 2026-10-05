# 汇总策展与验证范围

- 基点c873fb87ec0f0ce13dcb1d7f2b9b4d4737bb894e，保留全部原主线Git树，不改变历史实验文件。
- 两条独立结果目录逐Git blob导入；IMPORTED_RESULT_SNAPSHOTS.json逐文件记录来源SHA。并未把其源码变化并进主线。
- 新发布本地真实demo代码/缓存及2026-10-04综合报告的MD/HTML/PDF/图/视频。LOCAL_PUBLICATION_MANIFEST.json保留初始逐文件hash；node_modules、执行日志、重复source缓存不发布。
- 旧科学SOURCE_MAP/封条保持原样；绝对路径或out链接不是伪装成Git存在的文件。
- 验证所有新策展相对链接的Git树目标、逐导入blob、demo数据清单、测试与基础媒体；不重跑原科学，不重新授予视觉GO。
- 历史分支不删除/重命名/强推；新汇总入口不是GitHub默认分支改动。
