# Gap recovery：实际运行完成，NO-GO

2026-09-18。本轮完成文献核验、三场景载体审计、Lego 预注册、实现、测试、
自动选桥、未参与选择的 TRAIN/DEV 验证及完整 120 帧视频。**方法未通过视觉
kill-test，不扩第二场景，不调阈值救结果。** 机器可读判定见 [RESULTS.json](RESULTS.json)。

## 文献与实现边界

[文献与设计](LITERATURE_AND_DESIGN.md) 区分原文、作者摘要和仅搜索命中的来源。
NerVE 原文已明确使用距离与切向一致性连接端点；SketchSplat 已有端点合并、
gap closing 和多视图图像优化；Active Strokes 已有图像／载体分离及笔触连贯性。
因此，本轮不声称这些组合本身具有新颖性，只检验一个局部机制：**固定 3D
桥假设能否由多视图可见边缘证据筛出有用补笔，并拒绝错误连接。**

实现：`src/stroke_bridge.py` 生成端点切向约束的固定 cubic Hermite 曲线，检查
尺度归一化距离、弧长／转角和 Gaussian 邻域密度；`src/bridge_evidence.py`
只在离线 TRAIN 视角评估中段 DT、方向与跨视图支持。遮挡是不可评价，
可见无边缘才是负证据；前景深度不匹配／背景跨越可以否决。`scripts/run_gap_recovery.py`
保存每条假设、原因、预算和固定顶点。原始路径不移动；运行时只投影并使用原有
GS depth 裁剪。`scripts/inspect_gap_recovery.py` 是结果检查工具，不进入选择。

## 数据与协议真实状态

| 审计场景 | 干净原路径数 | 通过几何筛选的桥假设 | 候选获取时间 |
|---|---:|---:|---:|
| chair | 1,258 | 997 | 0.044 s（复用已核验池） |
| lego | 1,986 | 405 | 59.011 s（重新生成） |
| cadpartA | 26 | 0 | 37.805 s（重新生成） |

Chair 只读复用 clean VRSS 全池并核验 SHA、TRAIN indices 和生成源码；其余采用
相同 frozen vanilla 配方重新生成，旧 provenance 不明的缓存没有进入方法。
假设数不是 G1 数。CadpartA 的大空段不符合当前局部端点桥条件，没有调整
抽取参数把它变成成功案例。三个场景的无 GT overlay 审计图保存在 `audit/`。

选定 Lego，在 image scoring 前标记 b71、b152、b153 三处可见 G1，见
[目标核查](audit/lego/target_inspection.png) 和 [人工评估标记](G1_AUDIT.json)。
G1 标记只用于评估；方法访问 guard 明确禁止读取它。
[PREREG](PREREG.md) 和 [MANIFEST](MANIFEST.json) 在选桥前提交；固定桥在打开
validation RGB／生成最终轨迹前另行提交。没有 TEST/VAL RGB 读取。

官方 full-SH RGB 使用固定官方 Python 源码和 stock CUDA kernel（逐次哈希见
`audit/*/audit.json`、`lego_dev/render_metrics.json`）。可见性深度仍是既有
vanilla GS disc G-buffer，**不是官方 renderer 的深度**。全 K 和 TRAIN-only
修复来自基点，相关回归仍通过。原始 GS 训练 split 未独立重建，TRAIN-only
保证的范围是本轮线抽取与桥证据流程。没有 mesh、GT label 或额外 2DGS normals。

## 数字：仅来自这次运行

8 个 fit 视角下，405 个几何假设中：67 个通过 image gates；306 个缺少足够
支持视角；18 个被深度／背景条件否决；14 个跨视图支持率不足。

| 指标 | object-only | object + image |
|---|---:|---:|
| 接受桥数 | 20 | 20 |
| 新增 3D 弧长（场景单位） | 0.328754 | 0.722429 |
| 视频平均新增可见线长 | 22.439 px/frame | 62.686 px/frame |
| 视频平均新增可见线长比例 | 0.2502% | 0.6999% |
| 视频最大新增可见线长比例 | 0.2907% | 0.7298% |
| 视频平均实际新增抗锯齿墨面积 | 9.036 px²/frame | 18.779 px²/frame |
| 全轨迹完全没有可绘制可见段的桥 | 5 | 5 |
| 通过预注册 held-out 支持规则 | 4/20 | 12/20 |

两组共 36 条不同的固定桥，全部进入主视频／消融和逐桥检查；没有只展示成功桥。
两组都先触及 20 条上限，远未耗尽 5% 墨长预算。**实际墨量没有相等**，不能把
任何画面差异单纯解释为 image evidence 优势。这里遵循的是相同上限、无低置信
补墨，不是严格墨量匹配的因果比较。

Fit+selection 11.124 s；held-out validation 3.355 s；三部完整视频及指标生成
29.653 s。三部 MP4 均实际解码核验为 120/120 帧、24 fps（5 秒），没有挑帧。
Python 3.9 / Torch 2.3.1+cu121，单 A6000 GPU。完整环境版本见 JSON。

## 亲自检查得到的视觉结果

已查看四帧主图、覆盖 0–119 的六页主 contact sheet、全部 36 条桥的六页局部
检查、b71 全 120 帧跟踪图，以及三个预注册目标在 TRAIN 1/27/79 的冻结补后图。
这是内部图像检查，**不是盲评，也不是参与者实验**。

* b71 确实被选中；在 TRAIN 1/27 的局部图中，底板边缘空隙被连接。
  [冻结目标补前／补后](lego_dev/preregistered_target_check.png) 同时展示 b152、
  b153 未修复，不能把只展示 b71 的放大图当完整成功。
* b152 的 fit 支持为 3/8，b153 为 2/7，被冻结的证据条件拒绝。不是预算挤掉。
  b152 多视角最近边缘方向不一致；b153 在一些视角 DT 和方向均不足。
  尚不能区分是 Hermite 位置偏差、原端点错位、最近边缘歧义或视觉 G1 标记的
  三维解释不成立；本轮没有额外实验去证明其中某一种解释。
* 主静帧与全轨迹原始／补后非常接近。许多新增桥只是重叠、加粗已有墨迹，
  个别连接只在放大图上可辨。b71 在最终轨迹也大多与原线重叠。
  当前接受准则奖励边缘支持，**未直接奖励实际消除可见空隙**，这一机制缺口
  是合理诊断，但不是已经通过消融验证的唯一原因。
* Object-only 的 16 条接受桥被 image gates 拒绝。但逐桥图没有清楚证明其中
  存在一个“视觉错误连接被正确拒绝”的反例；一些拒绝可能是有用补笔被误拒。
  数值拒绝次数不能冒充 image evidence 的机制价值。
* 所检查的完整轨迹没有发现明显持续大于 0.5 秒的穿透／跨部件长捷径；细小
  与隐藏桥的真实拓扑不能由此确认。Full 的 b60/102/172/298/299 全轨迹没有
  可绘制可见段，不能把它们计作成功恢复。

**额外协议限制必须保留：**冻结前没有查看的新 TRAIN-7-derived orbit 实际仰角
为 **87.4702°**，方向锥最大跨度仅 **5.0596°**。120 帧完整绕轴，但主要体现
俯视画面的平面内旋转，不是充分覆盖不同表面的遮挡压力测试。没有事后换轨迹
挑效果。此缺陷限制时间／遮挡结论；G1 选择门槛失败则在打开此轨迹前已成立。

## 逐条 GO/NO-GO

| 预注册条件 | 判定 |
|---|---|
| 三个 G1 至少两个在多视角持续修复 | **FAIL**：只选中一个，整体轨迹收益仍不明显 |
| 图像证据拒绝明确错误的 object-only 连接 | **未证实，不算通过** |
| 完整视频无持续 >0.5 s 明显错误 | 所观察轨迹未发现；近俯视和隐藏桥限制外推 |
| <=5% 新墨且连续性／可读性明显改善 | 墨长通过，**视觉改善 FAIL** |
| held-out 中多数接受桥仍有支持 | **PASS，12/20**，仅是证据一致性 |

**总判定 NO-GO。** 没有扩展到第二个 recovery 场景，没有 Hermite 参数扫掠，
没有增加网络、mesh、2DGS normals、逐帧 2D 补墨或重训。
代码完成、held-out 边缘支持及一点局部补笔，都不等于视觉方法成功。

## 产物与复现

主产物：[四帧主图](lego_dev/fixed_quartiles.png)、
[消融四帧](lego_dev/ablation_quartiles.png)、
[全桥诊断](lego_dev/bridge_debug.png)、
[完整主视频](lego_dev/rgb_original_recovered.mp4)、
[消融视频](lego_dev/ablation_original_object_full.mp4)、
[完整彩色诊断视频](lego_dev/bridge_debug_all.mp4)。视频／npz 留服务器，Git 忽略。
`contact_sheet_00..05.png` 覆盖所有主帧，`all_bridge_crops_00..05.png` 覆盖所有
选中桥。后者按每桥可见长度最大帧取局部，仅供定位审计，不是主结果挑帧。

原始 JSON：`fit_evidence.json` 有每桥物空间项、8 视角证据及拒绝原因；
`frozen_bridges.json` 有所有最终固定顶点／IDs 与预算；`validation.json` 有
4 个 held-out TRAIN 视角证据；`render_metrics.json` 有逐桥逐帧可见长度、
实际墨面积、视频哈希、运行时间。方法的 `access_render.json` 中 RGB 读取为空。
所有穷举端点配对日志在服务器 `audit/*/hypotheses.json`，大日志不入 Git；
选中场景的输入哈希进入 manifest，生成方法和筛选摘要已经提交。

18 个相关回归测试全部通过，其中新桥模块 8 个，覆盖 good continuation、
确定性、G3 近邻拒绝、空中支撑拒绝、预算、深度跨层、遮挡中性和可见无边缘。
两个开发期输入类型错误在预注册前修复；没有基于实景结果修改阈值。

执行顺序（已完成的同名产物有意拒绝覆盖）：

```bash
PY=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
$PY -m unittest discover -s tests -v
# 从 audit 配方生成三个场景，每场景 candidates 后 audit；chair 依赖已核验 VRSS 池。
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 600 $PY scripts/run_gap_recovery.py candidates --scene lego
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 180 $PY scripts/run_gap_recovery.py audit --scene lego
# PREREG / MANIFEST 必须先提交；不允许任意换场景。
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 300 $PY scripts/run_gap_recovery.py fit --scene lego
# 将 frozen_bridges.json 原样提交后，程序才允许 validate / render。
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 180 $PY scripts/run_gap_recovery.py validate --scene lego
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 600 $PY scripts/run_gap_recovery.py render --scene lego
$PY scripts/inspect_gap_recovery.py
CUDA_VISIBLE_DEVICES=1 $PY scripts/inspect_gap_recovery.py --train-targets
```

在服务器已核验冻结池上复跑，可给 `fit`、`validate`、`render` 三个命令统一添加
`--run-name lego_repro_01`，结果另存于同名新目录，不覆盖历史。新选择仍必须先
提交才允许后两步。此输出目录参数在结果检查后加入，没有重跑或改写本轮数字；
产物各自保留实际运行源码 SHA。若从无缓存环境重建，须取得 manifest 指定的 GS、
TRAIN 数据与 stock renderer，先重建 acquisition，并重新核验／登记生成池的
哈希；不能把不同文件冒充这里已冻结的同一候选池。检查脚本针对原始 `lego_dev`。

里程碑：`c0e6bce` 文献／几何审计；`39c44fe` 预注册／证据门槛；
`2014846` 运行入口；`b510838` 在 held-out 前冻结最终桥。均 push 并核验远端 SHA。

下一步是保留这个负结果并停止扩场景。若另开研究轮次，先解决“可见 G1 的
空间定位与冗余候选”以及非退化验证轨迹的协议问题；不能把本轮失败解释成
只需放宽阈值，更不能把局部补笔包装成已经成立的 NPR 整体改善。
