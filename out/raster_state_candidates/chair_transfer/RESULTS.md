# Chair：四 TRAIN 视角迁移诊断

按 primary NO-GO 的预注册分支，只用 TRAIN [1,27,53,79]，保持全部阈值。
已实际运行 128px GPU smoke、Step1、Step2、Step3 与初始 linelet 生成。
没有完整 chair M1a/DT/prune/chaining、DEV 或 TEST 实验。

| 来源 | 全量初始 linelets | 匹配观测 real clusters | ID shuffle | shifted |
|---|---:|---:|---:|---:|
| top-k | 66 | 31 | 0 | 1 |
| RGB | 91 | 82 | 0 | 0 |
| union | 338 | 276 | 0 | 26 |

RGB null=0，不能把带分母 floor 的内部比值字段解释成真实“82 倍”。
k4/k8 掩码平均 Jaccard=0.1964，仍有明显截断敏感性。
Step1/2/3 分别用时 5.82/1.82/3.31 s，另加 smoke 1.51 s。
实际检查 TRAIN53 channels 及完整四视角 aggregation contact sheet：
RGB/union 在一些外框上比 top-k 更集中，但仍是很稀的短段；没有可据此
宣布 chair NPR 成功的最终画面。它支持“重复性不等于结构线画”的主结论，
不构成跨场景视觉性能验证。
