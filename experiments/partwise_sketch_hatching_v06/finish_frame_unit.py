"""Post-result readback and delivery; never changes frozen scientific sources."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT,js,sha,now
from pathlib import Path
import datetime,json,shutil
import numpy as np
from scipy import ndimage
from run_frame_unit import protocol,OLD
from run_hybrid import read_npz

def main():
    p=protocol();s=json.loads((UNIT/'SUMMARY.json').read_text());val=json.loads((UNIT/'VALIDATION.json').read_text())
    media=json.loads((UNIT/'MEDIA_VALIDATION.json').read_text());replay=json.loads((UNIT/'cold_replay_001/REPLAY_CHECK.json').read_text())
    visual=json.loads((UNIT/'VISUAL_REVIEW.json').read_text());assert visual['all_four_DEV'] and visual['all_nine_arc_frames']
    assert all(media['all_frames_decoded_exact']) and replay['all_links_zero_equals_original_GS']
    assert replay['all_four_hybrids_exact'] and len(val['views'])==13
    b=s['build'];asset=s['asset'];dev=[r for r in s['records'] if r['kind']=='dev'];assert len(dev)==4
    # Saved-result-only investigation of every nonzero far pixel. No mask change.
    farrecords=[]
    for r in s['records']:
        f=read_npz(UNIT/r['kind']/r['view']/'FRAME.npz');far=~ndimage.binary_dilation(f['regions']==4,iterations=2)
        d=np.abs(f['local_raw']-f['xz_raw']).sum(2);yy,xx=np.where(far&(d>0))
        for y,x in zip(yy,xx):
            farrecords.append(dict(kind=r['kind'],view=r['view'],xy=[int(x),int(y)],region=int(f['regions'][y,x]),
                source=f['source'][y,x].tolist(),paper=f['paper'][y,x].tolist(),
                xz_alpha=float(f['xz_raw_alpha'][y,x]),local_alpha=float(f['local_raw_alpha'][y,x]),
                raw_L1_between_arms=float(d[y,x]),source_damage_xz=float(np.abs(f['xz_raw'][y,x]-f['source'][y,x]).sum()),
                source_damage_local=float(np.abs(f['local_raw'][y,x]-f['source'][y,x]).sum())))
    js(UNIT/'FAR_READBACK.json',dict(records=farrecords,warning='Saved-result diagnostic; fixed2px mask and all output values preserved; repeated cameras are not independent samples'))
    rows=[];damage=[];effect=[]
    for r in dev:
        c=r['coverage'];i=r['ink'];a=c['xz_matched'];n=c['local_matched']
        rows.append(f"| {r['view']} | {a['target']['pixels']}/{a['interior']['pixels']} | {i['xz_matched']['target_full']['raw_L1_sum']:.3f}/{i['local_matched']['target_full']['raw_L1_sum']:.3f} | {a['target']['ink_fraction']*100:.2f}%/{n['target']['ink_fraction']*100:.2f}% | {a['interior']['ink_fraction']*100:.2f}%/{n['interior']['ink_fraction']*100:.2f}% |")
        ch=r['changes']['matched']['target_full'];effect.append(f"| {r['view']} | {ch['raw_L1_mean']:.6f}/{ch['raw_L1_sum']:.3f} | {ch['useful_fraction_0_05']*100:.2f}% |")
        x=r['metrics']['xz_raw'];l=r['metrics']['local_raw'];damage.append(f"| {r['view']} | {x['far_other']['raw_L1_sum']:.8f}/{l['far_other']['raw_L1_sum']:.8f} | {x['far_background']['raw_L1_sum']:.8f}/{l['far_background']['raw_L1_sum']:.8f} | {r['far_readback']['new_far_sum']:.8f} |")
    ratios=[r['ink']['local_matched']['target_full']['raw_L1_sum']/r['ink']['xz_matched']['target_full']['raw_L1_sum'] for r in dev]
    diag=asset['diagnostics'];normal=asset['frame']['normal'];tilt=float(np.rad2deg(np.arccos(abs(normal[1]))))
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-23T12:12:36.171256+00:00')).total_seconds()/60
    report=f'''# Unit010：原ID关联的方向编辑可见，局部框架整体优势未建立

**冻结两臂实验完成。方向变化在完整物体上清楚可见；退化减少有限，三个DEV视角墨覆盖下降，弱视角整体质量优势未建立。不升级默认，scientific_seal=false。**

本轮只改变切平面法向的参考基底。旧资产实际为XZ、35°/95°，修正unit009 NEXT的XY文字误述，但没有修改旧文件。新框架只由四BUILD首交可见且属于固定目标的去重面产生：2096面，面积{asset['frame']['visible_area']:.8f}。法向使用面积加权n n^T，位置协方差使用三角形面积精确积分；不以顶点数量或三角形重心采样代替面积。宏观法向约({normal[0]:.6f},{normal[1]:.6f},{normal[2]:.6f})，法向特征值为0.285527/0.301690/0.412783，只有有限主方向优势；切平面长轴特征值0.058916与次轴0.012878，本轮没有触发回退。规则、符号及退化处理均在生成前冻结，无角度搜索。

两层35°/95°、间距0.06/0.075、长度0.12、间隙0.035、1px线宽、世界原点、切片相位、0.004遮挡容差、2倍采样和2px评价带不变。旧2030面与新增91面继续分别生成，保留各自停止边界和可见性规则。旧375条/2004段逐值恢复；新380条/1946段、世界长度{asset['local']['world_length']:.6f}，有独立stroke身份及face/bary锚点。数量不是配平条件。

作者目标2121面、unit008自然纸底41058个原行及原强度、21006行墨责任及权重、195279个UNKNOWN保持。原310475行身份/顺序、原PLY、中心、协方差、opacity和完整SH均不变。没有叠加unit009饱和纸底或以前的补间隙、明暗、轮廓变体。原ID区域责任连接新代理墨层，不是新笔触的逐路径Gaussian归属证明。

协议SHA256 `{sha(UNIT/'PROTOCOL.json')}`；54份输入、源码和相机先冻结，随后BUILD框架/路径单独锁定，再做BUILD配平和DEV。所有源纸底/S缓存来自锁定unit008实际完整GS结果；改变的路径重新栅格化。冷重放另外实际渲染完整原GS三次，没有把缓存复用冒称全部重渲染。

## 机制诊断与解释范围

BUILD面积加权表面交叉角从{diag['xz']['area_weighted_cross_angle']:.4f}°到{diag['local']['area_weighted_cross_angle']:.4f}°；小于15°的面积从{diag['xz']['angle_area_bins']['0_15']*100:.3f}%到{diag['local']['angle_area_bins']['0_15']*100:.3f}%。第二层切向sin<0.1的面积从{diag['xz']['layer_area_fraction_sin_below']['0.1'][1]*100:.3f}%到{diag['local']['layer_area_fraction_sin_below']['0.1'][1]*100:.3f}%。这些只是代理几何诊断，未证明主要杂乱来自方向退化。

局部宏观平面与世界XZ平面只相差约{tilt:.3f}°；但冻结符号规则取n的最大绝对分量为正、u同理、v=n×u，使局部第二基向量主要指向负z，旧XZ第二基向量为正z。因此本次还体现同一参考框架定义中的有向方位/手性约定变化，不能把明显图像差全归于小幅退化减少。未设置同等旋转的手工方向对照，不证明PCA优于简单角度编辑。

## 完整物体结果

{visual['observation_chinese']}

四BUILD自然目标墨RGB L1为XZ {b['natural_target_ink_L1']['xz']:.6f}、局部框架{b['natural_target_ink_L1']['local']:.6f}；公共预算{b['budget']:.6f}，全局系数{b['scales']['xz']:.10f}/1。自然局部墨量为旧臂{b['natural_target_ink_L1']['local']/b['natural_target_ink_L1']['xz']*100:.3f}%。配平实际合成读回一致，没有DEV或逐帧拟合。DEV局部/旧实际墨量比{min(ratios):.4f}–{max(ratios):.4f}，BUILD相等不代表每个DEV相等。

以下为BUILD配平后XZ/局部框架；墨覆盖阈值alpha>0.05。

| DEV视角 | 全目标/内部像素 | 目标墨RGB L1 | 全目标墨覆盖 | 内部墨覆盖 |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

前三个DEV目标及内部覆盖下降，241°/60°略增。前侧略疏、更顺的观感包含较少墨量与覆盖的因素，不以少画作为质量成功。

| DEV视角 | 配平两臂目标图像差mean/sum | 目标差clipped L1≥0.05比例 |
|---|---:|---:|
{chr(10).join(effect)}

显著变化覆盖53.21%–56.47%的目标像素，证明方向操作可见，不等于NPR质量优势。全目标/腐蚀内部/边界/远其他/背景的mean、sum与覆盖均保存。

## 远区与实际短弧

| DEV视角 | 远其他原源差L1 XZ/局部 | 背景原源差L1 XZ/局部 | 两臂远区图像差L1 |
|---|---:|---:|---:|
{chr(10).join(damage)}

远区差不是严格零：13条记录最大新增单像素raw L1={max(r['far_readback']['max_new_raw_L1'] for r in s['records']):.10f}，超过1/255的新增远区像素合计{sum(r['far_readback']['new_visible_pixels'] for r in s['records'])}。FAR_READBACK保存所有非零像素的源色、纸底、两臂alpha和实际源差；弱相机在短弧中重复一次，不作独立样本。部分最终源差减少含颜色抵消，不能据此称没有新增墨。原纸底既有损伤继续存在，没有扩目标、边界带或删除异常像素。

九帧为231°–251°、仰角24°、距离5.3的真实相机短弧，各臂使用同一固定三维路径集。全部视频帧解码并与PNG逐值一致；前侧新增91面在后侧短弧不可见。4DEV+9arc只有12个不同相机设置，全部已曝光，无独立时序/语义/物理真值。

## 验证、失败保留与交付

两项针对性测试包含解析斜面60°交叉、面积矩、真实共享边/分区/分离片、非法基底、真实Lego旧路径及64像素渲染逐值恢复、零S空墨。预期缺模块RED rc1保留，GREEN rc0。冻结后所有科学、审计、冷重放和媒体阶段均完成rc0，无修参、重写协议或失败覆盖。

独立读回检查54份输入、完整原行、固定许可/M1、锚点与切片层位、BUILD预算和13条记录的全部指标；从实际已接受原ID alpha×T trace与完整SH重建原源、纸底和S。弱角度冷进程实际完整GS三次，并重新栅格化两套路径：四种自然/配平混合结果逐值一致，零墨等于纸底，全部许可置零等于原GS。CPU replica不是原生CUDA认证。

v05稀疏capsule远区8.044%失败及4.49%区域变化、v06单位001–009负结果与历史中断/配额失败均原封保留。当前目标是已显式扩展的2121面区域，不能倒算旧稀疏门槛成功。交付是原GS纸底与原ID关联代理墨层，未证明原生Gaussian排线、完整语义铲斗、物理附着或H1/H2/H3。

实际可重放源码、框架/路径/原行连接、纸底/墨层/混合图、九帧视频随单元保存。原PLY、本地Python和历史锁定缓存仍为外部依赖。默认不升级，新资产作为比较证据保留。

## 截止与下一步

NEXT=stop，stop_reason=no_new_units_deadline。{visual['next_step']}

{visual['next_why']}

本轮执行约{elapsed:.2f}分钟；只完成unit010，未启动新科学单元，早于21:45科学收尾和22:00硬截止。
'''
    report += '\n交付工程补记：handoff_001在写根交付前因finish_frame_unit缺少OLD导入而rc1。科学结果不受影响；原源码、部分报告/状态及原失败回执保存在interrupted_handoff_001与logs。修复只补导入并允许记录该已知交付失败，用handoff_002新回执完成交付，未改变冻结源码、协议、参数或科学输出。\n'
    (UNIT/'REPORT_ZH.md').write_text(report)
    py='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
    (UNIT/'README_ZH.md').write_text(f'''# Unit010：固定原Gaussian连接的局部方向框架对照

可见方向编辑成立；多数视角整体NPR优势未建立，默认未升级。全部负结果保留。

- [中文报告](REPORT_ZH.md)
- [自然强度完整物体](ALL_DEV_VIEWS.png)
- [同BUILD墨预算完整物体](ALL_DEV_MATCHED.png)
- [独立墨层](ALL_DEV_INK.png)
- [九帧实际短弧](media/local_frame_arc_ffv1.mkv)
- [框架与路径说明](asset/ASSET.json)

冷重放（实际完整GS三次，重新渲染两套代理路径；新输出目录必须不存在）：

```bash
V06_UNIT_DIR={UNIT} CUDA_VISIBLE_DEVICES='' {py} -B {UNIT}/source_snapshot/audit_frame_unit.py replay --out {UNIT}/replay_user_001
```

串行CPU最多2核，无GPU；编译临时文件在本单元scratch。原PLY、本地Python、unit008目标/路径和缓存路径见INPUT_LOCK.json，需保留这些依赖，不是独立移动包。

asset/SOURCE_LINK.npz中的source_index是完整原PLY行，paper_strength与ink_strength固定；LOCAL_OLD_PARTITION/LOCAL_ADDED_PARTITION中的stroke_id/face是代理身份，不能当Gaussian ID。FRAME.npz的paper是原GS颜色副本渲染；xz/local_ink是代理墨，raw/matched_alpha包含原ID责任门控；各层独立保存。不是原生Gaussian排线。

协议只允许一次BUILD框架。所有评价相机已曝光；三DEV覆盖下降和极小非零远区变化见报告。NEXT停止仅因21:20后禁启新单元。
''')
    receipts=[dict(name=f.name,**json.loads(f.read_text())) for f in sorted((UNIT/'logs').glob('*.receipt.json'))]
    assert all(r['returncode']==0 for r in receipts if r['name'] not in ('tdd_red_001.receipt.json','handoff_001.receipt.json'))
    progress=dict(actual_advance='One fixed BUILD-derived tangent frame changes visible region-scale original-ID-linked proxy hatching; real GS cold replay and null controls exact.',
        original_rows=310475,paper_rows_unchanged=41058,ink_rows_unchanged=21006,UNKNOWN_unchanged=195279,target_faces_unchanged=2121,
        old_strokes=375,new_strokes=380,old_segments=2004,new_segments=1946,
        visible_target_change_fraction_range=[min(r['changes']['matched']['target_full']['useful_fraction_0_05'] for r in dev),max(r['changes']['matched']['target_full']['useful_fraction_0_05'] for r in dev)],
        visible_outcome=visual['observation_chinese'],representation=p['scope'])
    artifacts={n:str(UNIT/n) for n in ('REPORT_ZH.md','README_ZH.md','PROTOCOL.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json','ASSET_LOCK.json','BUILD_LOCK.json','SUMMARY.json','VALIDATION.json','ALL_DEV_VIEWS.png','ALL_DEV_MATCHED.png','ALL_DEV_INK.png','ALL_ARC_FRAMES.png','MEDIA_VALIDATION.json','cold_replay_001/REPLAY_CHECK.json','asset/SOURCE_LINK.npz','asset/ASSET.json','VISUAL_REVIEW.json','FAR_READBACK.json')}
    status=dict(execution_state='completed',stage='BUILD_local_frame_handoff',scientific_verdict=visual['scientific_verdict'],
        gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,variant_retained='comparison asset; no quality promotion',
        completed_utc=now(),elapsed_minutes=elapsed,artifacts=artifacts,tests_and_actual_commands=receipts,blockers=[],next_action='stop',
        stop_reason='no_new_units_deadline',parent_monitor_verification='pending',old_failures_preserved=True,
        preserved_failures=[dict(stage='tdd_red_001',returncode=1,reason='expected missing module before implementation'),
            dict(stage='handoff_001',returncode=1,reason='post-result handoff missing OLD import; original source and partial handoff archived; science unchanged')])
    js(UNIT/'STATUS.json',status);js(UNIT/'NEXT.json',dict(action='stop',stop_reason='no_new_units_deadline',recommended_next_step=visual['next_step'],why=visual['next_why']))
    js(UNIT/'SOURCE_PROVENANCE.json',dict(parent_hatching=str(OLD.parent/'unit_009/source_snapshot/hatching.py'),
        modification='v06 hatching adds optional validated orthonormal cutting_basis; absent basis retains exact original behavior; new local_frame and unit010 runners',
        original_sources_unchanged=True,old_reports_unchanged=True,protocol_sha256=sha(UNIT/'PROTOCOL.json')))
    backup=UNIT/'delivery_previous';backup.mkdir(exist_ok=False);backups={}
    for name in ('DELIVERY_STATUS.json','DEMO_README_ZH.md'):
        f=OUTPUT_ROOT/name
        if f.exists():shutil.copy2(f,backup/name);backups[name]=sha(f)
    js(UNIT/'DELIVERY_PREVIOUS_LOCK.json',dict(files=backups))
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(latest_unit=str(UNIT),execution_state='completed',scientific_verdict=visual['scientific_verdict'],
        gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,variant_retained='comparison asset',
        readme=str(UNIT/'README_ZH.md'),report=str(UNIT/'REPORT_ZH.md'),next_action='stop',stop_reason='no_new_units_deadline',
        old_delivery_backup=str(backup),parent_monitor_verification='pending',utc=now()))
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text('''# v06交付：原Gaussian关联区域NPR与方向编辑

最新unit010完成一次BUILD局部参考框架对照。方向编辑清楚可见，53.2%–56.5%的目标像素明显改变；但三个DEV墨覆盖下降，完整物体质量优势未建立，默认未升级。当前为原GS纸底加原ID关联代理墨，不是原生Gaussian排线。

- [unit010报告](units/unit_010/REPORT_ZH.md)
- [完整物体自然对照](units/unit_010/ALL_DEV_VIEWS.png)
- [同BUILD墨预算对照](units/unit_010/ALL_DEV_MATCHED.png)
- [视频与冷重放命令](units/unit_010/README_ZH.md)
- [此前unit008可见前侧补选变体](units/unit_008/README_ZH.md)
- [unit009纸底饱和负结果](units/unit_009/REPORT_ZH.md)

原310475行、原PLY及几何保持；原行连接、代理路径、独立源/纸底/墨层/混合图均已交付。依赖原PLY、本地Python及锁定历史缓存，不是独立移动包。相对v05/unit005，任务从稀疏路径变为显式区域操作，不能倒算旧8.044%远区失败及4.49%区域变化为成功。所有旧负结果与中断保留，前版根交付说明备份在unit010/delivery_previous。

21:20后不启动新单元；unit010完成后按截止要求结束今晚科学实验。停止不代表所有独立路线耗尽。scientific_seal=false，父级独立监测仍待确认。
''')
    hand=UNIT/'handoff_source';hand.mkdir(exist_ok=False);shutil.copy2(Path(__file__),hand/Path(__file__).name)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={Path(__file__).name:sha(Path(__file__))}))
    print('HANDOFF completed',elapsed,'minutes; NEXT stop for new-unit deadline; far nonzero records',len(farrecords),flush=True)

if __name__=='__main__':main()
