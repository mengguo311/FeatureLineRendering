"""Report actual saved results; never changes the frozen science or decision."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,sha,js,now
import json,time
from pathlib import Path
import numpy as np
from scipy import ndimage

def load(p):return json.loads(p.read_text())
def npz(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def main():
    audit=load(UNIT/'AUDIT.json');assert audit['status']=='pass'
    replay=load(UNIT/'cached_walk_replay/REPLAY_RECEIPT.json');assert replay['all_equal']
    stats=load(UNIT/'asset/ASSET.json');readback=load(UNIT/'DIRECTION_TOPOLOGY_READBACK.json')
    match=load(UNIT/'BUILD_MATCH.json');summary=load(UNIT/'SUMMARY.json');attribution=load(UNIT/'attribution/SUMMARY.json')
    receipts={p.stem:load(p) for p in (UNIT/'logs').glob('*.json') if p.stem!='handoff'}
    failures={k:v for k,v in receipts.items() if v['child_returncode']!=0}
    assert set(failures)=={'walk_RED'}
    rows=[];far=[]
    for row in summary:
        if row['duplicate']:continue
        folder=UNIT/row['kind']/row['view'];f=npz(folder/'FRAME.npz');target=f['regions']==4;near=ndimage.binary_dilation(target,iterations=2);mask=~near
        delta=np.abs(f['B_linked_matched']-f['A_linked_matched']).sum(2)
        record=dict(view=row['view'],kind=row['kind'],far_raw_L1_sum=float(delta[mask].sum()),far_max_pixel_L1=float(delta[mask].max()),
                    far_changed_pixels=int((delta[mask]>0).sum()),far_pixels_above_1_255=int((delta[mask]>1/255).sum()),
                    target_delta_L1=float(delta[target].sum()),target_fraction_delta_at_least_005=float((delta[target]>=.05).mean()))
        far.append(record)
        if row['kind']=='dev':
            a,b=row['A_linked'],row['B_linked']
            rows.append(f"| {row['view']} | {row['target_pixels']} | {a['ink_L1']:.3f}/{b['ink_L1']:.3f} | {100*a['coverage']:.2f}%/{100*b['coverage']:.2f}% | {100*a['interior_coverage']:.2f}%/{100*b['interior_coverage']:.2f}% | {100*record['target_fraction_delta_at_least_005']:.2f}% |")
    js(UNIT/'FAR_READBACK.json',far);js(UNIT/'EXECUTION_RECORDS.json',receipts)
    attr_rows=[]
    for x in attribution:
        attr_rows.append(f"| {x['view']} {x['arm']} | {x['proxy_visible_length']:.3f} | {x['preS_own_visible_missing_length']:.3f} | {x['linked_matched_own_visible_missing_length']:.3f} |")
    far_rows=[]
    for x in summary:
        if x['kind']!='dev':continue
        a,b,u=x['A_linked'],x['B_linked'],x['B_ungated']
        far_rows.append(f"| {x['view']} | {a['far_other']:.9f}/{b['far_other']:.9f} | {a['background']:.9f}/{b['background']:.9f} | {u['far_other']:.9f} |")
    next_step='在下一次只读Astra审查和父级冻结后，执行独立A/C载体诊断：固定unit010原切片生成器、基底/相位/风格和unit008原行纸底/S/目标；只在v07副本进行一次保拓扑、保分区边界及锐边的有界降噪。先冻结可移动顶点、位移尺度与规则，检查平面/折面/孔洞/相邻分离片，避免补洞或合并片层；重新生成带新身份的路径并重建face/bary锚点。明确区分生成载体与遮挡参照，保持评价掩码和遮挡判据，报告位移、法线及可见性变化；比较pre-S、linked及同墨预算ungated完整前后视图。现有旧/新增分区分别有694/27个不接触分区边界的顶点，锐边保护后是否仍有有效干预须公开；若变成no-op或破坏几何，记录诊断无效，不用调参扫描冒充结果。无需再次bootstrap，不同时叠加B。'
    why='固定载体的straightest续接已真实改变曲线并减少跨面转折，但多数完整视角未建立可读性优势，弱后视角乘S前/后自身缺失均未改善。载体降噪是尚未测试的独立变量；当前证据不能证明噪声为主因，也不应继续角度、纸底或容差扫描。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,estimated_minutes=30,
       requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    elapsed=(time.time()-min(v['started_unix'] for v in receipts.values()))/60
    text=f'''# Unit001：冷重放恢复；同载体表面续接尚未建立整物体收益

**执行完成，科学结果为局部几何变化、整体可读性优势未建立。不升级默认，NEXT=continue，scientific_seal=false。**

已查看四个完整DEV自然/配平面板、前后独立墨层、弱后视角linked/ungated对照及231°/241°/251°实际相机序列。B的局部线形略顺，但整体仍是短笔触交叉网格；前侧新选面未丢弃，后侧纸底斑驳与碎乱仍明显。没有观察到足以宣称形体更清楚的整物体优势。该判断为有限目视检查，不是独立用户研究。

## 工程恢复与范围

一次bootstrap约21.37秒完成：现有指定Python实际导入NumPy2.2.6、SciPy1.15.3、plyfile1.1.5、Pillow12.2.0、Open3D0.20.0。未安装任何包，仅在v07复制包的requirements中补列Open3D。mapping、source-only、hybrid分别有原始退出回执；source/paper/S及hybrid的pre-S墨层/混合五层均与包内参考逐值一致，最大误差0。实际重新读取原PLY并编译CPU renderer；不是缓存图冒充冷重放。原生产者记录与先前独立验收缺依赖的失败范围均保留，本次不改写旧验收。

科学阶段复用哈希固定的unit010 source/paper/S与相机，每个不同视角真实栅格化A/B路径。另一次新进程从保存A/B资产重栅格化弱角度，与本单元全部数组逐值一致；该入口明确是cached-GS/actual-ink replay，不是第二次cold GS。

## 干预与保持项

A为unit010 local旧/新增分区原路径，只作冻结参照，不代表升级默认。B为每条旧stroke的弧长中点种子、相同初始切向及双向各半长度预算；仅通过真实共享边展开传输切向。跨边保持沿边分量，再进入邻面内部；不做KNN连接、法线平滑、角度拟合、缺口填充或逐相机重生成。每条B有新ID=父ID+100000000000、face/bary、种子、父ID和停止原因。它是逐路径续接变体，尚不是全局相干方向场。

原310475行、源PLY/几何/协方差/opacity/完整SH/行序、41058纸底许可及权重、21006墨责任及权重、195279 UNKNOWN、2121面作者目标均不变。旧2030面与新增91面分别停止；1px线宽、2倍采样、0.004遮挡容差及2px评价带固定。source_index仍是原PLY零起始行号；新的stroke/face ID不构成逐路径Gaussian归属证据。

380条种子均保留；A1946段、B2300段，其中B新增380个种子处分段，不能把分段数或零转角直接当收益。请求长度{stats['requested_length']:.9f}，实际B长度{stats['actual_length']:.9f}，减少{100*(1-stats['actual_length']/stats['requested_length']):.3f}%。93条提前停止，双向端点共656个达到请求长度、93个遇分区边界、11个遇网格边界；未触发顶点歧义/退化/步数保护。两臂存储内部断点均为0。长度/间距/间隙的实际变化是机制结果，不声称逐点风格相同。

独立读回排除种子处分段后，旧主分区跨面转角中位数18.817°→14.890°，总转角/世界长度1515.043→1185.948；新增分区中位数9.534°→8.209°。几何变化确实存在，但形状锐边、载体噪声和走向并未独立分离，转角更小不等于更好NPR。旧/新增分区分别33/6个拓扑连通分量，最大1948/83面；694/27个顶点不接触各自分区边界。目标共享边无向法线夹角中位数20.206°、P95 74.377°，这含真实棱边，不能直接叫噪声真值。

## BUILD配平与完整DEV

四BUILD自然目标墨RGB L1：A-linked6283.397649，B-linked6315.630994，A-ungated8883.581836，B-ungated8958.911539。公共预算6283.397649；冻结全局系数为1、0.994896259、0.707304527、0.701357260。实际合成读回匹配；所有自然强度也保存。BUILD相等不保证各DEV相等，不能把更淡或覆盖更少称为成功。

下表为配平linked的A/B；可见墨阈值alpha>0.05仅用于描述，不是新通过门槛。图像差为目标像素RGB L1≥0.05。

| DEV相机 | 目标像素 | 目标墨RGB L1 A/B | 目标覆盖 A/B | 内部覆盖 A/B | A/B明显图像差比例 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

三个DEV目标覆盖下降，弱241°/24°持平；四个DEV内部覆盖均下降。变化并非无操作，但不支持整体质量提升。完整逐像素数组、自然/配平、pre-S与post-S图均保存。所有相机已曝光；四DEV加三个arc只有6个不同评估相机，241°/24°重复，已复用完成结果且不计为新独立样本。三帧实际变相机序列不是连续视频或无闪烁认证。

## 断裂归因与门控

以下为每条笔触自身光栅支持，不借其他笔触重叠获益；长度单位是投影像素。中心线代理射线仅为当前几何参照，不是物理可见性真值。

| 相机/臂 | 代理可见长度 | pre-S自身缺失 | 配平linked自身缺失 |
|---|---:|---:|---:|
{chr(10).join(attr_rows)}

弱后视角pre-S缺失23.893→26.685px，linked缺失127.588→127.746px，未改善；前侧pre-S仅少1.599px，linked反而略增。S会扩大缺失，但pre-S本身仍是短交叉网格，因此不能把全部问题归于门控。A端点类别为{json.dumps(readback['A_endpoint_counts'],ensure_ascii=False)}。不能把计划长度停止、作者边界、真实遮挡与实现断裂混为一谈；93个B提前停止也不能冒充修复。

同预算ungated对照保留。弱后视角目标覆盖A/B约40.57%/40.70%，比linked更多，但完整物体仍杂乱；未见明确整体门控质量优势，门控保留为可选对照，不宣称新颖机制。真实原GS纸底/原行选择能力独立成立。

## 绝对远区损伤

下表是相对原GS的raw RGB L1绝对和，纸底既有损伤包含在内；不是只看比例。右列为B-ungated同BUILD预算的远其他部件损伤。

| DEV相机 | 远其他 A/B linked | 背景 A/B linked | B ungated远其他 |
|---|---:|---:|---:|
{chr(10).join(far_rows)}

六个不同评估相机新增A/B linked远区差最大单像素L1={max(x['far_max_pixel_L1'] for x in far):.12g}；超过1/255的远区像素合计{sum(x['far_pixels_above_1_255'] for x in far)}。不能称严格零；FAR_READBACK逐视角保留非零差和目标变化。未扩评价带、删困难像素或修改作者目标。

## 验证、复放与失败保留

5项针对性TDD先因缺surface_walk模块RED(rc1)，再GREEN(rc0)：平面共享边及反绕序、圆柱条带展开、作者边界与分离片、同标签真实前景遮挡及S=0、真实Lego种子/锚点/身份。98个输入/旧文件哈希保持；380条种子全部读回；锚点最大误差{audit['max_anchor_error']:.3g}，初始种子误差{audit['max_seed_error']:.3g}，跨边切向沿边分量误差{audit['max_edge_tangent_component_error']:.3g}。56张保存PNG完整解码并与数组一致，合成误差0，A全部实际渲染逐值恢复旧结果。无科学执行失败；预期RED原回执保留。

PROTOCOL/INPUT/SOURCE/CAMERAS在生成与评估前冻结，DECISION未修改。独立读回、复放和报告辅助源码另列HANDOFF_SOURCE_LOCK，不重写科学源码锁。命令、实际child rc与耗时见EXECUTION_RECORDS及logs；未GPU、未训练、未安装、未改旧环境或包、未push/merge、未嵌套模型。已检查四个完整DEV面板、自然图、前后墨层及三相机后侧序列。

代码位于`{HERE}`。真实运行解释器为`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python`。可在新目录复放B：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B {HERE}/replay_walk.py --out {ROOT}/user_walk_replay_001 --view orbit_241_24_5.3
```

该命令真实重栅格化A/B，但复用哈希固定旧GS层；依赖旧只读缓存，不能称独立便携包。完整冷GS入口是`{ROOT}/replay_package/code/linked_source_cli.py`，该包hybrid目前重放原A，不是B。所有新输出目录须不存在；运行时固定CPU两核亲和、数值线程1、CUDA为空。

v05远区8.044%、31像素腐蚀目标及4.49%作者区域变化失败、v06各负结果和历史工程/配额中断均保留，不能用扩区后的本结果回填。当前交付是CPU EWA原GS纸底加区域原ID门控代理墨，非原生Gaussian排线、物理/语义真值、H1/H2/H3或全局方向场成功。

## 下一步

{next_step}

{why}

本单元从首次执行回执计约{elapsed:.2f}分钟，早于35分钟上限；下一单元仍须父级只读审查/冻结，14:25禁启新科学、14:45收尾、15:00硬停止。
'''
    (UNIT/'REPORT_ZH.md').write_text(text)
    appendix={str(p.relative_to(HERE)):sha(p) for p in [HERE/'audit_unit.py',HERE/'replay_walk.py',HERE/'finish_unit.py']}
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files=appendix,scope='Post-evaluation audit/replay/report helpers; no mutation of frozen scientific code'))
    js(UNIT/'VISUAL_INSPECTION.json',dict(utc=now(),inspected=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png',
       'dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_61_24_5.3/INK_LAYERS.png','dev/orbit_241_24_5.3/INK_LAYERS.png'],
       verdict='Local line shape changes; no clear whole-object readability advantage; weak rear remains fragmented cross grid',independent_user_study=False))
    js(UNIT/'STATUS.json',dict(execution_state='completed',stage='bootstrap_and_frozen_real_scene_A_B_complete',
       scientific_verdict='NEGATIVE for whole-object readability advantage; PARTIAL geometric continuation effect; default not promoted',
       gaussian_link_progress='Actual cold full-original-GS source/paper/S/ink/hybrid exact. Original 310475 rows, M1/UNKNOWN and per-row weights fixed. B has new proxy anchors/IDs and region S; per-path source-Gaussian attachment uncertified.',
       scientific_seal=False,parent_verification='pending',bootstrap='completed_once_no_install',tests=dict(expected_RED=1,GREEN_tests=5,audit='pass',cached_path_replay='exact'),
       actual_commands=receipts,artifacts=['REPORT_ZH.md','NEXT.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','asset','dev','arc','attribution','AUDIT.json'],
       blockers=[],limitations=['All views exposed;6 unique evaluation cameras','No whole-object advantage','Not a global coherent field','No geometric truth or new per-path Gaussian certificate'],
       next_action='continue',elapsed_minutes=elapsed,completed_utc=now()))
    manifest={str(p.relative_to(UNIT)):sha(p) for p in UNIT.rglob('*') if p.is_file() and p.name not in ('ARTIFACT_MANIFEST.json',) and 'logs' not in p.relative_to(UNIT).parts}
    js(UNIT/'ARTIFACT_MANIFEST.json',dict(files=manifest,scope='Artifact content inventory, not scientific certification; orchestration excluded'))
    print(json.dumps(dict(execution_state='completed',next='continue',elapsed_minutes=elapsed,manifest_entries=len(manifest))),flush=True)
if __name__=='__main__':main()
