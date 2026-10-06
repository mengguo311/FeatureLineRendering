"""Add audited interpretation and downloadable actual view tables, without refitting."""
import sys,json,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/gaer_rgb_union_voting_v01'))
from runtime import *
from freeze import check_protected
from PIL import Image

def main():
    final=json.loads((ART/'FINAL.json').read_text());frozen=json.loads((ART/'PRODUCTION_FREEZE.json').read_text())
    actual=json.loads((ART/'results/PRODUCTION_RUNNER_RECEIPT.json').read_text());audit=json.loads((ART/'tests/INDEPENDENT_AUDIT.json').read_text())
    resume=json.loads((ART/'tests/RESUME.json').read_text())
    for scene,s in final['scenes'].items():
        s['received_ratio_all_marked']=s['received_pixels']/s['marked_pixels'];s['received_ratio_actual_center_contributor']=1.
        s['fallback_pixel_count']=sum(v for k,v in s['fallback_reasons'].items() if k not in ('BEST_RETAINED_D','UNASSIGNABLE_BACKGROUND'))
        s['fallback_fraction_received']=s['fallback_pixel_count']/s['received_pixels']
    final.update(actual_initial_runner_seconds=actual['actual_seconds'],independent_saved_result_audit=audit,
        resume=resume,semantic_geometric_GO='NOT_ESTABLISHED',temporal_stability='NOT_TESTED',
        effectiveness='Lego main TOP500/TOP2000 pooled line mass recall below mandatory center-alphaT; Chair difference small; high leakage and strong K sensitivity; no clear mechanism advantage')
    atomic_json(ART/'FINAL.json',final)
    # Explicit background coordinates are retained as well as the winner map.
    import numpy as np
    for scene in ('lego','chair'):
        with scoped(ART/'downloads'/(scene+'_per_view_counts.csv')).open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['scene','view','marked','weak','received','background','received_ratio','D_winners','fallback_normal','fallback_zeroD','fallback_unknown',
                'unknown_bound_positive_pixels','internal_marked','internal_received','endpoint_only_best'])
            for view in frozen['scenes'][scene]['vote_views']:
                r=json.loads((ART/'results'/(scene+'_vote_'+view['key']+'.json')).read_text());d=r['fallback_reasons']
                writer.writerow([scene,view['key'],r['marked_pixels'],r['weak_pixels'],r['received_pixels'],r['unassignable_pixels'],r['received_ratio'],
                    d['BEST_RETAINED_D'],d['NORMAL_UNDEFINED_OR_LOW_CONFIDENCE'],d['D_NUMERICAL_FLOOR'],d['SIDE_UNKNOWN_EXCEEDS_D'],r['unknown_positive_pixels'],
                    r['regions']['interior_line']['marked'],r['regions']['interior_line']['received'],r['endpoint_only_best_pixels']])
        with scoped(ART/'downloads'/(scene+'_unassignable_background_xy.csv')).open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['scene','view','x','y','reason'])
            for view in frozen['scenes'][scene]['vote_views']:
                a=np.load(ART/'downloads'/scene/view['key']/'assignment.npz');y,x=np.nonzero(a['fallback_map']==5)
                for X,Y in zip(x,y):writer.writerow([scene,view['key'],int(X),int(Y),'UNASSIGNABLE_BACKGROUND'])
    report=(ART/'REPORT_ZH.md').read_text()
    paragraph='''实测判断：**工程映射完成，线绘效果仍是 PARTIAL，没有显示清楚的 D 推核优势。** 两个保留相机合计，TOP500 线域质量召回为 Lego **1.4575%**、Chair **0.8268%**，中心最大 alpha·T 对照为 **1.6409% / 0.8238%**；非线域泄漏为 **86.55% / 81.98%**。TOP2000 也只是 **5.1215% / 3.0596%** 线域质量召回。内部支持已确实存在，但图中仍是稀疏斑块或宽足迹，不能读成完整、干净的物理特征线。

K8→K32 的同四源视角 TOP500 Jaccard 为 Lego **0.4771**、Chair **0.2837**；这一大幅变化与截断残量使主方法大量回退有关。八图主分配回退分别 **209,976（65.53%）/144,140（80.95%）** 个有效像素，回退仍全部接收真实中心核。屏幕内部标注像素分别 **281,706 / 150,015** 个，全部接收一票；这证明内部参与工程分配，不证明内部物理边语义。

'''
    if paragraph not in report:report=report.replace('## 先看实际图\n',paragraph+'## 先看实际图\n',1)
    extra='''
额外展示：[Lego 频率与 full-T 支持](media/lego/fourview_frequency_and_support.jpg)、[Chair 频率与 full-T 支持](media/chair/fourview_frequency_and_support.jpg)、[Lego 内部原生 ROI](media/lego/fourview_internal_ROI_nearest2x.png)、[Chair 内部原生 ROI](media/chair/fourview_internal_ROI_nearest2x.png)。图中文字已用独立呈现脚本整理；原封印的生产面板保留。原 gain=8 频率图容易饱和，新增统一 gain=1 原始频率特征图，计票/排名/评价完全不变。原封印 ROI 预览采用重采样；新增 `native_ROI_nearest2x.png` 才是精确最近邻 2×。

[Lego 每视角计数](downloads/lego_per_view_counts.csv)、[Chair 每视角计数](downloads/chair_per_view_counts.csv)、[Lego 无贡献像素坐标](downloads/lego_unassignable_background_xy.csv)、[Chair 无贡献像素坐标](downloads/chair_unassignable_background_xy.csv)。

初次两场景实际 runner wall time **181.260 秒**；逐单元工作累计 Lego **92.302 秒**、Chair **76.385 秒**，其余为加载/校验开销。恢复运行 **13.753 秒**，**30 个封印单元跳过、新增生产渲染 0**。独立保存结果审计 **5,696 项通过**，保护 **3,198 个文件** 字节不变。随机集合的源可见质量总量匹配误差均低于 0.12%，但它可与主集合重叠，TOP500 重叠 Lego112/Chair58 个；不把它描述成完全独立的不相交集合。

出处区别：旧图像法已有经典方向场/颜色张量基础，可对照 [Coherent Line Drawing 作者 PDF](https://cg.postech.ac.kr/papers/kang_npar07_hi.pdf)。[Hao/Mukai 作者预印本](https://mukai-lab.org/content/SA2026PosterHao.pdf) §2 保留 top-K ID/alpha·T，并比较邻域原始 ID 支持。它还使用深度/法线等 renderer states；本阶段复用的是已有 GAER 原生贡献缓冲区，通过旧 RGB 标注强制分配与统计，未复现该论文完整检测器。没有新颖性声明。
'''
    if extra not in report:report+=extra
    scoped(ART/'REPORT_ZH.md').write_text(report)
    reproduce=(ART/'REPRODUCE.md').read_text()
    addition='''
To reproduce the final readable presentation after the frozen runner, use:

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaer_rgb_union_voting_v01/CURATE_MEDIA.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/verify.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B artifacts/gaer_rgb_union_voting_v01/FINALIZE.py
```

`FINALIZE.py` requires the saved initial PRODUCTION_RUNNER_RECEIPT.json and tests/RESUME.json from this completed run. These keep initial and resume wall times separate. CURATE_MEDIA adds display-only unit-gain frequency features and nearest-neighbor native ROIs; it never changes frozen winners, rankings, sets or evaluation. Original sealed production media remain intact. Source hashes of both postproduction scripts are recorded separately.
'''
    if addition not in reproduce:reproduce+=addition
    scoped(ART/'REPRODUCE.md').write_text(reproduce)
    sources=json.loads((ART/'SOURCE_MAP.json').read_text());sources.setdefault('postproduction_presentation',{})[relative(Path(__file__))]=sha(__file__)
    atomic_json(ART/'SOURCE_MAP.json',sources)
    manifest=[]
    for path in sorted((ART/'media').rglob('*'))+sorted((ART/'downloads').rglob('*')):
        if path.is_file():
            item=dict(path=relative(path),bytes=path.stat().st_size,sha256=sha(path))
            if path.suffix in ('.png','.jpg'):
                with Image.open(path) as im:item.update(width=im.width,height=im.height)
            manifest.append(item)
    atomic_json(ART/'MEDIA_MANIFEST.json',dict(files=manifest,count=len(manifest),total_bytes=sum(x['bytes'] for x in manifest)))
    protected=check_protected(frozen)
    if not protected['passed']:raise AssertionError(protected['changed'])
    print(json.dumps(dict(finalized=True,manifest_files=len(manifest),protected_files=protected['checked_files']),ensure_ascii=False))

def relative(p):return str(p.relative_to(ROOT))
if __name__=='__main__':main()
