# VRSS 最小实现 / 冻结执行入口

新核心文件只有 src/stroke_relations.py、src/stroke_select.py、scripts/run_vrss.py；必要测试在 tests/。未导入旧 run_m1b/strokeviz/dd3 的评估/2DGS 路径。

- TRAIN coarse Canny → LSD 有限长臂 → L/T 图像关系；角度、双尺度复现、每 cell 上限；候选 arm 匹配枚举 2–3 路径 AND bundles，同一 evidence 的不同 bundle 取 max。未能解释的关系保留分母。
- U 为可见路径对粗长线 evidence 的长度支持（短于 12px 的可见段线性折扣）；按候选全池可见长度归一化。D 为不同路径落在同一二值像素的 pair overlap / 全池可见长度。
- 全局一个路径开关，无逐视图 ID/alpha。所有 singleton/关系 bundle 的 deterministic gain/cost greedy；最多两次、固定 shortlist 的 1↔1/1↔2/2↔1 swap。精确重算受影响关系的 max/AND 增量；不是最优解声明。
- 渲染只对固定折线作线性细分，以查询 GS 可见性；不改变路径几何、连接或选中 ID。所有 A/B/C/D 共用细分、可见性和 1px 黑笔。
- 写入前检查分支和 protected baseline SHA。输入/候选/evidence hash、TRAIN indices、源码 hash 随阶段输出。Python open 和 cv2.imread 守卫拒绝非 TRAIN RGB、额外 ply、mesh、旧 cache；这是可审计入口，不声称可拦截任意原生库所有 IO。

## 有界执行

```
PY=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 120 "$PY" scripts/run_vrss.py smoke
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 1200 "$PY" scripts/run_vrss.py candidates
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 900 "$PY" scripts/run_vrss.py evidence
OPENBLAS_NUM_THREADS=1 timeout 900 "$PY" scripts/run_vrss.py select
CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 timeout 1200 "$PY" scripts/run_vrss.py render
```

入口拒绝覆盖已完成阶段；完整重跑须保存旧 out/vrss 产物后在独立 checkout 使用相同协议。测试命令见 PHASE0.md。

## 实现前测试诊断

首个双尺度 corner fixture 用 3px 黑线中心当 candidate，但 Canny 实际检测的是模糊后的两侧边缘（关系中心偏移约 4.3px），所以 3px 几何匹配正确拒绝。fixture 改为实心区域的边界；算法阈值未调整，尚未查看 chair 选择结果。

算法语义测试不代表视觉有效。chair 是否 GO 留待实际结果与固定帧/完整连续视频检查。
