# Unit006：全局传输场及交叉风格混杂

本轮在完全相同的Lego载体、种子、请求长度、行走器、原Gaussian行权重和渲染规则上，比较原切片场F0与每个共享边传输分量单锚约束的全局无向张量场H。没有再次bootstrap，没有方向角或平滑参数扫描。

H的归一化图内方向能量从0.077420降至0.003303，前侧局部线束更顺。但最大分量将锚面2.768896°的近平行夹角传播到73.8146%的目标面积，弱后侧linked支持长度720.578→665.518px。结论为局部PARTIAL，不能将观感变化全部归于相干性，不升级默认。

- [完整中文报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_006/REPORT_ZH.md)
- [完整物体对照](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_006/ALL_DEV_MATCHED.png)
- [执行状态](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_006/STATUS.json)
- [下一步反证](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_006/NEXT.json)

五组针对性测试、真实场景运行、独立张量/路径/图像审计及30数组逐值复放通过。唯一运行失败为预期TDD RED，另外保留一条H路径触发旧行走器zero_step_cycle的记录。旧v05/v06及unit001至005负结果不变。

实际复放使用已有Python环境，输出目录必须不存在：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/global_field_unit/replay_global.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_006/user_replay_001 --view orbit_241_24_5.3
```

该入口实际重画新墨层，复用哈希固定原GS source/paper/S；不是新一次冷GS或独立便携包。新路径具有代理face/bary身份及区域原ID门控，不具逐路径Gaussian所有权或时序稳定认证。
