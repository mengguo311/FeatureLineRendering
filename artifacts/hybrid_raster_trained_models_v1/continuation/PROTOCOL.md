# 已授权外部存储续跑协议（GPU 前冻结）

本次仅恢复因根磁盘容量守卫中断的既有四模型 NPR 实验，不改变方法或科学设置。基线为工作树 `/home/u00134/3dgs_line/hybrid_raster_trained_models_v1`，分支 `hybrid-raster-trained-models-v1`，提交 `607b908a5dd0f195a55dd97fc4161cbd7a839d6c`。用户明确授权新大文件根 `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1`。该目录当前已有本会话 agent task/log/launcher；保留它们，不要求目录重新为空。

## 路径和写入权限

`STORAGE_MAP.json` 是精确机器可读映射。Hotdog 49帧及6视频继续从原工作树 `out/hybrid_raster_trained_models_v1/transport` 只读解析；Materials、Mic、Ship 的所有新 raw/fields/calibration/staging/media/native logs/runtime/cache/temp/launch logs 均写到授权外部根。已有训练 checkpoint、相机、来源、二进制和全部旧结果只读，不移动、不删除、不重训，不在其他路径建立 symlink 来绕过 guard。

小代码、metadata、报告写当前工作树的 `artifacts/hybrid_raster_trained_models_v1`。仓库文件系统始终保留至少 1073741824 字节；每次启动分别记录仓库根和外部根空闲量、空间门槛与 GPU 计算进程。GPU存在任何外来计算PID即拒绝启动，保留原生 gpu_guard。仅当前任务拥有的进程可受本任务超时管理。环境沿用现有 vfsdgs 解释器及原 native binaries，无安装、无全局修改。会话日志及 output-last-message 均留外部，不写跟踪封印目录。

## 冻结与可解释的存储适配

原 `transport/adapters.py` 和 `run_transport.py` 字节保持不变。新的 storage wrapper 仅绑定 `OUT` 及 native `STAGE` 到外部 transport，保留 `ROOT`、`ART`、native `NATIVE`、原 source manifest 和 seal context。原 producer 的 `__file__` 仍是真实旧源，不能伪造。另行记录新存储 glue 的精确 hash、路径映射及实际 binding receipt；独立核验同时核对两层。不存在科学源哈希被操作代码变化悄悄替代的问题；若实现必须改变该设计，先发布精确差异并重新冻结再运行。

原六个科学源码、patched/unpatched 二进制、四个 checkpoint 和全部精确相机哈希必须匹配。parameter hash 保持 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`，不重新拟合 scales、author gain、F normalization。输出原生800×800、SH0、白背景，原Gaussian行ID和 raw alpha*T；A/B/C/独立 AUTHOR Eq1–5 读出、相机矩阵与计算顺序均继承。AUTHOR 为独立重建 NOT official。C参与GS训练，仅对NPR参数拟合留出；不是盲测。TEST/mesh/源 C 图像不得由 NPR 读取。

## 执行与恢复

先完成新 rootmapping/adapters/seal/ownership 的 TDD RED/GREEN 和相关旧回归，审阅差异，将协议、mapping、可执行glue及测试提交并推送，核对远端SHA，记录 release receipt，之后才准 GPU。依次 Materials、Mic、Ship，每场景先完成全部8F patched/unpatched原容差校准，再生成8F+8C+arc33共49帧，然后生成媒体；总新增147帧及18视频。校准失败保持 ENGINEERING_INVALID，不算科学负结果，不调科学参数修救。

实际每次 render/media 用 `strace -f -q -yy -s 4096 -e trace=open,openat,openat2,creat` 包裹。持久supervisor记录 START/LAUNCH/EXIT、stdout、资源及完整trace；记录正常退出及全部已观察PID退出，不以命令字符串冒充执行。新trace只证明各自捕获进程树，不补齐旧Hotdog第一次143中断trace。旧第一次独立checker143证据也保持 INVALID。失败帧/staging保留；只有上下文和完整seal有效才可跳过恢复，部分结果不能算成功。STATUS通过原子替换逐校准/帧/阶段更新。

预算从本次协议创建起：续跑GPU进程阶段合计≤4小时，墙钟≤8小时；本轮工程修复最多3个清晰轮次且≤90分钟。历史训练/Hotdog消耗单独报告，不重写旧计时。

## 核验、评审和交付

独立核验器必须显式覆盖两个存储根，重新检查Hotdog49和新增147，合计196帧、24视频、60联系表、36首中末面板。每视频完整解码33帧和33 distinct，核对原生4000×832与Telegram1600×368、H264/yuv420p/faststart及哈希；三种comparison/overlay/matched均为未经删帧33帧。完整raw/typed/provenance/diagnostics/camera/seal字段、原Gaussian IDs、alpha*T、参数/源码/二进制/相机/校准都要核验。禁止仅从路径或期望数量推断完成。

模型实际查看每个新场景 F1/F41、C7/C47、arc000/016/032，完整F/C/arc联系表、五列 RGB|A|B|C|AUTHOR、white-ink/同相机overlay/等墨量 controls。中文报告如实描述内部密纹、轮廓与细节；这只是模型review，人类GO仍待定，不声称更多墨量代表更好、不声称fixed3D或temporal增益，不升级旧训练/科学成功状态。

在仓库硬保留允许时仅复制小JPEG评审图和Telegram视频到跟踪 `artifacts/.../review/` 或 `media/`，实际push并readback校验hash，保证GitHub链接可访问。巨大原生字段/视频保留外部并提供精确路径/hash清单；不得为交付挤占硬保留。若必要可仅使用明确记录的本地Git object storage适配，禁止全局设置改变，避免不必要复杂性。

历史 `REPORT/FINAL/REPRODUCE/STATUS` 与全部小审计源证据在 `historical_607b908/` 逐字节保存，`SNAPSHOT_MANIFEST.json`绑定251文件。最终新REPORT/FINAL应连贯说明历史与新增范围、两个存储根、真实计数、测试、实际审计缺口、剩余人类review，并提交推送核对远端SHA和干净工作树。
