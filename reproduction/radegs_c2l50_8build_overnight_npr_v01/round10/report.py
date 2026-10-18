from env import *

def main():
 tests=(R/'logs/09_regression.txt').read_text()
 assert 'Ran 18 tests' in tests and tests.rstrip().endswith('OK')
 replay=json.loads((R/'REPLAY_CHECK.json').read_text())
 assert [replay[k] for k in ['feature_views_replayed','model_replays','prediction_replays','match_replays']]==[12,6,24,6]
 js(R/'TEST_RESULTS.json',dict(new_tests_passed=18,groups=dict(supported=10,protocol=8),inherited_tests_counted_as_new=0,red_logs=['logs/01_supported_RED.txt','logs/03_protocol_RED.txt'],green_logs=['logs/02_supported_GREEN.txt','logs/04_protocol_GREEN.txt','logs/09_regression.txt'],algorithm_tolerances_changed=False,scope='Two actual API slices missing implementation RED then GREEN, not 18 independently observed RED runs.',pre_science_engineering_receipt='ENGINEERING_PREFLIGHT_RECEIPT.json'))
 gates=dict(overall='NO_GO',engineering='GO',precise_partition='NO_GO',scenes=dict(scan24=dict(state='NO_GO',A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',why='Near-unit scene alpha cannot distinguish platform from roof; fragmented roof and background contamination remain.'),scan65=dict(state='NO_GO',A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',why='Scene coverage includes tabletop. Dark bone, teeth and table still mix; no reliable complete subject.'),ficus=dict(state='NO_GO',A='INHERITED_GO_PROXY',B='NO_GO',C='NOT_RUN',D='NOT_RUN',why='Partial pot-bottom recovery versus r09, but pot edge UNKNOWN, soil/crown confusion and missing crown-internal wood remain. No improvement in mutual region qualifications.')),new_source_memberships=0,new_GS_models=0,styles=0)
 js(R/'STAGE_GATES.json',gates)
 seen=['figures/ficus/train_r_80/FULL.jpg','figures/scan24/0000/FULL.jpg','figures/scan65/0000/FULL.jpg','figures/scan24/0036/FULL.jpg','figures/scan65/0036/FULL.jpg','figures/ficus/test_r_14/FULL.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/OVERVIEW.jpg','features/ficus/train_r_80/FEATURES.jpg','delivery/ficus_FAILURE_ROI.jpg','delivery/ANALYTIC.jpg']
 js(R/'VISUAL_AUDIT.json',dict(actual_image_tool_inspection=True,files={n:sha(R/n) for n in seen},all_twelve_views_in_full_frame_boards=True,judgement=gates,roi_selection='Inherited r09 explanatory crops, not algorithm masks or fitting inputs.',native_dimensions=dict(scan24=[777,581],scan65=[777,581],ficus=[800,800])))
 js(R/'NEXT_REVIEW.json',dict(next_allowed=False,next_hypothesis=None,decision='STOP_NEW_SCIENCE',reason='This finite-support hypothesis was actually tested. Current frozen inputs and automatic proxy seeds do not provide a newly justified independent mechanism for precise identity. Further sigma/K/posterior/graph-strength changes would repeat tested mechanisms. Stop science and summarize completed evidence; this is not an impossibility theorem.',finalization_in_this_invocation=True,latest_new_science_JST='07:40',hard_stop_JST='08:00',no_r11_started=True))
 (R/'REPORT_ZH.md').write_text('''# r10：有限覆盖归一化修正了背景污染机制，仍未得到可靠部件分区

**本轮科学结论 NO_GO，工程复算通过。** 实际新运行三场景×四个冻结视角×两臂：12份特征缓存、6个密度模型、24份原尺寸分区及6组Ficus双向区域资格检查。Ficus盆底相较r09局部恢复，但盆边仍大片UNKNOWN、土面误入冠类、冠内木枝丢失；建筑和头骨几乎重现上一轮问题。没有通过精确部件门，没有新source成员、线成员、GS模型或多风格NPR。原C8与joint完整保留。

## 独立机制与冻结对照
r09梯度窗口会把主体外的背景卷入纹理统计。本轮检验有限观测支持，不改变颜色分类因子、sigma、类别数、代理种子或拒绝门。原source alpha只表达全scene覆盖，不是语义主体；建筑地台、头骨桌面也能有alpha接近1。Ficus孤立背景有较低覆盖，因而具有可证伪的实际条件。RGB本身已经包含半透明边缘混色，归一化不能反推出纯物体颜色。

令w为原alpha的有限值裁到[0,1]，非有限置0并记录；s=min(H,W)/581。N=G_s(wI)，D=G_s(w)，尺度归一梯度为 `g_x=s*(∂xN*D-N*∂xD)/D²`，y方向相同，RGB三通道分别求导。张量 `J=G_(3s)(w·g·gᵀ)/G_(3s)(w)`，编码沿r09的方向、相干性和固定0.05能量常数。D与积分分母都大于1e-6才有数值资格，其他像素UNKNOWN；这个epsilon不是测得的几何置信度。全1权重恢复无条件r09表示，软权重整体倍乘不改变结果。

两个新臂是alpha_texture和shifted_alpha_texture。null只把alpha向右循环平移round(3s)，原RGB、seed UV/labels和推断mask不变，全图权重多重集及总质量exact保留。有限错位仍与真实支持高度相关，画边有循环接缝；它检验局部对齐而非模拟任意语义错误。原mask不侵蚀、不补洞、不减少薄叶。全部真实构建seed都有数值资格，全部12视图原mask内无特征资格丢失，所以本轮没有靠缩小推断域改善图片。

分类器仍为16³密度直方图、0.75bin平滑、每类/每view等质量、自身BUILD的5%密度门、posterior≥0.65和margin≥0.2。RGB×texture只是条件独立近似，不是校准语义概率。图像方向随相机改变，也没有变成材料或物理部件不变量。只读r09 raw_rgb/unconditional、r05图传播和v02 RGB-only作为强对照，旧结果不计入新运行次数。

## 解析干预真的有效，但不能代替真实物体
固定161²图中9像素薄条的RGB不变，仅把零支持背景从白色换成固定seed2随机RGB。薄条内归一描述子的最大变化为0，无条件描述子最大变化0.6083658816481043。这证明实现确实阻止零支持背景进入该统计，不是把输出淡化。它不证明真实alpha提供了正确前景，也不证明纹理本身能区分盆/干/冠。解析图域外的颜色只是特征显示，未赋予物理部件身份。原小图标题拥挤保留，delivery/ANALYTIC以近邻放大展示相同数值，没有重造证据。

## 三场景完整视图判断
**scan24：A NO_GO。** 四视角原推断mask中的平均alpha为0.99895、0.99404、0.99884、0.97224，几乎全覆盖。屋顶、地台和背景在alpha上没有可分的主体身份。主臂0000仅110个像素与r09标签不同，0024为676个，0036为1303个；后者UNKNOWN仍159888，r09为159769。屋面碎裂、窗檐拒绝与地台错误仍在。r05大块更连续，却同样不能认证蓝色就是屋顶。B/C/D均NOT_RUN。

**scan65：A NO_GO。** 原mask平均alpha0.98590、0.98985、0.98731、0.95696，桌面也被覆盖。0036主臂UNKNOWN117815、橙色153511，r09对应118103与153174，肉眼并无可靠身份改进。桌面接触阴影、暗骨和牙列仍混合，0012也保留噪杂。不能把颅顶大体完整当作全主体分离成功，更不能提前切颅/面颌。B/C/D均NOT_RUN。

**Ficus：B NO_GO。** 原mask内alpha约0.94—0.96、外部约0.005—0.008，使有限支持有真实作用。train80主臂相较r09有6413个标签变化；test14盆类由16568到17584，木类1729到1923，UNKNOWN19335到18244，盆底局部可见恢复。但原RGB对照test14盆25296、木6322，主臂仍明显缺完整盆缘和冠内木枝；土面和盆口又常为冠色。test79盆由8662到9256，木由2593降至2436。错位alpha画面相近，test14盆17283、木1856，不能凭主臂略多蓝色断言身份更准。r05盆形和裸干总体更完整，仍有高光横纹/土面/冠内木枝错误。原叶间负空间和推断mask保持，但被拒绝或误分类的合法结构仍不能用于可靠风格。A只继承整体范围proxy资格，C/D NOT_RUN。

全12张原尺寸画面均实际核读，0036/test14/test79和放大负例保留。灰色UNKNOWN不是删除source、不是去刺，也不是分类正确；这些数是面积/变化诊断，没有GT accuracy/precision。所有原C8长刺照常在只读context中，未被隐藏或修复。

## 跨视角与能力边界
冻结2p深度、1.5px循环、3p世界一致资格完全不变，遮挡不负票。Ficus DEV到AUX/test14/test79，主臂与错位支持都为2/1/1互配，与r09无条件相同；raw为1/2/2，r05为2/2/2。主臂AUX是木/冠，两个保留视角只剩冠；盆没有获得资格。因此有限背景修正确有局部效应，但没有提高本轮实际跨视角部件资格。6组匹配是本轮新算，另外9组控制是只读引用，不能合称15组新实验。配对数本身也不是语义质量或物理primitive证明。

三场景分别两BUILD拟合：DTU0000/0024、Ficus train_r_80/train_r_7；统一推断0012/0036、test_r_14/test_r_79。全部历史曝光，DTU属于原GS训练视角，不是blind/GS-heldout。DTU输入为native RaDe缓存777×581，Ficus为vanilla GS及CPU条件平面深度代理800²，世界单位非米。全部fx/fy/cx/cy/W2C保持，C8仍原arms/C八BUILD资产；本轮分类只用两构建视角，不能宣称新增八视角对应。

图中source/C8/true joint为封存只读context，CPU fullSH/EWA统一source+ink排序，非RGB×ink，也不等价官方CUDA。本轮新图是2D区域诊断，不是joint多风格渲染。未进入源核责任阶段，不新增all-N责任实验、不把旧renderer校准算本轮新测试；原source fullSH/filter/+Inf/XYZ和线核均不写。

## 实际测试、封存与停止
18项本轮新测试：supported10、protocol8。两次API缺实现真实RED后最小实现GREEN，随后完整18项回归；不是18项各自独立RED，没有改fixture容差。冻结脚本遇到runner预建空目录的前置工程错误已单独记录，修复只允许空目录且拒绝已有METHOD；科学运行前解决，不能算科学失败或测试RED。

独立readonly replay真实重算12特征、6模型、24预测、6匹配和解析干预；6个RGB密度因子与r09exact，12个错位alpha多重集exact。62封存单元、3557来源文件、主工作树893 Python与12受保护树HEAD/status/index通过。资源实测在12GiB硬cap内，无GPU、训练、外部模型或旧资产编辑。文件数和测试通过只说明工程，不替代视觉门。

本轮不推荐替换原C8/joint，不启动下游NPR。已有低频颜色、图传播、种子反驳、形态、SH/明暗、纹理及有限支持证据，仍缺精确部件身份。继续换sigma、K、门限或传播权重只会重做已测机制；当前没有足够证据冻结另一项独立科学干预。因此本调用完成r10与已有轮次终验汇总后停止新科学，next_allowed=false，不编造r11填满时段。这是对当前输入/预算/方法的边界判断，不是证明自动分块不可能。未来若另获授权，应先补足可独立检验的部件身份信息，再谈源核软归属和多风格；不能在失败上游制作正式风格图。
''')
 (R/'FORMAT_ZH.md').write_text('''# r10格式与范围
features/<scene>/<view>/FEATURES.npz：texture/shifted_texture为H×W×3 float64；eligible和shifted_eligible独立；denominators保留归一卷积D/W，weight为原有限alpha裁[0,1]，shifted_weight为固定循环错位。支持是scene coverage，不是主体GT。
models/<scene>/<arm>/MODEL.npz：RGB/texture代理条件密度及拒绝门，非3DGS模型；SEEDS保存原uv/labels及特征与eligible。6新模型全部原seed资格完整。
inference/<scene>/<arm>/<view>/RESULT.npz：labels(0未知)、unknown/inference_mask、概率/密度、source_uv、feature_eligible。source_uv是图像xy，不是source核ID。原mask外不造标签。
evaluation：仅两个新臂的六组FORWARD/REVERSE真实数据；MATCH_COUNTS的九项readonly_controls指向旧封存文件，不作为新实验。
figures为固定gain原尺寸图；delivery为同尺度全图板和说明crop。新颜色只是2D诊断，不是物理部件或NPR写回。C8、source、joint只读context。
安全包与RESULTS_MANIFEST采用{members:{relative_path:{sha256}}}；禁止link/absolute/../旧env/credentials。runtime文件排除，绝不改旧seal。verify --readonly --replay重算全部科学数组而不写原数据。
''')
 (CODE/'README.md').write_text('''# Round 10: finite observation-support falsification

Three scenes, four historical views, two new arms. Scientific NO_GO. No new GS/source membership/NPR.

Use official_code_fix_v01/env/bin/python -B (readonly). freeze.py before science; test_supported.py RED then supported.py GREEN; test_protocol.py RED then protocol.py GREEN; analytic.py; experiment.py --phase pilot; reviewed fit; reviewed reserved; unittest discover; evaluation.py; delivery.py; verify.py --readonly --replay; report.py; closure.py; local commit; finish.py. Completed units verify seals. Do not rerun freeze or overwrite sealed results.

18 actual new tests in two RED/GREEN API slices. Numerical support does not define semantic foreground. Model/RGB seed identity, full-mask coverage, alpha-multiset null, all scientific arrays, source hashes, old trees and package paths are verified. Runtime files excluded from static seals. No external agents, GPU, source training or edits. Stop new science after r10; finalization summarizes previous sealed rounds and is not an eleventh experiment.
''')
 commands=['freeze.py: first stopped on runner-created empty directory; bounded pre-science fix; same freeze succeeded (ENGINEERING_PREFLIGHT_RECEIPT.json)','test_supported.py RED > logs/01_supported_RED.txt; implementation; GREEN > logs/02_supported_GREEN.txt','test_protocol.py RED > logs/03_protocol_RED.txt; implementation; GREEN > logs/04_protocol_GREEN.txt','analytic.py > logs/05_analytic.txt','experiment.py --phase pilot > logs/06_pilot.txt','experiment.py --phase fit > logs/07_fit.txt','experiment.py --phase reserved > logs/08_reserved.txt','-m unittest discover -s reproduction/radegs_c2l50_8build_overnight_npr_v01/round10 -p test_*.py -v > logs/09_regression.txt 2>&1','evaluation.py > logs/10_evaluation.txt','delivery.py > logs/11_delivery.txt','verify.py --readonly --replay > REPLAY_CHECK.json 2> logs/12_verify.stderr','report.py after actual replay and full-image inspection','closure.py: readonly prior-round seals and final evidence summary, not new science','local commit round10 code only','finish.py after clean commit; receipt outside sealed round']
 (R/'RUN_COMMANDS.md').write_text('# Execution ledger\n\nInterpreter `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B`. Code `reproduction/radegs_c2l50_8build_overnight_npr_v01/round10/`. CPU affinity and BLAS threads limited to two in env.py.\n\n'+'\n'.join('- '+x for x in commands)+'\n\nCommit/package success requires their actual receipts, not this command list. No new renderer/source training/model edit.\n')
 review('04_delivery_GO_science_NO_GO','实际图核读与18新测试、12/6/24/6只读重放通过，允许封存本轮NO_GO。解析背景替换证明有限支持改变机制，真实精确身份仍失败。禁止进入C/D/NPR。现无充分证据再冻结独立科学变量；停止新科学，做只读已完成轮次汇总后退出，不启动r11。',[R/'delivery/OVERVIEW.jpg',R/'delivery/ANALYTIC.jpg',R/'delivery/ficus_FAILURE_ROI.jpg',R/'REPLAY_CHECK.json',R/'STAGE_GATES.json'])

if __name__=='__main__':main()
