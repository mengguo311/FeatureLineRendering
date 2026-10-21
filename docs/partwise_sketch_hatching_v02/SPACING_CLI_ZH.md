# 单次灯罩种子重排

`spacing_cli.py` 对 unit010 的完整 434 路径 GT 台灯执行一次冻结的灯罩种子重排。仅改变 260 条灯罩路径，原 24 条支杆和 150 条长度 0.12 的底座路径作为保留资产复用。该命令是一个明确的有限域操作，不提供参数扫选，也不代表通用风格配方组合。

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/spacing_cli.py edit --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_011/inputs/asset.json --part shade --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_011/user_preview
```

输出目录必须在 unit011 下且此前不存在。`preview --asset` 直接渲染保存资产；`regenerate --recipe` 从网格、174 条保留路径和配方重新生成灯罩；`replay --bundle` 重放保存路径。三种操作均接受 `--output`，默认生成方位 30/120/210/300 度的四张整灯图，`--azimuths` 可指定预览视角。本轮评价只使用冻结视角。

外壁、上缘、内壁、下缘分别保持 121、1、136、2 条原种子身份。每带生成 `max(256,64*n)` 个候选，以周期角度和剖面位置的固定各向异性距离做最远点选择。目标 seed ID 保留而坐标版本更新；不是目标几何不变。每个 ID 的原墨量保持，未按新位置法线重算照明；该设计用于隔离种子位置效应，明暗未校准。

`recipe.json` 记录算法、原 ID/带/墨量、依赖 SHA、配置和几何版本；不缓存目标路径。`SEED_AUDIT.json` 保存种子与跨带检查。`EDIT.json` 同时记录生成、首张预览、全部预览耗时；CPU 离线运行不宣称实时。科学结论以 unit011 的 STATUS、独立指标和实际视觉检查为准，资产不会自动晋级。
