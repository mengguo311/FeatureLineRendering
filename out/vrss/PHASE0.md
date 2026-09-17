# Phase 0 核验

预注册 commit: 030b0f1。基线 visual-stroke-render 保持 acd4ab9。

- CPU 三项回归测试通过：异 fx/fy、偏心主点与 skew 的每相机投影/梯度；G-buffer 单 Gaussian 垂直坐标由 fy 决定；M1a 拒绝缺失、重复、非整数以及 VAL/TEST indices。
- M1a 旧调用未传 train_indices 会明确报错，不默默延续历史泄漏。历史 score/cache 未改写，VRSS 不导入 run_m1b 的评估 driver。
- 官方 RGB 单帧 smoke 已实际运行成功，完整 SH，TRAIN index=1，400²。诊断 PSNR 28.3122 dB，含 G-buffer 的总耗时 1.72 s。详见 renderer_smoke.json 和 official_rgb_smoke.png。
- 外部官方 renderer 唯一源码补丁是从四个返回值解包 RGB/radii/depth/alpha，未修改 RGB 计算；这不是未改动官方二进制声明。官方仓库/源码/扩展 wrapper hashes 已记录。
- disc G-buffer 仍是旧近似：中心投影改用完整 K，半径仍保留 fx 对应的旧圆盘近似，未声称它是官方深度或完整投影椭圆。

命令：
```
OPENBLAS_NUM_THREADS=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
```
官方 RGB smoke 将由 run_vrss.py smoke 阶段提供可重复入口；本次单帧检查在候选生成前完成。
