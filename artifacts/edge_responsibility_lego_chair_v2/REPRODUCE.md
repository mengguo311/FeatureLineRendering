# 原生评分验证复现

依赖仅使用冻结v1路径：Python `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`，Graphdeco官方renderer及v1 object stage的已有stock/knn二进制。无需安装、训练底座或读取原始TEST图片。源PLY与旧目录只读。机器无人工内部语义标签。

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s experiments/edge_responsibility_lego_chair_v2/tests -v
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/edge_responsibility_lego_chair_v2/scripts/launch.py
```

launch启动独立session的普通runner；out下STATUS.json、EVENTS.jsonl、logs/runner.log及RUNNER_COMPLETE.json提供实际状态。每个原子unit先查询GPU0实际PID及磁盘空间，拒绝与foreign owner共享GPU。根保留4GiB、common Git保留1.5GiB、本stage上限10GiB；阈值固定。CPU2线程，GPU0单owner。文件锁阻止重复runner。失败单元保留，另一场景继续。

INPUT_FREEZE.json在首次GPU生产前保存代码、数据、模型、样本、24帧构造真值、相机、seed、颜色空间、容差和独立方向/幅度。已有freeze在源代码变化时拒绝继续。成功unit有seals哈希，resume核验后跳过。失败记录在failures；未成功unit可以重跑。不能改变旧freeze后冒充同次实验。构造探针为DC红通道和各向同性log-scale的±.01及±.005，另有三个固定尺度轴探针；独立验证为DC[.5,-.75,.25]和scale[1,-.5,.25]的±.006及±.003。

行为RED可用 `tests/legacy_regression_red.py` 复现（预期失败）；该脚本测试原封不动的v1证据接口，正常unittest验证新接口。CPU解析回归仅检验公式；真正的24帧验证用native Gaussian renderer。

结果保存在results、seals、两场景TARGET/GROUP_INPUT/RESPONSE_SELECTION_FREEZE。大型临时模型与样本缓存留在忽略的out中；原始full checkpoints不提交。发布media包含原生baseline、三种选核贡献/子集、正负完整渲染与float32差分、ROI和线性RGB剖面，SOURCE.json关联原始核row IDs、模型SHA及相机。arc33为新原生渲染，只用于展示。

评价为探索性：edit-holdout属于原始TRAIN且此前GS已见，不是新正式盲TEST。human visual GO仍pending。三项门槛未全通过时优化明确NOT_RUN。

主runner完成后，可顺序复现已封存的两个补充GPU单元与CPU复核：

```bash
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/out/edge_responsibility_lego_chair_v2/tmp"
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/edge_responsibility_lego_chair_v2/SUPPLEMENTAL_METRICS.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/edge_responsibility_lego_chair_v2/SYNTHETIC_SCORE_CHECK.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/edge_responsibility_lego_chair_v2/INDEPENDENT_CHECKS.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/edge_responsibility_lego_chair_v2/CURATE.py
```

主runner在成功unit的输出哈希不变时跳过GPU工作。补充runner也在自己的INPUT_FREEZE与seals下恢复；不得并行共享GPU0。原始失败不被补充夹具替换。SOURCE_MAP分别记录生产源和补充runner；生产源freeze保持字节不变。

GROUP_TIME_COST来自首次运行的resource/event日志，逐群结束时刻只有秒精度，因此保留实际时间区间而非编造GPU精确耗时。初次独立检查错误地把64上限视作平坦负例必须填满的数量；失败日志保留，后续检查改为同目标四种方法的数量一致（47/29核负例也合法）。科学门槛从未因此改为通过。
