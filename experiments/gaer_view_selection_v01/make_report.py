"""Reports derive every real scene count/statistic from actual sealed units."""
import json
from itertools import combinations
import numpy as np
from PIL import Image
from stage_runtime import ROOT,ART,EXP,OUT,atomic_json,sha
from media import sheet
from selection import jaccard

def main():
    freeze=json.loads((ART/'PREREGISTRATION.json').read_text());results=[];missing=[]
    for name,r in freeze['scenes'].items():
        for c in r['cameras']:
            key=name+'_'+c['key'];path=ART/'results'/(key+'.json')
            if path.exists():results.append(json.loads(path.read_text()))
            else:missing.append(key)
    cal=json.loads((ART/'results/SYNTHETIC.json').read_text());pairs=[]
    for scene in freeze['scenes']:
        rows=[r for r in results if r['scene']==scene]
        items=[];full=[]
        for r in rows:
            key=r['unit'];im=Image.open(ART/'figures'/(key+'_gaer_ratio_selected_only.jpg')).copy()
            items.append((f'{key} selected original kernels ONLY n={r["main_selected_count"]}; 0.5% diagnostic',im))
            original=Image.open(ART/'figures'/(key+'_full_RGB.jpg')).copy()
            full.extend([(key+' full native SH3',original),(key+' selected-only native original SH3',im)])
        if items:sheet(ART/'figures'/(scene+'_fourview_selected_only.jpg'),items,cols=2,tile=800)
        if full:sheet(ART/'figures'/(scene+'_fourview_full_RGB_vs_selected_only.jpg'),full,cols=2,tile=800)
        for a,b in combinations(rows,2):
            x=np.load(ROOT/a['diagnostic_archive'])['gaer_ratio_0.005_ids'];y=np.load(ROOT/b['diagnostic_archive'])['gaer_ratio_0.005_ids']
            pairs.append(dict(scene=scene,views=[a['unit'],b['unit']],selected_set_jaccard=jaccard(x,y),
                interpretation='independent per-view selection ID overlap only; no multiview/temporal consistency claim'))
    atomic_json(ART/'results/VIEW_SET_COMPARISON.json',pairs)
    manifest=[]
    for directory in ('figures','downloads'):
        for path in sorted((ART/directory).glob('*')):
            item=dict(path=str(path.relative_to(ROOT)),sha256=sha(path),bytes=path.stat().st_size)
            if directory=='figures':
                with Image.open(path) as im:item['dimensions']=list(im.size)
            manifest.append(item)
    atomic_json(ART/'MEDIA_MANIFEST.json',dict(files=manifest,source_method_sha256=freeze['source_method_sha256'],
        panel_semantics='full RGB / alpha boundary / edge-gated observed L1 / unknown residual / full-model-T contribution / selected-only changed T / same-count baseline / endpoints and centers',
        crops='three fixed candidate positions sorted by row, 128x128 -> 256x256; positions labeled; not selected by effect'))
    lines=['# GAER 按视角选核与有界删除诊断 v0.1','',
        f'已完成 {len(results)}/8 个实际 800×800 原生视角。输出包含每视角独立分数、原始 ID、仅选中核的原色 SH3 渲染，以及真实 opacity=0 删除对照。主展示为预注册 0.5% 预算诊断；自动阈值状态逐视角记录，不能将诊断预算当作自动选核成功。',
        '', 'Lego 保留全部 310475 行、Chair 全部 256690 行，原始 30k PLY/SH3/opacity/scale/rotation 与相机 metadata 均只读。相机按 r_1、r_14、r_7、r_33 文件名匹配实际 metadata，不按文件名中的数字直接索引。沿用已有隔离 GAER API 和二进制，未构建新 kernel。旧树脏 REPRODUCTION.json 的字节 SHA 被保护，未恢复、编辑或提交旧树。',
        '', '## 方法与边界', '',
        '深度为 NOT_AVAILABLE，额外几何数据 NOT_RUN。本次 E=1 是 alpha>0.5 的一像素内轮廓，不代表全部内部几何。法向来自 signed Euclidean distance 的梯度；修正原文 ∇E 在边响应脊线处可能为零的问题。端点 ±1/2/4px 使用固定法向；双线性采样先合并四邻域的 ORIGINAL ID，再做 D_i=|w_i^-−w_i^+|，没有逐槽插值。',
        '', 'raw_i=Σ E D_i；score_i=raw_i/(full_visibility_i+1e−6)，full_visibility 来自原生 RGB feature pass 对独立 precomputed color 的全像素梯度。bg=0、feature=1，各颜色通道相互独立；原始 RGB 始终另用完整 SH3。可见质量<0.25 的核分数置零，raw 最低证据 0.01。全量 raw、floored ratio、full visible mass 按原始模型行输出 NPY/NPZ。CPU 独立逐射线 accepted alpha*T 真值验证此梯度。',
        '', 'top-K 没出现的 ID 是截断未知项。双线性插值后的 R^-+R^+ 给出 |true L1−observed L1| 的界；保存 lower=max(0,L1−Rsum)、upper=L1+Rsum。背景/画面外贡献可为零，positive-alpha 截断遗漏不能称真实零。本阶段 K8 为主，全部 8 视角实际 K16/K32 重渲染并验证精确 K8 前缀。',
        '', '同数量对照为 GAER raw、full-native alpha*T 在固定轮廓上的参与质量、独立 seed 的可见质量分箱匹配随机组。各方法原色 selected-only 渲染确实移除其他核、T 发生改变；full-T contribution feature pass 保留其他核的遮挡，单独绘制。投影中心与完整 footprint 的位置/质量分别统计。随机组全图质量匹配误差单独报告，不保证逐像素区域匹配。',
        '', '三个预算为原模型计数的 0.1%、0.5%、1%（向上取整、仅有证据 eligible 核，不补零分核）。它们是诊断档位，没有按真实结果调最优比例。自动 ratio floor 由独立平坦共面 null 的 p99.9×2 与 numerical floor 的最大值固定，随后要求总未知界/L1≤0.1 与 heldout δ4 Jaccard≥0.6。删除结果从未参与阈值选择。',
        '', '## 合成证据与限制', '',
        f'CPU 射线积分的 full-visibility 最大绝对误差 {cal["cpu_ray_max_mass_error"]:.8g}。纹理只改变颜色时，native IDs/weights 逐位相同；RGB 最大变化 {cal["texture_RGB_max_change"]:.6g}。在独立真值明确无内部几何边的 441 个共面内点上，observed L1 均值 {cal["null_observed_L1_mean"]:.6g}，最大 {cal["null_observed_L1_max"]:.6g}。这是 footprint 平滑导数的反例；自动 ratio floor={cal["auto_ratio_floor"]:.6g}。',
        '', 'B4 standalone detector 为 NOT_RUN；没有用只在候选边处非零的图计算 AUROC/AP。真实图中的轮廓定位来自 alpha，并非 GAER 新检测器。本实验只检验已知固定轮廓上的核参与排序，H1 一般几何版本未验证。',
        '', '## 八视角结果', '',
        '|视角|原始核数|诊断选中数|自动状态/候选数|K8 全图质量覆盖|端点未知界/L1|选中 full-T 质量落在 ring4|full-T outside4 质量|',
        '|---|---:|---:|---|---:|---:|---:|---:|']
    for r in results:
        fs=r['budgets']['0.005']['gaer_ratio'];a=r['automatic'];v=r['coverage']
        lines.append(f'|{r["unit"]}|{r["gaussian_count"]}|{r["main_selected_count"]}|{a["state"]}/{a["proposed_count"]}|{v["global_mass_coverage"]:.4f}|{v["aggregate_ambiguity_over_observed_L1"]:.4f}|{fs["ring4_mass_fraction"]:.4f}|{fs["outside4_mass_fraction"]:.4f}|')
    lines.extend(['','宽 footprint 或内部覆盖是应保留的失败情况；中心落在轮廓附近不代表全部贡献只位于轮廓。具体 raw/ratio dispersion、eligible/weak-mass counts、coverage quantiles 与 endpoint bound 均见每视角 JSON。','',
        '## 独立真实删除（有界 B）','','同数量/质量对照均执行孤立内存 clone opacity=0 后 native 重渲染。target ring2/ring4、outside4=|SDF|>4、exterior4=SDF<−4、interior4=SDF>4 在选分与删除前固定。边 profile 用 −8..8px 原生 RGB：±4px contrast、梯度质量中心 location 与标准差 width。出现空洞意味着 alpha 损失，不视作好线或唯一几何因果责任。','',
        '|视角/方法|n|Σ full mass|ring4 RGB MSE|outside4 RGB MSE|alpha 前景损失像素|contrast Δ|location Δpx|width Δpx|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|'])
    for r in results:
        for method,b in r['causal'].items():
            lines.append(f'|{r["unit"]}/{method}|{b["selected_count"]}|{b["summed_full_visibility"]:.2f}|{b["ring4_mse"]:.6g}|{b["outside4_mse"]:.6g}|{b["alpha_foreground_lost_pixels"]}|{b["contrast_change"]:.4g}|{b["location_pixels_change"]:.4g}|{b["width_pixels_change"]:.4g}|')
    lines.extend(['','这些实测支持“边参与”的比较，不能只因删除损伤边就宣布唯一几何责任。完整 alpha 变化、位置/宽度 before/after 与区域维度在 per-view JSON。较小 opacity± 诊断 NOT_RUN。','',
        '## K / 端点与性能','','|视角|K16 / K32 相对 K8 Jaccard|δ1 / δ4 相对 δ2 Jaccard|native stock / K8 / K16 / K32 median ms|CPU 三个 δ 比较 ms|全 unit 秒|',
        '|---|---|---|---|---:|---:|'])
    for r in results:
        t=r['timing'];k=r['K_sensitivity'];v=r['stability']
        ms=' / '.join(f'{t[z]["cuda_median_ms"]:.3f}' for z in ('native_stock','K8','K16','K32'))
        lines.append(f'|{r["unit"]}|{k[0]["K8_jaccard"]:.4f} / {k[1]["K8_jaccard"]:.4f}|{v["delta1_delta2_jaccard"]:.4f} / {v["delta2_delta4_jaccard"]:.4f}|{ms}|{t["CPU_sparse_comparison_all_deltas_ms"]:.1f}|{r["end_to_end_seconds"]:.2f}|')
    lines.extend(['','CUDA 完整 forward 为 3 warmup + 5 event/wall samples，包含 renderer 内部 host 调度空档，未声称单 compositor kernel 的时间。CPU copy、full-visibility backward、sparse comparison 与端到端单位时间分开记录。medium 512 边像素 batches，没有 H×W×N。GPU0 PID-only ownership checks/CPU2/root4GiB/Git1.5GiB/stage8GiB 见 ignored logs。','',
        '## 可直接查看的输出','','- [Lego 四视角：仅选中核原色](figures/lego_fourview_selected_only.jpg)','- [Chair 四视角：仅选中核原色](figures/chair_fourview_selected_only.jpg)',
        '- [Lego 同相机 full RGB 对照](figures/lego_fourview_full_RGB_vs_selected_only.jpg)','- [Chair 同相机 full RGB 对照](figures/chair_fourview_full_RGB_vs_selected_only.jpg)',
        '- 每视角 downloads/*_scores_ids.npz 含 scene/camera、original_ids、每核 raw/ratio/full_visible_mass、全部预算/方法/K IDs；不含模型副本。',
        '- figures/*_evidence.jpg、*_crops.jpg、*_deletion.jpg、*_score_hist.jpg 与逐视角 800×800 selected-only JPG。MEDIA_MANIFEST.json 记录全部 SHA/尺寸/语义。',
        '', '## 决策与来源','','primary visual GO=HUMAN_PENDING。自动可靠性拒绝与预算图都保留。criteria1 的一般几何条件未验证，criteria3 的 footprint 地域成本实测而不是中心点推断，criteria4 为有界真实删除对照而不是同一权重差值自评。本阶段停止选核/诊断，不进行艺术黑墨、协方差弯曲、训练、完整轨迹或 C/D。','',
        '各视角独立计算 S_i(camera)，没有冻结 union mask。不同集合及 ID overlap 只能说明视角选核变化，不证明多视图/时序一致性；所有视角均为以前 GS/实验可见的探索视角，没有 formal blind。','',
        '最近先例为 Hao / Mukai 的作者 SIGGRAPH Asia 2026 预印本 [Feature Line Rendering from Rasterization States in 3D Gaussian Splatting](https://mukai-lab.org/content/SA2026PosterHao.pdf)。它保留 top-K 原语 ID 与 alpha*T，并比较相邻 raster states；Eq.3 的 overlap 思路与 attribution/support 比较重合，本阶段不作新颖性声明。作者 PDF 的 DOI/ISBN 为占位符，此处按预印本引用。原始 GAER 指令保存在旧阶段，授权仅对新阶段选核/诊断解除 section25 停止。',
        '', f'完整视角 trace={len(results)}/8；缺失={missing}。测试与独立进程真实重渲染证据见 results/VERIFICATION.json、results/REPRODUCTION.json；资源/输入 hash 见 PREREGISTRATION.json、PROTECTED_AFTER.json。'])
    (ART/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    final=dict(completed_views=len(results),expected_views=8,missing=missing,
        units=[dict(unit=r['unit'],selected_count=r['main_selected_count'],automatic=r['automatic'],archive=r['diagnostic_archive']) for r in results],
        selection_scope='view-dependent alpha-silhouette responsibility ranking, original SH3 selected-only diagnostics',
        H1_general_geometry='NOT_VALIDATED',standalone_detection='NOT_RUN',human_visual_GO='PENDING',artistic_pipeline='NOT_RUN',
        protected_unchanged=json.loads((ART/'PROTECTED_AFTER.json').read_text())['passed'],
        verification=json.loads((ART/'results/VERIFICATION.json').read_text()) if (ART/'results/VERIFICATION.json').exists() else {'passed':False,'state':'PENDING'},
        media_manifest='artifacts/gaer_view_selection_v01/MEDIA_MANIFEST.json',publish_receipt='out/gaer_view_selection_v01/PUBLISH_RECEIPT.json')
    atomic_json(ART/'FINAL.json',final)

if __name__=='__main__':main()
