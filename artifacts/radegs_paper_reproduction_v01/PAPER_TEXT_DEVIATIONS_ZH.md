# RaDe-GS v2 paper-text variant 的方法边界

本变体遵循本轮用户明确指定的 v2 文字/公式优先级。它是在 C24 上做的独立工程实现，**不是作者全部表格的原始实验提交，也不是 bit-exact reproduction**。原始 C24 clone 的字节、Git 历史、gitlinks、许可证保留，工作文件设为只读；修改仅在 HDD 的 `sources/paper_text_variant`。核心补丁见 [SOURCE_PATCH.diff](SOURCE_PATCH.diff)，补丁所依赖的 Python loss、恢复与 runner 模块在 `reproduction/radegs_paper_v01/stage2/`，由配置中的明确 `PYTHONPATH` 加载。

## 明确采用的公式

[v2 PDF](https://arxiv.org/pdf/2406.01467v2) 第 6 页 Eq.23 的逐像素目标为

\[
L_d=\sum_i\sum_j\operatorname{stopgrad}(w_iw_j)(z_i-z_j)^2,\quad w_i=\alpha_iT_i.
\]

`z_i` 是 C24 Eq.4 仿射平面求得的 **camera-z**。遍历当前高斯时，已有权重和、一阶、二阶矩分别为 `M,S,Q`，新增项为 `2*w*(z*z*M+Q-2*z*S)`；乘 2 对应有序双重求和。深度梯度为 `4*w*(M_total*z-S_total)`。CUDA 中只把这一项送入深度链路，不为 distortion 增加 opacity/weight 的梯度；由位置、尺度、旋转影响深度的梯度仍保留。

C24 [forward.cu #L746-L779](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/submodules/diff-gaussian-rasterization/cuda_rasterizer/forward.cu#L746-L779) 使用 mapped/NDC 深度和单次无序 pair 累积；[train.py #L140-L146](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/train.py#L140-L146) 再除以 detached alpha² 并乘 RGB edge。新活动路径全部移除这些差异。保留的内部变量名称 `mapped_max_t` 在 forward 中实际直接赋值为 `depth`，不会执行 NDC 变换；backward 的旧 NDC 导数声明已删除。

Eq.24 实现为

\[
L_n=\sum_iw_i(1-n_i\cdot\widetilde n)
=M-\left(\sum_iw_in_i\right)\cdot\widetilde n.
\]

直接使用渲染器的 alpha 和未归一化 blended normal，不把混合 normal 做 normalize，也不除以 alpha。`n_tilde` 仅由最终 median camera-z depth 的有限差分计算，不混合 expected depth。Eq.24 的权重与 depth-normal 路径均保留梯度；论文对 Eq.23 明说 weight detach，没有把它额外扩展到 Eq.24。C24 [train.py #L148-L157](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/train.py#L148-L157) 的 normalized mixed normal 与 0.4/0.6 两种 depth-normal 混合不再采用。

## Schedule 和保留项

固定 `wd=100, wn=5`。迭代 1–15000 只含 photometric，15001–30000 加入 geometry；不会运行 wn=.05 对照 arm。命令显式传参且入口校验，不依赖 C24 的 `.05` 默认。[C24 参数源](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/arguments/__init__.py#L76-L100) 仍保留在原 clone 中。

Eq.4 仿射 camera-z、原高斯 alpha/RGB 合成、SH、相机投影、Mip 3D filter、GOF densification、DTU decoupled appearance、median 深度选择和 TSDF/marching cubes 继承 C24。kernel 的改动限定为 distortion 累积与其深度导数，不改 RGB/alpha、normal/depth 的 forward 定义或其原有 backward。GPU smoke 将比较原版与变体 RGB、radii、expected-depth sum、median depth、alpha、blended normal，并比较 RGB+alpha loss 的参数梯度；这些比较尚需真正空闲 GPU，编译通过不代表比较通过。

不引入 C25/C26 深度重写、PGSR 多视图、Objaverse、别的训练 checkpoint 或第二个场景。

## 论文未充分指定、在此公开固定的细节

| 项目 | 本 pilot 的选择与限制 |
|---|---|
| 图像级 reduction | 两个逐像素 loss 都取完整图像的 mean。论文公式未完整规定图像/批 reduction；不能把这一选择说成已找到作者隐藏配置。 |
| depth-normal 离散化 | 继承 C24 的中心差分、相机坐标、像素中心 +0.5、行差分 cross 列差分、零边框；实现改成 device-agnostic torch，CPU/GPU 可检验。空洞/边界不新增 mask 或 edge 加权。 |
| median | 保留 C24 遍历时 `T>0.5` 的 median 选择，不改成除以总 opacity 的加权中位数。TSDF 仍按 alpha≥.5 与图像 alpha mask 剔除。 |
| DTU 分辨率 | 下载后实际 scan24 为 1554×1162 RGBA；C24 `-r 2` 实际是 777×581。没有重采样成假定的 800×600。 |
| 视角与背景 | 依 C24 同期 README：49 个视角全部训练，不加 `--eval`，无 held-out RGB 测试；训练黑背景、appearance 开启。mesh 脚本原有白背景保留。 |
| 优化器与其余超参 | C24 原值保留。训练内的评估视图日志用 `--test_iterations -1` 禁用，几何评价在最终独立 stage 运行。 |
| 30k 的最后一步 | C24 最后一轮不调用 optimizer.step，且在 step 前保存。本变体每轮都有一次 step 调用机会，并在 step 后保存，使“30k”边界明确。densification 内部替换参数的原逻辑保留。这是公开的工程差异。 |
| 恢复 | 新格式保存全部高斯参数、appearance embedding/network、3D filter、densification buffers、Adam、Python/NumPy/torch/CUDA RNG、剩余相机 stack；不使用不完整的 C24 capture tuple。CPU 恢复已检验，真实 GPU 长程恢复仍未验证。 |
| 评价随机性 | C24 DTU evaluator 的 `default_rng()` 未固定 seed，保留其算法与默认参数；不能声称评价 bit-exact。仅修正调用方不传播子进程错误的问题。 |
| 环境 | Python 3.9 / torch 2.3.1+cu121 / CUDA 12.1 / GCC 12.4 为本次实际解析并锁定的隔离环境。同期 README 没有指定全部精确版本；不是作者历史完整环境。 |

## 已验证与尚未验证

CPU 已检查 Eq.23 双重求和、camera-z 尺度关系、weight detach、解析梯度、共享 C++/CUDA header 的 host recurrence；Eq.24 的权重代数和 autograd、median-depth normal gradcheck、15000/15001 边界、完整 Adam/RNG 恢复，以及 GPU/queue/seal 安全条件。日志在 [CPU 测试证据](stage2_evidence/tests/paper_math_FINAL_GREEN.log) 和 [preflight](stage2_evidence/preflight.json)。

CUDA smoke 预先固定了单/多高斯 forward oracle、冻结权重的有限差分、normal/median 链路梯度、baseline RGB/alpha 回归，以及真实 scan24 的初始化/appearance/filter forward+backward（0 optimizer steps）。若任何门槛失败，runner 写 `ENGINEERING_NOT_READY` 并停止，不能改回 C24 loss、调低 wn 或跳过测试。固定 fixture 的通过也不构成所有高斯配置的数学证明；验证限制随最终日志报告。
