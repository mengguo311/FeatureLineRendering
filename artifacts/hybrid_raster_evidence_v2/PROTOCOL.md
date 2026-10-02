# 阶段 1 冻结协议：同源 raster-state / RGB / complement

冻结于任何新生产实现、GPU实验或新场景图像查看之前。工作区 `/home/u00134/3dgs_line/hybrid_raster_evidence_v2`，分支 `hybrid-raster-evidence-v2`，初始 HEAD `e9b7e59ab109097aca46c374a3544c0eea3b93ab`。协议先 commit/push，成功后才实现。模型配置与启动命令均为 gpt-6-astra / ultra，保持 `.codex/config.toml`。这是有界研究执行，不是后续阶段的授权。

## 问题、归属与范围

固定 vanilla 3DGS 下，原生内部状态能否提供 RGB-Canny 未表达的有用线细节，自动互补是否值得人类继续评审？优先更多有用细节，不能只凭墨量判优。主实验为纯 2D 视角相关输出；不使用旧橙色 I-arm 曲线。因此旧 fixed-3D NO_GO 不变，原始固定三维目标仍未实现。无 mesh、人工线标、重训练、容量扩展、自动 3D/2D routing 或 temporal identity propagation；后两方向必须等实际结果与 parent/user 视觉评审。

第三方作者：Hao–Mukai 的 [SA2026 poster](https://mukai-lab.org/content/SA2026PosterHao.pdf) Eq.1–5 与常数；Zhang 等的 [RaDe-GS](https://github.com/HKUST-SAIL/RaDe-GS) 原生 rasterizer（既有 pinned d72f207 系列源码）。本实现是独立重建；OUR dense readout 与 A+B 融合是我们的附加。旧 proxy rank-max 不是作者方法；hybrid 本身不作为新颖性，3Doodle 已有视角独立/相关组合。作者论文也明确输出是视角相关 raster field。

## 输入与开放顺序

使用 `artifacts/direct_curve_global_fit_probe/INPUTS.json` 已封存的 seed1729 checkpoint、精确相机 K/w2c/native尺寸和 arc0 的全部 33 poses。首要 Lego、Chair。F=[1,14,27,41,53,67,79,93]；C=[7,21,33,47,59,73,86,99]。C 只对本次 evidence/参数拟合留出，仍属 GS TRAIN 且历史已看过，绝非新 blind。无需解码原图：从元数据加载相机与 PLY 重渲染。禁止为调参解码 C/DEV/TEST；TEST 始终关闭。

先合成 fixtures，再 Lego/Chair F1/F41 原生 800x800 工程/可视充分性切片。校准通过且可运行后完整八 F；从两主场景所有 F 锁定一个全局尺度集与配置 hash，再运行两主场景全部 C 和完整 arc0。C 与 arc 不参与尺度、阈值或挑选。主场景工程有效后，Drums/Ficus 用同一个已经锁定的 recipe/尺度跑 F/C/arc0，不再归一化适配；披露其继承 posterior/input quality 限制。不得因 C 难看进行救援或自主 sweep。

## 原生工程契约

只向本工作区新 `out/hybrid_raster_evidence_v2` 与阶段 artifacts 写入；sibling native/foundation 为只读参考。最小源复制到本目录 isolated build，不安装到环境、不修改其他 worktree 或 tmux/Claude。每次 GPU launch 前查询 nvidia-smi 与 PID ownership；有非本任务 GPU 作业则等待/记录阻塞，不重叠、不终止别人。

同一个 CUDA renderCUDA 遍历输出 original Gaussian ID、实际 alpha*T 的 top4 权重（不归一化 raw）、同贡献者 depth/normal、RGB/alpha/expected depth/median depth/normal、全贡献二阶矩与 normal length。top4 归一化仅用于作者公式且另存 mass coverage。不得使用 proxy ID 与另一 renderer geometry 拼接。载入 PLY 时不计算 covariance-axis surface normal。原生 RaDe normals 仅称 splat/raster normals；病态 inverse-covariance fallback 计数披露，不当成表面真值。

此次固定 SH0 colors、white background、kernel_size=0、无训练时 filter_3D；缺失不补造。A/B/C 共享完全相同 native RGB/alpha/depth grid。不加入 full-SH RGB practical reference，以免混淆因果比较。相机保留 INPUTS 的 native_K=399.5 主点约定，验证 CUDA ndc2Pix 映射；不能悄改 K 为400。新 unpatched 与 patched 构建同输入逐元素校准 RGB/alpha/depth/normal：max_abs<=3e-6；深度可接受相对<=3e-6且绝对<=1e-5。未通过不能解释字段。

验证 raw 全有限、维度、ID 范围/空 -1、空权重0、top4非增序、sum(top4)<=alpha+3e-6；合成 fixture 覆盖真实 blend/深度二阶矩、原ID不重映射、>4贡献遗漏质量。不得用 nan_to_num 把坏 export 修成假字段。正常 alpha=0 的定义性零不是替代测量。

## 冻结三臂、读出与控制

统一 native800、黑墨白底、同图模型 overlay、1 pixel sample brush，不额外膨胀线宽。共同 foreground=3x3 dilation(alpha>=.08)，保留 silhouette；foreground 外墨为零。全部作者 raw delta/E/q/u/L/S_L/E_T 留存，作者原始 S_L 无改动另存/展示。

A：继承 dense v1 的 grayscale RGB Canny：3x3 sigma .65、18/48、L2；5x5 sigma1.4、25/65、L2；alpha Canny25/65。depth evidence 必须从同次 native median depth 重算：sigma1.5 derivative，除 max(.002*z,5x5 median local abs depth difference,1e-12)，方向 NMS，正响应95/70百分位 hysteresis，alpha>=.5；规则固定，非重新寻优。保留每一通道和二值 union。

B：保留作者原公式 S_L 原值及 F-only positive-P99 增益展示。另提供明确 OUR dense 读出：raw delta_D/A/N/C/G 和 visibility raw response（dominant weight ratio smoothstep 乘 top2 depth/normal discontinuity max，去掉 q_s）的六个通道；分别以全局 primary-F positive P99 归一化，clip[0,1] 后 smoothstep(.10,.70)，乘 (.35+.65*q) 强度，仅在共同 foreground 内；无 pooled top-k、无连通域删减、无额外稀疏 cap、无 hard reliability rejection。B 为六通道逐点 max；连续 response 直接作为墨浓度，允许粗/噪声响应并如实报告。此读出并非作者公式或证明的几何边线；不把更黑自动解释成更好。保存 raw、normalized、每通道墨浓度与 argmax/bit provenance。

C：C=1-(1-A)*(1-B)，逐像素保存 A、B、A-only/B-only/shared support、continuous overlap=A*B 与 B 的逐通道贡献标签；不删除 A 的弱连接，不以池化 top-k 控制墨量。主对比是 A、OUR B dense、C，同时提供 author S_L absolute 与固定F增益列。

墨量控制：每帧额外输出 A/B/C ink-matched，target=min(sum(A),sum(B),sum(C))，各 arm 整图乘 target/sum(arm)（空图gain=0）。该确定性控制只缩放浓度、完全保留非零 support，不按像素截断；不是等黑像素数。原始高密度输出始终保留，逐帧记录 gain/mass/support/阈值面积。阈值面积只作诊断(.1,.3,.5)，不用于方法筛选。每帧 scalar gain 可能闪烁，不能从其视频推断时序优越。

冻结 null controls：B=0 时 C=A；A=0 时 C=B；全背景无墨；原ID全局双射重命名不改变 overlap/typed response；相同支持集权重重排结果不变；shape/source mismatch拒绝。这些合成控制不引入额外场景调参。

## TDD、生产封存与产物

必须先写一个贯通 fixture（export语义→typed→A/B/C→provenance/shape/background）的测试，运行真实 expected RED，记录命令/log/exit，再实现并 GREEN。进一步测试原生空射线、同源校准、融合/重叠、维度、原子封存/损坏重启、视频完整解码。没有有效工程测试不能 launch science。

plain executable runner 使用指定 `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`，环境 PATH 按用户指定；`PYTHONDONTWRITEBYTECODE=1`，缓存/临时文件均在新输出目录。配置 canonical JSON hash；F-only normalization lock 自带 F frame hashes。在 C 之前封存锁。每 frame 写 staging 目录，raw/typed/responses/provenance/diagnostics/camera 与图片全部完成并校验后 atomic rename；SEAL.json 包含 checkpoint/camera/config/source及每文件 SHA。restart只跳过验证通过 seal，不用“文件存在”等价成功。STATUS.json 原子更新，失败写具体原因与缺失清单。

每 F/C 的 native full-resolution raw字段、response/line/overlay panels；每 arm 白底墨、同相机overlay、原值和ink匹配控制。完整 arc0 对照 MP4（33 frames/12fps，无剪切）与全部33帧full-frame contact sheets、first/mid/last；原始 native grid 不裁切。临时MP4→逐帧完整decode，预期尺寸、33/33与33 distinct→promotion→SHA；所有相机独立重算，可复用严格相同相机且hash一致的native缓存。不得动画静态图/隐去坏帧。

诊断：raw alpha/top4 coverage/normal coherence/variance、background/outline/interior 分层墨量与support、A/B重叠和新增pixel量，均与视觉结论分开；无真值线precision/recall或可用性假指标。实施模型查看每场景 F/C 代表帧和arc first/mid/last，写具体可见缺陷；完整contact sheets提供用户审阅。实现模型评审非独立human GO。无新增时序身份，不主张优越 temporal stability。

## 有界停止与交付

限制为本协议一次 recipe，最多4 scenes×(8F+8C+33arc)=196 frames，外加primary四帧工程/校准与合成fixtures；不做阈值搜索。工程排查限3轮明确失败修复或90分钟工程预算；全流程最多4小时本任务GPU时间。工程不足/校准失败为 ENGINEERING_INVALID/UNDETERMINED，不是科学 NO_GO；可保存负结果，不伪造字段/指标/缺失视频。校准有效但视觉噪声占主导可记录本recipe无可证明收益，仍交付全部预定义帧。阶段最终必须等待user视觉review；方向2/3保持关闭。

中文 REPORT、复现命令、测试命令/log、STATUS.json、FINAL.json（明确实现commit与最终封存commit关系，避免自引用SHA）、diff review、new+relevant regressions、commit/push并验证remote SHA和clean status。大体积raw/native build本地可复现且路径+hash清单入库；报告/配置/代码/代表图/视频清单入库。已有任务launch/AGENT日志保持原样，不将动态日志误作待修文件。
