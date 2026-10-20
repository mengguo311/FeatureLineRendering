以下为本轮实际运行命令记录。已有封存目录不得重跑写入型入口；只读完整性检查见末尾。计算均在授权worktree，CPU affinity[0,1]、线程≤2、CUDA禁用。

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/run_round015_tests.py
```

14组顺序执行：RED为预期rc=1（6项，3失败）；其余13组rc=0，共102次正常测试执行。每组准确子命令、rc、耗时、日志路径及SHA保存在对应执行收据。`TESTS.json`列全体收据；六项新测试的直接入口为`test_planar_temporal_metrics.py`（RED追加`--broken`）。继承测试不修改旧文件。

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round015_receipt.py PREPARE_EXECUTION experiments/partwise_sketch_hatching/run_round015.py prepare
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round015_receipt.py EVALUATION_EXECUTION experiments/partwise_sketch_hatching/run_round015.py evaluate
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/round015_receipt.py VALIDATION_EXECUTION experiments/partwise_sketch_hatching/run_round015.py validate
```

以上三项rc均0；子调用均由`taskset -c 0,1 timeout 600`包装。独立重放：12帧、496数组及全部时序/控制指标精确相等。完整历史回放6,864科学数组和180适配器数组精确相等。实际视频编码/完整解码命令与二进制SHA在`VIDEO_VALIDATION.json`，两项rc均0，12帧RGB完全相同。

协议`aadd5332`；算法/评价实现`1b9bd9b4`；评价前仅图题纠正`63891918`；最终锁`ee3c87bd`。prepare之后、评价之前纠正近邻放大图题，其先前锁SHA及唯一源码变更记录在ASSET_LOCK；协议、指标、轨迹及候选未变。报告提交由STATUS与SEAL记录。新增源码：`round015_common.py`、`round015_receipt.py`、`build_round015_protocol.py`、`planar_temporal_metrics.py`、`test_planar_temporal_metrics.py`、`run_round015.py`、`run_round015_tests.py`、`seal_round015.py`。

只读封存验证命令（不重新执行评价）：

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 taskset -c 0,1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching/seal_round015.py --verify
```
