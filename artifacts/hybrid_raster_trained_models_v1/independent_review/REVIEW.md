# 独立工程复核

最终结论：四个模型的实际30000步训练全部通过独立复核；Hotdog的49帧和全部媒体产物完整通过。**总体仅49/196帧，缺147帧，状态为存储阻塞下的INCOMPLETE，不是完整实验PASS。** Materials/Mic/Ship尚未做NPR校准或渲染，不构成科学负结果。精确结论与证据hash见 `CONCLUSION.json`；逐模型训练见 `ACQUISITION_FINAL.json`，原始字段、媒体与缺失清单见 `PRODUCTION.json`。

四个场景的实际30000步 acquisition 已全部通过独立复核，且 `ACQUISITION_FINAL.json` 对四场景再次实际核验通过：合计120000条有限loss、四次fresh launch、8个PLY和8个snapshot及sidecar；所有62个PLY数值字段含45个full-SH系数均有限。四个实际训练trace各3156次打开尝试、200次TRAIN源图打开，未发现 TEST/VAL/mesh/越界写入。每场景 checkpoint 中心和全部 arc 的独立重算误差均为0，33 poses各自distinct；Materials 独立FoV为0.6194058656692505、native fx为1250.0000504168488，不能沿用其他场景焦距。四个CPU resolve trace各615次打开尝试、0次源图打开。上述仍不替代之后的 NPR 校准和196帧完整交付检查。

`ACQUISITION_PACKAGE.json` 另核对四个场景52个小证据副本与运行原件逐字节一致，以及36个保留大文件和24幅TRAIN内样本诊断的SHA；不把这些诊断算作 NPR 帧。`TEST_INDEX.json` 按最终有效suite去重，合计92项（独立13、acquisition12、transport10、离线summary5、旧CPU45、旧GPU/包装器7）通过；另单列最终8×8两步真实CUDA训练集成，不把合成fixture或RED/重复运行计入92项或场景产物。

`INHERITANCE.json` 逐字节核对旧 LOCK、六个科学源码、patched/unpatched 两个隔离 CUDA 二进制；当前工作区与旧源码均相同。科学参数 hash 保持 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`，包括原尺度、A/B/C 定义和作者增益，无新 F 拟合。正常法线仍是 raster/splat 语义，缺少 filter3D；作者列为独立重建、非官方。

`ACQUISITION_PREFLIGHT.json` 核对 upstream pin、许可证、隔离副本与三处受控补丁、既有二进制、manifest、默认训练 schedule 和 TRAIN 元数据。训练保持 seed1729、30000步、原生分辨率、白底、SH3、原 photometric loss 和默认 densification。必要差异明确为全部100 TRAIN 相机（旧 Lego 是86）、禁止 TEST/VAL、仅 TRAIN 内样本诊断、I/O 封存及精确 RNG/camera-stack resume。C 将参与 photometric 训练，只对 NPR 拟合留出，不是 blind evaluation。

**第3轮发现并纠正了前述来源证明的缺口。** 早期 preflight 确认的是“外部工作文件→隔离副本”的 SHA 相同以及 Git HEAD 的提交名，没有独立证明每个工作文件都等于该提交的 blob。外部 `gaussian_renderer/__init__.py` 实际带有未提交改动，将标准 rasterizer 的两个返回值解包改为四个；这使第二个合成训练fixture失败。早期 PASS 报告全部保留，只能按工作文件身份一致理解，不能用来证明 pristine upstream。失败发生在任何真实场景训练之前；没有把它计为场景负结果。

最终第3轮的 `ACQUISITION_ROUND3_PREFLIGHT.json` 对全部17个文件独立执行 `git show 472689c0dc70417448fb451bf529ae532d32c095:path`，重建唯一已声明的 seed/TRAIN-only/I/O 补丁，逐字节比较隔离文件和记录的 patch。旧 Lego 实际 vendor 也逐文件对照：除已知 train/general_utils 的 seed 补丁外均与 Git pin 相同，标准 renderer 的正确 hash 为 `75fcc86a57d27d9ea55b2904a4faaf075e7f73dba8c54bcb6cbd4c02c4884084`。外部脏工作文件和 diff 只读保留，没有回写修复。新增 dirty-renderer 拒绝测试实际RED→GREEN；独立测试合计13项通过。该轮独立preflight的实际trace共1055次打开尝试，源图像0次，无 TEST/VAL/mesh/越界写入。NPR 科学源码、尺度和二进制均未改变。

相机阶段有不可消除的依赖：旧 arc 中心由最终 checkpoint 的 float64 位置 .001/.999 分位框计算，不能在模型尚不存在时伪造精确 arc。因此训练前冻结 F/C 精确矩阵、checkpoint 目的地与唯一 arc 算法；训练完成后先冻结 checkpoint hash，再封存并推送精确33 poses，之后才允许 NPR。独立 checker 重算整个轨道并检查33 distinct、Materials 独立 FoV、399.5主点及每场景49帧；0/0或缺帧均不能 PASS。

实际 RED 为缺少 checker 模块的导入失败，随后 GREEN。独立合成测试覆盖：源/参数改动、seal 缺失/额外/损坏、launch冻结顺序、相机 FoV/主点/重复、未完成trace、失败的禁读尝试、-yy显示的 TRAIN symlink目标，以及 NPR 忽略的 full-SH f_rest 字段中的 NaN。45项旧 CPU 回归通过，旧fixture写入新工作区 sandbox；这些都不计为新增scene产物。

协议首次推送 `8b3915b5e3211530beefd8606dbdcdd5cdf25e2d` 后，7项相关旧 GPU/包装器回归通过，三个隔离子进程均退出。每次启动前 nvidia-smi/PID 检查为空，旧构建只读；数据是合成 splat fixture，不是新scene校准。三个实际trace首次因 `-yy` 的 `/dev/nvidiactl<char 195:255>>` 嵌套设备注释而保守拒绝。明确工程修复第1轮只修改独立parser：实际RED→GREEN，并额外拒绝缺角括号、坏设备号及普通文件伪注释。最终12项独立测试通过；原INVALID报告和trace保留。修复后3个trace分别审计7926、1768、1766次尝试，无源图像/TEST/VAL/mesh/越界写入；详见 `FIX_ROUND_1.json`、`PRIOR_GPU_TESTS.json` 和 `GPU_ACCESS_*.json`。

`INPUT_FREEZE_ACCESS.json` 检查实际输入hash进程的924次 openat/openat2尝试：909次成功、15次失败、800次TRAIN PNG打开（400文件各进行hash及头检查），没有 TEST/VAL/mesh/越界写入。原 `-qq` 隐去exit行，首次检查保留为 `INPUT_FREEZE_ACCESS_INITIAL.json` 的不完整记录；最终采用 exact trace SHA 绑定、exit_code=0 的执行回执，不篡改trace。系统调用本身不能证明是否decode；无decode由执行的freeze源代码支持。

`ACQUISITION_PREFLIGHT_ACCESS.json` 另外覆盖独立preflight进程及子进程：446次打开尝试，源图像打开0次，没有禁读或越界写入。访问审计只覆盖所记录进程的 open/openat/openat2/creat 范围；当前实际出现的调用均为 openat/openat2。-yy返回fd目标用于识别 staged TRAIN symlink，未记录的会话操作和无注释动态symlink不在证明范围内。

生产checker要求所有 raw/typed 数值有限，完整检查原ID/raw alpha*T、公式互补、provenance、标量诊断、作者原值和固定gain、原生PNG像素/尺寸、全部33帧视频decode/distinct/hash、1600宽H264/yuv420p/faststart。校准双方buffer独立重算误差。训练checker核验两次checkpoint、所有PLY数值（含45个被NPR忽略的f_rest）、全部30000条loss、单次fresh launch、恢复身份、GPU归属和实际TRAIN-only trace。工程有效不等于线条质量更优；human review仍待完成，无固定3D或时序收益主张。

Hotdog 首次 NPR 执行在27个完整frame、28个raw封存后异常中断；工具返回143，信号来源未知。`HOTDOG_RENDER_ATTEMPT000_ACCESS.json` 因实际trace缺少子进程exit保持INVALID，未填造完成回执。`HOTDOG_PARTIAL.json` 对27个完整frame逐个检查raw/typed/provenance/公式/所有PNG像素及seal无错误，但仍标INCOMPLETE（目标196）；第28个raw arc011另经完整native/context检查，未封存的frame staging不计入数量。`HOTDOG_RESUME_INTEGRITY.json` 只认定同参数确定性续跑的缓存完整性：旧PID消失、seal锁为空，原失败证据和staging保留。原runtime快照与622秒保守预算计费单独核对。这个续跑资格不撤销首段系统调用审计的不完整性，也不构成实验PASS。

最终四场景预期验证实际完成：Hotdog全部49帧逐一通过raw/typed数值、原ID、alpha*T、provenance、互补公式、diagnostics、作者固定gain、所有PNG完整decode与seal检查。6个视频各完整decode33帧且33帧distinct；原生4000×832，Telegram1600×368，后者另核对H264/yuv420p及MP4 moov在mdat之前。15个contact、9个first/mid/last均通过，所有SHA与封存manifest一致。首次验证CPU前台进程也遭143中断，原因未知；原log/trace与INVALID审计保留，未修改checker，改以独立进程重新执行后完成（exit1表示另外三场景缺失）。最终验证进程审计5454次打开、源图0次、禁读/越界写入0次，全部子进程exit齐全。

Hotdog续跑的实际trace审计49219次打开，媒体trace审计3351次打开，均无源图/TEST/VAL/mesh/越界写入且exit完整；原首次render的缺失尾部仍不在证明范围内。`INHERITANCE_FINAL.json` 再次确认六个科学文件、旧LOCK全部尺度及author gain、两个只读native二进制均未变。`FREEZE_ORDER.json` 逐一核对四场景TRAIN启动、checkpoint冻结、精确相机提交推送及Hotdog实际NPR启动顺序，并确认续用的27个frame seal和28个raw seal未改变。

真实存储阻塞已独立核对：Materials启动前guard退出，未启动producer；记录剩余1266896896字节，扣除固定1GiB硬保留后193155072字节，甚至小于Hotdog已测16个校准NPZ的206130333字节。后者仅是已测参照，并非对Materials压缩大小的预测。外部盘写入未获授权，未删除失败或已完成证据。所有模型和Hotdog完整产物保留；余下三个scene的147帧及相应媒体缺失。工程产物有效性不说明线条更好，仍需用户审阅，无固定3D或时序收益主张。
