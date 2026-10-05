# 四模型冻结 NPR：存储续跑完成报告

**计划产物已完成并逐项独立核验：196/196 帧、24/24 视频、60/60 完整联系表、36/36 首中末面板。** 本次新增 Materials、Mic、Ship 各49帧和6视频；旧 Hotdog 49帧和6视频保持只读。四个30000步模型没有重训，科学设置没有改变。此结论限于产物完整性，**不是科学效果通过或人类 GO**；历史首次 Hotdog render 与首次 checker 的143中断审计缺口仍保留。

机器结论：[FINAL.json](FINAL.json)；本次完整独立核验：[PRODUCTION.json](continuation/independent_review/PRODUCTION.json)。续跑前的报告、FINAL、STATUS、代码与审计证据共251份小文件已保存为[历史快照](continuation/historical_607b908/REPORT.md)，原始失败trace与旧产物均未删除、移动或重写。

## 实际范围与可访问评审入口

| 场景 | 冻结模型 | Gaussian数 | F / C / arc | 视频 | 联系表 / 首中末 | GitHub完整33帧comparison |
|---|---|---:|---|---:|---|---|
| Hotdog | 30000步 / seed1729，原训练PASS | 148610 | 8 / 8 / 33 | 6 | 15 / 9 | 原本地根，见路径/SHA索引 |
| Materials | 30000步 / seed1729，原训练PASS | 282537 | 8 / 8 / 33 | 6 | 15 / 9 | 批准外部根，见路径/SHA索引 |
| Mic | 30000步 / seed1729，原训练PASS | 311562 | 8 / 8 / 33 | 6 | 15 / 9 | [播放或下载](review/mic/arc0_comparison_telegram1600.mp4) |
| Ship | 30000步 / seed1729，原训练PASS | 320284 | 8 / 8 / 33 | 6 | 15 / 9 | [播放或下载](review/ship/arc0_comparison_telegram1600.mp4) |
| 总计 | 4个既有模型 | — | 32 / 32 / 132 = 196 | 24 | 60 / 36 | 其中Mic/Ship已上传并读回核对SHA |

小JPEG评审面板：[materials](review/materials/materials_F001_arc016_review.jpg)、[mic](review/mic/mic_F001_arc016_review.jpg)、[ship](review/ship/ship_F001_arc016_review.jpg)。JPEG为评审缩略副本，不替代原生图或独立数值检查。实际GitHub交付为Mic/Ship两段Telegram comparison和三个新场景各一张F001/arc016 JPEG，共2421867字节；[DELIVERY.json](continuation/DELIVERY.json)逐项列出源、目标、大小、SHA和空间检查，[GITHUB_READBACK.json](continuation/GITHUB_READBACK.json)给出固定提交URL与远端读回哈希。GitHub可能需要下载MP4后播放。

完整的12段Telegram视频及12段原生视频均已生成。复制前实测根空闲1099980800字节，所选切片按原守卫3×payload+16MiB估计24042817字节，余量仍高于1073741824字节。更大的四视频/三新视频方案在实测空间下降后均未通过原守卫；没有为发布放松守卫或改共享Git配置。GitHub只上传上述小评审切片；Hotdog/Materials的comparison、全部Telegram overlay/matched、全部原生媒体和巨大raw字段保留在记录的双根，不能把未上传文件的本地路径当作GitHub链接。

每帧原生800×800，五列顺序 **RGB | A | B | C | AUTHOR**；原生line/overlay/matched面板及视频为4000×832。每场景的六视频为三类各一原生版、一Telegram版，全部未剪切33帧；Telegram为1600×368、H264/yuv420p/faststart。独立checker完整解码24段，每段均33 expected、33 decoded、33 distinct并核对SHA，不以首帧或路径存在推断完整。每帧均保留raw、typed、responses、provenance、diagnostics、单臂图、同相机overlay、等墨量控制、相机及raw/frame seal；四场景共588张五列面板。AUTHOR仍用冻结增益，等墨量只适用于A/B/C。

## 双根路径与科学冻结

| 用途 | 真实路径 |
|---|---|
| 当前工作树、小元数据/报告/评审副本 | `/home/u00134/3dgs_line/hybrid_raster_trained_models_v1` |
| Hotdog旧transport，只读 | `/home/u00134/3dgs_line/hybrid_raster_trained_models_v1/out/hybrid_raster_trained_models_v1/transport` |
| Materials/Mic/Ship新transport | `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/transport` |
| 新trace、cache、tmp、失败staging和agent日志 | 批准的外部根 `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1` 内 |
| 四个既有训练模型，只读 | 工作树内 `out/hybrid_raster_trained_models_v1/training/{scene}/seed_1729/checkpoints/` |

解析器使用[STORAGE_MAP.json](continuation/STORAGE_MAP.json)中每场景的真实根；没有用symlink绕过守卫，也没有伪造旧seal的ROOT或source上下文。[ARTIFACT_PATH_SHA256.json](continuation/ARTIFACT_PATH_SHA256.json)以场景根加相对路径逐项给出完整产物的大小和SHA，包含视频、原始字段、seal及元数据；训练checkpoint的精确路径/SHA沿用FINAL中既有lineage。

存储协议与代码在GPU前冻结并推送为 `baadea14f7dfe74722dfb9b896135882d3f1a614`，release receipt提交 `95c79369fd8e614084f5db092f2bb9798efe783f` 随后通过远端顺序核验。封存清单见[STORAGE_FREEZE.json](continuation/STORAGE_FREEZE.json)。新adapter只绑定原producer的OUT、adapters.OUT及native.STAGE；ROOT、ART和native二进制路径仍为真实旧路径。原producer/adapters/checker及六份科学源码字节不变，运行另存新的glue绑定凭证；准确范围和diff见[SOURCE_DELTA.json](continuation/SOURCE_DELTA.json)、[STORAGE_GLUE.diff](continuation/STORAGE_GLUE.diff)。

模型/相机既有冻结顺序、checkpoint SHA、patched/unpatched native二进制、原尺度及AUTHOR增益全部保留。parameter SHA固定为 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。F=[1,14,27,41,53,67,79,93]；C=[7,21,33,47,59,73,86,99]；arc33为冻结C7→C33轨迹。每场景先做全部8F的原patched/unpatched资格检查，再生产；新三场景各8F的五项比较max_abs均0，独立重算通过，旧Hotdog8F亦重核通过。

原生readout继续白底SH0、精确800网格、原Gaussian行ID与raw alpha*T，各臂同一次native traversal。A为灰度RGB/depth/alpha dense edges，B为原OUR六通道，C为原自动互补；无新尺度拟合/F归一化、逐场景救援、路由或时间身份算法。AUTHOR为独立Eq.1–5重建，**NOT official**。缺filter3D，raster/splat/ray-plane normals不是GT表面法线。C参与全部100个TRAIN相机的GS训练，只对NPR拟合留出，**不是盲测或泛化评估**；本次没有NPR重拟合，也没有读取源C图像进行NPR计算。

## 实际画面检查与限制

检查者是模型代理，人类科学评审仍pending。每个新场景直接查看原件或由F001/F041、C007/C047、arc000/016/032的line/overlay/matched共21张原生面板生成并绑定源hash的缩览，以及全部F/C/arc × RGB/A/B/C/AUTHOR的15张完整联系表的分块/缩览；覆盖全部245个联系表子图，未逐像素放大全部原件。原生文件完整保留。具体查看文件、seal/SHA、缩览来源与观察分别记录在[Materials](continuation/MATERIALS_MODEL_REVIEW.json)、[Mic](continuation/MIC_MODEL_REVIEW.json)、[Ship](continuation/SHIP_MODEL_REVIEW.json)。Ship还直接查看arc016原生RGB。Hotdog既有模型review和历史缺陷仍有效，见[NPR_VISUAL_REVIEW.json](NPR_VISUAL_REVIEW.json)与[SECOND_VISUAL_REVIEW.json](SECOND_VISUAL_REVIEW.json)。

- **Materials：** A常能显示球体外缘和底座环线，但反射球也出现碎线和密纹。B/C在平滑灰球、绿球内部形成颗粒或云状灰填充，C更暗，overlay会遮住细节；等墨量变浅后空间杂纹仍在。AUTHOR细且断续。F041的不规则深色楔块在共同SH0 RGB已有，不能归因于新增NPR；边缘对象与底座裁切保留。
- **Mic：** A的主体、支架、电缆轮廓较清楚，网罩本身已有密线。B/C在金属表面、底座和电缆产生密集划痕状纹理，C007网罩接近黑团；等墨量不消除内部杂纹。弧线中后段支架/电缆出下边界，部分帧麦克风头部出右边界，末帧电缆仍有裁切。AUTHOR较淡。
- **Ship：** B在水面形成密集卷曲灰纹，部分底座墙面也有RGB不明显的纹理；C进一步压暗船体/水面，overlay遮住甲板和船身细节，等墨量仅减轻深浅。**弧线中段严重出画：arc016大部分船体和圆盘落在下边界之外，上部大面积空白；原生RGB直接证实，并非JPEG排版裁切。** 首末视角较完整也不能掩盖中段问题。桅杆附近孤立点在RGB亦有，不能认作真实细索。AUTHOR主要留下淡外缘，细部较弱。
- **Hotdog（保留旧观察）：** A有盘沿/食物边线，也有拥挤内部碎线；B/C内部密纹与盘面杂纹明显。等墨量后图案仍在。arc中段盘子下沿出画，AUTHOR细而稀疏。

这些缺陷全部保留，没有为好看而改相机、追加训练、删帧或逐场景调参。不建立“更多墨量意味着更好线条”、fixed3D线身份或时序稳定/收益结论。

| 场景 | 每帧连续墨量均值 A | B | C | 前景加权top4贡献覆盖 |
|---|---:|---:|---:|---:|
| Hotdog | 38992.69 | 94992.00 | 112476.05 | 0.519233 |
| Materials | 30905.41 | 67056.94 | 81817.22 | 0.563793 |
| Mic | 19075.59 | 35538.14 | 43553.39 | 0.594190 |
| Ship | 37953.76 | 100832.90 | 118468.18 | 0.531567 |

统计按196帧既有diagnostics/provenance汇总，见[DIAGNOSTIC_SUMMARY.json](continuation/DIAGNOSTIC_SUMMARY.json)。墨量不是准确率；top4为alpha>0.05前景像素加权的截断贡献统计，不是几何正确性。汇总脚本不是独立产物checker。

## 执行、测试与保留的失败

新增三次render和三次成功media均有实际strace、正常exit0及完整退出尾部，逐次检查外来GPU任务、双根归属/空间及冻结hash。独立访问审计未见这些NPR进程树打开TEST、mesh或源C图像；确实观察到所需checkpoint、冻结camera/parameter/science/native来源读取。索引：[LAUNCH_INDEX.json](continuation/LAUNCH_INDEX.json)；六份独立审计位于 `continuation/independent_review/{SCENE}_{RENDER,MEDIA}_ACCESS.json`。本次全量checker本身亦有[完整访问审计](continuation/independent_review/FULL_VERIFIER_ACCESS.json)。范围仅为记录的open/openat/openat2/creat进程树与退出，不宣称全会话系统调用覆盖。

本次 **124项唯一单元/相关回归测试PASS**：原相关CPU回归85、存储adapter13、launcher10、独立多根checker16。adapter/路径、seal上下文、归属及启动守卫均保留真实RED→GREEN证据。另 **1项真实媒体集成PASS**：同一历史编码器实际编码并完整解码33帧。命令/日志SHA/计数见[TEST_INDEX.json](continuation/TEST_INDEX.json)。RED、中间失败、重跑不增加通过数；旧92项测试和旧真实CUDA训练集成只是保留的历史证据，本次未重训或重复计入。

Materials首次media正常记录exit1：新Python写守卫拒绝imageio_ffmpeg自动探测写`/dev/null`，库吞掉该PermissionError后报告找不到编码器。保留原trace、stdout、staging和INVALID结果；修复只以进程局部`IMAGEIO_FFMPEG_EXE`绑定旧Hotdog使用的同一ffmpeg（SHA `e7e7fb30477f717e6f55f9180a70386c62677ef8a4d4d1a5d948f4098aa3eb99`），实际编码与解码照常进行，没有安装环境、改全局配置或跳过验证。绑定在重试前冻结并推送为 `c3f6d25bac9c07da22b517880e1dd566d2c95679`，见[修复记录](continuation/REPAIR_LOG.json)及[失败审计](continuation/independent_review/MATERIALS_MEDIA_ATTEMPT001_ACCESS.json)。

续跑用掉2/3轮明确工程修复；从协议建立至媒体修复完成的保守计时1688.216秒（含中间生产），低于90分钟。三次GPU render阶段总墙钟 **2087.729秒 / 34.795分钟**，低于4小时预算；本次墙钟至最终记录4524.214秒，低于8小时。GPU阶段墙钟不是独占GPU核时。精确运行账本、预算与双根空间在FINAL/启动凭证中；未终止外来任务、删除旧文件或改动共享Git配置。

**历史缺口仍未解决：** 首次Hotdog render在27帧后143中断，无完整子进程退出；第一次checker亦143中断，原因/发信者未知。两份审计仍INVALID。原失败文件哈希及251份小快照已重新核对，见[HISTORICAL_GAP_RECHECK.json](continuation/HISTORICAL_GAP_RECHECK.json)。新checker可以证明现存196帧/24视频的完整性，却不能补齐旧执行trace。原存储阻塞当时真实存在；本次用户授权的新外部根解决续跑容量限制，不将过去“未运行”改写成科学负结果或过去审计PASS。

## 后续判定边界

计划产物生产和发布切片已完成，旧训练资格状态原样保留。人类仍需结合完整五列、等墨量、overlay、原始字段与裁切问题评审科学解释并决定GO；本报告不替代该判断。复现/只读复核入口见[REPRODUCE.md](REPRODUCE.md)。本报告的Git版本以所在提交为准；远端媒体固定版本及读回SHA在GITHUB_READBACK，最终分支HEAD核对结果另存外部交付凭证，避免自引用提交哈希。
