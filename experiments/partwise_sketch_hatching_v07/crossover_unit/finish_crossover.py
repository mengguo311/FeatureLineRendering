"""Evidence handoff for the completed saved-layout/embedding crossover."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now,output_guard
import json,datetime
from run_crossover import protocol,check_assets,PATH_ARMS
AUTHORIZED='2026-10-25T14:03:37.201698+09:00'
def load(name):return json.loads((UNIT/name).read_text())
def main():
    protocol();check_assets()
    asset=load('asset/ASSET.json');audit=load('AUDIT.json');geom=load('GEOMETRY_READBACK.json');material=load('MATERIAL_VISIBILITY.json')
    match=load('BUILD_MATCH.json');rows=[r for r in load('SUMMARY.json') if r['kind']=='dev'];attr=load('attribution/SUMMARY.json')
    replay=load('cached_crossover_replay/REPLAY_RECEIPT.json');assert audit['status']=='pass' and replay['all_equal'] and replay['all_four_arms_rerasterized']
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['red_crossover']['child_returncode']==1
    assert all(r['child_returncode']==0 for name,r in commands.items() if name!='red_crossover')
    visual=dict(verdict='negative: no established whole-object benefit from saved C-layout after return to original embedding',
        inspected=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','dev/orbit_61_24_5.3/COMPARISON.png','dev/orbit_241_24_5.3/COMPARISON.png','dev/orbit_61_24_5.3/INK_LAYERS.png','dev/orbit_241_24_5.3/INK_LAYERS.png'],
        front='四组合前侧均呈现原有排线及小幅局部位置变化。CO将降噪载体生成的材料路径拉回原载体后，未显现明确更完整、清楚的铲斗形体。',
        rear='弱241/24及高后侧仍有碎线、交叉网格、空白和照片残留。231/241/251三相机中无稳定整物体优势。',
        ungated='自然及配平、linked及同预算ungated均未建立清晰度优势；pre-S本身仍碎乱，S另使墨变淡。',
        scope='有限目视检查；不是独立用户偏好、物理表面或时序稳定认证。')
    js(UNIT/'VISUAL_REVIEW.json',visual)
    nextstep='下一次只读Astra审查、父级冻结并在同会话授权后，在Chair作者座面region4执行一次标准间距编辑及有界新路径原ID支持记录。重新检查实际便携资产，复制最小输入到新v07单元并记录原哈希；先以同生成器、同owner-only支持规则重生成spacing0.045控制，再一次改为0.05625，保持angle95、length0.22、width1、ink_strength0.35及载体/纸底/S/M1/UNKNOWN。原140条转移路径及继承掩码保留作历史参照，不能把其与新owner-only控制的差异归于间距。非目标路径字节保持；新路径新身份，预先固定分层弧长样本和前后相机，记录实际CPU接受的original source_index、alpha、T、alpha*T、无支持样本与未认证剩余路径。交付完整自然/配平linked及同预算ungated、保存加载与实际重放。复用现有依赖和冷bootstrap基础；这是编辑及来源证据，不是Lego噪声的跨场景证明。'
    why='本轮已补齐两套材料路径的四组合；回到原载体未发现隐藏的整物体生成收益，两套路径嵌入C都增加原参照下的深度拒绝，继续扩大降噪或扫描角度没有依据。重新只读检查Chair前61/24、后241/60完整图，座面平行线可辨；asset.json明确140条转移路径、2704作者面及继承capsule支持，实际link_renderer保留CPU原行接受事件。一次标准编辑和新路径来源采样是尚未完成的独立授权路线。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=nextstep,why=why,estimated_minutes=25,requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    verdict='negative for whole-object NPR improvement; within-family embedding support loss observed for both layouts; no hidden useful saved-layout benefit established; default unchanged'
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(AUTHORIZED)).total_seconds()/60
    status=dict(unit='unit_010',execution_state='completed',stage='four_arm_real_scene_visual_attribution_audit_and_replay_complete',scientific_verdict=verdict,
        gaussian_link_progress='Original310475 GS rows/PLY/geometry/fullSH/opacity/order, paper41058/ink21006 weights and M1/UNKNOWN195279 unchanged. Saved OO380 and CC376 paths preserved;756 new cross identities have identical parent material face/bary coordinates and explicit immediate saved-layout provenance. Actual proxy ink with original-GS cached paper/S; no per-path Gaussian ownership certification.',
        scientific_seal=False,parent_verification='pending',actual_commands=commands,
        tests=dict(expected_red='missing crossover module rc1 preserved',green='4 groups: unequal families, roundtrip, flat/fold/curve/shared-edge, topology/labels and actual same-label foreground occluder/zeroS',audit='Independent anchors, hashes, diagonal equality, images and composition',replay='All four arms rerasterized in a fresh process;45 arrays equal',material_visibility='Fixed O-embedded sample weights separately for each family'),
        artifacts=['PROTOCOL.json','asset/ASSET.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','GEOMETRY_READBACK.json','MATERIAL_VISIBILITY.json','VISIBLE_INTERVENTION.json','FAR_READBACK.json','FAR_ABSOLUTE.json','FRAGMENT_READBACK.json','PIXEL_INTERACTION.json','AUDIT.json','VISUAL_REVIEW.json','cached_crossover_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json'],
        blockers=[],execution_authorized_jst=AUTHORIZED,elapsed_minutes_from_authorization=elapsed,finished_utc=now(),
        limitations=['One bounded saved geometry perturbation and one slicing generator; not all carrier noise or a generator-algorithm factorial.','Embedding contrast includes displacement relative to fixed original first-hit reference.','No stroke pairing across P_O/P_C; path counts380/376 and material layouts differ.','Six distinct exposed evaluation cameras; three rear frames are not a temporal certification.','All previous failures preserved; current result does not repair inherited H zero_step_cycle.'])
    js(UNIT/'STATUS.json',status);js(UNIT/'EXECUTION_RECORDS.json',commands)
    far=[r for r in load('FAR_READBACK.json') if r['mode']=='linked_matched'];maxfar=max(r[k]['max'] for r in far for k in ('other','background'));farpixels=sum(r[k]['above_1_255'] for r in far for k in ('other','background'))
    effects=[r for r in load('VISIBLE_INTERVENTION.json') if r['mode']=='linked_matched' and r['pair']=='OO_CO' and r['view'] in {x['view'] for x in rows}]
    report=['# Unit010：材料路径与载体嵌入交叉后，未建立整物体收益','',
        '**四组合真实场景对照、四BUILD、四DEV/三arc、逐笔触自身支持、同材料诊断、独立审计及四臂新进程重放完成。execution_state=completed；科学结果为负，不升级默认；scientific_seal=false，父级验证待完成，NEXT=continue。**','',
        visual['front']+visual['rear']+visual['ungated']+visual['scope'],'',
        '本轮有用结论是有限机制归因：将同一套材料路径嵌入降噪载体，两套路径族均损失原遮挡参照下的可见支持；将降噪后生成的路径拉回原载体，支持与原基线接近但完整观感仍未改善。没有证据支持“可观生成收益只是被嵌入遮挡掩盖”。这不证明全部表面噪声无关，也不排除其他生成器。','',
        '## 冻结对照与保持项','',
        '| 组合 | 材料路径 | 嵌入载体 | 本轮动作 |','|---|---|---|---|',
        '| OO | unit002 A=P_O | 原始O | 原路径文件逐字节复制；核验后复用自然输出 |',
        '| OC | 同一P_O face/bary | 已保存C | 新ID，实际重栅格化 |',
        '| CO | unit002 C=P_C face/bary | 原始O | 新ID，实际重栅格化 |',
        '| CC | 同一P_C | 已保存C | 原路径文件逐字节复制；核验后复用自然输出 |','',
        '所有组合的首交遮挡及区域图都来自原始O；笔触所属面平面来自各自嵌入。0.004容差、1px/AA2、2px评价带不变。未重新降噪、生成、求场、修补、改变方向/相位/风格或按相机重建路径。切片风格仍为35°/95°、spacing0.06/0.075、length0.12、gap0.035。','',
        '原16543顶点/29999面的拓扑对应、2121作者目标面与旧2030/新增91分区、310475原PLY行身份/顺序/几何/协方差/opacity/完整SH、41058纸底与21006墨行权重、M1/UNKNOWN195279保持。C仅为unit002已保存441个移动顶点、最大0.002位移的诊断副本，非物理真值。','',
        'OC新ID为5e12、CO为6e12，加分区偏移和各自源路径排序。每条新增路径记录immediate_saved_layout_id；不把P_C路径强行对应到P_O。旧父路径、全部负结果和H的zero_step_cycle记录不修改，本轮不声称修复该行走器问题。','',
        '| 组合 | 路径数 | 段数 | 世界总长度 | 主分区跨面转角中位数/P95 |','|---|---:|---:|---:|---:|']
    for arm in PATH_ARMS:
        qq=[asset['paths'][arm+'_'+part] for part in ('old','added')];turn=geom['face_transition_turns'][arm+'_old']['world_turn_quantiles']
        report.append(f"| {arm} | {sum(q['strokes'] for q in qq)} | {sum(q['segments'] for q in qq)} | {sum(q['length'] for q in qq):.9f} | {turn[0]:.3f}°/{turn[2]:.3f}° |")
    report+=['','OO/OC为380条，CO/CC为376条；各路径族内材料坐标及连接保持，空间长度和角度随嵌入变化。跨族数量与长度差异属于既有生成响应，不以删除短线或相同笔触数冒充公平。内部存储断点均0，不等于视觉连续。','',
        '## 实际BUILD墨量与完整DEV','',
        '自然四BUILD目标RGB L1：'+json.dumps(match['natural_totals'],ensure_ascii=False)+'。',
        '共同预算'+f"{match['budget']:.6f}"+'；每臂唯一全局因子：'+json.dumps(match['scales'],ensure_ascii=False)+'。自然输出同时保留，无DEV拟合；本轮共同最小值恰仍为CC，因此两个历史对角线的原配平系数也恢复，但这并非预设。','',
        '| DEV | 目标像素 | linked墨L1 OO/OC/CO/CC | 全目标覆盖 OO/OC/CO/CC |','|---|---:|---:|---:|']
    for r in rows:
        qq=[r[a+'_linked'] for a in PATH_ARMS]
        report.append('| '+r['view']+f" | {r['target_pixels']} | "+'/'.join(f"{q['ink_L1']:.3f}" for q in qq)+' | '+'/'.join(f"{100*q['coverage']:.3f}%" for q in qq)+' |')
    report+=['','核心比较CO与OO共享原载体和原遮挡参照。弱后侧覆盖35.658%→35.560%，未显示完整可读性改善；不能把微小差异当成视觉优势。高后侧与三后侧实际相机仍保留失败。原ID区域S使墨衰减，但同预算ungated也未建立整物体收益，S继续仅作可选连接机制。','',
        'CO相对OO的配平linked目标像素L1差≥0.05占比（描述口径，非通过门槛）：'+', '.join(r['view']+'='+f"{100*r['above_005_fraction']:.2f}%" for r in effects)+'。不把微小可见变化当成功，也不以几何中位数代替观感。','',
        '## 自身可见支持与固定材料采样','',
        '| 相机/臂 | 可见px | pre-S自身缺失px | linked配平缺失px | linked支持px |','|---|---:|---:|---:|---:|']
    for r in attr:report.append(f"| {r['view']} {r['arm']} | {r['proxy_visible_length']:.3f} | {r['preS_own_visible_missing_length']:.3f} | {r['linked_matched_own_visible_missing_length']:.3f} | {r['proxy_visible_length']-r['linked_matched_own_visible_missing_length']:.3f} |")
    report+=['','同在原载体O上的OO/CO，前侧linked支持858.679/857.704px，弱后侧726.061/725.584px，接近且略降；未揭示隐藏的连续支持增长。嵌入C后的缺失分子较小伴随可见分母缩小，不能称连续性修复。','',
        '为避免独立自适应采样的分母混杂，每个路径族分别采用O嵌入的同一材料样本与固定投影长度权重，迁移到C并重新判可见；不跨族匹配样本。','',
        '| 相机/族 | O可见固定权重px | C可见固定权重px | 可见→深度拒绝px | 深度拒绝→可见px |','|---|---:|---:|---:|---:|']
    for r in material:report.append(f"| {r['view']} {r['source']}→{r['destination']} | {r['source_visible_length']:.3f} | {r['destination_visible_with_fixed_source_weights']:.3f} | {r['visible_to_depth_rejected']:.3f} | {r['depth_rejected_to_visible']:.3f} |")
    report+=['','两族都出现净可见支持损失。该现象包含载体相对固定原遮挡面的偏离及真实遮挡；不是物理噪声真值，不能放宽容差掩盖。仅可归因于本有限载体替换在当前参照下的响应。PIXEL_INTERACTION保存逐像素带符号差分的差分，天然强度为主要描述；配平后的不同全局因子会额外影响强度，不能将该量当质量评分或独立物理交互证明。','',
        '## 远区绝对损伤','',
        '| DEV | linked远其他源差L1 OO/OC/CO/CC | 背景源差L1 OO/OC/CO/CC |','|---|---:|---:|']
    for r in rows:
        qq=[r[a+'_linked'] for a in PATH_ARMS];report.append('| '+r['view']+' | '+'/'.join(f"{q['far_other']:.9f}" for q in qq)+' | '+'/'.join(f"{q['background']:.9f}" for q in qq)+' |')
    report+=['','上述源差包含固定纸底既有影响。六个不同评估相机的六组两两比较，配平linked远区最大单像素L1='+f'{maxfar:.12g}'+f'；超过1/255的变化像素合计{farpixels}。存在浮点级非零差，不宣称严格零。FAR_ABSOLUTE含全部自然/配平、linked/ungated的远其他与背景绝对源差；FAR_READBACK为臂间增量，不混用分母或扩大边界带。','',
        '## 验证、执行与复放','',
        'TDD先因缺crossover模块预期RED rc1，原回执保留；随后4组GREEN覆盖数量不同的两族、恒等/往返、平面/折面/曲面/共享边、标签与拓扑拒绝、同标签分离前景真实遮挡和零S。派生、BUILD、DEV/arc、归因、同材料采样、独立审计和重放均rc0，无新增科学执行失败。',
        f"独立审计核对{audit['input_files_checked']}份输入、756条交叉新路径，锚点独立求和最大误差{audit['max_independent_anchor_error']:.3g}；核对{audit['pngs_checked']}张主PNG与数组、完整解码评估时全部{audit['all_png_fully_decoded']}张PNG，独立合成误差{audit['composition_error']:.3g}。",
        '新进程在弱241/24实际重新光栅化全部四臂，而非仅载入两个缓存对角线；45数组逐值恢复。该检查复用固定GS层，不冒称再次冷GS。','',
        '```bash','/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/crossover_unit/replay_crossover.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_010/user_replay_001 --view orbit_241_24_5.3','```','',
        '输出目录须不存在且位于unit010。依赖指定现有Python、NumPy2.2.6/SciPy1.15.3/Open3D0.20.0；未安装或改旧环境。两核亲和、数值线程1、串行、CUDA为空。unit001一次完整冷hybrid及旧独立验收缺依赖失败均保持。原PLY、旧包、旧单元和父级DECISION只读；无GPU/训练/下载/嵌套模型/push/merge。','',
        '四DEV与三arc只有六个不同评估相机，241/24明确重复并复用，全部EXPOSED；三帧不是连续视频或时序认证。Lego为既有NeRF Synthetic冻结vanilla-GS与CPU协方差平面深度/TSDF代理，并非本轮采集真实物体或RaDe训练/GT。输出为原GS纸底加原ID区域S门控代理墨，不是原生Gaussian排线、完整语义分部或逐路径Gaussian归属。','',
        'v05的far8.044%、31像素腐蚀目标、4.49%作者区域变化失败，v06及v07 unit001–009全部负结果保持；H局部PARTIAL不升级，不据此次有限负结果否定所有载体或生成器路线。','',
        '## 下一步','',nextstep,'',why,'',
        f'本单元从执行授权至本报告约{elapsed:.2f}分钟。下一科学单元仍须只读审查与父级冻结；14:25禁启、14:45科学收尾、15:00硬停止。']
    output_guard(UNIT/'REPORT_ZH.md').write_text('\n'.join(report)+'\n')
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(HERE/'finish_crossover.py'):sha(HERE/'finish_crossover.py')}))
    print(json.dumps(dict(execution_state='completed',scientific_verdict=verdict,next='continue',elapsed_minutes=elapsed,max_far_pixel_L1=maxfar),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
