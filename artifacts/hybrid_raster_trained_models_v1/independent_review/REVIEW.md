# 独立工程复核

当前已完成的是运行前检查，**不是四个训练模型或196帧实验的完成证明**。最终实际产物以 `ACQUISITION_FINAL.json`、`PRODUCTION.json` 与逐阶段访问审计为准；文件未生成时对应验证尚未执行。

`INHERITANCE.json` 逐字节核对旧 LOCK、六个科学源码、patched/unpatched 两个隔离 CUDA 二进制；当前工作区与旧源码均相同。科学参数 hash 保持 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`，包括原尺度、A/B/C 定义和作者增益，无新 F 拟合。正常法线仍是 raster/splat 语义，缺少 filter3D；作者列为独立重建、非官方。

`ACQUISITION_PREFLIGHT.json` 核对 upstream pin、许可证、隔离副本与三处受控补丁、既有二进制、manifest、默认训练 schedule 和 TRAIN 元数据。训练保持 seed1729、30000步、原生分辨率、白底、SH3、原 photometric loss 和默认 densification。必要差异明确为全部100 TRAIN 相机（旧 Lego 是86）、禁止 TEST/VAL、仅 TRAIN 内样本诊断、I/O 封存及精确 RNG/camera-stack resume。C 将参与 photometric 训练，只对 NPR 拟合留出，不是 blind evaluation。

相机阶段有不可消除的依赖：旧 arc 中心由最终 checkpoint 的 float64 位置 .001/.999 分位框计算，不能在模型尚不存在时伪造精确 arc。因此训练前冻结 F/C 精确矩阵、checkpoint 目的地与唯一 arc 算法；训练完成后先冻结 checkpoint hash，再封存并推送精确33 poses，之后才允许 NPR。独立 checker 重算整个轨道并检查33 distinct、Materials 独立 FoV、399.5主点及每场景49帧；0/0或缺帧均不能 PASS。

实际 RED 为缺少 checker 模块的导入失败，随后 GREEN。11个独立合成测试覆盖：源/参数改动、seal 缺失/额外/损坏、launch冻结顺序、相机 FoV/主点/重复、未完成trace、失败的禁读尝试、-yy显示的 TRAIN symlink目标，以及 NPR 忽略的 full-SH f_rest 字段中的 NaN。45项旧 CPU 回归通过，旧fixture写入新工作区 sandbox；这些都不计为新增scene产物。

协议首次推送 `8b3915b5e3211530beefd8606dbdcdd5cdf25e2d` 后，7项相关旧 GPU/包装器回归通过，三个隔离子进程均退出。每次启动前 nvidia-smi/PID 检查为空，旧构建只读；数据是合成 splat fixture，不是新scene校准。三个实际trace首次因 `-yy` 的 `/dev/nvidiactl<char 195:255>>` 嵌套设备注释而保守拒绝。明确工程修复第1轮只修改独立parser：实际RED→GREEN，并额外拒绝缺角括号、坏设备号及普通文件伪注释。最终12项独立测试通过；原INVALID报告和trace保留。修复后3个trace分别审计7926、1768、1766次尝试，无源图像/TEST/VAL/mesh/越界写入；详见 `FIX_ROUND_1.json`、`PRIOR_GPU_TESTS.json` 和 `GPU_ACCESS_*.json`。

`INPUT_FREEZE_ACCESS.json` 检查实际输入hash进程的924次 openat/openat2尝试：909次成功、15次失败、800次TRAIN PNG打开（400文件各进行hash及头检查），没有 TEST/VAL/mesh/越界写入。原 `-qq` 隐去exit行，首次检查保留为 `INPUT_FREEZE_ACCESS_INITIAL.json` 的不完整记录；最终采用 exact trace SHA 绑定、exit_code=0 的执行回执，不篡改trace。系统调用本身不能证明是否decode；无decode由执行的freeze源代码支持。

`ACQUISITION_PREFLIGHT_ACCESS.json` 另外覆盖独立preflight进程及子进程：446次打开尝试，源图像打开0次，没有禁读或越界写入。访问审计只覆盖所记录进程的 open/openat/openat2/creat 范围；当前实际出现的调用均为 openat/openat2。-yy返回fd目标用于识别 staged TRAIN symlink，未记录的会话操作和无注释动态symlink不在证明范围内。

生产checker要求所有 raw/typed 数值有限，完整检查原ID/raw alpha*T、公式互补、provenance、标量诊断、作者原值和固定gain、原生PNG像素/尺寸、全部33帧视频decode/distinct/hash、1600宽H264/yuv420p/faststart。校准双方buffer独立重算误差。训练checker核验两次checkpoint、所有PLY数值（含45个被NPR忽略的f_rest）、全部30000条loss、单次fresh launch、恢复身份、GPU归属和实际TRAIN-only trace。工程有效不等于线条质量更优；human review仍待完成，无固定3D或时序收益主张。
