# 四模型冻结 NPR：双存储根复核与续跑

本次是已有30000步模型的存储续跑。不得重新训练、重新拟合尺度或作者增益、重算/改变冻结相机、改变原生800×800、白底SH0或科学代码。C参与GS训练，仅对NPR拟合留出，不是盲测；AUTHOR是独立Eq.1–5重建，NOT official。

工作树：`/home/u00134/3dgs_line/hybrid_raster_trained_models_v1`。现有解释器：`/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`。以下均从该工作树运行。原始复现说明及全部小证据见 [历史快照](continuation/historical_607b908/REPRODUCE.md)，保持字节不变。

## 冻结与路径

GPU前存储续跑代码/协议冻结提交：`baadea14f7dfe74722dfb9b896135882d3f1a614`；release receipt在提交 `95c79369fd8e614084f5db092f2bb9798efe783f` 推送后核验。详细机器映射：[STORAGE_MAP.json](continuation/STORAGE_MAP.json)，完整约束：[PROTOCOL.md](continuation/PROTOCOL.md)。原模型/相机的既有冻结顺序仍有效，不被此次存储冻结替换。

- 四个训练模型与全部原结果保留在原工作树，均只读。
- Hotdog已有49帧/6视频从 `out/hybrid_raster_trained_models_v1/transport` 解析，不重跑、不复制巨大字段。
- Materials/Mic/Ship的新校准/raw/frames/media/runtime写 `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/transport`。
- 新trace、运行日志、cache、临时文件和agent日志只写批准的外部根。
- 小metadata/STATUS/报告保留当前工作树。两根分别检查空间和归属，仓库硬保留1GiB。

`continuation/run_storage_transport.py` 只绑定原 `run_transport.OUT`、`adapters.OUT`、native `STAGE`。`ROOT`、`ART`、原producer文件路径和native二进制路径保持真实。原封印记录原源码；每次运行的外部binding receipt另行记录存储glue、映射与release hash。原producer、两个adapter/source manifest中的原文件及六份科学源码没有改动，新增代码精确diff见 [STORAGE_GLUE.diff](continuation/STORAGE_GLUE.diff)。

科学parameter hash：`6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。每场景先验证全部8F patched/unpatched原容差，再运行8F+8C+arc33。不存在新F拟合、per-scene rescue、路由或时间身份算法。

## 真实启动入口

以下命令是已授权阶段的复现方式，已有完整结果不要重复生成。按 Materials→Mic→Ship 串行执行，每阶段必须查看返回的外部 `EXIT.json`，确认 `completed:true`、正常exit0和完整trace后再进入下一阶段。预先核对 `STORAGE_FREEZE.json`，它会核对本地字节、Git blob与远端祖先。不要直接调用旧producer main，否则会回到旧根。

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/tmp /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/hybrid_raster_trained_models_v1/continuation/launch_storage.py --phase render --scene materials
IMAGEIO_FFMPEG_EXE=/home/u00134/bin/miniconda3/envs/vfsdgs/lib/python3.9/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/tmp /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/hybrid_raster_trained_models_v1/continuation/launch_storage.py --phase media --scene materials
```

媒体命令必须带上面进程局部 `IMAGEIO_FFMPEG_EXE`：它绑定旧Hotdog同一编码器和SHA，绕开自动探测写 `/dev/null` 被新guard拒绝的问题；不是安装或切换编码器。Materials首次media exit1及staging原件保留，修复记录见 [MEDIA_ENCODER_BINDING.json](continuation/MEDIA_ENCODER_BINDING.json)。Mic和Ship仅替换`--scene`。启动器返回后实际detached supervisor继续工作；日志位于外部 `launchlogs/SCENE_PHASE_TIMESTAMP_ID/`。实际子进程由 `strace -f -q -yy -s 4096 -e trace=open,openat,openat2,creat` 包裹，保留 START/LAUNCH/EXIT、逐次GPU/双根空间守卫、资源、stdout与完整trace。仅管理本任务准确PID/starttime/private process group，不能停止外来任务。新4小时GPU阶段/8小时墙钟预算与旧历史预算分开。

只有原上下文及完整seal匹配的产物才可恢复跳过。失败帧/partial staging保留，不能覆盖为成功。原STATUS原子更新，最终总体计数依赖独立核验，不依赖目录名。

## 独立复核与报告

完整双根检查器复核196帧、24视频、60联系表、36首中末面板。包括原字段/typed/response/provenance/PNG、相机/参数/来源/seal、每场景8F校准，以及视频完整33帧、33 distinct、尺寸、codec/pixel format/faststart/hash。启动索引在 `continuation/LAUNCH_INDEX.json`，实际核验trace与退出记录另存外部。

```bash
IMAGEIO_FFMPEG_EXE=/home/u00134/bin/miniconda3/envs/vfsdgs/lib/python3.9/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2 PYTHONDONTWRITEBYTECODE=1 TMPDIR=/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/tmp /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/hybrid_raster_trained_models_v1/continuation/independent_review/verify_multiroot.py --launch-index artifacts/hybrid_raster_trained_models_v1/continuation/LAUNCH_INDEX.json
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/tmp /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/hybrid_raster_trained_models_v1/continuation/postprocess.py --phase aggregate
```

复核命令默认写新的 continuation 报告；若要保留已经发布的核验快照，使用 `--output artifacts/hybrid_raster_trained_models_v1/continuation/independent_review/PRODUCTION_RECHECK.json`。报告汇总器只消费既有diagnostics/provenance，不能替代完整checker。测试的精确命令、日志hash与唯一计数见 [TEST_INDEX.json](continuation/TEST_INDEX.json) 及引用记录；全部新测试夹具和日志在外部。

历史Hotdog第一次render与第一次checker均为未知原因143中断，原始不完整trace和INVALID结果保持原样；新完整trace绝不补齐旧缺口。模型视觉review不是人类GO，不可从墨量、支持数或视频视觉直接升级训练/科学成功结论。

## GitHub交付

本次GitHub小交付只包含 `continuation/DELIVERY.json` 实际列出的完整33帧Telegram comparison视频和新场景F_001与arc0_016双视角JPEG；精确数量、路径和复制/推送状态以该清单及远端readback为准。根文件系统可用空间在核验期间继续下降，完整12条Telegram加9张JPEG、含Hotdog的四场景comparison方案以及三个新场景comparison加三个双视角JPEG方案均未通过当时仓库1GiB硬保留量的守卫。未上传的comparison、全部overlay/matched控制视频及完整7视角JPEG继续保留在记录的双根/外部评审目录并逐项索引，不宣称已上传GitHub。被选中的comparison MP4按原字节复制；双视角JPEG保留每个选定面板的全部五列与原始构图，只作缩略展示，不改变原始800px列或科学结果。7个固定代表视角及完整联系表的模型复核不因GitHub缩略切片而减少。

原生4000×832视频、全部控制视频和原始大字段均保留在显式双根路径；精确路径、SHA及已上传资产的远端readback见最终REPORT/FINAL索引。根文件系统同时承载当前工作树与共享Git对象目录，复制前按 `3×实际交付字节数+16MiB` 保守估算，再保留1GiB；空间守卫不通过则不复制。没有修改共享Git配置、移动旧文件或用被忽略的out路径冒充GitHub入口。
