from env import *
def main():
 replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['render_replays']==36 and replay['model_replays']==9 and replay['prediction_replays']==36 and replay['match_replays']==12
 rows=json.loads((R/'mechanism_audit/COUNTS.json').read_text());cal=[json.loads(p.read_text()) for p in sorted((R/'renders').glob('*/*/COUNT.json'))];source=[json.loads((R/'sources'/s/'SOURCE.json').read_text()) for s in SCENES];matches=json.loads((R/'MATCH_COUNTS.json').read_text());table=[]
 for v in views('ficus'):
  x={a:next(x for x in rows['pixel_transitions'] if x['scene']=='ficus' and x['view']==v and x['arm']==a) for a in ['full_sh','dc_only','anchor_sh']};table.append('|'+v+'|'+'|'.join(str(x[a]['unknown']) for a in ['full_sh','dc_only','anchor_sh'])+'|'+str(x['dc_only']['known_to_different_known'])+'|')
 caltable='\n'.join('|%s|%.6f|%.6f|%.6f|%.2f–%.2f|'%(s,max(x['calibration']['rgb_mae'] for x in cal if x['scene']==s),max(x['calibration']['alpha_mae'] for x in cal if x['scene']==s),max(x['calibration']['depth_relative_p95'] for x in cal if x['scene']==s),min(t for x in cal if x['scene']==s for t in x['seconds'].values()),max(t for x in cal if x['scene']==s for t in x['seconds'].values())) for s in SCENES)
 gate=dict(overall='PARTIAL',engineering='VALID_after_display_only_repairs',scenes=dict(scan24=dict(A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',reason='roof and white platform/background share proxy class; angular color removal does not identify whole building'),scan65=dict(A='NO_GO_with_local_coverage_changes',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',reason='dark teeth/cheek and table/shadow confusion remains; anchor helps part of cranium but not complete subject'),ficus=dict(A='GO_PROXY_inherited',B='PARTIAL_local_improvement_precision_NO_GO',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',reason='DC reduces pot glare stripes, but crown wood/soil unresolved and test79 unknown increases; pot lacks frozen common-visibility qualification')),formal_multistyle_ready=False)
 js(R/'STAGE_GATES.json',gate)
 tests=dict(new_tests_passed=25,failures_final=0,inherited_tests_counted=0,red_logs=['logs/color_RED.log','logs/render_RED.log','logs/protocol_RED.log','logs/labels_RED.log','logs/layout_RED.log'],green_log='logs/tests_COMPLETE_GREEN.log',engineering_negative=['ENGINEERING_LABEL_ADDENDUM.json','ENGINEERING_LAYOUT_REPAIR.json'],fixtures_or_tolerances_relaxed=False)
 js(R/'TEST_RESULTS.json',tests)
 counts=dict(scenes=3,views_per_scene=4,source_only_render_frames=36,source_render_replay_frames=36,density_models=9,predictions=36,matching_arm_view_units=12,reference_contexts=12,source_counts={s:source[i]['count'] for i,s in enumerate(SCENES)},source_raw_inf={s:source[i]['raw_positive_inf'] for i,s in enumerate(SCENES)},new_GS_models=0,source_role_groups=0,C8_new_or_changed=0,styles=0,video_frames=0,calibration=cal,classification=rows,matches=matches)
 js(R/'COUNTS.json',counts)
 seen=['renders/ficus/train_r_80/SOURCE_APPEARANCE.jpg',*[f'figures/{s}/{v}/FULL.jpg' for s in SCENES for v in [DEV[s],AUX[s]]],'figures/ficus/test_r_14/FULL.jpg','figures/ficus/test_r_79/FULL.jpg',*[f'delivery/native/{s}/{v}/FULL_CORRECTED.jpg' for s in ['scan24','scan65'] for v in RES[s]],'delivery/native/ficus/test_r_14/FULL_CORRECTED.jpg','delivery/native/ficus/test_r_79/FULL_CORRECTED.jpg','delivery/OVERVIEW.jpg','delivery/ficus_pot_FAILURE.jpg','delivery/ficus_crown_FAILURE.jpg']
 js(R/'VISUAL_AUDIT.json',dict(inspected_with_image_tool=[dict(path=x,sha256=sha(R/x)) for x in seen],assessment='same executing assistant actual full-frame qualitative review; no semantic GT',scan24='all four retain bright roof/background confusion; 0036 far black background can join wall proxy',scan65='DC often fragments shadowed bone; anchor 0036 improves cranial orange coverage but teeth/zygomatic/table remain mixed',ficus='DC clearly reduces pot false wood stripes in DEV/test14; test79 adds UNKNOWN and soil still wood; anchor loses much pot/crown to UNKNOWN',display_repairs_preserved=True))
 next_hyp='独立候选（本轮未执行）：对原冻结RGB观测做标量照度/亮度变化的商空间检验，用RGB颜色方向或log-chromaticity与完整RGB同预算对照，明确它消除的是I=s*r的乘性强度而非SH角度项。先解析检验同材质明暗应相同、异材同色/灰色无辨识力、低信噪暗像素必须UNKNOWN；只沿旧DEV/AUX种子且保留原mask，禁止按test图调亮度门/类数。r07 DC盆改善却木冠重叠变大，说明去角度项不等恢复材质；下一机制问固定RGB亮度混淆是否仍是可去的nuisance。需保留原RGB与强r05及同预算颜色打乱null，不应声称对同色屋顶/地台能自动分开。若该机制与既有试验实为重复或解析控制显示信息不可辨，则STOP/收尾；不能为了到8点制造新轮。07:40后禁止新科学。'
 js(R/'NEXT_REVIEW.json',dict(next_allowed=True,next_hypothesis=next_hyp,not_executed=True,different_mechanism='multiplicative intensity nuisance versus per-kernel SH angular appearance',requires_new_freeze=True,latest_start_JST='07:40'))
 report=f'''# r07：源GS角度外观分解——局部 PARTIAL，尚未达到精确分块

本轮亲自审查前轮封存、代码和实图后，冻结并运行了新的三场景配对实验。**去掉高阶SH颜色，在Ficus盆体高光条纹上确有局部帮助；它没有解决全部部件归属，更没有使建筑/头骨通过主体门。** 固定DEV观察方向颜色的anchor方案在另一弱视角明显退化。不能将本轮解释成已得到材质、源GS语义组或多风格NPR模型。
原C2L50＋8BUILD arms/C、原source完整SH/filter/opacity和所有历史候选保持原样。本轮新产物是36帧实际source-only渲染、36张原尺寸预测、9个条件密度文件、12个双向区域资格检查和相机/源index可追溯颜色证据。没有导出修改后的GS，没有改线、重采样、删核或调线宽。

## 为什么选这条不同机制
r06发现形态证据在叶缘不可靠，DTU全scene alpha又不是主体；重复形态/图平滑门限无法增加可识别信息。源码确认原GS有SH3，颜色求值与几何投影、depth sort分离，因此可以在同一组真实源高斯上只改变角度外观函数，直接检验盆高光和阴影混淆。没有利用C8墨迹再给自身投票。
对原核i，full_sh为c_i(d)=max(0,0.5+Σ f_i,lmY_lm(d))；dc_only为max(0,0.5+C0 f_i,0)；anchor_sh为c_i(d_DEV)，对每核冻结DEV方向颜色后在所有相机沿用。三臂geometry、effective covariance、opacity、完整核集合、camera、background、排序都相同。anchor在DEV的图像必须与full位级一致，但**分类可不同**：各臂密度模型还共同使用AUX，而AUX外观已不同。这不是输出不一致的工程bug。
DC不是albedo，也不是逆渲染的光照剥离；SH会吸收高光、曝光、错几何和视角遮挡补偿。保留一帧的每核颜色也不保证其它相机的真实材质外观正确，新的alpha*T贡献关系仍由几何决定。

## 实际协议与工程资格
DTU原777×581、完整fx/fy/cx/cy、COLMAP W2C；Ficus800×800。近面.2，世界单位非米。source filter按继承官方补偿激活，原+Inf opacity经sigmoid=1；完整SH只读，所有颜色counterfactual仅内存计算。CPU源EWA source-floor variance DTU.0144/Ficus.3，DTU黑背景/Ficus白背景。中心排序与covariance投影近似仍在，**不是官方CUDA等价**。
36帧实际source-only新渲染。12个full_sh帧对v01封存参考RGB/alpha/center-z逐数组位级相同；其它两臂alpha/median_center_z/expected_center_z逐值等于full。以下是fullCPU相对原缓存的最大误差，工程门仍为.02/.02/.15，没有为了通过改门。渲染center-z只用于校准，分类mask和跨视角对应仍使用原native RaDe depth（DTU）或vanillaGS CPU plane代理（Ficus），不拿核中心z替代它。

|场景|max RGB MAE|max alpha MAE|max相对depth p95|每帧实际秒数范围|
|---|---:|---:|---:|---:|
{caltable}

DTU DEV/AUX=0000/0024、reserved=0012/0036；Ficus=train_r_80/train_r_7与test_r_14/test_r_79。全为历史已曝光相机，DTU还是源GS训练视角，不是新blind/GS-heldout。各臂分别在同一旧种子UV/代理labels、同每view每类预算上拟合r03原16³ RGB密度：sigma.75、5%本类密度门、posterior .65、margin .2不变。没有graph、目标视角seed、target颜色训练或mask重算。9模型及BUILD预测先封存、审全图后一次推理reserved。
DTU的两类只是**外围水平与中央非水平代理种子的外观类**，不是前景/背景真值。建筑屋顶、窗框与白地台可能同类；头骨暗部与桌面也可同类。这正是A门失败的重要观察，不能把两色屋顶/墙外观重命名成已完成主体分块。

## Ficus：盆体改善真实存在，精确三部件仍未通过
四视角原图、full/DC/anchor与强r05、v02 RGB-only控制完整并列，见delivery/native/ficus。DEV的盆面橙色误木条纹在DC中减少；test_r_14最明显，盆侧高光不再大面积触发木类。这个改进不依赖删mask或减少原C8墨量，原mask和背景孔洞逐值保持。冠内真实枝条仍有叶类/UNKNOWN，土面仍常被称木，test_r_79的盆面/枝根和冠边灰区上升。

|Ficus视角|full UNKNOWN|DC UNKNOWN|anchor UNKNOWN|DC已知→另一已知|
|---|---:|---:|---:|---:|
{chr(10).join(table)}

UNKNOWN变化不是准确率。test14 DC的wood→pot有479个像素，wood→UNKNOWN有1217个；同时wood→crown805个，可能包含真实枝条损失，不能把木类减少全算对。test79 DC未知从14259升19575，anchor升33033，原79309个mask像素没有变。anchor仅剩7272个盆类像素（full14687），大块不确定没有被偷偷当背景删掉。
种子密度重叠（sum min，0少1多）中，盆/木从full .0466降DC .0173，但木/冠从.2592升.2836；这支持“盆角度外观是部分干扰”，也显示它不是全局部件解法。种子是历史代理labels，重叠不是GT识别精度。
冻结双向资格（DEV到AUX/test14/test79）：full=1/2/2，DC=2/2/2，anchor=2/2/2，r05=2/2/2；通过的都是木质/叶冠代理类，盆体共同可见资格仍未过。2p depth、1.5px cycle、3p world门完全沿用，遮挡/画外不作反对票。区域分母随预测变化，配对数不能证明语义正确。尤其anchor视觉更差却有同样配对数，是本轮必须保留的反例。

## 建筑与头骨：角度外观不是最早失败的全部原因
scan24四视角均保持白屋顶与白地台/背景同代理类；0036的远黑背景仍可进入砖墙外观类。DC改变瓦纹的未知比例，却没有得到完整建筑与背景的分离。继续B屋顶/墙体正式分组没有资格，B/C/D均NOT_RUN。
scan65的暗颧骨、牙齿、眼眶边缘与桌面/阴影仍混淆。DC在0000/0012常增加碎片；anchor在0036使颅盖有更多连续橙色，但牙齿/颌侧和背景接触仍不完整，不能称A通过，也不能把灰洞全部当真实孔洞。旧r05的粗覆盖更连续，其上游疑义仍在；本轮没有否定其已见进展，也没有用本轮counterfactual替换它。
因此本轮总评PARTIAL只表示**有可解释的局部外观收益**；三场景精确可编辑分块的总门仍不通过。C线边界消融、D源GS软角色以及真正joint多风格NPR本轮全部NOT_RUN，不以彩色2D叠图冒充。

## 真实工程修复、复算与完整性
先RED后GREEN的5个API组：颜色、renderer/source适配、fit协议、图例语义、异尺寸展示。最终25个本轮独立测试全部通过，历史测试未充数。两个显示工程失败保留：初始DTU图例错误地命名foreground/background，原图保留并以delivery/native/*/FULL_CORRECTED.jpg更正；多场景overview的777×581/800²形状断言失败，原目录delivery_attempt01_INVALID保留，修复只加白边不resize/crop原像素。没有改scientific arrays、种子、参数或冻结源码以掩盖它们。
独立verify --readonly --replay重算36render、9model、36prediction、12matching并精确比对；{replay['source_files']}个只读来源、旧main893 Python与12相关worktree HEAD/index/status保持。原source数量scan24/scan65/Ficus={source[0]['count']}/{source[1]['count']}/{source[2]['count']}；source_index颜色记录不等于部件role，不输出虚假原GS分组。旧all-N源责任校准随源文件继承封存；本轮没有声称又做新的all-N贡献实验。
资源实查CPU affinity两核、无GPU/训练/mesh、所有新数据在本任务HDD且低于12GiB。每scene/相机单位SEAL可恢复。打包只有新证据/代码与报告，不含源模型/环境/凭据；AGENT_LAUNCH与ASTRA_RUNTIME_FINAL运行时文件排除静态seal。

## 下一轮候选，尚未执行
{next_hyp}
本invocation到r07封存退出，不开始r08。下一次runner需重新审查真实剩余时间、独立假设与门；07:40起只收尾，08:00停止。当前不能承诺最终多风格目标已经实现。
'''
 (R/'REPORT_ZH.md').write_text(report)
 (R/'FORMAT_ZH.md').write_text('''# r07 资产格式
renders/<scene>/<view>/<arm>.npz：float32 rgb、alpha、median_center_z、expected_center_z；后三项三臂exact相同。非nativeCUDA，depth不是用于分类的原surface depth。SOURCE_APPEARANCE.jpg中差分固定x4只为显示。
models/<scene>/<arm>/MODEL.npz：r03原密度实现，hist/threshold/classes；*_SEEDS.npz保存原UV/原labels与本臂实际源RGB。只有DEV/AUX参与。
inference/<scene>/<arm>/<view>/RESULT.npz：labels0unknown；DTU1外围水平代理、2中央非水平代理；Ficus1盆/2木/3冠粗代理。probability未校准为语义概率。source_uv是像素，不是source核ID。mask与旧r03 exact。
sources/<scene>/COLOR_PROVENANCE.npz：source_index为原source PLY顺序，dc_color/anchor_color按原全SH计算的只读颜色证据，不含源geometry且不是语义角色。原source/ink不动，0新GS模型/风格资产。
figures为最早工程图（DTU早期图例错误有ADDENDUM）；最终请用delivery/native/*/FULL_CORRECTED.jpg，delivery/*FOUR_VIEWS与OVERVIEW。所有单场景图保持native帧，无aspect stretch；多sceneoverview只白边补齐。crop只作事后诊断不参与fit。
evaluation保存同原depth/camera的双向pixel投影state、区域资格和分母；unknown/occlusion不负票。COUNTS不是分类accuracy。
安全archive MEMBERS schema={members:{relative_path:{sha256}}}；所有成员regular file，无links/absolute/..。readonly replay只读，stdout由调用者另存新receipt。不能覆盖封存结果或修改旧CODE_FREEZE。
''')
 (R/'RUN_COMMANDS.md').write_text('''# r07 实际执行
解释器 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B
目录 reproduction/radegs_c2l50_8build_overnight_npr_v01/round07
1. round06 readonly verify及manifest/package检查 -> ROOT/r07_prior_verify.json；读取r06报告、图、git HEAD/status；审计joint renderer/format/ewa/produce与v01calibration。
2. freeze.py -> METHOD/CONFIG/SOURCE/ROLLBACK；全部在新scientific results之前。
3. test_color.py RED→appearance.py GREEN；test_render.py RED→render adapter GREEN；test_protocol.py RED→protocol GREEN。test_runner.py 20pass。
4. review01、CODE_PREEXEC；experiment.py --phase pilot -> logs/pilot.log（FicusDEV三臂）。图审review02；experiment.py --phase fit -> logs/fit.log。
5. 图例校正test_labels.py RED/GREEN与ENGINEERING_LABEL_ADDENDUM（原数据不改）；审6BUILD全图；review03；experiment.py --phase reserved -> logs/reserved.log。
6. EVALUATION_CODE_FREEZE；evaluation.py、audit.py、delivery.py。delivery在跨尺寸overview失败，记录原输出，test_layout RED/GREEN；deliver_repair.py -> logs/delivery_REPLAY.log，只pad。
7. test_runner_final.py -> logs/tests_COMPLETE_GREEN.log：25通过；verify.py --readonly --replay -> REPLAY_CHECK.json；实际图工具检查三scene全部四view及失败crop。
8. reports.py、READMEs、代码secret字面量检查与git diff --check，本地只提交round07；finish.py封存packages/STATUS；final readonly receipt另存ROOT/r07_seal_receipt.json。
未运行r08、NPR、source训练、视频。各unit有SEAL后会先hash再跳过，冻结不能重复写；父级可单独执行verify.py --readonly --replay。源码冻结旧版本保留，显示修复走新wrapper。
''')
 review('06_science_PARTIAL_delivery_GO','实际全图：Ficus DC盆误木条纹减少，为局部实证；test79未知上升，anchor明显退化，同配对数未保证视觉。建筑A失败、头骨局部颅盖覆盖改善不足全主体。全C/D/NPR NOT_RUN。25测试与36/9/36/12独立replay通过，允许封存可看负例与局部进展，不替换原C8或声称可编辑多风格。',[R/'REPORT_ZH.md',R/'delivery/OVERVIEW.jpg',R/'delivery/ficus_pot_FAILURE.jpg',R/'STAGE_GATES.json',R/'REPLAY_CHECK.json'])
if __name__=='__main__':main()
