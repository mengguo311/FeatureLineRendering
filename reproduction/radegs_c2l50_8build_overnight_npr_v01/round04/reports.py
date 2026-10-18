from env import *

def main():
 replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert [replay[k] for k in ['graph_replays','target_replays','native_arrays_checked','match_replays']]==[12,24,48,24]
 counts=json.loads((R/'COUNTS.json').read_text());diffs=json.loads((R/'delivery/ARM_DIFFERENCES.json').read_text())
 gates=dict(overall='PARTIAL',scan24=dict(A='NO_GO',benefit='coherent brick/roof appearance',failure='roof/platform/background share label; dark background enters central class',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'),scan65=dict(A='PARTIAL',complete_subject_precision='NO_GO',benefit='cap/jaw and many shadow areas more continuous',failure='0036 teeth and dark posterior bone remain background-like or UNKNOWN; holes ambiguous',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'),ficus=dict(A='GO_PROXY_INHERITED_UNCHANGED',B='PARTIAL',B_precision='NO_GO',benefit='pot highlights partly corrected; disconnected leaves gain evidence',failure='soil assigned wood; crown-internal wood absorbed by crown; pot common visibility insufficient',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'),engineering=dict(first_large_unsealed_solve='STOPPED_BUDGET_INVALID',repair='SAME_SYSTEM_ORIGINAL_TOLERANCES_PASSED',not_new_scientific_round=True))
 js(R/'STAGE_GATES.json',gates);js(R/'SOURCE_ROLE_STATUS.json',dict(status='NOT_RUN',reason='Precise subject/part gates did not pass; frozen round stops before C/D',source_kernel_memberships=0,line_memberships=0,new_gaussians=0,styles=0,original_C8_untouched=True))
 images=['figures/ficus/train_r_80/FULL.jpg','figures/ficus/train_r_7/CONTROLS.jpg','figures/scan24/0000/FULL.jpg','figures/scan24/0024/CONTROLS.jpg','figures/scan24/0036/FULL.jpg','figures/scan65/0000/FULL.jpg','figures/scan65/0036/FULL.jpg','figures/ficus/test_r_14/FULL.jpg','figures/ficus/test_r_79/CONTROLS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/OVERVIEW.jpg','delivery/ficus_train_r_80_FAILURE.jpg','delivery/ficus_train_r_7_FAILURE.jpg','delivery/scan65_0036_FAILURE.jpg','delivery/SEEDS_train_r_80.jpg']
 js(R/'VISUAL_AUDIT.json',dict(inspected_with_actual_view_image=[dict(path=p,sha256=sha(R/p)) for p in images],reviewer='same execution context; qualitative assessment, no manual GT',judgment=gates))
 nxt='若另次resume且仍早于07:40，先核验r04，再冻结“可否撤回被另一构建视角独立外观证据反驳的代理硬种子”这一新机制。r04中Ficus 81/113个原外观木类seed被冠硬约束覆盖，表明有可证伪的先验冲突；它不是GT错误数。用leave-one-build-view-out模型判冲突，只取消该硬约束、不把像素直接改成外观类别、不改图/平滑强度/拒绝阈值/原C8；比较原硬种子、同预算随机撤回、跨view冲突撤回，检查冠内木干是否恢复而盆亮纹/土不恶化。仅BUILD决定种子资格，reserved没有新种子。若独立模型无法支持冲突，则NO_GO/STOP，不靠减UNKNOWN成功。DTU种子语义问题仍可能无法辨识，勿把该机制许诺为自动主体分割；其A不过就不启动B/C/D。此建议本轮未执行，亦未允许正式NPR跨过上游门。'
 js(R/'NEXT_REVIEW.json',dict(next_allowed=True,next_hypothesis=nxt,reason='specific observed hard-prior versus accepted-appearance conflict; withdraw unsupported assumption rather than retune graph strength',not_executed_this_round=True,deadline_jst='2026-10-19T07:40:00+09:00'))
 rows=[]
 for v in views('ficus'):
  d=next(x for x in diffs if x['scene']=='ficus' and x['view']==v);q=next(x for x in counts['rows'] if x['scene']=='ficus' and x['view']==v and x['arm']=='coupled');rows.append(f"| {v} | {d['r03_unknown']} | {d['r04_unknown']} | {q['old_r03_known_both_changed']} | {d['comparisons']['no_cross']['both_known_class_difference']} |")
 table='\n'.join(rows)
 (R/'REPORT_ZH.md').write_text(f'''# r04：外观与合格邻接联合，分块更连续，但错误先验也会扩散

**本轮PARTIAL。** 真正执行了三场景、四固定视角、四臂，48张原尺寸分类输出。Ficus叶片覆盖和盆体连续性、头骨颅盖及下颌覆盖都有可见进步；与此同时，Ficus盆土仍归木干、冠内木枝被并入冠层，头骨弱视角牙齿和暗骨仍缺失，建筑屋顶/背景不能分开。当前最有用的是Ficus粗分块和头骨的局部主体候选，尚不足以把全模型按精确部件做正式多风格NPR。原C8及source+ink模型完全保留，未修改/删除/重采样高斯。

## 先前最早失效的假设，以及本轮新变量
r02的纯图传播被无种子分量限制；r03非局部RGB条件证据补回叶片，却把盆亮纹看作木干。r04先核验r03封存、源码和实际图，再冻结同一个screened harmonic图：邻接维护连续性，外观给断连区域证据。不是改K或再调阈值，也不是把C8投影八次算八票。原C8仍为8BUILD资产，本轮区域推理只使用DEV+AUX两张实际source图构建，再固定推理两个reserved图。

能量为 `Σ w_ij ||q_i-q_j||² + Σ γ_i ||q_i-u_i||²`，构建种子固定onehot。u直接读取r03 pooled_rgb的冻结后验，只有r03已经通过外观拒绝门的像素才给一元精度；γ=`max(weighted_degree,1) × (qmax-qsecond)/(4×5²)`。5px为冻结解析扩散尺度，并非真实物理半径。局部4邻接需世界距离≤4p，p=z/sqrt(fx fy)；跨view仍depth≤2p、cycle≤1.5px、world≤3p，遮挡/画外不负票。目标图没有新高度/人工种子，不回写构建模型；其本身RGB只用于固定推理，加上合格构建概率回投。输出仍max≥.65、margin≥.2；没有任何锚的分量UNKNOWN。传播后的标签不重新套r03单像素density拒绝门，此点在新结果前已冻结。

理论沿用前轮已核验作者全文：[Grady2006 seeded Laplacian](https://leogrady.net/wp-content/uploads/2017/01/grady2006random.pdf)及[GrabCut条件外观](https://pub.ista.ac.at/~vnk/papers/grabcut_siggraph04.pdf)。这里的screening、跨view资格和自动代理种子是自定义组合，既非论文完整复现，也不继承自动语义质量保证。已保存正文在r02/r03 literature并纳入来源hash；本轮无新模型下载。

四臂使用相同原尺寸RGB/depth/alpha、相机、代理种子和外观模型：coupled完整联合；no_cross只移除**构建图**跨边，目标仍可从两个独立构建图转移；geometry_pair去成对RGB权但仍有外观一元，且按同一公式重算degree相关γ，不能叫完全无颜色或单独固定γ的消融；unary_seeded无图边，保留同一hard seed夹持，目标则只原外观。r03本身不夹种子，所以单看r03→r04不能把全部变化归因邻接；unary_seeded专门揭示该差异。另列r01/r02及v02 RGB-only K3强基线，旧图明确标只读对照。

## Ficus：覆盖与连续性改善，精确身份仍失败
实际检查四张全图、test_r_14长刺参考、冠内部枝条及盆面放大。新方法补回许多原来灰色叶片，叶间原负空间mask逐像素保留；裸露主干仍连贯。盆高光的橙色条纹明显缩小，未完全消失。test_r_79土面几乎整片变橙色木干；冠内一部分可见木枝从r03橙色变绿色。更一致的颜色既可能是改善，也可能是错误先验传播，不能拿更少UNKNOWN当正确率。

| 相机 | r03 UNKNOWN | r04 UNKNOWN | 双方已赋类但类别改变 | 去构建跨边后双方已赋类改变 |
|---|---:|---:|---:|---:|
{table}

所有数字仅是同一mask内像素诊断，无GT accuracy/precision。去跨view边后，四图类别变化只有196/25/69/123；去成对颜色后为29/28/214/40，多数变化涉及UNKNOWN覆盖。完整联合、no_cross、geometry_pair都得到木/冠两对相互配对；r03在DEV↔AUX只有木干一对，两个reserved各两对。说明局部连续性与一元互补有实际作用，但没有证据称跨view边独自纠正了大规模身份。

盆的共同可见资格仍不足：DEV→AUX只119/1233点合格、反向113/1208，低于冻结20%；已合格点虽大多同类也不能绕过分母。两个reserved盆同样不达门，不能把遮挡当反对票，也不能用少数同色点认证整盆稳定。该配对按各臂当前区域定义分母，已知覆盖不同，绝非相同GT采样上的准确率比较；原输入预算与4像素采样网格一致，分母/UNKNOWN全部保留。

## 原因审计：hard seed并不等于真标签
两构建图各6144个Ficus seed，来源是r01粗层中部，不是语义标注。与r03已接受外观相冲突的seed为99/132个；其中81/113个外观木类被硬性要求为冠类。图求解按定义无法推翻这些标签。`unary_seeded`与coupled在seed处都保持硬类别，构成这一约束影响的直接对照；但外观也会错，231个冲突**不是231个GT错误**。当前只证明存在不可纠正的假设冲突；冠内木干变绿的所有传播范围不能仅靠这些计数作因果认证。SEED_CONFLICTS、原尺寸seed图及冠内放大保留证据。

## 建筑与头骨分别判定
scan24四图墙面/屋顶的材料分块更平滑，然而蓝色同时含屋顶、窗白框、地台和白背景；0036黑背景部分甚至成为橙色中央类。主体A **NO_GO**，不能把两个颜色改名成“屋顶与墙体”绕过背景错误。B/C/D不运行。
scan65四图较r03有真实改善：颅盖、鼻面、下颌大部分更连续，桌面噪点减少。但0036牙齿和后侧暗骨仍是蓝/灰，0012和0024牙列/眼眶内部也有未决位置。某些黑处可能是合法孔洞，某些是暗骨，仅凭当前代理不能逐处认证。A的局部视觉结果 **PARTIAL**，完整主体精度门仍 **NO_GO**，未据此切颅/面颌或制作风格。改善不是零，尚未满足正式分组条件。

## 工程INVALID如何处理
首次scan24大图未封存求解运行约11分钟，SIGINT未返回后只终止本任务PID，保留失败日志、停止记录和原coupling源码SHA；没有足够堆栈证据确认卡在哪个C函数。修复仍求同一A/rhs，所有图、种子、容差不改：>30万节点的CG数值解先作概率初值投影，再校验原残差；需要时最多5000步同矩阵Jacobi修复，否则INVALID。小Ficus沿原LU路径并保留原封存结果。原METHOD/CONFIG不篡改，另存ENGINEERING_SOLVER_AMENDMENT。
修复后scan24联合构建实际92.48秒、scan65 50.50秒；36个完成单元累计求解时间{counts['total_solve_seconds']:.2f}秒（不含第一次中止、文件压缩、制图和重放）。7个小系统走原LU，17个大系统走同矩阵修复；原相对残差1e-8和概率1e-5门没有放宽。概率范围使用±1e-5；行和检查沿用numpy allclose的atol1e-5加默认rtol1e-5（在1处合计2e-5），最终输出仍逐行归一。NUMERICAL_CONTRACT记下实际API口径，未在修复时改容差。数值可计算并不代表语义成功；也不声称未完成旧大LU与新解bitexact。当前代码独立重放才是本轮数组精确复现标准。

## 实际输出与下一轮资格
12构建图模型、24reserved推理、48原尺寸输出、24双向方法对照及全frame/失败图真实存在。DTU 777×581原native RaDe camera-z；Ficus800×800 vanillaGS+CPU covariance-plane depth代理；完整fx/fy/cx/cy/W2C保留，单位非米。所有视角历史曝光，DTU是source GS训练图，不叫blind。Ficus主体mask沿封存proxy不变，DTU全scene alpha不是主体mask。
原C8 line-only为xray参考；TRUE joint列为旧CPU fullSH/EWA统一source+ink排序，非RGB×ink，亦非官方CUDA等价。新颜色列只是图像诊断，未生成source_index成员、线归属、GS模型、视频或NPR样式，均0/NOT_RUN；原模型仍是回退入口。q最大值是代理模型数值置信，不是校准语义概率。

本轮23个新测试（18行为+5同矩阵数值修复）真实RED/GREEN及回归通过；只读精确重放12图模型、24目标推理、48原尺寸输出检查、24配对，{replay['source_files']}来源SHA和旧893 Python/12工作树HEAD/index/status未变。详见REPLAY_CHECK、TEST_RESULTS、COUNTS、GATES、RUN_COMMANDS。包使用安全相对路径members+SHA，runtime文件与ASTRA_FINAL分离。

允许另次resume提出一项不同机制：用另一构建视角的独立条件外观证据检验代理seed的可信性，对被明确反驳者撤回硬约束，**不直接改成外观标签**；与随机撤回的同预算对照比较，检验冠内木干是否恢复且盆/主体不恶化。它是对先验不可推翻这一假设的证伪，不是再次调平滑权重；外观反驳仍非GT，若无独立证据则STOP/NO_GO。该实验本轮未执行，C/D/NPR不能借此越门。本invocation只封存r04并退出；07:40收尾/08:00截止不变。
''')
 (R/'RUN_COMMANDS.md').write_text('''# r04 actual execution
CWD /home/u00134/3dgs_line/gaer_c2l50_8build_overnight_npr_v01
Read-only Python /mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B
New code prefix reproduction/radegs_c2l50_8build_overnight_npr_v01/round04

1. round03/verify.py --readonly -> ROOT/r04_prior_verify.json; HEAD/status/diff and real report/images read.
2. freeze.py; METHOD/CONFIG/source/rollback/resource frozen before scientific output.
3. test_coupling.py RED/GREEN8; test_graph.py RED/GREEN6; test_output.py RED/GREEN4.
4. experiment.py --phase fit --scene ficus -> logs/FIT_FICUS.log; actual DEV/AUX viewed.
5. experiment.py --phase fit --scene all -> logs/FIT_ALL.log; first unsealed large solve stopped (owned PID only), engineering receipts preserved.
6. test_solver_repair.py RED/GREEN5; ENGINEERING_SOLVER_AMENDMENT; same command -> logs/FIT_ALL_REPAIR.log, actual exit0; sealed Ficus skipped.
7. python -m unittest discover -s round04 -p 'test_*.py' -v -> logs/REGRESSION_23.log (exit0).
8. experiment.py --phase reserved --scene all -> logs/RESERVED.log (exit0); evaluation.py -> logs/EVALUATION.log; delivery.py -> logs/DELIVERY.log.
9. verify.py --readonly --replay -> REPLAY_CHECK.json, stderr logs/REPLAY.stderr. reports.py writes reports only after successful replay.
10. local commit only round04 using git add --sparse; finish.py -> ROOT/r04_seal_receipt.json, safe archives and final readonly check.

Independent readonly replay:
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B reproduction/radegs_c2l50_8build_overnight_npr_v01/round04/verify.py --readonly --replay`
It never writes sealed outputs. Checked units skip production reruns. No source-GS training/GPU/mesh/model download/other agent or next round executes.
''')
 review('06_science_PARTIAL_delivery_GO','已真实检查三scene各四完整视角及负例。Ficus盆/叶覆盖改善，冠内木干与土错误保留；头骨主体更完整但0036牙齿/暗骨仍缺，建筑A失败。跨view边消融显示多数作用在覆盖，不认证大规模身份纠错。23新测试与readonly全部精确重放及旧树/source核验已通过；允许本轮PARTIAL封存，C/D/NPR仍NOT_RUN。下一轮仅可另次resume预冻代理seed可靠性证伪，不在本次执行。',[R/'REPLAY_CHECK.json',R/'delivery/ARM_DIFFERENCES.json',R/'delivery/SEED_CONFLICTS.json',R/'VISUAL_AUDIT.json',R/'STAGE_GATES.json'])
if __name__=='__main__':main()
