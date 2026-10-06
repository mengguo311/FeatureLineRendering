"""Generate reviewable delivery summaries directly from sealed measured evidence."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from runtime import ART, EXP, OUT, ROOT, atomic_json, digest, guard, sha, source_hashes

def read(name):return json.loads((ART/name).read_text())
def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)

def main():
    guard('report',gpu=False)
    build=read('BUILD.json');pinned=read('PINNED_SOURCE.json');test=read('results/NATIVE_TESTS.json')
    reproduction=read('results/REPRODUCTION.json');verify=read('results/REAL_RERUN_VERIFICATION.json')
    scenes=read('CAMERA_FREEZE.json')['scenes']
    units=[read('results/'+n+'.json') for n in ('lego_r_001','lego_r_014','chair_r_001','chair_r_014')]
    protocol=json.loads((EXP/'protocol.json').read_text())
    assert test['passed'] and verify['passed'] and reproduction['success']
    assert read('PROTECTED_BEFORE.json')==read('PROTECTED_AFTER.json')
    native_modified=[p for p,h in build['variants']['original']['files'].items()
                     if build['variants']['patched']['files'][p]!=h]
    locations={}
    targets={'cuda_rasterizer/forward.cu':['renderCUDA(', 'const float weight = T * alpha;', 'void FORWARD::render('],
             'cuda_rasterizer/rasterizer_impl.cu':['int CudaRasterizer::Rasterizer::forward('],
             'rasterize_points.cu':['RasterizeGaussiansAttributionCUDA('],
             'diff_gaussian_rasterization/__init__.py':['class AttributionOutput(', 'def rasterize_gaussians_attribution(',
                'class _RasterizeGaussiansAttribution(', 'ctx.mark_non_differentiable(ids, weights, all_sum, final_T)']}
    for path,needles in targets.items():
        lines=(OUT/'native/patched'/path).read_text().splitlines()
        locations[path]={needle:next(i for i,l in enumerate(lines,1) if needle in l) for needle in needles}
    atomic_json(ART/'SOURCE_LOCATIONS.json',dict(patched_files=native_modified,
        generated_source_root=str((OUT/'native/patched').relative_to(ROOT)),functions=locations,
        modified_kernels=['renderCUDA<3, true>'],off_kernel='renderCUDA<3, false>',
        unchanged_native=['cuda_rasterizer/backward.cu','cuda_rasterizer/backward.h','cuda_rasterizer/rasterizer_impl.h'],
        patch_sha256=sha(EXP/'native.patch')))
    memory_rows=[]
    for K in (1,4,8,16):
        pair=800*800*K*8; maps=800*800*8
        memory_rows.append([K,f'{pair:,}',f'{maps:,}',f'{pair+maps:,}',f'{(pair+maps)/2**20:.5f}'])
    perf_rows=[];coverage_rows=[];overheads=[]
    for u in units:
        baseline=u['benchmarks'][0]['whole_forward_cuda_events']['median_ms']
        for b in u['benchmarks']:
            label=b['label'].removeprefix(u['unit']+'_')
            t=b['whole_forward_cuda_events'];kernel=b['compositor_kernel_profiled'];m=b['memory']
            assert 'median_ms' in kernel
            copy=b.get('cpu_copy_all_debug_maps',{}).get('median_ms')
            perf_rows.append([u['unit'],label,f"{t['median_ms']:.4f}",f"{t['p95_ms']:.4f}",
                f"{t['median_fps']:.1f}",f"{t['p95_fps']:.1f}",f"{kernel['median_ms']:.4f}",
                f"{kernel['p95_ms']:.4f}",f"{kernel['median_fps']:.1f}",f"{kernel['p95_fps']:.1f}",
                f"{m['forward_peak_delta_allocated_bytes']/2**20:.2f}",'-' if copy is None else f'{copy:.2f}'])
            if label=='K8':overheads.append(dict(unit=u['unit'],vs_actual_stock_percent=(t['median_ms']/baseline-1)*100))
        c=u['checks'];coverage_rows.append([u['unit'],f"{c['sum_all_vs_alpha_max_error']:.3g}",
            f"{c['global_mass_coverage']:.5f}",f"{c['coverage_mean_positive_alpha']:.5f}",
            f"{c['missing_mass_mean']:.5f}",f"{c['missing_mass_max']:.5f}"])
    synth=read('results/SYNTHETIC_BENCHMARK.json')
    synth_rows=[]
    for b in synth['benchmarks']:
        t=b['whole_forward_cuda_events'];k=b['compositor_kernel_profiled']
        synth_rows.append([b['label'].removeprefix('synthetic_'),f"{t['median_ms']:.5f}",f"{t['p95_ms']:.5f}",
                          f"{t['median_fps']:.1f}",f"{t['p95_fps']:.1f}",f"{k['median_ms']:.5f}",f"{k['p95_ms']:.5f}"])
    example=units[0]['benchmarks'];allocator_rows=[]
    for b in example:
        m=b['memory'];allocator_rows.append([b['label'].removeprefix('lego_r_001_'),
            f"{m['base_allocated_bytes']/2**20:.2f}",f"{m['peak_allocated_bytes']/2**20:.2f}",
            f"{m['base_reserved_bytes']/2**20:.2f}",f"{m['peak_reserved_bytes']/2**20:.2f}"])
    report=f'''# GAER 原生 attribution buffer v0.1 — 工程验证

已完成上传原文 section 25 FIRSTTASK，并在此停止。新增 opt-in 原生 CUDA top-K `T_before*alpha` 缓冲区；没有执行边检测、邻域分布差、Gaussian 边评分、移除因果实验、线/笔触渲染或协方差编辑。结果只支持缓冲区工程正确性，不验证 H1 或几何/时间语义。

## 来源和隔离

上传文件 681 行，原始字节 SHA256 为 `{read('ORIGINAL_INSTRUCTIONS_SHA256.json')['sha256']}`。文件未修改，来源与启动提交见 `ORIGINAL_INSTRUCTIONS_SHA256.json`。工作基准为 `b2d562753de6759b1bb2d3ac2034b35dc080d025`，启动提交为 `20f6e4baa4f2c6c90319f8f030da0426154195ab`；目标分支仅 `gaer-attribution-buffer-v01`。

完整读取指定的 `native.py`、旧 `adapter.py` 及其 runtime 的字面路径，确认二者实际加载 `onec_stock_C.so`。源根为 `{pinned['source_path']}`，rasterizer commit `{pinned['source_commit']}`，父 3DGS commit `{pinned['parent_commit']}`；446 个必要源码/GLM 文件的 SHA256 见 `PINNED_SOURCE.json`。源码集合 hash `{pinned['aggregate_sha256']}`。历史 top32/RaDe patch 已检查并记录在 `REUSE_AUDIT.json`，未复用它的深度、法线或 renderer。

源码仅复制到忽略的 `out/gaer_attribution_buffer_v01/native/`；Git 只保存 8 文件的最小 patch、源码哈希、构建 recipe、上游原样 license 和验证证据。独立模块 `gaer_original_C` 与 `gaer_native_C` 使用同一现有 Python/Torch/CUDA 编译器，`MAX_JOBS=2`、sm_86、C++17，沿用实际 stock 编译参数，无 fast-math 或额外优化参数。未安装或覆盖生产模块。Python import 使用独立 `gaer_attribution` 接口。原 stock module、全部源文件、模型及 metadata 的前后 hash 均一致。

## 合成路径与 API

唯一修改的 CUDA 合成 kernel 是 `renderCUDA<3,true>`；关闭路径使用编译期 `renderCUDA<3,false>`。`preprocessCUDA`、排序/point_list、backward kernels 和 `ImageState/GeometryState/BinningState` 布局保留。补丁传递新增指针的函数包括 `FORWARD::render`、`CudaRasterizer::Rasterizer::forward` 和新增 `RasterizeGaussiansAttributionCUDA`。生成后函数/行号见 `SOURCE_LOCATIONS.json`：合成 kernel 起于 forward.cu:263，权重计算于 :367，dispatch 于 :408，C++ debug entry 于 rasterize_points.cu:119，Python debug autograd Function 于 __init__.py:263。

8 个 native 修改文件：{', '.join('`'+p+'`' for p in native_modified)}。实验 harness、测试、重现脚本在 `experiments/gaer_attribution_buffer_v01/`，无需 giant repo 或二进制提交。

```python
import sys
sys.path.insert(0, 'experiments/gaer_attribution_buffer_v01/src')
from gaer_attribution import GaussianRasterizer
renderer = GaussianRasterizer(settings)  # stock settings，full SH3 或 precomputed colors
rgb, radii = renderer(**model)           # 默认关闭，原返回值和 RGB autograd
out = renderer(**model, attribution=True, K=8)
ids = out.gaussian_ids.cpu().numpy()
weights = out.gaussian_weights.cpu().numpy()
alpha = out.accumulated_alpha            # 1 - out.final_T
```

`K` 默认 8，支持任意 Python int 1–32，包含 1/4/8/16；启用时拒绝负数、0、33、非整数及 bool。IDs 为 CUDA contiguous int32 `[H,W,K]`，原始 PLY/model 行编号；weights 为 float32 `[H,W,K]`，非归一化正的 alpha*T。未用槽为 ID=-1、weight=0。float32 `[H,W]` 的 `all_contribution_sum` 与 `final_T` 在 debug 开启时一并返回；dominant_id 为第一槽，accumulated_alpha 为 `1-T`。所有归因输出显式 `mark_non_differentiable`，RGB 保留梯度。

与 stock 完全相同的 power/filter、alpha clamp 0.99、alpha `<1/255` 跳过、`test_T<0.0001` 提前终止。在最后一种情况下，当前 splat 不进入 RGB、T 不更新，本缓冲区也不记录它。只在 RGB 接受后、T 更新前计算 `T*alpha`；从 `collected_id[j]` 获取 original ID。top-K 按实际权重降序，相等 FP32 权重保留已有深度遍历次序。直接对每像素输出槽进行插入，时间复杂度 O(accepted contributions × K)，没有 H×W×N 或 dense fallback，也没有额外 per-pixel 局部 K 数组。RGB backward 的 native ABI、十个 saved tensors 顺序及原始 RGB backward 方法保留。

stock 的 P=0 特例返回零 RGB 而非 background；本阶段保留该行为，同时归因数组初始化为 -1/0，sum=0、T=1。不要用这个空模型特例检查带背景的颜色重建公式。

## RED → GREEN 和梯度/训练验证

`tdd/vertical_RED.log` 在真实实际 stock CUDA 输入上得到缺失新参数的 TypeError；随后相同测试在隔离 native debug 路径通过，日志为 `vertical_GREEN.log`。`PROTOCOL_SEAL.json` 在看结果前固定 FP32 绝对容差 2e-6、RGB 逐位一致要求、测试 hash 与 RED hash，没有事后放宽。

六个 native 验证测试全部通过：中心精确 alpha*T、20 个贡献超过 K、前景遮挡与 opacity/真实权重反向排序、相等权重的稳定次序、alpha 临界值、0.99 clamp、近裁剪、被拒绝的终止 splat、空模型/空 tile、图像边界截断、K 前缀/质量单调、dtype/layout/CPU numpy、默认 8 和非法 K。`all_sum` 累加全部接受项后才检查 top-K；与独立乘积得到的 `1-T` 比较，未把截断 top-K 质量等同于完整 alpha。

actual stock、隔离 unmodified、debug OFF、debug ON：合成 RGB 最大误差 0、radii 一致；xyz、scales、quaternion、opacity、full SH3 或 precomputed color、means2D 梯度逐位一致，最大差值 0。损失是非平凡加权 RGB 二次项加颜色乘积，输入远离 clamp 不连续点，各有效参数组梯度非零。单像素选型避免多像素原子加法顺序噪声。真实 Adam 一步比较了梯度、更新参数及 optimizer state；额外 raw 模型测试使用 log-scale、opacity logit、归一化 quaternion、SH DC/rest，原版/OFF/ON 更新均逐位相同。这些是已测 fixture 的结论，不声称对所有训练任务做过穷尽测试。详见 `results/NATIVE_TESTS.json`。

## 原始模型与四个 800×800 视图

Lego 原始 30k PLY：310,475 个 Gaussian，SHA256 `{scenes['lego']['model_sha256']}`；Chair：256,690 个，SHA256 `{scenes['chair']['model_sha256']}`。两者均保留 16×3 SH3 系数与所有 model 行。摄像机 r_1/r_14 从 DATA_FREEZE 的冻结文件名匹配实际 transforms_train.json；它是 86 帧子集，r_14 的 metadata 行号为 12，不能用 14 直接取行。四个 w2c 与冻结记录 float64 最大误差均为 0；原始图片确为 800×800。

每视图保存 baseline、patched OFF、patched ON 的 PNG 与原始 float32 RGB，native IDs/weights、all_sum/T、alpha/coverage/missing_mass、dominant ID；原始完整数值位于忽略的 `out/.../views/`，由原子目录批次和 `seals/*.json` 封存。tracked 四张小 panel 的顺序为 RGB、dominant ID、alpha、coverage。实际 vanilla 没有公开 depth 输出，状态为 **NOT_AVAILABLE**，未发明 proxy depth。

四视图实际 stock / 隔离原版 / OFF / ON 的 RGB 都逐位相同、最大误差 0。独立 `verify_real.py` 又在全部视图和 K=1/4/8/16 上实际重渲染，验证 RGB、精确前缀、非负权重、质量单调、K 不影响 all_sum/T，以及原始输入和输出 seals。K=8 统计：

{table(['视图','max |all_sum-(1-T)|','全图 top-K/alpha','alpha>0 像素均值 coverage','missing mass 全图均值','missing mass 最大值'],coverage_rows)}

全图比例是 `sum(top-Kmass)/sum(alpha)`，像素 coverage 是 `top-Kmass/alpha`（alpha=0 处定义为 0）；missing_mass=`alpha-top-Kmass`，原始数值保留 FP32 舍入误差。top-K 缺失项不代表真实零贡献。完整质量检查上限 {max(u['checks']['sum_all_vs_alpha_max_error'] for u in units):.8g} < 2e-6。

## 实测内存与性能

RTX A6000 GPU0，PyTorch {build['torch']}，现有 CUDA 12.6 compiler，CPU affinity 两核。每 unit 检查 GPU0 所有进程，拒绝其他占用而不终止任务；固定 root 4GiB、common Git 1.5GiB reserve 与 stage 5GiB cap。资源记录在忽略的 `logs/resource_checks.jsonl`。

800×800 输出张量的实际 numel×element_size 字节数（非估计峰值）：

{table(['K','IDs+weights bytes','sum+T bytes','debug 总 bytes','MiB'],memory_rows)}

只算 IDs/weights 为 H×W×K×(4+4)，两张 debug map 再加 H×W×8。alpha 是调用方 `1-T` 派生 map；coverage、missing_mass、图片和 CPU 临时数组不属于 native API 的上述容量。

每场景/相机/参数完全相同，5 次 warmup、20 次 CUDA event 完整 forward、显式 synchronize；另记录 wall 时间与全部样本。CUDA event 完整 forward 包含本 renderer 内部 host prefix readback/调度产生的 GPU 空档。compositor kernel 用独立 20 次 torch.profiler CUDA/CUPTI pass 获取，因 profiler instrumentation 单独标记，不混入主 forward 数字。CPU copy 是另行 20 次把四张 debug 输出转 CPU，包含 pageable CPU 分配；不含磁盘 PNG IO。FPS 的 p95 是 1000/ms 样本的 p95，另在 JSON 记录保守 p05 FPS。

{table(['视图','模式','forward median ms','p95 ms','median FPS','p95 FPS','kernel median ms','p95 ms','median FPS','p95 FPS','forward peak Δallocated MiB','CPU copy median ms'],perf_rows)}

K=8 对 actual stock 的 forward 中位开销分别为 {', '.join(o['unit']+' '+format(o['vs_actual_stock_percent'],'.1f')+'%' for o in overheads)}。OFF 相对 actual 的微小实测差异也已列出，没有宣称零性能开销。O(K) 插入开销随 K 增大；当前实现以正确性为目标，没有进入后续 runtime 优化阶段。

上述 peak Δallocated 为 `max_memory_allocated - base_allocated`，重置峰值后实际运行一次 native forward，包含 RGB/radii、debug 输出和原始排序/几何临时 workspace；不是公式推算。输出 byte 总数与 allocator 峰值差别来自分配颗粒及 workspace。例 Lego r_001 的 allocator 数字：

{table(['模式','base allocated MiB','peak allocated MiB','base reserved MiB','peak reserved MiB'],allocator_rows)}

allocated 是活跃 tensor/workspace，reserved 是 PyTorch cache；reserved 依赖固定执行顺序与缓存历史，未当作实际额外 tensor 容量。其他视图同类原始值均在各 unit JSON。没有 H×W×N 的储存。

同一 20-Gaussian 单像素解析 fixture、相机准备位于计时外的性能：

{table(['模式','forward median ms','p95 ms','median FPS','p95 FPS','kernel median ms','p95 ms'],synth_rows)}

`reproduce.py --benchmark` 已真实执行一次，重建检查、垂直 API、六个 native checks、四视图四个 K 重渲染及完整 benchmark 重复均通过，receipt 见 `results/REPRODUCTION.json`；独立第二次 real 性能在 `results/REBENCHMARK_REAL.json`，保留首次 canonical 结果以展示测量差异。已解决的 PATH/EOF/profiler API/metadata 匹配问题见 `FAILURE_STATES.json`，无现存 blocker 或数值失败。初次完整命令行进程检查意外显示了无关敏感参数；后续检查仅 UUID/PID，Git 交付不含原始进程输出、agent 日志或该敏感值，事件已在同一审计文件说明。

## 科学边界与交付

alpha*T top-K 与多邻居 raster state 机制和 [Hao/Mukai SA2026 作者预印本](https://mukai-lab.org/content/SA2026PosterHao.pdf) §2 重合，不作新颖性声明。未实现论文或上传文档的后续边算法。归一化 L1/支持重叠关系、脊线处 grad(E) 可能为零、top-K 未保留项的未知质量、删除导致 T/空洞变化，以及背景/SH 色彩影响仅写在 `FUTURE_CAVEATS.md`。

`REPRODUCE.md` 给出实际使用的单命令 recipe；`FINAL.json` 汇总 source/patch/module hashes、API、内存、性能、测试与 failure state。仅提交本阶段 experiments/artifacts，ignored out 保留 full arrays、builds、资源/重现日志和 push readback receipt；不提交模型、CUDA dependencies 或 raw agent logs。发布目标为 SSH `git@github.com:mengguo311/FeatureLineRendering.git` 的 `refs/heads/gaer-attribution-buffer-v01`，最终 commit/readback/clean 证明写入 `out/gaer_attribution_buffer_v01/PUBLISH_RECEIPT.json`，避免把自身 commit hash 写入自身内容的循环依赖。基准分支保持原 SHA。
'''
    (ART/'REPORT_ZH.md').write_text(report)
    final=dict(status='SECTION25_FIRSTTASK_COMPLETE',stop=True,future_phases_started=False,
        original_instructions=read('ORIGINAL_INSTRUCTIONS_SHA256.json'),
        scope='native opt-in alpha*T attribution buffer and engineering validation only',
        source=dict(path=pinned['source_path'],commit=pinned['source_commit'],aggregate_sha256=pinned['aggregate_sha256'],
                    patch_sha256=sha(EXP/'native.patch'),modules={k:{'path':v['binary'],'sha256':v['binary_sha256']} for k,v in build['variants'].items()},
                    actual_module_before_after_sha256=None),
        api=dict(import_path='experiments/gaer_attribution_buffer_v01/src',package='gaer_attribution',
                 opt_in='GaussianRasterizer(settings)(**model, attribution=True, K=8)',default_K=8,K_range=[1,32],
                 IDs=dict(shape='H,W,K',dtype='int32',unused=-1,identity='original model row'),
                 weights=dict(shape='H,W,K',dtype='float32',unused=0,normalized=False,formula='T_before*alpha'),
                 maps=dict(shape='H,W',dtype='float32',names=['all_contribution_sum','final_T']),
                 attribution_differentiable=False,RGB_differentiable=True,tie_policy=protocol['tie_policy'],depth='NOT_AVAILABLE'),
        modified_native_files=native_modified,modified_kernels=['renderCUDA<3,true>'],functions=locations,
        validation=dict(vertical_RED=True,vertical_GREEN=True,native_tests=test['tests'],native_passed=test['passed'],
                        gradient_max_error=0.,training_one_step_exact=True,raw_model_Adam_exact=True,
                        real_views=len(units),resolution=[800,800],full_SH_degree=3,
                        real_RGB_max_error=0.,real_RGB_bitwise_equal=True,all_contributions_alpha_tolerance=2e-6,
                        real_sum_alpha_max_error=max(u['checks']['sum_all_vs_alpha_max_error'] for u in units),
                        real_all_K_rerun_passed=verify['passed'],selfcontained_reproduction_passed=reproduction['success'],
                        protected_sources_and_checkpoints_unchanged=True),
        memory=dict(formula_bytes='H*W*(8*K+8)',at_800x800={str(k):800*800*(8*k+8) for k in (1,4,8,16)},
                    no_H_W_N=True,peak_measurement='per-forward reset_peak_memory_stats; allocated/reserved reported separately'),
        runtime=dict(warmup=5,repeats=20,K8_overhead_percent_vs_actual=overheads,
                     compositor_timing='separate profiler CUDA/CUPTI pass',cpu_copy='separate 20 copies',
                     canonical_results=[str((ART/'results'/(u['unit']+'.json')).relative_to(ROOT)) for u in units],
                     measured_not_estimated=True,complexity='O(accepted_contributions*K)'),
        failures=read('FAILURE_STATES.json'),science_claim='engineering only; H1/geometric/temporal claims untested; mechanism not novel',
        delivery=dict(branch='gaer-attribution-buffer-v01',remote='git@github.com:mengguo311/FeatureLineRendering.git',
                      base='b2d562753de6759b1bb2d3ac2034b35dc080d025',
                      publish_receipt='out/gaer_attribution_buffer_v01/PUBLISH_RECEIPT.json'),
        source_code_sha256=source_hashes())
    # Find actual binary hash by its basename rather than inferring a directory.
    final['source']['actual_module_before_after_sha256']=next(h for p,h in read('PROTECTED_AFTER.json').items() if p.endswith('/build/stock/onec_stock_C.so'))
    atomic_json(ART/'FINAL.json',final)

if __name__=='__main__':main()
