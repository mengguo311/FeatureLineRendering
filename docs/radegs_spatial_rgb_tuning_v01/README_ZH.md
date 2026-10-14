# Spatial RGB 检线强度与纹理抑制实验

本目录记录 **16 个预设 × 11 个原生视角 = 176 组**实际结果。仅调整 RGB 检线，不改变深度、alpha 或源模型；尚未选定预设，也未自动重建三维线高斯。

## 在线查看

- [选图索引](GALLERY.html)（需浏览器打开 HTML；GitHub 页面也可直接点击下方图片）。
- [建筑尺度系列](images/scenes/scan24/0000/SCALE.jpg)
- [建筑阈值系列](images/scenes/scan24/0000/THRESHOLD.jpg)
- [头骨阈值系列](images/scenes/scan65/0000/THRESHOLD.jpg)
- [头骨结构/detail 系列](images/scenes/scan65/0000/MIX.jpg)
- [Ficus 候选对照](images/selection/ficus_train_r_80_CHOICES.jpg)
- [完整结果与边界](REPORT_ZH.md) · [选择指南](SELECTION_GUIDE_ZH.md)

图例使用英文，完整原生画面未裁主体；放大 ROI 只用于解释，不参与检测。二值候选图用于区别“更淡”与“实际候选减少”。

## 配方

| 系列 | IDs | 实际变化 |
|---|---|---|
| 阈值 | A10/A15/A20/A30/A40/A50 | 原 union 不变，严格 darkness > T；A20 是旧 05 基线 |
| 细节权重 | B75/B50/B25/B00 | max(structural, lambda * detail)，T=.20 |
| 混合 | M75T30/M50T30 | lambda=.75/.5，T=.30 |
| 中等尺度 | C1U20/C1L50 | scales=[1,2,4]，lambda=1/.5，T=.20 |
| 粗尺度 | C2U20/C2L50 | scales=[1.4,2.8,5.6]，lambda=1/.5，T=.20 |

全部 gain=1、ink_sigma=.5，未逐图归一化。字段与精确参数见 [PRESETS.json](PRESETS.json)。

暂定优先比较：建筑 C2U20/A40/C1L50；头骨 A40/C1L50/C2U20；Ficus A30/C1U20/M75T30。不是自动生产选择，更不是 GT 信噪比排序。B00 纯结构会丢失大量主体，保留为负例。

## 源码与执行

代码位于 [`reproduction/radegs_spatial_rgb_tuning_v01`](../../reproduction/radegs_spatial_rgb_tuning_v01)。原 Spatial `boundary.py` SHA256：`11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30`。

```bash
cd reproduction/radegs_spatial_rgb_tuning_v01
python -B test_detector.py
python -B apply_preset.py --input /path/to/input_rgb_float32.npz --preset C2U20 --output /mnt/hdd1/u00134/radegs_paper_reproduction_v01/spatial_rgb_tuning_v01/new-replay-output
```

单图入口读取原任务根的 PRESETS.json，输出必须位于该任务根且目录尚不存在；离开远端环境需先显式适配 common.py 的任务根并部署 PRESETS.json，不是开箱即用 CLI。单图入口只读取 RGB 字段，保持 float32（包括原始 HDR 渲染值），并输出 soft/darkness/marked/skeleton/candidate_darkness。依赖 numpy、scipy、OpenCV、scikit-image；详细原执行命令及只读环境见 [RUN_COMMANDS.md](RUN_COMMANDS.md)。批量重现依赖已封存源模型渲染输入和原任务注册表；当前脚本有明确的远端任务路径，不宣称下载仓库即可独立复现所有数据。

## 验证与未上传内容

16 项测试通过；176 组输出回读通过；DTU 10 张 A20 与原 05 检线缓存位级一致。图像更干净不等于三维定位正确，候选数量不是 SNR。评估视角已在历史研究中查看，用户据图选择后不能再称盲测。

仓库仅包含本轮代码、配方、统计、报告与轻量选图。未上传原始 checkpoint、训练数据、完整 846 MB 数值交付包、176 组 NPZ 或 3D PLY/NPZ；原生图片包保留在任务目录并已通过聊天交付。其它未提交的研究目录不包含在本提交中。
