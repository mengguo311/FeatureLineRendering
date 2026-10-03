# 新场景 transport 扩展冻结协议

工作区仅 `/home/u00134/3dgs_line/hybrid_raster_extra_models_v1`，分支 `hybrid-raster-extra-models-v1`，基点 `f2a618450e0d0d142a059794149021fe3c2644ab`。模型/推理配置由本任务启动命令指定为 `gpt-6-astra` / `ultra`，不改全局配置。新增输出仅写本工作区 `out/hybrid_raster_extra_models_v1` 与 `artifacts/hybrid_raster_extra_models_v1`；其他 worktree、数据、构建只读。

本协议与 `INPUTS.json`、库存、继承锁证据先 commit/push，且验证远端 SHA，之后才允许查看新结果图。库存调查只读文件名、TRAIN 元数据及 checkpoint 的格式/数值，不查看图像。没有新模型时立即停止生产，提交的是输入阻塞证据，不把空集合称为实验成功。

## 问题与新场景选择

目标是检查既有 recipe 能否在更多冻结 vanilla synthetic NeRF 模型上带来有用线条细节；墨量增加不是质量改善。只允许新场景，排除 lego/chair/drums/ficus，不重跑旧场景冒充新增模型。优先并依次选择 hotdog/materials/mic/ship，最多四个；若有其他可用新 synthetic NeRF 场景，则在上限内按场景名排序补足。选取所有发现且合格的场景，不依据结果挑选。

可用性要求：真实存在、冻结且可读的 vanilla 3DGS checkpoint；可确认原 Gaussian 行 ID、三维 scale、rotation、opacity、SH0 属性及有限数值；对应 TRAIN 元数据具备全部预定索引及可确定原生网格。2DGS、CAD/自建几何体、非 synthetic NeRF 模型、只存在图片或配置而不存在 checkpoint 的记录均不能替代。多个合格 checkpoint 时优先既有封存 seed1729/iteration30000，其次有明确 vanilla 训练来源的最高完整 iteration，同级路径字典序；不得训练或下载大型资产。

实际库存见 `inventory/INVENTORY_DISCOVERY.json`。冻结时可用新场景 **0**，四个优先场景均缺 vanilla checkpoint；ship 的 2DGS checkpoint 明确排除。因此 `INPUTS.json` 的 runnable scene/camera 集合为空，生产预期帧数为0。四个缺失场景的每场景49帧要求列为未执行，绝不以“0/0通过”主张完成 transport。此零输入停止分支优先于下面的条件生产契约；本轮不继续搜索整个 home、不扩大方法或生成伪结果。

## 精确继承，不重新拟合

只读旧目录 `/home/u00134/3dgs_line/hybrid_raster_evidence_v2` 的 PROTOCOL、REPORT、REPRODUCE、源码、原 INPUTS 与未跟踪的 `out/hybrid_raster_evidence_v2/LOCK.json`。旧 LOCK 文件 SHA256：`d5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926`；canonical lock hash：`543666726d9fe38adcf85bcc8c56ace57bb0121e4598e7fb0a312302af2c3dbf`；原 parameter hash：`6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。`INHERITED_LOCK.json` 是字节相同副本，原文件只读。

六个旧锁定源码逐文件 hash 不变：native、evidence、author formula、IO、stage、旧runner。A 为旧同源 SH0 RGB 双尺度 Canny、median-depth evidence、alpha silhouette 的精确定义；B 为旧六通道 OUR dense 连续 max 读出；C=`1-(1-A)*(1-B)`。作者原式、原始 `S_L` 与独立展示均继承，必须标注 `AUTHOR independent reconstruction — NOT official`，不能称官方实现。

全局尺度原值固定：delta_D=`0.08261344276368612`、delta_A=`0.7444546544551854`、delta_N=`0.9862916707992548`、delta_C=`0.6385581493377686`、delta_G=`1.0`、visibility_raw=`1.0`；作者显示分母=`0.7533644223213196`。完整 recipe/阈值/归一化以旧 LOCK 为准，新 F/C/arc 均不得重拟合、逐场景归一化、阈值救援或 sweep。新配置若有封装 hash，必须与继承 scientific parameter hash 分开记录。

## 条件相机与原生契约

对可用场景固定 F=`[1,14,27,41,53,67,79,93]`、C=`[7,21,33,47,59,73,86,99]`，全部是 TRAIN 索引。若原 INPUTS 已覆盖则使用其中精确相机；实际原 INPUTS 只覆盖四个旧场景。否则只从 TRAIN transform 及原生尺寸证据派生：`w2c=inv(transform_matrix @ diag(1,-1,-1,1))`，`fx=W/(2*tan(camera_angle_x/2))`，方像素 `fy=fx`，主点 `((W-1)/2,(H-1)/2)`，不误改为400，不静默强制800。网格为800才在800渲染；尺寸无法确认即输入不合格。禁止解码原始 C 图像、打开 TEST/mesh、人工标注。

新 arc 固定 C7→C33、33个唯一 pose、`t=linspace(0,1,33)`。严格继承 `artifacts/direct_curve_global_fit_probe/freeze.py` 的构造：c2w rotation 的 SciPy Slerp；相对 checkpoint eligibility box 中心的球面方向插值，半径线性插值，合成为 c2w 再取逆。box 中心源自 mu.float64 逐轴 .001/.999 quantile 边界均值；旧对称 .1*diagonal 扩边不改变中心。不重做 look-at，不按结果挑轨道。无 checkpoint 时不编造中心、arc 或49个生产相机；本轮仅封存 TRAIN 可用性证据。

每可用场景49帧（8F+8C+33arc），保留全部预声明帧及失败状态；封存残缺/不匹配时拒绝静默覆盖，resume只接受内容、camera、checkpoint、source、parameter hash均正确的seal。A/B/C与作者读出共用同一次原生 traversal 的 SH0 RGB/alpha/depth；white background、kernel_size=0、filter_3D缺失不补造。原生normal是splat/ray-plane语义，不是表面真值。

旧隔离 patched/unpatched 构建可在逐文件hash、解释器兼容性确认后只读复用，不重装或改变环境。每新场景至少F1做同输入两版校准；沿用旧容差：一般max_abs<=3e-6；depth容许相对<=3e-6且绝对<=1e-5。输入/输出非有限、维度、camera、校准或export问题为 ENGINEERING_INVALID/UNDETERMINED，不是科学 NO_GO。

导出原始 Gaussian 行 ID、raw alpha*T top4（不重归一化）、对应depth/normal、全贡献矩、alpha与同源RGB；空ID=-1/权重0、排序、sum(top4)<=alpha+3e-6与全部有限性必须检查。公式使用的top4归一化与遗漏质量另外保存。每次GPU运行前检查nvidia-smi和PID归属，有别人的任务即不启动，不重叠、不终止任何会话或作业。检测不是跨任务原子GPU锁。

## 条件交付、审计与停止

若有合格输入，交付每帧原生全分辨率五列 RGB | A | B | C | AUTHOR（独立重建、非官方）、原值及连续字段、provenance/diagnostics、等连续墨量控制、同模型overlay；完整未剪切33帧comparison/overlay/matched视频、全contact sheets与首/中/末。另给H264/yuv420p/faststart、1600宽、保留全部33帧的Telegram兼容视频，标签重新绘制确保可读；需要时补1600宽的多行较高版本。视频逐帧完整decode，验证数量、尺寸、33 distinct及hash；不得用静态动画或挑剪辑替代。

新支持代码先实际RED fixture后GREEN，旧scientific computation不得修改。独立checker核验输入清单、camera、frame/raw seals、字段、来源、计数和完整视频；空输出只允许得到输入阻塞确认。执行相关旧回归及新增测试，保存命令/显式stdin/参数/退出码/log。访问审计要准确披露覆盖范围，不能用未运行的production trace声称全会话TEST审计通过。

上限四个新场景、4小时本任务GPU进程墙钟、工程修复最多3轮或90分钟；没有合格新checkpoint即停止生产。本轮预算实际GPU=0、工程修复=0。中文报告逐场景记录缺失；未生成图像时不捏造面内密纹等视觉缺陷。若运行则特别检查dense interior texture，不能把更多墨视为更多有用线。合成场景迁移是transport，不是新blind human evaluation。human review继续pending，不宣称fixed3D或temporal成功，不实现3D/2D routing或时序传播，不推进方法优化。

提交/推送协议与清单后，再完成独立库存核验、中文REPORT/REPRODUCE、FINAL.json和AGENT_FINAL.md，审阅diff、commit/push、核对remote SHA和clean tree。FINAL记录缺失产物和未执行校准，不自引用自身提交hash；最终封存提交由包含FINAL的Git commit解析，远端验证写入终答及新out的本地回执。
