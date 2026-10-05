# 复现与恢复

使用本独立worktree，Python `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`，CPU2/GPU0。已封存S0源配置不要修改。运行 `bash artifacts/representative_edge_gaussians_three_v1/run.sh --check-only` 校验阶段，去掉 `--check-only` 继续plain pipeline；每pose仅校验seal后跳过。已有F seal必须始终不变。deadline后停止并保存工程阻碍，不悄悄延长。

生产前运行18项CPU：`OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B -m unittest discover -s artifacts/representative_edge_gaussians_three_v1/code -p 'test_*.py' -v`。

顺序：`run.py evidence`、`run.py contributions`（全部24F按K32→需要时K64/K128）、`selection.py`（先新A和counts seal，再全部F选择seal）、`audit.py`、`evaluate.py`（全147）、`projection_audit.py`、`delivery.py`、`ledger.py`、`verify_delivery.py`。pipeline顺序执行，nohup独立进程即使编码agent退出仍可恢复。config预算为规则，运行具体counts只从immutable BUDGET_SEAL读取。

A是same algorithm newly computed，legacy_core字节相同，旧Mic-onlysigma1normalization原样；新多尺度直接读旧MicF持久化scales，不拟合新场景。每个场景所有输入原场景ID，tree显示别名Ficus，ficus不替换。

SOURCE_MAP列原checkpoint、cached native与camera、所有封条、前景CSR、objective矩阵、selected IDs、图、原尺寸完整视频的绝对路径/bytes/SHA256。大数组留out，不发布Git。报告每scene六图；Telegram1600视频在media，native在out/scene/media。独立视频decode去标题RGB内容distinct及camera hashes在FINAL，父母/第三方需自己下载观看，人类验收PENDING。

旧native为第三方RaDe与历史项目独立插桩，只读；K64 helper验证二进制/build/capacity-onlypatch后引用，不复制或改写。若资源、GPU外来进程、来源hash、calibration失败，STATUS保留具体工程阻碍与实际阶段；未跑null。旧报告与模型不可改名。
