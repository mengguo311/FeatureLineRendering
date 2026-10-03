# TRAIN → FREEZE → NPR：四个新场景冻结协议

本轮只为 hotdog、materials、mic、ship 获取缺失的标准 vanilla 3DGS 模型，再运行已冻结的 NPR recipe。用户本轮明确允许这四个模型的光度训练；该许可取代旧 extra-model 协议的禁止训练条款，不扩大为几何监督、NPR 优化、路由或时序方法研究。

工作区 `/home/u00134/3dgs_line/hybrid_raster_trained_models_v1`，分支 `hybrid-raster-trained-models-v1`，基点 `fef9b8566b9fc3aa42a8639b336987b302041c99`。代码和报告在 `artifacts/hybrid_raster_trained_models_v1`，运行产物在 `out/hybrid_raster_trained_models_v1`；其他 worktree、原始数据、旧模型、构建、日志只读。使用既有 vfsdgs 解释器，不安装包、不改全局设置、不终止其他作业。任务模型及子任务指定 gpt-6-astra / ultra。

## 开放顺序与相机冻结

1. 只读继承 extra-model 的 PROTOCOL/REPORT/INPUTS/INHERITED_LOCK，旧 raster v2 的协议、源码及真实 LOCK；读取旧训练入口、LEGO seed1729 entry/manifest/cfg_args 和标准源码。读取并 hash 四个场景的 TRAIN 元数据/文件，先做 CPU 合成 RED→GREEN。
2. 在任何 GPU、训练、新场景结果查看前，提交并推送本协议、确定性 TRAIN 输入 hash、采集配置/源码 hash、checkpoint 目标路径和精确 F/C 相机；核对远端 SHA。
3. 每场景固定一次 30k 训练。保存 7000 和 30000 checkpoint、种子、损失、资源、时间、命令、状态及 syscall trace。失败保留，不通过更改模型或 recipe 掩盖。
4. 训练结束先封存 checkpoint SHA，再从此 checkpoint 按继承算法生成并封存精确 49 帧相机清单；该解析清单再次提交、推送，之后才可启动 NPR 校准/渲染。不查看结果后挑选相机。
5. 所有新场景先逐场景八 F 做 patched/unpatched 数值校准，再解释字段。通过者完整生成 49 帧及媒体；无效者保留具体失败和缺失计数。NPR 使用旧参数，不拟合新 F。

**相机依赖披露：** F/C 外参与内参可以在训练前精确冻结。继承 arc 的中心来自训练后 checkpoint 的 `.001/.999` quantile box，所以训练前不可能诚实填写精确 arc 矩阵。本轮训练前冻结完整确定性构造、端点、33 个 t 和目标 checkpoint；checkpoint 封存后、任何 NPR render 前才解析、提交精确矩阵。这是数据依赖的两阶段冻结，不采用初始化中心，不假造训练前已知的姿态。

F=`[1,14,27,41,53,67,79,93]`，C=`[7,21,33,47,59,73,86,99]`，固定四场景，各 8F+8C+33arc=49 帧，总期望196。所有相机来自 TRAIN，原生800×800。`w2c=inv(transform_matrix @ diag(1,-1,-1,1))`；`fx=800/(2*tan(camera_angle_x/2))`、`fy=fx`，主点399.5。Materials 使用自身 FoV=0.6194058656692505，其余三场景0.6911112070083618。清单保存实际值及矩阵，不借旧 Lego 焦距。

arc 固定 C7→C33，`t=linspace(0,1,33)`。严格沿用 `artifacts/direct_curve_global_fit_probe/freeze.py`：`mu.astype(float64)` 逐轴 `.001/.999` quantile，两角均值得中心；对称0.1×box diagonal扩边不改变中心。相对中心的相机位置方向球面插值、半径线性插值；c2w rotation 独立 SciPy Slerp；组回 c2w 后取逆。不重建 look-at。33 pose 必须互异。

## 标准采集及必要差异

标准源 pin `472689c0dc70417448fb451bf529ae532d32c095`，来自只读 `/home/u00134/3dgs_line/ext/gaussian-splatting`。最小源码复制到本轮隔离目录并保存原 license/逐文件hash。复用既有 official vanilla rasterizer 和 simple_knn，不改环境或旧二进制。

精确旧依据为 `/home/u00134/3dgs_line/tier1/scripts/{multiscene_train_entry.py,run_multiscene_training.py}` 及 `tier1/out/multiscene_foundation/training/lego/seed_1729/{entry.json,manifest.json,checkpoints/cfg_args}`。固定 seed1729、iterations30000、resolution=-1（实际native800）、SH degree3、white background、random_background=False。标准随机100000点初始化：xyz均匀[-1.3,1.3]，SH2RGB(U/255)颜色；初始化PLY/cache只写本轮。原始损失 `(1-.2)*L1+.2*(1-SSIM)`，无normal/depth/mesh/NPR监督或损失。默认 optimizer/LR/densification 参数完整记录于 ACQUISITION.json；同样每1000步提高SH阶，增密500→15000、间隔100、阈值0.0002、opacity reset间隔3000。保存7000/30000，不根据结果选 iteration 或重训。

必要差异逐项披露：旧LEGO输入为86个TRAIN相机并将16个VAL诊断帧暂存成test metadata（eval=True）；本轮严格使用原始全部100个TRAIN相机，不读取TEST/VAL元数据或像素。C全都参与vanilla GS训练，**C仅对NPR参数拟合留出，不是盲测或泛化评估**。fullSH训练后NPR仍只读取SH0，刻意沿用旧场景设置。端口/日志/输出路径及禁用GUI连接只属隔离执行差异。新增记录与可验证恢复机制不改变训练损失或迭代更新。

标准 reader 即使 eval=False 仍会打开 transforms_test.json；因此显式 wrapper 替换 Blender 回调，只读 transforms_train.json 和经过路径约束的 train PNG，test list恒空，拒绝越界路径。不能通过复制TEST元数据或假test文件绕过。合成fixture必须证明禁止路径未打开；实际整个训练进程及子进程 strace核对TRAIN文件、TEST/VAL/mesh访问和写入边界。监控/库文件访问的审计范围如实记录。

诊断只选预声明TRAIN F1/F41/F79，源RGB与fullSH训练渲染对照标注“in-sample TRAIN，仅检查灾难性输入问题”；不能宣称generalization，也不以自造分数门控科学优劣。不得解码C源图作NPR调参。Materials折射/高光和其他训练后验缺陷照实报告，不追加几何损失或阈值救援。

checkpoint 目标：`out/hybrid_raster_trained_models_v1/training/{scene}/seed_1729/checkpoints/point_cloud/iteration_{7000,30000}/point_cloud.ply`。保存完整训练状态及匹配清单的resume证据；恢复仅接受种子、输入、配置、源码、iteration和hash一致，不悄悄覆盖不匹配文件。STATUS原子更新；有效完成标记只在预期检查点完整且hash验证后写入。

## 精确继承的 NPR

`INHERITED_LOCK.json` 是旧真实 LOCK 的字节副本。文件SHA256=`d5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926`，parameter hash=`6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。六个锁定科学源逐字节不变；新增适配、路径和媒体代码另外hash。全局scale：D=.08261344276368612、A=.7444546544551854、N=.9862916707992548、C=.6385581493377686、G=1、visibility=1；作者增益分母=.7533644223213196。完整常数/阈值以锁为准，任何新F/C/arc不得重新归一化、扫参或逐场景调整。

A为同源SH0灰度RGB双尺度Canny、median-depth evidence、alpha silhouette的旧精确定义。B为OUR dense六通道连续读出，C=`1-(1-A)*(1-B)`。AUTHOR独立实现Hao–Mukai Eq1–5，明确标注 `AUTHOR independent reconstruction — NOT official`，保留原S_L和固定显示增益；不得将OUR dense写作作者官方方法。像素浓度变黑不等于有用线增益。

所有臂共享同一次 native renderCUDA traversal 的white SH0 RGB、alpha/depth；raw原Gaussian行ID、raw alpha*T top4（未重归一化）、对应depth/normal、全贡献二阶矩、normal length全部保留。空ID=-1且权重0、排序、ID范围、sum(top4)<=alpha+3e-6及有限性检查。top4归一化只给公式，coverage/遗漏质量单列。缺filter_3D不补造；法线是splat/ray-plane normal，非真值。

只读复用旧 v2 isolated patched/unpatched binary，逐文件验证其hash。每场景八F同输入数值校准：RGB/alpha/normal max_abs<=3e-6；depth/median-depth可接受max_abs<=1e-5且max_rel<=3e-6。camera/schema/export/nonfinite/calibration失败为工程无效或未定，不叫科学负结果。NPR沿用原GPU guard，全部训练结束后串行执行，不弱化外来作业检测。

## 产物、验证与资源

每个有效场景49帧全分辨率 RGB | A | B | C | AUTHOR 五列、各臂墨图和model overlay、原生响应、typed/provenance/diagnostic以及原子SEAL。native-best指原冻结recipe浓度，绝非挑选最优scene参数；另提供旧确定性等连续墨量控制，逐帧gain保留。所有F/C/arc保留，不挑帧。

完整33帧comparison/overlay/matched视频、全部contact sheets、首/中/末图；另给1600宽H264/yuv420p/faststart Telegram版本，重新绘标签保证可读，保留全部33帧。所有视频完整decode、33帧/33 distinct/尺寸/SHA核验后封存，不以静态动画替代。

CPU TDD覆盖TRAIN-only reader、seed、checkpoint/resume、camera/adapters，并保存真实RED/GREEN命令与退出码。新测试及相关旧回归、独立产物checker、锁/科学源参数相等性、实际launch访问审计均执行。审计不声称覆盖未trace的整会话。training与NPR全过程状态可查；失败清单硬计数，0/0不算196帧完成。

每次GPU launch前记录nvidia-smi设备/计算PID/所有者；两GPU仅在明确验证本任务进程及不同设备时并行采集，否则串行。检测不构成跨任务原子占用承诺，外来工作出现则不新启动、不终止对方。总预算12小时，每scene训练2小时，transport GPU进程墙钟4小时；工程最多3轮明确修复或90分钟（训练运行时间另计），超限保留真实阻塞。磁盘安全余量至少1GiB；不删除旧资产或损失性改存字段来掩盖容量不足。

初查本磁盘仅余约6.7GiB，旧NPR自身约7.9GB，存在明确容量风险。只有用户另行批准时才可将本轮新增大文件放到 `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1`，在本轮out下符号链接；批准及实际映射另存STORAGE.json。未批准时严格不写该目录，容量不足即记录真实阻塞。

最终中文REPORT记实测可见缺陷、资源/训练差异及限定，不声称额外墨量更好、fixed3D成功或时序收益。human review保持pending。FINAL.json列精确lineage/路径/计数/测试/资格/剩余门槛及已存在提交；包含它的最终提交用Git解析，避免自引用。提交前审阅diff，push后核对remote SHA与clean tree。动态AGENT.log/AGENT_FINAL/最终流只留ignored out，不纳入产物seal。
