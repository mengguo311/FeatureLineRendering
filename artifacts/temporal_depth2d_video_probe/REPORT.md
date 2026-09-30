# Temporal depth2d video probe：冻结候选 NO_GO

完整 Lego arc0 kill test 未通过：二维曲线候选没有优于相机/深度 warp+EMA 控制。协议、风格、结构要求和门槛未修改，候选扩展立即停止。原生对照的四场景、八条原始路径全部完成；没有挑选成功帧。

这是 **二维、视角相关 NPR 视频实验**。GS 深度及临时投影锚点只用于 renderer-domain 运动验证，不构成固定三维墨迹。没有自动三维资产成功、held-out 真实照片或独立人类美观偏好的结论。旧 3D 曲线仅有 depth2d 约 0.09–0.37 的墨量，其稳定性不能迁移为本实验的证据。

## 直接查看实际视频与画面

- [视频画廊：全部八条路径与完整 kill 比较](gallery.html)。本机 HTML 使用本 worktree 的相对视频路径；远程仓库保留完整 contact sheets 和视频 hash，视频本体位于服务器 out/。
- [完整墨量匹配视频](../../out/temporal_depth2d_video_probe/run/lego_arc0/comparison_forward.mp4)，依次 GS / B 原生 depth2d / W warp+EMA / CAND 二维曲线。
- [三法 native 最佳固定配方展示](../../out/temporal_depth2d_video_probe/run/lego_arc0/comparison_native.mp4)。未做隐藏的风格或参数搜索。
- [候选完整往返](../../out/temporal_depth2d_video_probe/run/lego_arc0/CAND_pingpong.mp4)、[反向播放](../../out/temporal_depth2d_video_probe/run/lego_arc0/CAND_reverse.mp4)、[身份编辑往返](../../out/temporal_depth2d_video_probe/run/lego_arc0/identity_edit_pingpong.mp4)。
- [最坏帧 028 及邻帧 027/029，完整画面](media/lego_arc0/worst_and_neighbors.png)；全部 frame PNG、矢量 NPZ 与完整视频保存在 `out/temporal_depth2d_video_probe/run/lego_arc0/`。
- [全部33帧，视频实际解码 000–010](media/lego_arc0/video_decoded_000_010.png)、[011–021](media/lego_arc0/video_decoded_011_021.png)、[022–032](media/lego_arc0/video_decoded_022_032.png)。每条路径另有完整 400px contact sheets，不能只看 quartiles。

## 真实全帧计数与全部路径

264 个原始相机帧：B=264，W=33，CAND=33；剩余231帧的 W/CAND 按预注册 kill 规则未运行。F构建32帧、C保留32帧另计，不与视频计数混合。正放/倒放各33播放帧；往返65播放帧并非65个新相机帧。每段封存原始比较视频均实际解码33帧。

| 场景 | 原路径 | B | W | CAND | 原视频解码 | B平均运动差异 | 全帧图 |
|---|---|---:|---|---|---:|---:|---|
| lego | arc0 | 33 | 33 | 33 | 33 | 0.082019 | [全33帧](media/lego_arc0/B_all33_overview.png) |
| lego | arc1 | 33 | 0 — NOT_RUN_KILL | 0 — NOT_RUN_KILL | 33 | 0.115468 | [全33帧](media/lego_arc1/B_all33_overview.png) |
| chair | arc0 | 33 | 0 — NOT_RUN_KILL | 0 — NOT_RUN_KILL | 33 | 0.047596 | [全33帧](media/chair_arc0/B_all33_overview.png) |
| chair | arc1 | 33 | 0 — NOT_RUN_KILL | 0 — NOT_RUN_KILL | 33 | 0.052033 | [全33帧](media/chair_arc1/B_all33_overview.png) |
| drums | arc0 | 33 | 0 — NOT_RUN_KILL | 0 — NOT_RUN_KILL | 33 | 0.009005 | [全33帧](media/drums_arc0/B_all33_overview.png) |
| drums | arc1 | 33 | 0 — NOT_RUN_KILL | 0 — NOT_RUN_KILL | 33 | 0.038264 | [全33帧](media/drums_arc1/B_all33_overview.png) |
| ficus | arc0 | 33 | 0 — NOT_RUN_KILL | 0 — NOT_RUN_KILL | 33 | 0.024657 | [全33帧](media/ficus_arc0/B_all33_overview.png) |
| ficus | arc1 | 33 | 0 — NOT_RUN_KILL | 0 — NOT_RUN_KILL | 33 | 0.028642 | [全33帧](media/ficus_arc1/B_all33_overview.png) |

路径和全部 K/w2c 已在 [INPUTS.json](INPUTS.json) 冻结。原视频路径/hash 也在 [MEDIA_MANIFEST.json](MEDIA_MANIFEST.json)；画廊提供只读复制的八段原始比较视频。原生 depth2d 使用 sealed `D.native_edge` 的 OpenCV 2×2 膨胀，保持原始配方。仅读取 `gs_rgb/depth/alpha/D.native_edge`，不读取 F/C 中可能含真实照片的 `rgb` 成员。

## 为什么 kill

每个方法均测量完整32次相邻转换。墨量以最终 uint8 图像的 `sum(1-gray/255)` 计算；不是线数、声明宽度或几何长度。

| 方法 | 平均几何差异 | p95 | 平均 opacity 残差 | popping组件数 | 当前墨迹运动可评估比例 |
|---|---:|---:|---:|---:|---:|
| B | 0.082019 | 0.109276 | 0.310814 | 803 | 73.576% |
| W | 0.020760 | 0.036320 | 0.217847 | 560 | 72.758% |
| CAND | 0.061039 | 0.081892 | 0.180726 | 752 | 71.609% |

候选平均差异 0.061039，约为 W 的 2.94 倍；预注册要求 <=0.90×W。候选 p95 0.081892 也高于 W 的 0.036320。这两项必要门槛失败，因此 NO_GO。候选比未处理 B 降低约 25.6% 的平均差异，仍不足以证明优于控制。

CAND 每帧真实墨量比为 0.999819–1.000255，W 为 0.998206–1.001087，都在 [0.95,1.05] 内。两者每帧 all/outline/interior 原边界骨架覆盖均为100%；候选 unsupported ink 最大0.00107%，W 最大2.574%，都低于5%。因此这里没有通过删掉必要结构或降低总体墨量来换取稳定性。

候选 native 墨量约为 B 的1.52–1.59倍；匹配时只用全局 opacity 约0.630–0.656，未删组件。W 的固定 EMA 原生配方另外保留，匹配使用0–3次全局膨胀插值再归一化；其淡色尾迹可能降低几何代理数值，不能由此宣称 W 更漂亮。完整 native 每帧比率见 [NATIVE_INK.json](NATIVE_INK.json)。

运动有效墨迹比例约71.6%–73.6%；其余未知/遮挡/深度不一致区域没有获得稳定性信用。全部逐帧覆盖、深度拒绝、支持比例、归一化参数和运动诊断保存在 [kill RESULTS.json](media/lego_arc0/RESULTS.json)。这些是 GS 深度代理，不是光流真值或真实照片验证。

## 视觉与身份限制

实现方内部检查了匹配视频解码后的全部33帧、最坏转换及邻帧，以及其余七条路径的全部33帧 GS/B overview。外轮廓与主要板面保留；候选仍继承内部机构短线、缺口和拓扑变化。细节并未明显恢复；W 可见淡色残影。静态对照和短小平滑不能证明候选的视频优于 W。没有独立人类偏好评估，也没有宣称实时完整播放的人工评估通过。

候选是逐帧完整边界图的二维折线链；身份附着在顶点运输标签，链拓扑可以重建。它不是固定全局曲线，也不是语义笔触资产。深度拒绝遮挡、链 split/merge 不跨空洞、66帧 dormant 缓存处理重新显露；合成遮挡/显露和 split/merge 测试通过，但真实路径身份不足：共 16878 个身份，相邻帧平均身份延续 65.1%，最大 40.1% 的顶点重复使用同一标签。此版本允许 many-to-one 附着，不能据此宣称每条完整曲线身份稳定。

身份编辑仅是一个持久顶点标签的局部 opacity 演示，不是完整语义笔触编辑。正反向输入重算会先按冻结 frame key 建 atlas，再按请求次序显示，逐帧几何/身份/纹理完全相同；往返回到起点的差异为0。这是非因果视频 atlas 的缓存一致性，不是对任意往返相机或固定三维路径的泛化证明。两段原路径是 open arcs；没有伪造32→0闭环。真正闭合相机回路仅在合成测试验证。

## 封存、测试、复跑和审计

协议提交 `4f604fd`；RED提交 `0ef3609`；GREEN/实现封存提交 `c183e53`。协议 SHA256 `cc53655e5fe2589bd3dc3a14673405e349b35a222d7a89b9f4490e7059d49fee`；输入 manifest SHA256 `29cfaea04e804013dff428d8d04b70bc5b77bf32489b45bea8fa7716716db1aa`。实现源文件 hash 见 [IMPLEMENTATION_SEAL.json](IMPLEMENTATION_SEAL.json)，先于任何实验 F/C/arc 解码。

14项针对性测试通过：投影、遮挡/显露、split/merge、身份纹理、反向重算、真实闭环、量化墨量、异常姿态、未知 alpha、atomic seal 与审计行为。[TDD_LEDGER.md](TDD_LEDGER.md)、[FINAL_TESTS.log](FINAL_TESTS.log) 保留真实 RED/GREEN。审计解析器把 SIGCHLD 当未知记录的工程问题，通过独立 RED fixture 修正；科学实现和所有门槛保持不变。

主运行 CPU wall 509.2s（约8.5分钟），kill 单元 154.0s；全部单元低于预注册5分钟，整体低于45分钟。GPU未分配。独立同参数 kill 复跑：366/366 图片/视频/矢量资产完全一致，全部指标（除耗时）一致，科学结论相同；见 [RERUN.json](RERUN.json)。真实续跑验证所有10个已封存单元并跳过重算，见 [RESUME.log](RESUME.log)。主运行原始状态保留在 [RUN_STATE.json](RUN_STATE.json)，续跑状态另存，不能拿续跑耗时替代原始耗时。

内核 Landlock 仅允许逐文件封存输入只读、当前 worktree 写入。主运行 strace 审计 7121 次成功文件系统调用：0次越界成功科学读取、0次 worktree 外写入、0条未解析记录；所有源文件 hash 不变。复跑与续跑也独立审计。见 [AUDIT.json](AUDIT.json)、[RERUN_ACCESS_AUDIT.json](RERUN_ACCESS_AUDIT.json)、[RESUME_ACCESS_AUDIT.json](RESUME_ACCESS_AUDIT.json)。没有 mesh、TEST/DEV、raw照片或其他科学数据引入。

[DELIVERY_DECODE.json](DELIVERY_DECODE.json) 记录51个视频文件（43个生成视频、8个封存原视频）共2035次播放帧解码，以及1060张PNG完整解码和最终 seal 路径；真实唯一相机帧仍为264。原始 DECODE.json 的 `.partial` 路径是原子封存前真实解码位置，最终路径已显式解析。所有完整视频、native800画面和矢量身份记录保留在服务器 `out/temporal_depth2d_video_probe/run/`，Git跟踪协议、完整contact sheets、指标、hash、状态与复现实验脚本。runner启动/续跑方法见 [RUNNER.md](RUNNER.md)。

没有调整门槛、第二候选或成功场景子集结论。冻结候选不支持“优先做漂亮视频”的成功声明；本次交付是可检查、可复跑的负结果和全部原始路径的完整展示。
