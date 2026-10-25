# Unit003：固定载体的共享方向场比较

结果：F0逐值恢复旧A；F1降低共享边方向差，但未建立整物体可读性优势，不升级默认。

科学协议、实际资产和中文报告位于：

`/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_003`

- `REPORT_ZH.md`：完整结果、失败、范围和下一步。
- `ALL_DEV_MATCHED.png` / `ALL_DEV_NATURAL.png`：完整前后物体比较。
- `REAR_CAMERA_SEQUENCE.png`：实际变化相机的三帧比较，不是时序稳定性认证。
- `asset/FIELDS.npz`、路径NPZ、种子JSON：独立路径身份及代理face/bary锚点。
- `AUDIT.json`、`FAR_READBACK.json`、`attribution/SUMMARY.json`：实际读回。
- `cached_field_replay/REPLAY_RECEIPT.json`：新进程实际重画墨层，26数组逐值一致。

F0采用原切片切向 `normalize(n_face × q_layer)`。F1采用固定8次、原场/传输邻域等权的无向dyad平滑；载体、原Gaussian参数、纸底与区域S、目标、相机、线宽及遮挡均保持。两臂共享同一场驱动行走器和380个旧种子，F1初始切向可以改变。

针对性TDD先RED后GREEN，真实场景及审计通过。677个冻结输入保持。弱后视角linked目标覆盖35.66%→35.33%，三个DEV覆盖下降；自身缺墨减少伴随可见长度下降，不能据此宣布成功。新路径仍为代理笔触，不是逐路径Gaussian所有权认证。

复放命令（输出目录必须不存在且位于unit_003）：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/field_unit/replay_field.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_003/user_replay_001 --view orbit_241_24_5.3
```

运行时固定CPU两核亲和、数值线程1、禁用CUDA。此入口依赖锁定历史缓存并实际重画新墨，不是第二次冷GS重放或独立便携包。沿用现有NumPy/SciPy/Open3D环境，没有安装。

冻结生产者的序列图名称含`CAMERF0`误替换，保留原文件并提供相同字节的正确名称别名。首个交付脚本导入错误及其源码保留于`interrupted_handoff_001`，第二次交付完成。科学源码和父级决策未修改。

下一步仅为待父级审查的独立路线：检查同层拥挤/空白是否有实际余量，再决定是否比较保持方向场和长度分布的表面间距约束种子放置；不扫描本轮场平滑强度或角度。
