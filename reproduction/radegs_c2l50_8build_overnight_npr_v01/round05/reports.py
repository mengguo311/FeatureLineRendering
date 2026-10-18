from env import *
def main():
 replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['graph_replays']==6 and replay['target_replays']==12 and replay['native_arrays_checked']==24 and replay['match_replays']==9 and replay['crossfit_replays']==6
 counts=json.loads((R/'COUNTS.json').read_text());diff=json.loads((R/'delivery/ARM_DIFFERENCES.json').read_text());audit=json.loads((R/'mechanism_audit/COUNTS.json').read_text())
 tests=[]
 for name,n in [('01_policy',5),('02_random',4),('03_binding',5),('04_integration',4)]:
  red=R/'logs'/(name+'_RED.log');green=R/'logs'/(name+'_GREEN.log');assert f'Ran {n} tests' in red.read_text() and 'FAILED' in red.read_text() and f'Ran {n} tests' in green.read_text() and '\nOK' in green.read_text();tests.append(dict(behavior=name,new_tests=n,red=dict(path=str(red.relative_to(R)),sha256=sha(red)),green=dict(path=str(green.relative_to(R)),sha256=sha(green))))
 assert 'Ran 18 tests' in (R/'logs/REGRESSION.log').read_text() and '\nOK' in (R/'logs/REGRESSION.log').read_text()
 js(R/'TEST_RESULTS.json',dict(new_tests_passed=18,vertical_slices=tests,inherited_r04_tests=23,inherited_tests_not_recounted=True,core_files_bitexact='CORE_COMPARE.json',regression='logs/REGRESSION.log',exact_replay='REPLAY_CHECK.json'))
 gates=dict(overall='NO_GO',mechanism='executed seed-withdrawal intervention, not sufficient precision benefit',engineering='GO_EXACT_REPLAY',scan24=dict(A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',failure='roof/platform/whitebackground same class, dark background central class'),scan65=dict(A='PARTIAL_INHERITED',complete_subject_precision='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',failure='0036 dark bone/teeth remain UNKNOWN or background-like; cavities ambiguous'),ficus=dict(A='GO_PROXY_INHERITED_UNCHANGED',B='PARTIAL_INHERITED',B_precision='NO_GO',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN',failure='crown wood remains crown; soil wood and pot highlight errors remain; no new mutual pair'))
 js(R/'STAGE_GATES.json',gates)
 nxt='若下一次resume仍早于07:40，先核验本轮，再考虑不同信息源：source-only主体负空间/局部投影厚度的形态证据能否补足纯RGB条件外观，而非继续调图平滑或撤seed比例。先做解析同色细枝/宽叶/厚盆及真实Ficus两个BUILD的无图条件证据pilot；使用固定r03代理seed和相同类别/像素预算，比较RGB-only、RGB+预冻尺度归一形态描述、打乱形态的null，不改C8/原GS，不把厚度直接当部件标签，不看reserved选特征。视角改变会改变投影宽度，必须预冻跨view可见性及拒绝门，薄叶/枝不能靠被删而成功。DTU全scene alpha不是主体，若其形态输入不合格只保留A负对照，不强行套Ficus成功；先审计是否有真实独立可识别信息，若无则STOP。这是新候选研究机制，未执行、未授予精确分块或NPR资格，下一轮还须真实评估冻结。'
 jst=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)));allowed=jst.hour<7 or (jst.hour==7 and jst.minute<40)
 js(R/'NEXT_REVIEW.json',dict(next_allowed=allowed,next_hypothesis=nxt,not_executed=True,deadline_jst='2026-10-19T07:40:00+09:00'))
 seen=['delivery/OVERVIEW.jpg','figures/ficus/test_r_14/FULL.jpg','figures/ficus/train_r_7/FULL.jpg','figures/scan24/0000/FULL.jpg','figures/scan65/0000/FULL.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ficus_train_r_7_FAILURE.jpg','delivery/ficus_test_r_14_FAILURE.jpg','delivery/scan65_0036_FAILURE.jpg','delivery/scan24_0036_FAILURE.jpg','delivery/MECHANISM_COUNTS.jpg']
 js(R/'VISUAL_AUDIT.json',dict(actual_tool_inspected=[dict(path=f,sha256=sha(R/f)) for f in seen],judgement='same executor qualitative assessment, not blind or semantic GT',negative_findings=gates))
 table='\n'.join('|'+r['scene']+'/'+r['view']+'|'+str(r['r04_unknown'])+'|'+str(r['arms']['withdraw_conflict']['unknown'])+'|'+str(r['arms']['withdraw_conflict']['both_known_change'])+'|'+str(r['arms']['withdraw_random']['both_known_change'])+'|' for r in diff)
 aa=[r for r in audit if r['arm']=='withdraw_conflict'];seedtable='\n'.join(f"|{r['scene']}/{r['view']}|{r['withdrawn']}|{r['final_original']}|{r['final_other']}|{r['final_unknown']}|" for r in aa)
 (R/'REPORT_ZH.md').write_text(f'''# r05：撤回错误先验的硬约束，仍不足以获得精确部件

**科学结论NO_GO，工程执行及精确重放通过。** 本轮真正完成三场景、四固定历史视角、两新臂，24张原尺寸标签输出；并非把r04图换标题。冲突撤回比同预算随机撤回确实引起更多变化，但关键部件误分没有得到足够视觉改善。不建议用它替换当前粗分块，更不应据此进入正式多风格NPR。r04已有的叶片覆盖、盆/裸干粗结构与头骨主体局部改善仍保留，NO_GO只针对本轮精度改进假设。

## 只改变硬约束资格，独立性有边界
r04图中粗代理种子无法被推翻；Ficus冠内木枝被冠种子压住是实际可见问题。本轮在新结果前冻结：对构建图v，读取仅在另一构建图w拟合的r03条件颜色模型，检查v原seed的RGB。已通过原概率/密度门且预测不同才撤回；UNKNOWN不反对。撤回只将硬seed置0，像素仍在图中，不直接改成外观预测，不删原线/原GS。
另一臂每scene/view/原类别以PRNG1729随机撤回相同数量，可自然与冲突集合重叠。原r04 coupled为只读baseline。两个新臂的图边、权重、外观一元、gamma、mask、原source/camera全部保持；新图与r04的i/j/weight/gamma/prior/view_offsets逐数组exact核验。目标视角无新seed、不回馈构建图；构建结果改变会通过同一投影资格与已知门影响目标soft prior，此为同一干预的下游作用，不是独立新算法。
“独立”仅指反驳模型的训练图不同，不是新的语义标注或独立源GS。两图仍共享原GS与粗代理偏差；真正图求解的一元沿r03 pooled模型，含本图，不能把整个算法说成leave-one-out。6个other-view模型预测从原RGB/seed独立重算exact，证实来源没有混用目标训练。
理论沿用已核验的[Grady2006图推理](https://leogrady.net/wp-content/uploads/2017/01/grady2006random.pdf)与[GrabCut条件外观](https://pub.ista.ac.at/~vnk/papers/grabcut_siggraph04.pdf)。跨view撤回规则是本任务自定义证伪，不继承论文的语义准确性保证。

## 真正干预到了求解，但多数冲突仍被环境支配
以下只统计被定向撤回的原seed像素，不是GT错误数，也不代表正确率：

| 场景/构建图 | 撤回 | 最终仍原类 | 改为其它已知类 | UNKNOWN |
|---|---:|---:|---:|---:|
{seedtable}

Ficus共430个冲突seed：355仍原类，15改类，60 UNKNOWN。不是撤回失败或seed偷偷保留：所有这些硬约束已为0，真实方程重放确认。其自由节点满足 `q=(Σw·邻居q+γ·外观先验)/(degree+γ)`；两Ficus图γ占比分位数中位为0和0.00457。239/430个点在原pooled外观门下本来UNKNOWN，只有191提供已接受其它类的一元；空间/跨view邻接因而常把它们带回旧类。该局部平衡是数值证据，不是说所有邻居都错或简单增γ就能解决。建筑0024还有108个独立反驳seed被pooled一元支持原类，显示不同view颜色证据本身也矛盾。
同预算随机撤回的Ficus430点中只有1个改已知类、10个UNKNOWN。定向规则确有选择性作用，不能因此推导作用方向符合真实部件。MECHANISM_COUNTS图给出三scene两对照，完整节点UV、原标签、预测、邻居概率和一元比例在mechanism_audit，平衡及全部数组可重放。

## 全图与弱视角结论
Ficus四图主体、裸干和叶间负空间mask未变；几乎没有恢复足够的冠内木干。train_r_7/test_r_14放大里绿色冠仍盖住木枝，盆亮纹仍有橙色，test_r_79土面仍归木。新的UNKNOWN略增，不能把更谨慎叫更准确。两新臂和r04在DEV↔AUX、DEV↔两个reserved仍只得到木/冠两对；盆仍因共同可见覆盖不足未获资格，没有新增稳定部件。遮挡不是负票；区域分母按各臂当前标签定义，配对数字不是等GT区域准确率。
建筑墙面/材料色块保持连贯，但屋顶、白窗框、白地台和背景仍同蓝类；0036黑背景仍大片橙色。0000周围零碎误类减少，未解决完整主体A，B/C/D不运行。头骨大部分颅盖/鼻面/下颌依旧连贯，背景少数点变化；0036牙列、后侧暗骨仍灰/蓝，0024眼眶内灰区增多。黑孔和暗骨无法逐处认证；A局部能力仍PARTIAL，完整主体精度NO_GO，不切颅/面颌。

下表只作变化诊断，不给precision/accuracy：

| 场景/视角 | r04 UNKNOWN | 定向撤回 UNKNOWN | 定向双方已知改类 | 随机双方已知改类 |
|---|---:|---:|---:|---:|
{table}

所有24输出固定原图尺度/显示规则，无ROI筛选/每图调色。完整source/C8/TRUE joint参照见figures，四视图总览及继承r04失败crop见delivery。颜色是诊断代理，不是语义GT或源GS分组。原C8固有长刺依然在参照中，未被隐藏、裁切或修复。

## 实际边界、工程与交付
DTU777×581为官方native RaDe camera-z；Ficus800²为vanillaGS+CPU covariance-plane深度proxy。完整fx/fy/cx/cy及W2C不变，非米。构建使用0000/0024或train_r_80/train_r_7，保留0012/0036或test_r_14/test_r_79；全历史曝光，DTU还是sourceGS训练图，不能称blind。C8仍原arms/C八BUILD，区域推理仅两BUILD实际图，不能声称新八视角融合。
原joint参照是旧CPU fullSH/EWA统一排序，非RGB×ink、非官方CUDA等价；本轮没有新joint渲染/模型/视频，也没有source_index或line group样式。C/D/NPR均NOT_RUN，避免在失败上游做漂亮风格演示。原source/线核所有属性保持原样。
本轮18个新测试四次真实RED→GREEN与回归通过；旧23测试仅继承引用，不重算新测试数。5核心文件SHA与r04完全相同，CG/同矩阵修复原容差未放宽。6构建图、12目标图、24原尺寸结果、9双向对照、6个other-view模型及6组机制审计均readonly精确重放。{replay['source_files']}个来源文件、旧893 Python及12工作树HEAD/branch/index/status未变。生产18求解单元累计{counts['total_solve_seconds']:.2f}秒，不含压缩/制图/重放。
包PREVIEWS与DELIVERABLE采用安全相对成员与SHA；RUN_COMMANDS/FORMAT/COUNTS/GATES/CODE_FREEZE可独立追溯。没有用新manifest掩盖旧失败。

## 后续资格，本轮不执行
仅撤回少量种子不足，继续调撤回比例或γ没有新证据。本轮允许另次resume评估一个不同信息源：source-only负空间/局部形态厚度能否补足单像素RGB，先做同色不同形状解析与小Ficus可拒绝条件证据，对照RGB-only和打乱形态，杜绝按位置直接命名部件。投影形态本身随view变，可能再次NO_GO；DTU主体mask不合格时不能套用Ficus结论。具体方案必须下一轮另冻，本轮没有执行，不保证有足够信息。07:40起收尾、08:00截止，本次r05封存后退出。
''')
 (R/'RUN_COMMANDS.md').write_text('''# 实际命令（在隔离worktree，旧env只读，-B）

解释器 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python；代码 reproduction/radegs_c2l50_8build_overnight_npr_v01/round05。

1. round04/verify.py --readonly → ROOT/r05_prior_verify.json（旧seal/package/source核验）。
2. round05/freeze.py → METHOD/CONFIG/SOURCE/rollback。
3. test_policy.py、test_random.py、test_binding.py、test_integration.py：每slice真实stub RED后最小实现GREEN；logs/01..04保留。test_runner.py回归18个distinct新测试。
4. experiment.py --phase fit --scene ficus → logs/PILOT.log。
5. 实际view_image检查后 experiment.py --phase fit --scene all → logs/BUILD_ALL.log；Ficus已seal跳过，其它scene执行。
6. 实际全图检查后 experiment.py --phase reserved --scene all → logs/RESERVED.log。
7. audit.py → logs/AUDIT.log；evaluation.py → logs/EVALUATION.log；delivery.py → logs/DELIVERY.log。
8. 实际四视图/失败crop检查后 verify.py --readonly --replay → REPLAY_CHECK.json（stderr单独日志）。
9. reports.py；本地只stage本round05源码后commit，不push/merge；finish.py归档、成员及最终readonly验证 → ROOT/r05_seal_receipt.json。

独立只读复核：python -B round05/verify.py --readonly --replay。该命令不写封存文件；stdout请写到封存目录外。已有计算单元按SEAL hash复核后恢复，不依赖文件数。生产CODE_PREEXEC校验，core5文件继承exact；图/一元数组另与r04 exact比较。
''')
 review('05_delivery_GO','科学精度NO_GO已保留完整负例；readonly exact重放6图/12目标/24原尺寸/9配对/6crossfit/6审计通过，旧source及worktree核验通过。允许本地commit、安全归档和r05终态，不允许NPR或本次r06。',[R/'REPLAY_CHECK.json',R/'REPORT_ZH.md',R/'TEST_RESULTS.json'])
if __name__=='__main__':main()
