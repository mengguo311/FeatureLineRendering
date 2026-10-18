from env import *
def main():
 assert git(Path.cwd(),'rev-parse','HEAD')=='91da4bf45bf3b79b06b0cc8eb605598fe41545d7'
 prior=json.loads((R2/'ITERATION_STATUS.json').read_text());assert prior['round']==2 and prior['sealed'] and prior['next_allowed']
 for f,d in json.loads((R2/'RESULTS_MANIFEST.json').read_text())['members'].items():assert sha(R2/f)==d['sha256'],f
 assert not (R/'METHOD_FREEZE.json').exists();R.mkdir(exist_ok=True)
 for d in ['reviews','logs','literature']: (R/d).mkdir(exist_ok=True)
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard())
 files=json.loads((R2/'SOURCE_MANIFEST.json').read_text())['files']
 for f in R2.rglob('*'):
  if f.is_file() and 'mplconfig' not in f.parts and f.name not in ['ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and not f.name.endswith('.tar.gz'):files[str(f)]=sha(f)
 for suffix in ['pdf','txt']:
  f=V1/'literature'/('grabcut2004.'+suffix);files[str(f)]=sha(f);shutil.copyfile(f,R/'literature'/f.name)
 js(R/'SOURCE_MANIFEST.json',dict(files=files,read_only=True))
 cfg=dict(round=3,mechanism='nonlocal seed-conditional RGB density with explicit rejection; no spatial propagation',views={s:dict(fit=[DEV[s],AUX[s]],reserved=RES[s]) for s in SCENES},
 density=dict(bins=16,sigma_bins=.75,floor=1e-12,equal_class_prior=True,equal_view_mass=True,seed_density_quantile=.05,posterior=.65,margin=.2),
 seeds=dict(ficus='same exact r02 seeds copied by pixel IDs; r01 coarse interior only',dtu='r02 reliable local upright peripheral=class1, central reliable angle>=35 degrees=class2; no GT',dtu_nonhorizontal_angle=35,max_per_class_per_view=2048,selection='equal linear indices',no_inference_seed_clamping=True),
 arms=['pooled_rgb','dev_only','shuffled_labels'],shuffle_seed=1729,
 inference=dict(no_world_height_or_position_features=True,no_target_seeds=True,no_graph=True,no_smoothing_labels=True,mask_ficus='exact inherited r01 subject',mask_dtu='finite z>.2 alpha>=.5; whole scene NOT subject'),
 crossfit='DEV density predicts AUX seed labels and vice versa; agreement with geometric proxies only, not accuracy',
 gates=dict(ficus='complete recognizable pot/trunk/crown, disconnected leaves recovered without relabeling soil/wood as foliage; at least2 visually coherent parts in4views, clear advantage over shuffled and dev-only for multiview claim',dtu='roof/teeth/cap retained, platform/table rejected without deleting horizontal subject; otherwise subject NO_GO',uncertainty='missing/overlapping appearance must UNKNOWN, never force identity',downstream='C/D/NPR NOT_RUN this round'),
 matching=dict(depth_tolerance_p=2,cycle_px=1.5,world_p=3,min_visible_fraction=.2,max_unknown_fraction=.35,min_known=30,min_dominant=.75),
 limits=dict(unit_seconds=600,round_minutes=65,cpu=2,cap_gib=12,wrap_jst='07:40',stop_jst='08:00'),threshold_tuning=False,historically_exposed=True)
 js(R/'CONFIG.json',cfg)
 (R/'METHOD_FREEZE_ZH.md').write_text('''# r03：非局部可拒绝外观证据，能否突破传播可达性限制

本文件冻结于本轮真实输出之前。先已核验r02 seal/源码HEAD并实际查看四相机全图与总览。r02联合图41,367像素无种子、88,089只触及单类，颜色去除后所有双方已赋类像素类别不变；所以调图边或概率阈值不是本轮机制。r01全高程粗块更完整但盆沿/土与干混淆。r03允许GO执行证伪，不授予分块成功。

## 核心新变量与方程
去掉像素连通传播，用真实source RGB建立固定粗块种子条件颜色密度。每类在16×16×16 RGB网格计数，Gaussian核sigma=.75bin平滑，reflect边界；每view/class先单位质量，再平均两view，所有类别等先验。h_k(c)=归一化(max(G*.hist_k,1e-12))；q_k=h_k/sum_j h_j。只在qmax>=.65、margin>=.2，且赢家密度不低于其构建种子密度5%分位时赋类，其余UNKNOWN。密度阈值来自原构建种子，不是GT校准概率；种子外颜色和重叠颜色必须能拒绝。固定RGB量纲，不逐图归一，不从target高度/位置/连通块填身份；同颜色不同物体本来不可辨识。平滑的是颜色统计网格，**不是检测器、depth或输出图像**。原C2L50、C8核均不变。

三个固定臂：pooled_rgb两实际构建图同预算种子，dev_only仅DEV条件模型（明确样本/view数量不同，是额外view消融），shuffled_labels每view同种子位置/数量、固定RNG1729打乱label，检验身份条件是否有信息。另并列r01粗层、r02传播及v02共享RGB-only K3强基线。本轮不是新Kmeans，也不是v01 graph-cut再调阈值；只估计颜色似然、无邻域优化、不强制seed处输出原label。跨view交叉拟合分别用DEV预测AUX种子、反向亦然，记录冲突/拒绝。这只是与几何种子自洽度，不叫accuracy。

## 三场景可执行范围
Ficus直接复用r02冻结的DEV/AUX原种子像素（每类/相机2048，来源r01粗层中部50%与alpha边距）。原主体mask/负空间逐像素不变。独立颜色可给断连叶片证据，但冠种子有枝木污染，盆/土/木颜色相似；若彩色图好看却主干/土错误，仍NO_GO。不从评估图再种子。
DTU没有合格主体，绝不能照搬Ficus三部件。仅做新的两类**颜色可分性诊断候选**：r02可靠局部深度方向中，旧peripheral池且upright<=20°取背景外观候选1；central池且angle>=35°取主体外观候选2；两类每view最多2048等距索引。都不是GT，方向不可靠/缺类则拒绝。用同条件密度预测全scene alpha>=.5、finite camera-z>.2范围，标签只能称背景外观/中心外观匹配，不称物体部件。对亮屋顶/白地台、暗骨/桌面同色反例做全图核读；主体不完整就A NO_GO，B/C/D NOT_RUN。不得因为出现两种色就过门。

## 相机与门
DEV/AUX固定DTU0000/0024，Ficus train_r_80/train_r_7；reservedDTU0012/0036，Ficus test_r_14/test_r_79。全已历史曝光，DTU源GS训练视角，非blind。先执行构建图、实际核读工程与失败机制后才固定规则输出reserved；无调参。只有seed来自构建图，targetRGB是固定模型推理输入，不能误称新增训练。Ficus主张跨视图收益须胜单DEV与打乱对照，并保盆沿、裸干、叶片/负空间；DTU须全主体/桌面分离，不能删水平颅顶/屋顶。匹配评价复用r02严格2p depth/1.5px cycle/3p world，occluded非反对票，所有方法同门。至少2块满足数值配对仍必须视觉形状正确，不以配对或UNKNOWN下降当成功。
本轮C线边界、D原GS归属、多风格NPR预定NOT_RUN：先验证颜色辨识性。source fullSH、filter/Inf/geometry不变；参考joint是真实旧CPU EWA统一排序，诊断色覆盖不是修改模型或NPR渲染。DTU native RaDe，Ficus vanilla+CPU depth代理；world单位非米。

## TDD / 限制 / 停止
逐API RED→GREEN：相同颜色两类须拒绝，远域颜色拒绝，断开叶片位置不影响密度，视图样本复制不改变平衡质量，类别置换/seed打乱不造身份，零类INVALID，target无seed/高度强赋，主体外像素不进标签，低alpha/无depthUNKNOWN，原ID/源hash/相机完整K重放。概率不是语义后验真值。最大单unit600s/本轮65min、CPU2、总12GiB/root1/HDD10，保留失败，不新模型下载，不GS训练。先freeze再生产，单轮结束seal后退出由runner决定；07:40起只终验。本轮最多一次配置，无科学调参。

## 文献实读边界
重新核读已有作者公开GrabCut全文§2.1–2.2（histogram/data term Eq1–3）和§3（colour GMM、迭代及人工修正）。它明确颜色重叠/伪装及种子影响，本轮只借用类别条件外观这一统计证据；用RGB直方图而非论文GMM，无graph-cut、无人工trimap，**不是GrabCut复现，也不继承自动语义保证**。本轮对照片段和引用写SOURCES.json，公开本地PDF/hash冻结，无需下载模型。
''')
 js(R/'METHOD_FREEZE.json',dict(utc=now(),config_sha256=sha(R/'CONFIG.json'),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),before_new_scientific_results=True))
 review('00_mechanism_GO','GO做条件外观独立证伪：从冻结粗层内部学真实RGB，移除像素可达性依赖；DTU只诊断主体候选颜色可分性，不能越过主体门。r02实际四视图及SOURCE封存核验通过。',[R2/'REPORT_ZH.md',R2/'delivery/ficus_FOUR_VIEWS.jpg',R/'METHOD_FREEZE.json'])
 status('FROZEN',children=[])
if __name__=='__main__':main()
