from env import *
def main():
 replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['shape_replays']==12 and replay['prediction_replays']==12 and replay['match_replays']==12
 rows=json.loads((R/'mechanism_audit/COUNTS.json').read_text());table='\n'.join('|%s|%d/%d|%d|%d|%d|%d|%d|'%(x['view'],x['shape_reliable'],x['mask_pixels'],x['arms']['rgb']['unknown'],x['arms']['rgb_morph']['unknown'],x['arms']['rgb_shuffled_morph']['unknown'],x['arms']['rgb_morph']['different_known'],x['arms']['rgb_morph']['unknown_to_known']) for x in rows)
 gates=dict(overall='NO_GO',engineering='VALID_with_one_explicit_analytic_negative',scenes=dict(scan24=dict(A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',reason='source scene coverage almost whole frame; no subject silhouette input'),scan65=dict(A='PARTIAL_inherited_visual_structure_not_qualified',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',reason='table and skull both covered; alpha morphology cannot separate dark bone/table'),ficus=dict(A='GO_PROXY_inherited',B='NO_GO_precision',coarse='PARTIAL_inherited',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',reason='new descriptor mostly abstains at pot boundary and branches, fails coherent fine parts; no superiority to r05')))
 js(R/'STAGE_GATES.json',gates)
 seen=['figures/ficus/train_r_80/FULL.jpg','figures/ficus/train_r_7/FULL.jpg','figures/ficus/test_r_14/FULL.jpg','figures/ficus/test_r_79/FULL.jpg','figures/scan24/0000/EVIDENCE.jpg','figures/scan65/0000/EVIDENCE.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ficus_train_r_7_FAILURE.jpg','mechanism_audit/FEATURE_OVERLAP.jpg','delivery/OVERVIEW.jpg']
 js(R/'VISUAL_AUDIT.json',dict(inspected_with_image_tool=[dict(path=f,sha256=sha(R/f)) for f in seen],human_GT=False,assessment='same executing assistant qualitative full-frame review',ficus='pot edges and root become UNKNOWN; pot rim may take crown green; crown-internal visible wood not improved; holes retained',scan24='full scene alpha includes white platform and background; not subject shape',scan65='source alpha covers table as well as skull; teeth/posterior loss not solved'))
 cfg=json.loads((R/'CONFIG.json').read_text());cfg['morphology']['frame_guard']='eligible also requires pixel distance to image frame >=4*.04*bbox_diagonal; frozen in METHOD_FREEZE_ZH before results, omitted from compact CONFIG field';cfg['note']='execution inventory, not retuning; original CONFIG+METHOD hashes preserved';js(R/'CONFIG_EXECUTED.json',cfg)
 next_hyp='独立新机制候选：审计冻结source GS的视角相关SH外观是否使盆高光/明暗骨与部件混淆。只读同一CPU renderer可将fullSH颜色与仅SH DC的诊断渲染配对，geometry/cov/filter/opacity/order/background完全相同，先验证alpha/depth不变及RGB fullSH重放，再以同mask/原seed预算比较条件外观与同预算无方向信息对照。DC不是albedo/语义真值，SH也可能补偿错几何；若DC并未改善真实四视角主体/盆木叶，则停止，不用改色伪称NPR成功。首个source-only小帧预算通过才扩展，不能直接赋source角色。本轮仅读renderer的colors/eval_sh实现，未运行任何SH对照。下一resume需重新审计、冻结与TDD；07:40后只收尾。'
 js(R/'NEXT_REVIEW.json',dict(next_allowed=True,next_hypothesis=next_hyp,not_executed=True,reason='independent angular appearance decomposition, not graph/morphology threshold tuning; source renderer actual colors() supports full SH evaluation',source_code=str(JC/'renderer.py'),source_code_sha256=sha(JC/'renderer.py') if (JC/'renderer.py').exists() else None))
 report=f'''# r06：负空间形态证据测试——NO_GO

本轮真实执行后，不建议用新结果替换已有粗分块。Ficus的局部形态可以区分部分厚薄，但在真实投影和不确定边界下，主要增加UNKNOWN，没有更完整地区分盆、木枝、叶冠。建筑和头骨则更早失败：源alpha几乎覆盖全画面，不能给出主体形态。两者只做输入资格负对照，没有强行生成新部件。
这不否定r01/r04/r05已得到的粗结构可读性；目前r04/r05盆体连贯性仍优于本轮。本轮C线边界、D源GS软成员及多风格NPR均NOT_RUN。

## 与前五轮不同的可证伪机制
r05撤回hard seeds后大多仍被图邻域拉回。r06转而增加新图像信息源：**到主体负空间的距离与邻域覆盖程度**，无需C8线、source核ID、height类别位置或新语义模型。先冻结METHOD/CONFIG，TDD后才实际处理三scene各四相机。几何/线资产及检测/采样均不变。
对保留孔洞的mask下界L和含unknown上界U，以候选bbox对角线D归一：F(M)=[min(EDT(M)/(.04D),1), G_.01D*M, G_.04D*M]。用上下界中点，并以最大差<=.10和完整4sigma画内邻域判形态可用。否则该像素仍保留，回退原RGB条件外观；没有删薄叶或补孔。EDT不是物理厚度，occupancy不是密度，视角改变可使同枝/同叶的值变化。
三臂同一原r03粗代理seed，每view每类2048：rgb（精确复算旧r03）、rgb_morph、rgb_shuffled_morph（每view全seed形态向量与资格同排列，原RGB/label不变）。外观16³、形态8³直方图，固定sigma.75；按view和class等质量，条件密度相乘，max posterior .65、margin .2与本类5%训练密度门。没有graph/hard clamp。所谓posterior只是该密度模型结果，不是校准语义概率；RGB与形态独立乘积是假设，训练label还带粗高度偏差。
随机null保留同一形态边际与seed预算，但可用形态seed的各类数量自然变化，因此不是逐类可用样本完全相同；分别存计数。r05图方法与v02 RGB-only另作强只读参考，不能只与弱基线比。原RGB配对输出12项native数组核验与r03完全相同。

## Ficus：新信息覆盖有限，精确部件门未过

|视角|形态合格/主体|RGB未知|形态未知|随机形态未知|已知→另一已知|未知→已知|
|---|---:|---:|---:|---:|---:|---:|
{table}

形态训练可用seed：DEV盆/木/冠=2048/1245/149，AUX=2009/630/308，各原本2048。细叶边界在lower/upper覆盖中不稳定；不能为了更多可用率降低门。DEV形态合格只覆盖原RGB冠标签2662/33357像素，因此新线索大多不能替冠内木作判别。种子形态分布的Bhattacharyya重叠：盆-木.360、盆-冠.406、木-冠.719；打乱后约.998–1。这证明形态与代理类有关，但不证明与真实语义一致，木/冠仍明显重叠。
实际四幅全图：train80盆边灰、主干根部未知，盆沿还局部变绿；train7高光木色条纹保留，冠内木几乎未恢复；test14仍有盆面条纹并增加灰边；test79土面错误木色变UNKNOWN，这是有用的拒绝，但真枝根也同时灰，不能称精确盆/木分割已解决。叶间空洞和完整输入mask原样保留；灰色代表拒绝，不能被误读成对象不存在。
同一可见性规则的双向区域资格配对（DEV到AUX/test14/test79）：RGB=1/2/2，形态=1/2/1，随机=1/1/2，r05=2/2/2。形态在test79丢木类配对。盆类仍无足够共同可见资格，不能将遮挡当负票。每个方法区域分母随预测改变，详表保留分母、unknown和depth-cycle状态；这些不是GT正确率/同墨量指标，更不能由配对数证明语义成功。

## 建筑和头骨：明确识别信息前提失败
scan24 0000/0012的451437个像素全有有效scene coverage；scan65 0012也是451437/451437。新距离图几乎只有矩形画框，反映整场景覆盖，不是屋顶/立面或颅骨外形。0024/0036虽有空白/unknown，也只是画外与全scene缺观测，不能隔离平台或桌面。
因此实际产出8张DTU形态测量和12张全scene证据板中的对应项，但**0张DTU新部件预测**。建筑A NO_GO；头骨保留既有暗骨覆盖改善的PARTIAL事实，严格主体门仍不通过。后续B/C/D全部NOT_RUN，不用旧color标签改标题充新实验。

## 工程、测试与资料边界
本轮3个垂直API先实际RED（模块缺失）再实现：形态、条件密度、协议。最终19个用例中18通过、1个明确expected negative。初始解析测试错误地期待小尺度occupancy在宽叶与厚盆中心仍严格不同，实际两者都饱和。原fixture/失败日志和不等式完整保留，登记expectedFailure；没有改特征、fixture数值或容差，另测预冻大尺度有区分并显式测试小尺度相等。不能把这一负例计入18通过，也不宣称所有形态辨识断言成功。最初freeze仅因runner已建立空r06目录失败，空目录实查后修复前置条件，未读新科学结果。
CONFIG的简写eligibility字段未包含frame guard；完整中文METHOD在结果前已预冻该guard，CONFIG_EXECUTED逐项补记，原CONFIG/METHOD哈希不改。源数据精度未降。形态计算及RGB重放均精确可复算，新增输出为2D证据，不是持久3D部件。
三scene×4=12形态单位；Ficus3臂×4=12原尺寸预测、3密度文件、12双向方法/相机检查。readonly replay重算12形态、3模型、12推理、12匹配和机制统计，数组完全一致。来源{replay['source_files']}个文件、旧main893 Python及12相关工作树HEAD/index/status核验保持；原source/C8/joint不改。CPU2、无GPU/新模型下载/训练/mesh。完整shape上下界保留，不把shape proxy当RaDe或GT。
所有相机历史曝光；DTU也是源GS训练视角。Ficus是vanillaGS+CPU条件plane camera-z代理；DTU源nativeRaDe。原C8线和真正joint只读参考来自先前CPU fullSH/EWA统一排序，非官方CUDA等价；本轮没有重新渲染joint、视频或写风格模型。彩色分块只是诊断覆盖，与真正joint图严格分开。

## 下一轮审查建议（未执行）
{next_hyp}

此建议不构成本轮执行，更不能据此报告SH实验结果。runner需下一次resume；本次封存r06后退出。全夜最多07:40开始终验、08:00停止。
'''
 (R/'REPORT_ZH.md').write_text(report)
 (R/'FORMAT_ZH.md').write_text('''# r06格式与复现边界
shape/<scene>/<view>/FEATURES.npz：candidate/subject_unknown原mask，feature/lower/upper H×W×3 float64，spread/eligible/frame_unknown；bbox_diagonal仅图像尺度。DTU为scene coverage，禁止当主体。
models/<arm>：两BUILD原UV、原代理labels、原/打乱形态和可靠性，MODEL条件密度/门；rgb臂也存未使用形态密度以保持同fit预算，实际use_shape=False。
inference/ficus/<arm>/<view>/RESULT.npz：labels0unknown、1pot-prior/2wood-prior/3crown-prior，probability非校准语义概率，source_uv为像素不是sourceGS ID，morphology_used可核对fallback。三场景源GS/线GS无新成员、没有新PLY或joint模型。
evaluation：冻结真实depth/camera的双向采样状态、计数与region分母。STATE值继承geometry.py，画外/遮挡/未知不能作负票。
安全归档members统一{members:{relative_path:{sha256}}}，不含原GS/env/凭据、链接或绝对路径。verify.py --readonly --replay只读取，重放stdout需由调用者写入本任务新文件；不可覆盖既有sealed receipts。
''')
 (R/'RUN_COMMANDS.md').write_text('''# 本轮实际执行顺序
解释器 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B
代码目录 reproduction/radegs_c2l50_8build_overnight_npr_v01/round06
1. round05/verify.py --readonly -> ROOT/r06_prior_verify.json；查看r05状态/报告/图，git只读。
2. round06/freeze.py（第一次empty-dir assertion失败，修复后执行），产生METHOD与CONFIG，在结果前。
3. test_shape.py RED；实现后发现保留的小尺度饱和负例；test_likelihood.py RED/GREEN；test_protocol.py RED；test_runner.py -> logs/TEST_GREEN.log。
4. review01、CODE_PREEXEC封存；experiment.py --phase fit -> logs/FIT.log。
5. 实际图检查、review02；experiment.py --phase reserved -> logs/RESERVED.log。
6. evaluation.py、audit.py、delivery.py -> 对应logs；verify.py --readonly --replay -> REPLAY_CHECK.json。
7. reports.py、本地commit新round06代码，finish.py封存；final verify结果写 ROOT/r06_seal_receipt.json。
CPU affinity [0,1]、数值线程2，禁止旧目录写入；所有大型数据本任务HDD。
重启run检查SEAL哈希后跳过；已存在MODELFREEZE不能重新freeze。未运行第7轮。
''')
 review('03_visual_NO_GO_delivery_GO','实际全图和固定坏例已看：新形态未优于paired RGB或r05，主要增加UNKNOWN；test79木配对丢失。DTU主体资格不成立。封存负结果与可重放证据，禁止C/D/NPR升级。下一新机制仅提议source SH角度外观分解，未执行。',[R/'REPORT_ZH.md',R/'delivery/OVERVIEW.jpg',R/'STAGE_GATES.json',R/'REPLAY_CHECK.json'])
if __name__=='__main__':main()
