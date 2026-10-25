# Unit005：固定宏观方向的两种局部切向构造

冻结原Lego载体与unit010宏观框架，以相同380个种子、逐笔触请求长度和相同行走器，对比 `P0=normalize(n×q)` 与 `P1=normalize(a−(a·n)n)`，其中 `a=normalize(n0×q)`。参考平面上两者同向；没有角度搜索、载体修改、场平滑或种子重排。新代码在 `experiments/partwise_sketch_hatching_v07/projection_unit/`。

**实际结果为负，不升级默认。** P1明显改变可见方向，但前侧平行线束变为更零散的弯折短线；四DEV中三个覆盖下降，弱后侧稍多墨未形成完整物体可读性优势。总长度29.713595379→28.497526347，134条笔触缩短；一个方向触发继承行走器的zero_step_cycle保护，原记录保留。原Gaussian、纸底/墨权重、M1/UNKNOWN及作者目标不变；新路径仍仅通过区域S连接原ID，没有逐路径Gaussian认证。

五组针对性TDD先RED后GREEN。实际场景生成、BUILD墨量配平、四DEV/三arc、逐笔触归因、独立审计与新进程重放均完成。P0恢复旧基线，1315份输入及源码保持，140张PNG完整解码核验；新进程实际重画墨层，30数组逐值一致。source/paper/S复用已验证缓存，不重复unit001冷GS bootstrap。

完整证据：`/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_005/` 下的 `REPORT_ZH.md`、`STATUS.json`、`NEXT.json`、`PROTOCOL.json`、`ALL_DEV_MATCHED.png`、`REAR_CAMERA_SEQUENCE.png`、`WALKER_GUARD_RECORD.json` 和 `AUDIT.json`。所有旧负结果保持，scientific_seal=false，父级验证待完成。

在unit005内不存在的新输出目录复放：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/projection_unit/replay_projection.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_005/user_replay_001 --view orbit_241_24_5.3
```

使用现有依赖，CPU两核亲和、数值线程1、串行、CUDA为空。全部相机EXPOSED；三帧序列不构成连续视频或时序稳定认证。NEXT建议新的只读审查后，在已有可辨平行排线的Chair简单基线上验证一次区域间距编辑及新路径原ID支持；不据本轮负结果继续扫角度、平滑或长度。
