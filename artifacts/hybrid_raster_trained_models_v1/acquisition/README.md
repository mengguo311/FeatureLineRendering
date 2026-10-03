# Vanilla acquisition（冻结执行契约）

上游为 Graphdeco `gaussian-splatting` 提交 `472689c0dc70417448fb451bf529ae532d32c095`。只读旧 LEGO seed1729 的 entry、manifest、cfg_args 与两份 TRAIN 启动脚本；逐文件哈希见 ACQUISITION.json。许可证保留于 LICENSE.upstream.md，隔离源亦保留 LICENSE.md。

相同设置：30000 iteration、seed1729、SH degree3（每1000步升阶至3）、resolution=-1（800输入不缩放）、白背景、原始0.8L1+0.2DSSIM、默认optimizer/LR/densification，以及官方100000随机初始点 xyz∈[-1.3,1.3]、SH2RGB(random/255)。NPR后续有意只读SH0。

必要差异：旧LEGO实际86张TRAIN参与优化、16张VAL仅作diagnostic，本轮每场景全部100张TRAIN参与优化，绝不访问VAL/TEST metadata或pixels。C相机亦训练过，只在NPR参数拟合中留出，不能称blind或generalization。strict Blender loader直接产生空test_cameras；wrapper验证每个路径必须是train目录。源photometric loss、学习率与densification代码未改；patch仅seed、TRAIN-only与snapshot I/O接点。GUI关闭、TensorBoard由显式losses.jsonl替代；7000/30000保存F1/F41/F79源图/全SH渲染配对，明确in-sample且不设质量gate。

每场景目录为 out/hybrid_raster_trained_models_v1/training/{scene}/seed_1729，PLY保留iteration_7000及30000；snapshot额外保存optimizer、Python/NumPy/Torch/CUDA RNG、完整camera排列及剩余抽样stack。resume必须manifest和snapshot哈希一致，累计2h上限。初始点、缓存均在此目录；只以TRAIN目录symlink读取原图，源assets不写入。保留≥1GiB磁盘储备，写PLY/snapshot前按实际Gaussian/tensor大小检查，空间不足是失败而非删减要求的checkpoint。

启动使用run_training.py --manifest acquisition/manifests/{scene}.json --gpu 0|1 --freeze-commit SHA。wrapper核对manifest与已提交且远端一致的freeze SHA，检查所有source/module/input hash，逐GPU flock及nvidia-smi/PID guard。目标GPU必须空闲；其他GPU只允许当前run目录内、同UID且精确entry/manifest命令可验证的自己的训练，任何foreign job拒绝启动。strace -f -q记录真实训练后代open/openat/openat2/creat及退出；Landlock只允许TRAIN inputs/运行库读取和本场景目录、/dev写入。审计覆盖该子进程树，不宣称整会话系统调用全覆盖。

TDD_RED.log为模块不存在时的真实失败；TDD_GREEN.log包括严格TRAIN loader/path、seed实际CPU RNG、checkpoint实际保存恢复+camera/RNG、manifest mismatch、atomic status、GPU foreign拒绝等10项。LOADER_CPU.log和newout/training/LOADER_CPU.strace实际运行patched upstream reader的合成4×4输入，无GPU初始化，确认2TRAIN/0TEST/100000初始化点。此fixture不是新scene实验，也不替代实际训练trace。
