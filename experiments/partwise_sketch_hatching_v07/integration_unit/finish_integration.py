"""Handoff after inspecting actual complete A/B/D frames; not a science producer."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now,output_guard
from run_integration import protocol,check_assets,PATH_ARMS
import json,datetime
AUTHORIZED='2026-10-25T14:19:44.707967+09:00'
def load(name):return json.loads((UNIT/name).read_text())
def main():
    protocol();check_assets()
    asset=load('asset/ASSET.json');audit=load('AUDIT.json');geom=load('GEOMETRY_READBACK.json');match=load('BUILD_MATCH.json')
    rows=[r for r in load('SUMMARY.json') if r['kind']=='dev'];attr=load('attribution/SUMMARY.json');replay=load('cached_integration_replay/REPLAY_RECEIPT.json')
    assert audit['status']=='pass' and replay['all_equal'] and replay['all_three_arms_rerasterized']
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['red_integration']['child_returncode']==1
    assert all(r['child_returncode']==0 for k,r in commands.items() if k!='red_integration')
    visual=dict(verdict='negative: carrier-conditioned straightest integration did not establish whole-object readability improvement',
        inspected=['ALL_DEV_NATURAL.png','ALL_DEV_MATCHED.png','REAR_CAMERA_SEQUENCE.png','dev/orbit_61_24_5.3/COMPARISON.png','dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_241_24_5.3/INK_LAYERS.png'],
        front='前侧B/D线束整体近似，局部位置和短折线变化未形成更完整清楚的铲斗面；新增作者面仍保留。',
        rear='弱241/24及高后侧仍有短碎线、交叉网格、留白和照片残留；231/241/251三实际相机未见稳定整物体优势。',
        layers='自然和配平、linked及同预算ungated均未建立明确优势。pre-S已有碎乱，S另使墨变淡。',
        scope='有限目视判断，不是独立偏好研究、物理表面或时序稳定性认证。')
    js(UNIT/'VISUAL_REVIEW.json',visual)
    nextstep='14:25禁止启动新科学单元的截止已到；不再开unit012或新机制试验。完成当前成果的总交付：根目录DEMO_README_ZH.md、DELIVERY_STATUS.json、代码/数组/依赖/准确重放入口及带哈希包，保留全部负结果。后续若有新时间授权，可重新审查Chair标准编辑和新路径原ID支持；本次不执行该新科学路线。'
    js(UNIT/'NEXT.json',dict(action='stop',reason='no_new_science_deadline_2026-10-25_14:25_JST',recommended_next_step=nextstep,
        why='停止新科学是明确时间边界，不是本轮局部负结果强制全局停止；当前交付整理继续，14:45科学收尾、15:00硬停止。',delivery_work_may_continue=True))
    far=[r for r in load('FAR_READBACK.json') if r['pair']=='B_D' and r['mode']=='linked_matched'];maxfar=max(r[k]['max'] for r in far for k in ('other','background'))
    effects=[r for r in load('VISIBLE_INTERVENTION.json') if r['pair']=='B_D' and r['mode']=='linked_matched' and r['view'] in {x['view'] for x in rows}]
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(AUTHORIZED)).total_seconds()/60
    verdict='negative for whole-object improvement; same material seeds on saved C alter integration, but pullback to O does not provide practical readability benefit; default unchanged'
    status=dict(unit='unit_011',execution_state='completed',stage='actual_scene_visual_attribution_independent_audit_and_replay_complete',scientific_verdict=verdict,
        gaussian_link_progress='Original310475 rows/PLY/geometry/fullSH/opacity/order,paper41058/ink21006,M1/UNKNOWN195279 fixed.380 new D stroke identities with original A/B provenance and face/bary; source/paper/S cached, all A/B/D ink actually rendered. No per-path Gaussian ownership certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,
        tests=dict(expected_red='missing integration module rc1 preserved',green='6 tests: flat/fold/curve identity, affine tangent push, fixed seed/budget, boundary/topology, same-label foreground occlusion and zeroS',control='380 saved seeds on O exactly reproduce old B arrays and stops',audit=audit,replay=replay),
        artifacts=['PROTOCOL.json','asset/ASSET.json','asset/D_SEEDS_AND_STOPS.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','GEOMETRY_READBACK.json','attribution/SUMMARY.json','FAR_ABSOLUTE.json','FAR_READBACK.json','VISIBLE_INTERVENTION.json','AUDIT.json','VISUAL_REVIEW.json','cached_integration_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json'],
        blockers=[],execution_authorized_jst=AUTHORIZED,elapsed_minutes_from_authorization=elapsed,finished_utc=now(),
        limitations=['Only one bounded saved carrier and inherited straightest walker; no general statement that noise is irrelevant.','Carrier intervention includes tangent differential, metric and boundary-stop changes.','All final owner and first-hit geometry is O; C is diagnostic, not true surface.','Six unique exposed evaluation cameras; three arc frames are not temporal certification.','Every historical failure, including H zero_step_cycle, remains unchanged.'])
    js(UNIT/'STATUS.json',status);js(UNIT/'EXECUTION_RECORDS.json',commands)
    text=['# Unit011：固定种子在降噪载体上积分后映回，未建立整物体收益','',
        '**实际A/B/D、四BUILD、四DEV/三arc、逐笔触自身支持、独立审计及新进程重放完成。execution_state=completed；科学结果为负，默认不变；scientific_seal=false，父级验证待完成。**','',
        visual['front']+visual['rear']+visual['layers']+visual['scope'],'',
        '本轮将“生成载体影响累计行走”与“保存路径嵌入变化”分开。B在原O积分；D在unit002已保存C积分，再按结果face/bary映回O。全部显示路径的所属面和首交遮挡都为O，避免unit009/010的C嵌入偏离混杂。这一对照仍未建立收益，但不据此否定全部载体噪声或其他生成器。','',
        '## 冻结干预','',
        '原A是切片历史参照；B用unit001 SEEDS_AND_STOPS的380个材料种子和原请求长度重积分，几何、face/bary、元数据及停止原因逐值恢复旧B后逐字节复制。D保持每个seed_face/seed_bary，初始切向以O三角形的重心微分db推到C：normalize(db @ triangle_C)。每个方向仍请求原长度的一半，不从C或截短B重新提取预算。展开行走器原样复制，停止规则、真实共享边、分区和孔洞保持。','',
        'D新身份为7e12加分区偏移和种子排序；保存原A父ID与B ID、初始切向、C生成坐标、最终O坐标和全部停止记录。载体造成的切向、度量、轨迹及边界响应属于干预，不宣称分别隔离法线与度量效应。没有新降噪、求场、角度/间距/长度扫描或逐相机生成。','',
        '原16543顶点/29999面拓扑、2121作者目标面与旧2030/新增91分区、310475原PLY行/几何/协方差/opacity/完整SH、41058纸底与21006墨行权重、M1/UNKNOWN195279保持。C复用441个移动顶点、0.002位移上限的诊断副本；1px/AA2、0.004遮挡容差和2px评价带不变。','',
        '| 臂 | 路径 | 段数 | 显示世界总长度 | 主分区跨面转角中位数/P95 |','|---|---:|---:|---:|---:|']
    for arm in PATH_ARMS:
        q=[asset['paths'][arm+'_'+part] for part in ('old','added')];t=geom['face_transition_turns'][arm+'_old']['world_turn_quantiles']
        text.append(f"| {arm} | {sum(x['strokes'] for x in q)} | {sum(x['segments'] for x in q)} | {sum(x['length'] for x in q):.9f} | {t[0]:.3f}°/{t[2]:.3f}° |")
    text+=['',f"380条种子全部有输出，内部存储断点0。原请求长度{asset['requested_length']:.9f}；D在C上的实际长度{asset['generation_length']:.9f}，映回O后{asset['pulled_length']:.9f}。B双向停止为656请求长度/93分区边界/11网格边界；D为640/109/11。提前停止与映回长度变化如实保留，没有删除短线或重新分配预算。表中转角排除了种子处同面分段，不能用ASSET中包含同面分段的中位数代替。",'',
        '## BUILD与完整DEV','',
        '自然四BUILD目标RGB L1：'+json.dumps(match['natural_totals'],ensure_ascii=False)+'。',
        '共同预算'+f"{match['budget']:.6f}"+'，每臂唯一全局系数：'+json.dumps(match['scales'],ensure_ascii=False)+'。A/B配平系数保持unit001，D另用BUILD冻结；自然强度同时交付。','',
        '| DEV | 目标像素 | linked墨L1 A/B/D | 覆盖A/B/D |','|---|---:|---:|---:|']
    for r in rows:
        q=[r[a+'_linked'] for a in PATH_ARMS];text.append('| '+r['view']+f" | {r['target_pixels']} | "+'/'.join(f"{x['ink_L1']:.3f}" for x in q)+' | '+'/'.join(f"{100*x['coverage']:.3f}%" for x in q)+' |')
    text+=['','B→D的弱后侧覆盖35.658%→35.625%；两个高视角略增、前低视角持平。这些微小变化未形成整物体可读性收益。同预算ungated亦无明确优势；S继续作为可选原行区域连接，不宣称NPR改进。','',
        'B/D配平linked目标RGB L1差≥0.05占比（描述，非门槛）：'+', '.join(r['view']+'='+f"{100*r['above_005_fraction']:.2f}%" for r in effects)+'。变化不是完全no-op，幅度有限。','',
        '## 自身支持与绝对远区损伤','',
        '| 相机/臂 | 可见px | pre-S自身缺失px | linked配平缺失px | linked支持px |','|---|---:|---:|---:|---:|']
    for r in attr:text.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    text+=['','B→D前侧linked支持850.369→849.917px，弱后侧715.388→718.213px；一增一减，不能称稳定连续性修复。两条曲线的采样和可见长度不同，不是固定材料样本逐点匹配；每条笔触仅采自身光栅，不借其他笔触重叠获益，代理射线也不是物理真值。','',
        '| DEV | linked远其他源差L1 A/B/D | 背景源差L1 A/B/D |','|---|---:|---:|']
    for r in rows:
        q=[r[a+'_linked'] for a in PATH_ARMS];text.append('| '+r['view']+' | '+'/'.join(f"{x['far_other']:.9f}" for x in q)+' | '+'/'.join(f"{x['background']:.9f}" for x in q)+' |')
    text+=['',f'上述源差包含固定纸底既有影响。六不同评估相机B/D配平linked远区最大单像素L1={maxfar:.12g}；超过1/255的像素合计0，弱后侧有一个浮点级非零像素，不宣称严格零。FAR_ABSOLUTE保存各臂自然/配平及linked/ungated的绝对源差；FAR_READBACK保存臂间增量。','',
        '## 验证与复放','',
        'TDD缺integration模块的预期RED rc1保留；6项GREEN覆盖恒等恢复、平面/折面/曲面、已知仿射微分、固定材料种子/预算、分区停止、拓扑拒绝、真实同标签前景遮挡与零S。科学阶段所有命令rc0。',
        f"独立审计核对{audit['input_files_checked']}份输入、380条D路径；独立锚点误差最大{audit['max_independent_anchor_error']:.3g}，切向另用最小二乘独立求解，最大误差约1.67e-13；核对{audit['pngs_checked']}张主PNG与数组、完整解码当时{audit['all_png_fully_decoded']}张PNG，合成误差0。",
        '新进程在弱241/24真实重栅格化A/B/D，35数组逐值一致；复用GS source/paper/S，不冒称再次冷GS。unit001一次cold hybrid五层逐值恢复的工程结果与旧独立验收缺Open3D失败范围同时保留。','',
        '```bash','/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/integration_unit/replay_integration.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_011/user_replay_001 --view orbit_241_24_5.3','```','',
        '输出须不存在且位于unit011。现有NumPy2.2.6/SciPy1.15.3/Open3D0.20.0及Pillow12.2.0环境不改。两核亲和、数值线程1、串行、CUDA为空；无GPU、训练、安装、下载、嵌套模型、push/merge。冻结DECISION/科学源码/协议不变，旧资产只读。','',
        '四DEV与三arc只有六不同评估相机，241/24明确复用，全部EXPOSED；三帧不是连续视频或无闪烁认证。Lego为既有NeRF Synthetic冻结vanilla-GS及CPU协方差平面深度/TSDF代理，非本轮采集物体、RaDe训练或GT。输出是原GS纸底加原ID区域S门控代理墨，非原生Gaussian排线、完整语义分部或逐路径Gaussian所有权。','',
        'v05 far8.044%、31像素腐蚀目标、4.49%作者区域变化失败，v06及v07 unit001–010负结果全部保留；H局部PARTIAL与zero_step_cycle不改写。','',
        '## 截止与交付','',nextstep,'',f'授权至本报告约{elapsed:.2f}分钟。NEXT=stop仅针对已到14:25的新科学启动截止，当前交付整理继续。']
    output_guard(UNIT/'REPORT_ZH.md').write_text('\n'.join(text)+'\n')
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(HERE/'finish_integration.py'):sha(HERE/'finish_integration.py')}))
    print(json.dumps(dict(execution_state='completed',scientific_verdict=verdict,elapsed_minutes=elapsed,max_far_pixel_L1=maxfar),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
