from env import *
def main():
 prev=json.loads((ROOT/'r06_prior_verify.json').read_text());assert prev['manifest_verified'] and prev['packages_verified']
 st=json.loads((R5/'ITERATION_STATUS.json').read_text());assert st['sealed'] and st['next_allowed'] and st['round']==5
 assert git(Path.cwd(),'rev-parse','HEAD')=='a7bd5235134c9d85ffe6f5172d8f6adf751f33a2'
 assert not (R/'METHOD_FREEZE.json').exists();assert not list(R.glob('*'));R.mkdir(exist_ok=True);(R/'reviews').mkdir();(R/'logs').mkdir()
 js(R/'logs/PREFLIGHT_EMPTY_DIRECTORY_REPAIR.json',dict(first_attempt='assert not R.exists failed: runner-created directory was empty',inspection='ls -la showed only dot and dot-dot',repair='accept empty existing task round directory; still forbid any scientific outputs',scientific_results_before_freeze=False))
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard())
 sources=json.loads((R5/'SOURCE_MANIFEST.json').read_text())['files']
 for p in R5.rglob('*'):
  if p.is_file() and p.name not in ['ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz'):sources[str(p)]=sha(p)
 for folder in ['round05','round03']:
  for p in (CODE.parent/folder).glob('*.py'):sources[str(p.resolve())]=sha(p)
 js(R/'SOURCE_MANIFEST.json',dict(files=sources,read_only=True))
 cfg=dict(round=6,mechanism='negative-space morphology as independent conditional evidence; no graph or hard seed changes',arms=['rgb','rgb_morph','rgb_shuffled_morph'],fit_scene='ficus',morphology=dict(features=['clipped EDT / (.04 bbox diagonal)','Gaussian occupancy sigma=.01 diagonal','Gaussian occupancy sigma=.04 diagonal'],unknown_bounds='lower=subject candidate; upper=candidate OR unknown; interval midpoint feature',eligibility='max upper-lower feature spread <=.10; otherwise RGB-only fallback',bins=8,histogram_sigma=.75,constant_zero_padding=True),appearance=dict(bins=16,sigma=.75,threshold_quantile=.05,posterior=.65,margin=.2,product_weight=1),seeds='exact r03 pooled RGB original two BUILD seeds and labels; not GT',shuffle=dict(seed=1729,scope='morphology feature vectors permuted among all original seed IDs within each view, not within class; reliable flag travels with feature'),input_roster={s:views(s) for s in SCENES},build={s:[DEV[s],AUX[s]] for s in SCENES},reserved=RES,historically_seen=True,DTU='compute coverage morphology only, do not fit part model because no qualified subject mask',budget=dict(cpu=2,task_cap_gib=12,unit_seconds=600,round_minutes=50,no_new_science_after_JST='07:40'),tuning=False,downstream='C/D/NPR NOT_RUN; standalone B precision test')
 js(R/'CONFIG.json',cfg)
 (R/'METHOD_FREEZE_ZH.md').write_text('''# r06 冻结：负空间形态补充外观，非继续调平滑

## 真实前轮审查与GO/NO_GO
05:39后读取r05状态、完整报告、实际三scene四视角图和Ficus冠内木失败图；核验旧seal和packages、git HEAD/diff。r05只是撤回硬seed，430个Ficus冲突seed中355仍回原类，图邻接压过一元；木枝仍绿、盆高光串色。机制审查允许新信息源测试：主体轮廓周围的空隙/厚度能否为同色不同形态提供证据。本轮不调gamma、seed撤回比例、K或阈值，也不把新色图当原GS部件。
Ficus沿用r01已资格化的isolated coverage proxy：原valid depth>.2且alpha>=.5，unknown为alpha>=.1且不valid；这是特定孤立源场景的范围代理，非语义GT。DTU全scene coverage包含地台/桌面，r05仅颜色分离尚不完整；因此DTU只运行真实形态输入资格负对照，正式B分类NOT_RUN，不能把全scene alpha叫主体。三scene均交全图与新测量，不能把Ficus成功推广。

## 冻结新变量
对原尺寸source-only候选mask保留所有孔洞/细枝，不morph close/open、不读C8墨迹。L=candidate，U=candidate|unknown，D为L非空bbox对角线(同图无类别位置)。分别计算三分量：min(EDT/(.04D),1)，Gaussian occupancy sigma=.01D，sigma=.04D。画外常数0，同时将距画框<4*.04D像素视为形态未知，以免截断主体假厚度；该资格只使形态证据回退RGB，不删主体。上下界差max<=.10才用中点特征，否则形态UNKNOWN/RGB-only。D只归一尺度，不提供高度/XY或类别方向，不以厚度直接命名盆/叶/枝。滚动轮廓、斜看薄叶、重叠叶层都可能同厚度，预期负例保留。
只用r03原Ficus两BUILD seed IDs/UV/粗代理labels，逐类逐view归一密度。基线rgb完全复算r03 16³ histogram/sigma.75；新形态8³ histogram/sigma.75，分别5%本类训练密度门，q正比 RGB类密度*形态类密度，指数1不调。max posterior>=.65，margin>=.2；有资格形态需同时过原RGB和形态类密度门。无资格形态用原RGB判断，记录fallback，不伪称形态完成。形态种子每类必须至少8个可用，不足即INVALID/NOT_READY，不改变class或门。多view等类/等view质量而非像素量票数。
对照rgb_shuffled_morph在每BUILD全seed集合中用固定1729排列形态向量和可靠性，RGB/原labels/数量不变；打破空间形态与类别关联，保留边际与计算预算。推理图使用真实形态，不shuffle目标。这检验新类别关联而非仅加特征；代理seed仍共享旧高度偏差，不是手工GT。没有graph、hard seed clamp、source ID voting、训练GS。另并列r04/r05已改善粗结构和v02RGB-only强参考，不能只赢r03就说最好。

## 相机/时间/验收
DEV/AUX仍0000/0024、Ficus train_r_80/train_r_7；reserved0012/0036、test_r_14/test_r_79只在模型冻结和DEV实图后一次推理，历史曝光，非blind/GS-heldout。DTU nativeRaDe，Ficus vanillaGS+CPU条件plane proxy，非GT，完整fx/fy/cx/cy/W2C沿用。原C8 arms/C和source全SH/filter/opacity、旧joint统一排序CPU参考不改。
先解析TDD再Ficus两个BUILD实跑，工程合格无论科学正负都可跑冻结reserved负例；不以失败修参数。DTU只source coverage/原失败subject对比，不输出假部件。视觉gate：盆高光/土面、冠内木、细叶边缘同时不破坏；不能通过更多UNKNOWN或缺失躲错。全图与r05同ROI解释、配对深度可见性沿旧2p/1.5px/3p门；对照同种子预算、原mask。统计仅自洽，非GT准确率。若新特征只把叶端误标枝或带来更碎区域，则NO_GO，不进入C/D/NPR。保留预测概率/feature上下界/UNKNOWN/原UV，任何mask与原一致断言。
CPU2，全任务12GiB，root1GiB/HDD10GiB，每stage核查；单unit600秒，本轮50分钟有界，07:40不启新science。每invocation只本轮；后续需要新resume。

## TDD与交付
真实RED后GREEN分片：同色薄枝/宽叶/厚盆可测而非语义认证；孔洞/断裂/UNKNOWN与边界截断；旋转与缩放可复现；只收boolmask不读line/RGB；原样seed/匹配shuffle、密度视图归一/无资格回退RGB/保留视角不入fit；相机可见性不负票、源/线索引不混。解析几何不作sceneGT。三scene十二张native形态图、Ficus三臂四图、同图旧joint/C8、RGB/r04/r05/shape/null强对比、固定坏例、可重放数据。最后只读verify、旧hash/worktree、commit、安全包、r06状态封存退出。无新NPR模型/视频，不能用2D标签覆盖称joint多风格。
''')
 js(R/'METHOD_FREEZE.json',dict(utc=now(),config_sha256=sha(R/'CONFIG.json'),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),before_new_results=True))
 review('00_new_information_GO','Ficus输入资格GO_PROXY；DTU形态主体资格NO_GO，仅coverage负对照。允许检验负空间形态信息，禁止继续调图/原seed。已实看r05三scene四视角及冠内木失败；新分类/特征尚未运行。',[R5/'REPORT_ZH.md',R5/'delivery/ficus_FOUR_VIEWS.jpg',R5/'delivery/ficus_train_r_7_FAILURE.jpg',R/'METHOD_FREEZE.json'])
 status('FROZEN',children=[])
if __name__=='__main__':main()
