from env import *
def main():
 prior=json.loads((ROOT/'r05_prior_verify.json').read_text());assert prior['manifest_verified'] and prior['packages_verified']
 ps=json.loads((R4/'ITERATION_STATUS.json').read_text());assert ps['sealed'] and ps['next_allowed'] and ps['round']==4
 assert git(Path.cwd(),'rev-parse','HEAD')=='d7dda4b78e7fbad703c1860be3748e20a78a3796'
 assert not (R/'METHOD_FREEZE.json').exists();R.mkdir(exist_ok=True)
 for n in ['reviews','logs']:(R/n).mkdir(exist_ok=True)
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard())
 sources=json.loads((R4/'SOURCE_MANIFEST.json').read_text())['files']
 for p in R4.rglob('*'):
  if p.is_file() and p.name not in ['ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz'):sources[str(p)]=sha(p)
 for p in CODE.parent.joinpath('round04').glob('*.py'):sources[str(p.resolve())]=sha(p)
 js(R/'SOURCE_MANIFEST.json',dict(files=sources,read_only=True))
 cfg=dict(round=5,mechanism='cross-build-view appearance contradiction withdraws proxy hard seed, never relabels seed; frozen r04 coupled graph and unary',arms=['withdraw_conflict','withdraw_random'],baseline='readonly r04 coupled',seed_evidence='r03 crossfit other_build_TO_this_build: model fitted ONLY on other build RGB/proxy seeds; apply to this original seed RGB',contradiction='accepted crossfit predicted >0 AND != original seed; unknown never contradiction',random=dict(seed=1729,matched='same removed counts per scene/view/original class',selection='all original seed IDs of that class, including possible overlap with contradictions'),inputs=dict(original_C8='arms/C',fit={s:[DEV[s],AUX[s]] for s in SCENES},reserved=RES),graph_and_unary='r04 code identical; no thresholds, masks, geometry or unary retraining changed',output=dict(probability=.65,margin=.2),targets='no target seeds, no feedback, same r04 transfer and inference',scientific_limits='independent image/model-training view, not independent semantic GT nor independent source scene; proxy labels share inherited height/geometry bias',gates=dict(continue_diagnostic='engineering TDD and valid solver; if no conflicts, unchanged result named null',ficus='restore visible crown-internal wood without ruining pot, trunk, leaf coverage/holes; matched random control and reserved full frames; semantic precision not from counts',dtu='complete subject and background separated; otherwise B/C/D NOT_RUN',downstream='C,D,NPR NOT_RUN this round'),limits=dict(cpu=2,task_cap_gib=12,unit_seconds=900,round_minutes=55,stop_start_jst='07:40',hard_stop_jst='08:00'),tuning=False,historically_seen=True)
 js(R/'CONFIG.json',cfg)
 (R/'METHOD_FREEZE_ZH.md').write_text('''# r05 冻结：撤回跨构建视角反驳的代理硬约束

## 实际自评 GO：允许证伪，不预授成功
已读r04实际状态/REPORT、源码、OVERVIEW、SEEDS_train_r_80、ficus_train_r_7_FAILURE，旧seal/packages只读核验。最早可操作冲突是：r01粗高度/方向产生的hard seeds可能把冠内木枝当冠；r04图再好也无法改掉这些Dirichlet约束。r04改善盆面连续性同时使冠内木变绿，故本轮只改变**硬约束可信资格**，不是再调平滑、类别数、图门或更换detector。所有输入和旧负例不变。

## 新机制和对照（新结果前冻结）
对于构建图v的每个原seed，读取r03已封存crossfit w_TO_v。该条件颜色模型只用另一构建图w的RGB与代理seed拟合，再在v的seed颜色求预测；严格核对target_uv、target_seed_labels及other-view身份。其既有拒绝门（posterior>=.65、margin>=.2、密度门）未通过=UNKNOWN，不算反证。若已接受预测与seed类不同，withdraw_conflict将该seed硬标签改0；不把它改成预测类，RGB一元、图边、mask全不变。此seed像素仍在图里，可继续被软证据估计，绝不是删像素/删原线。另一view不能含目标view训练样本，亦不冒称不同源GS/独立语义真值，原粗代理偏差依然共享。
withdraw_random用固定PRNG1729在每scene/view/原class全部seed中抽同数量撤回；允许与冲突集合自然重叠，不刻意抽“干净”seed。保持各类删seed预算一致，检验收益是否来自选择冲突而非简单放松。唯一主baseline为r04 coupled冻结输出；不是把它重算/改标题当新轮。两新臂继续同一coupled图与r03 pooled_rgb一元；后者包含本view，明确独立性只针对撤回判据，而非整个求解器。其他v02 RGB-only、r03、r04图作为只读强对照。

## 不变科学与数值定义
r04局部4邻接及世界4p门、跨view 2p深度/1.5px cycle/3p world、RGB sigma.12/floor1e-5、跨边.5/degree、unary gamma=max(degree,1)*margin/(4*5²)全相同。相同满内参/原native图、固定subject mask/孔洞，目标图无新seed和反馈，固定r03自身unary+构建图合格回投。只根据seed撤回后重新求同类screened-Laplacian问题。概率max.65/margin.2不变。使用r04已修复同矩阵solver：CG rtol1e-8,max3000，概率范围±1e-5；行和沿原numpy allclose atol1e-5+rtol1e-5，不改容差，失败INVALID。保留继承代码SHA对照和新tests独立计数。

## 场景、预算、观看与失败门
三scene DEV/AUX scan24/65=0000/0024,Ficus=train_r_80/train_r_7；reserved=0012/0036与test_r_14/test_r_79。全历史曝光，DTU sourceGS训练视角；reserved仅固定推理/诊断不决定撤回。DTU nativeRaDe camera-z，Ficus vanillaGS+CPU plane depth代理非GT，世界单位非米。原C8 arms/C、source全SH/filter/opacity和joint参考全部只读。
先Ficus两构建图端到端TDD+实图，工程通过则两个DTU及全部reserved执行一次固定方案。即便Ficus科学不改善，DTU仍可作为同一冻结机制的低成本负对照；不因此升级部件/NPR。三scene×2新臂×4原尺寸图=24输出；6构建模型、12目标推理。unit900秒，轮55分钟，CPU2/ROOT12GiB/root1/HDD10，07:40起不得新科学轮。没有第二次调参或第三新臂。
主验收：冠内原本可见木恢复且盆土/高光/主干/叶间空洞不恶化；建筑整屋顶/窗框与地台区分，头骨暗齿/颅顶与桌面区分；必须全frame和两个弱reserved检查。颜色变化、UNKNOWN下降、冲突数和匹配数均非GT正确率。若只是局部木变好但盆/主体不完整，最多PARTIAL且精确gate NO_GO。跨view不同可见不作负票，不把少数同色配对认证整盆。所有C线边界/D source成员/NPR本轮冻结NOT_RUN；不跳上游失败门。

## 交付与TDD
新行为逐RED→GREEN：其他view-only证据、精确UV与原ID、不接受UNKNOWN反对票、撤回不重标签、random每类预算/确定性/无seed误删、reserved无seed、同graph/unary不变、同mask/负空间、目标推理重放。保留所有失败日志。全frame原RGB/C8 xray/真joint旧参考、r04/冲突撤回/随机撤回及seed冲突位置图；冠木/盆土/暗齿放大仅解释不作选择mask。所有输出为图像诊断，不是原GS成员/NPR模型。最终readonly replay精确重算新模型/目标，旧893源码+12worktrees/source哈希，安全包，本地commit，r05 ITERATION_STATUS封存后退出，不在本次调用运行r06。

沿用已核验Grady2006 seeded Laplacian作者全文 https://leogrady.net/wp-content/uploads/2017/01/grady2006random.pdf 和GrabCut2004条件外观 https://pub.ista.ac.at/~vnk/papers/grabcut_siggraph04.pdf 。跨view反驳撤回是本任务假设，非声称论文已经提供语义真值或自动NPR分块。
''')
 js(R/'METHOD_FREEZE.json',dict(utc=now(),config_sha256=sha(R/'CONFIG.json'),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),before_new_results=True))
 review('00_mechanism_GO','真实r04全图显示硬seed与冠内木外观冲突；允许以独立构建view外观撤回约束，与同预算随机撤回证伪。不得把反驳代理当GT。先TDD/Ficus，再统一DTU诊断；C/D/NPR冻结NOT_RUN。',[R4/'REPORT_ZH.md',R4/'delivery/SEEDS_train_r_80.jpg',R4/'delivery/ficus_train_r_7_FAILURE.jpg',R/'METHOD_FREEZE.json'])
 status('FROZEN',children=[])
if __name__=='__main__':main()
