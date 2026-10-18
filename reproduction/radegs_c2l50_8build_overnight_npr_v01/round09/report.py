from env import *

def main():
 tests=(R/'logs/10_regression.txt').read_text()
 assert 'Ran 19 tests' in tests and tests.rstrip().endswith('OK')
 replay=json.loads((R/'REPLAY_CHECK.json').read_text())
 assert [replay[k] for k in ['feature_views_replayed','model_replays','prediction_replays','match_replays']]==[12,12,48,15]
 js(R/'TEST_RESULTS.json',dict(new_tests_passed=19,groups=dict(texture=10,likelihood=9),inherited_tests_counted_as_new=0,red_logs=['logs/01_texture_RED.txt','logs/04_likelihood_RED.txt'],green_logs=['logs/03_texture_GREEN.txt','logs/06_likelihood_GREEN.txt','logs/10_regression.txt'],preserved_contract_failures=['logs/02_texture_GREEN_attempt.txt','logs/05_likelihood_GREEN.txt'],correction_receipt='TDD_CONTRACT_CORRECTIONS.json',algorithm_tolerances_changed=False,scope='Two API vertical slices RED before implementation, then GREEN; not 19 independently observed RED runs. Two test-contract errors corrected before real data; original fixtures and logs retained.'))
 gates=dict(overall='NO_GO',engineering='GO',precise_partition='NO_GO',scenes=dict(scan24=dict(state='NO_GO',A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',why='Roof fragments and platform remains same class; no complete near-subject recovery.'),scan65=dict(state='NO_GO',A='NO_GO',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',why='Dark bone, teeth and tabletop still mix; texture and shuffled null both spread class into table.'),ficus=dict(state='NO_GO',A='INHERITED_GO_PROXY',B='NO_GO',C='NOT_RUN',D='NOT_RUN',why='Some pot highlight stripes improve, but pot outline becomes UNKNOWN and crown-internal wood is lost; reserved matches lose wood.')),new_source_memberships=0,new_GS_models=0,styles=0)
 js(R/'STAGE_GATES.json',gates)
 seen=['figures/ficus/train_r_80/FULL.jpg','figures/scan24/0000/FULL.jpg','figures/scan65/0000/FULL.jpg','figures/scan24/0036/FULL.jpg','figures/scan65/0036/FULL.jpg','figures/ficus/test_r_14/FULL.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/OVERVIEW.jpg','features/ficus/train_r_80/FEATURES.jpg','delivery/ficus_FAILURE_ROI.jpg']
 js(R/'VISUAL_AUDIT.json',dict(actual_image_tool_inspection=True,files={n:sha(R/n) for n in seen},all_twelve_views_in_full_frame_boards=True,judgement=gates,roi_selection='Post-result explanatory crops only; not training, selection or segmentation masks.',native_dimensions=dict(scan24=[777,581],scan65=[777,581],ficus=[800,800])))
 nxt='只允许另冻一次局部观测域证伪：检验r09梯度窗口跨主体/背景混合是否使细干、盆缘被当作纹理。保持RGB和proxy seeds，比较原无条件窗口、由原封存alpha/有效支持归一的窗口，以及等预算错位支持mask；先用同一细物体更换背景的解析反事实证明机制，再Ficus真实小切片。UNKNOWN不能靠侵蚀薄枝或缩mask获得，DTU全scene alpha不能当主体mask；若不能构造不吞主体的有效支持，停止此假设。不换K、sigma、后验阈值，不用本轮reserved反向调参。它只是下一轮待评估机制，未在r09运行。'
 js(R/'NEXT_REVIEW.json',dict(next_allowed=True,next_hypothesis=nxt,not_executed=True,distinct_variable='finite observation support / foreground-background mixing, not texture scale or class count',risk='Alpha is scene coverage, not semantic foreground; interior region mixing may remain. Normalized filtering may erase true boundary evidence. No downstream gate bypass.',latest_new_science_JST='07:40',hard_stop_JST='08:00',runner_decides=True))
 (R/'REPORT_ZH.md').write_text('''# r09：局部纹理布局能分开代理种子，却没有恢复可靠大部件

本轮实际完成三场景×四个固定视角×四臂，共48份原尺寸分类结果、12个密度模型、12份双描述子缓存，以及15组Ficus双向可见区域资格检查。科学结论为 **NO_GO**；工程重放通过。纹理布局的确影响判断，但本轮具体表示与分类器未产生可用于多风格NPR的可靠分块。原C8线、source GS及joint完全保留，没有生成新GS、源核语义标签或正式NPR图。

## 本轮改变了什么
r08去掉单像素明暗后，Ficus盆/干明显退化。r09回到原RGB，单独检验颜色的局部空间排列能否增加部件证据。它不是再换K、门限、SH或图传播，也没有新的硬种子。使用原r03的构建视角代理UV/labels和原推断mask；原C8不是纹理检测输入，弃用的core-line标签不参与。

令s=min(H,W)/581，对原float RGB求sigma=s的尺度归一高斯梯度，再以3s积分得到结构张量J；t=Jxx+Jyy。描述子为

`f=(0.5+0.5(Jxx-Jyy)/(t+1e-12), 0.5+Jxy/(t+1e-12), sqrt(t)/(sqrt(t)+0.05))`。

前两维编码图像方向和相干性，第三维是固定对比能量。全部尺度、truncate=3及0.05常数在真实数据前冻结。图像旋转会改变方向分量，它不是跨相机材料不变量；透视缩短、轮廓、孔洞和背景混入都可能支配描述子。RGB与梯度相关，`p_RGB*p_texture`只是条件独立近似，输出posterior不称校准置信度。

四臂为原RGB、RGB+真实texture、RGB+打乱texture、texture-only。打乱臂仅把每个round(33s)非重叠方块内的RGB三元组排列打乱，固定seed1729；RGB分类因子仍用原图。每块RGB多重集逐块exact保留，但滑动窗口统计并不相同，且会新增人为高频，这是预先声明的null限制。所有臂沿用16³直方图、0.75bin平滑、每类/视角等质量、自身BUILD密度5%门、posterior≥0.65及margin≥0.2。没有看reserved后改参数。raw臂3模型与12幅数组均与r03位级一致。

## 原输入、相机和对照边界
scan24/65是native RaDe缓存RGB/alpha/camera-z，777×581；Ficus是vanilla3DGS与CPU条件平面深度代理，800×800。两种深度不可混称GT，世界单位非米。每scene拟合DEV/AUX两幅：DTU0000/0024，Ficus train_r_80/train_r_7；统一推断reserved0012/0036及test_r_14/test_r_79。全都历史曝光，DTU属于source GS训练视角，不是blind或GS-heldout。

DTU两类来自旧外围水平/中心非水平代理，不能把两色认证为屋顶/墙或颅/面颌。Ficus盆/木/冠也是粗代理，不是GT。每个目标图使用自身原RGB计算描述子；不是无图像的标签迁移。图中r05图传播、r07DC及v02 RGB-only为封存强对照。C8 xray与true joint为只读context，未冒充本轮新渲染。新分类图只是2D诊断着色，不是对joint模型做了多风格NPR。

## 三场景完整视图判断
**scan24：A NO_GO。** 原RGB已把屋顶与白地台/背景混为蓝类；纹理主臂没有解决身份，反而把0000/0024/0012屋顶打碎成大量UNKNOWN，0036整片屋顶大面积拒绝。砖墙虽更偏单色，窗框和檐边仍碎，背景错误类别仍在。0036 UNKNOWN从56591变159769，打乱臂112880；这不是清除了103178个错误背景像素，其中包含大量真实屋顶。r05外形更连贯，但仍有屋顶—地台错误，不能当已解决主体。B/C/D均NOT_RUN。

**scan65：A NO_GO。** 颅盖大体保持，但主臂把更多桌面边缘和接触阴影判成橙类；0024/0012出现外侧杂斑，0036暗颅/牙/桌面仍混。打乱纹理同样扩散，不能把更多已知像素解释为找回骨骼。0036 UNKNOWN从176343降到118103，橙类由95353增至153174，含明显桌面误入。r05边界更干净也仍不可靠；没有认证颅—面颌分组。B/C/D均NOT_RUN。

**Ficus：B NO_GO。** 主臂减少部分盆面高光被判木的横条，但盆缘、盆底和土/根交界变UNKNOWN或叶冠色；冠内真实细干也被叶冠色吞并。test_r_14盆类由25296减至16568，木类6322减至1729；test_r_79盆14757减至8662，木6556减至2593。原mask及叶间负空间未删，然而误分与拒绝使可用部件更不完整。BUILD的盆中央相对整齐不是整体视觉GO，r05和部分打乱臂的盆/干形体反而更完整。A仅继承整体范围proxy资格，未认证新的语义mask；C/D均NOT_RUN。

这些数字仅描述分类面积变化，没有逐像素GT，不能叫precision、accuracy或结构恢复率。查看的是全部12完整画面，困难0036/test14及test79都保留；坏例放大仅用于说明，不作为算法ROI。

## 为什么种子可分离不等于部件可靠
在Ficus代理BUILD种子上，真实texture直方图的两类重叠Σmin(h_i,h_j)为盆/木0.1097、盆/冠0.1303、木/冠0.1002；打乱texture分别0.3048、0.3762、0.7502。布局确实让这些特定种子更容易区分，不能说没有纹理信息。但是种子取样代表性、方向随视角变化、窗口跨背景和部件边界以及乘积过度自信，都可能使该优势在完整目标图中失效。实图不能分离各因素的因果份额；本轮不把其中任何一个猜测写成已证实根因。

Ficus冻结的2p深度、1.5px循环和3p世界一致规则不变，遮挡不当反票。DEV到AUX/test14/test79，原RGB可资格互配为1/2/2对，主臂2/1/1，打乱2/2/1，texture-only1/1/1，r05为2/2/2。主臂AUX多出的一对仅是粗区域身份检查；两个reserved都只剩叶冠对，木类配对丢失，盆始终未通过。不能凭AUX配对数量宣布多视角分块成功。跨视角相机与深度只用于这套冻结诊断，不提供新的真实线对应，更不产生source核物理面标签。

## 测试、可重放性与范围
19项本轮测试通过：texture10、likelihood9。两次模块/API缺实现的真实RED后实现GREEN；不是19项各自独立RED。另有两次测试契约错误：常量expected需显式广播；原四种子测试错误要求5%密度拒绝门下全部被接受。均在真实数据前修正，原varying fixture保留并核验[1,0,2,0]，另增重复模式正例；原失败日志和TDD_CONTRACT_CORRECTIONS保留，没有调算法参数或放宽数值容差。

只读verify实际重算12特征视图、12模型、48预测和15双向检查，原RGB模型/预测exact；每个打乱block的RGB三元组多重集都校验。来源文件及旧main893Python、12工作树HEAD/status/index保持。旧renderer和all-N责任校准未计作本轮新测试；因为本轮不渲染新source责任，没有新增全N实验。原source fullSH/filter/+Inf及线核从未改写。

交付在delivery/OVERVIEW.jpg、三个FOUR_VIEWS和失败放大；figures保留全部四臂原尺寸全图、C8/joint与强对照，features保留实际纹理图及数值，inference为完整48份NPZ。19测试通过只认证实现与数据重放，不认证语义正确。本轮不推荐取代原C8/joint，不启动正式NPR。

下一轮如果runner批准且仍有时间，建议只证伪“有限观测支持/背景混入”机制：不改变颜色和sigma，用冻结alpha/支持限定局部统计，与原无条件窗口及错位支持对照；先证明同一细物体换背景的影响。alpha仍非语义mask，不能通过侵蚀细枝或缩小范围造成功；DTU全scene覆盖可能使这条路线根本不可用。此建议尚未执行，下一轮须另冻方案。本调用完成r09后退出，不自动开r10；07:40起收尾、08:00截止。
''')
 (R/'FORMAT_ZH.md').write_text('''# r09格式和能力边界
features/scene/view/FEATURES.npz：texture和scrambled_texture为H×W×3 float64；shuffled_rgb保持原dtype；不修改原RGB。相邻小块打乱会引入人工边界。
models/scene/arm/MODEL.npz：rgb_hist、texture_hist为K×16×16×16，threshold[K]、classes；*_SEEDS含原uv、labels、raw_rgb和实际texture。密度模型是类别代理直方图，不是新3DGS模型。
inference/scene/arm/view/RESULT.npz：labels uint8，0=UNKNOWN/未赋值；unknown和inference_mask单列；probability/density为H×W×K；source_uv为原图整数xy，不是source GS index。原mask之外不新造标签，原未知保留。DTU1/2是旧几何代理，Ficus1/2/3是pot/wood/crown proxy，均非GT。
evaluation：FORWARD/REVERSE逐点uv、target_uv、state、target_label；遮挡/画外/循环不合等拒绝单列，不当负票。几何近似和阈值见geometry.py，不将coarse pair当物理部件认证。
每unit SEAL及最终RESULTS_MANIFEST、包MEMBERS统一{members:{relative_path:{sha256}}}。包不含原GS/旧环境；绝对只读依赖见SOURCE_MANIFEST。runtime文件排除静态封存。verify --readonly --replay只读复算，不重写旧证据。
''')
 (CODE/'README.md').write_text('''# Round 09: local RGB texture-layout falsification

Real 3-scene, four-view, four-arm experiment. Scientific result NO_GO; no source/ink editing, physical group or NPR export.

Use the readonly official_code_fix_v01/env/bin/python -B interpreter. Execution: freeze.py once before science; test_texture.py RED then implementation GREEN; test_likelihood.py RED then GREEN; experiment.py --phase pilot; reviewed fit; reviewed reserved; evaluation.py; delivery.py; unittest discover; verify.py --readonly --replay; report.py; local commit; finish.py. Completed units check their seals and are not recomputed for production. Do not rerun freeze or overwrite sealed data.

19 actual new tests. Two documented test-contract corrections retained original fixtures and failure logs. Full dependencies, conditions, source hashes and stage evidence are in the HDD METHOD_FREEZE, SOURCE_MANIFEST, REPORT_ZH and TEST_RESULTS. C8/source and all old worktrees remain readonly. Readonly verify checks feature/model/prediction/match bitexact replay, original r03 identity, null multisets, old protection, safe packages. No GPU, downloads or external agents.
''')
 commands=['freeze.py (before new scientific arrays)','test_texture.py: RED logs/01; implementation; attempted GREEN logs/02; explicit shape correction; GREEN logs/03','test_likelihood.py: RED logs/04; implementation; attempted GREEN logs/05; frozen rejection-contract correction plus retained fixture; GREEN logs/06','experiment.py --phase pilot > logs/07_pilot.txt','experiment.py --phase fit > logs/08_fit.txt','experiment.py --phase reserved > logs/09_reserved.txt','-m unittest discover -s reproduction/radegs_c2l50_8build_overnight_npr_v01/round09 -p test_*.py -v > logs/10_regression.txt 2>&1','evaluation.py > logs/11_evaluation.txt','delivery.py > logs/12_delivery.txt','verify.py --readonly --replay > REPLAY_CHECK.json 2> logs/13_verify.stderr','report.py (after replay)','local commit round09 code only','finish.py (after clean commit; receipt outside sealed round)']
 (R/'RUN_COMMANDS.md').write_text('# Actual execution ledger\n\nInterpreter `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B`\n\nCode `reproduction/radegs_c2l50_8build_overnight_npr_v01/round09/`\n\n'+ '\n'.join('- '+x for x in commands)+'\n\nNo threshold rerun, GPU, package install, source render or sourceGS/line edit. Final commit/package completion is certified separately by COMMIT_RECEIPT and ITERATION_STATUS, not by this command list alone.\n')
 review('04_visual_delivery_GO','实际查看三scene四视角完整board、总览、特征图及Ficus负例。工程19测试及12/12/48/15只读重放通过，允许封存科学NO_GO；纹理种子分离不能替代主体和部件完整。C/D/source软成员及NPR保持NOT_RUN。下一假设仅留待runner评估，本调用不执行。',[R/'delivery/scan24_FOUR_VIEWS.jpg',R/'delivery/scan65_FOUR_VIEWS.jpg',R/'delivery/ficus_FOUR_VIEWS.jpg',R/'REPLAY_CHECK.json',R/'STAGE_GATES.json'])

if __name__=='__main__':main()
