from env import *
import tarfile
NEXT='冻结一种非局部、可拒绝的粗块种子条件外观模型：只用r01可信内部的真实RGB建立类别条件证据，跨视角交叉检验，不依赖像素连通或目标高度填色；与原高度及无外观对照。检验断连叶片是否有独立证据，土面/木干/暗叶混淆为否决项，不把材质等同物理部件。DTU仍不得越过主体门；可另冻结局部支撑层观测一致性诊断，不放宽r02图边阈值。'
def reports():
 replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['fit_graph_replays']==3 and replay['target_replays']==6 and replay['dtu_replays']==8 and replay['match_replays']==15
 gates=dict(overall='NO_GO',scan24=dict(A='NO_GO',new_diagnostic='COMPLETE',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'),scan65=dict(A='NO_GO',new_diagnostic='COMPLETE',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'),ficus=dict(A='GO_PROXY_INHERITED_UNCHANGED',B='NO_GO',local_rim='PARTIAL',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'),reason='Frozen graph improves some pot rim, but fragmented/unknown leaves and almost no RGB-driven class changes; no precise part qualification.')
 js(R/'STAGE_GATES.json',gates);js(R/'SOURCE_ROLE_STATUS.json',dict(status='NOT_RUN',reason='B precise part gate failed',source_kernel_memberships=0,new_gaussians=0,styles=0,original_C8_untouched=True))
 images=['figures/ficus/train_r_80/FULL.jpg','figures/ficus/train_r_80/CONTROLS.jpg','figures/ficus/train_r_80/SEEDS.jpg','figures/ficus/test_r_14/FULL.jpg','figures/ficus/test_r_79/CONTROLS.jpg','A_DIAGNOSTIC/scan24/0000/FULL.jpg','A_DIAGNOSTIC/scan65/0036/FULL.jpg','delivery/COMPONENTS_train_r_80.jpg','delivery/RIM_test_r_79.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ficus_FOUR_VIEWS.jpg']
 js(R/'VISUAL_AUDIT.json',dict(inspected_with_actual_view_image=[dict(path=p,sha256=sha(R/p)) for p in images],reviewer='same execution context, not independent human/second model',judgment=gates,confidence_heatmap_legend_correction='FULL confidence panels: black=zero/no anchored probability; gray=fractional maximum. Separate colored UNKNOWN overlay is gray. Original caption grey UNKNOWN was imprecise; sealed original figures retained.'))
 review('04_final_science_NO_GO','完整四视图实际核读：Ficus盆沿局部改善，但上/下叶与盆面碎点UNKNOWN；无颜色与主臂双方已赋类像素无一类别变化，未知变化不能当精确分块提升。建筑背景方向呈弯曲条带，头骨桌面局部多水平但颅顶也可水平，单方向非主体身份。A/B原失败门未过，C/D/NPR全部NOT_RUN。允许下一次resume仅新机制冻结，不在本invocation启动。只读重放3模型/6目标/8DTU/15双向对照通过。',[R/'REPLAY_CHECK.json',R/'delivery/COMPONENT_AUDIT.json',R/'delivery/ARM_DIFFERENCES.json',R/'VISUAL_AUDIT.json'])
 js(R/'TEST_RESULTS.json',dict(new_tests_passed=18,slices=[dict(name='harmonic',tests=6,red='logs/01_harmonic_RED.log',green='logs/01_harmonic_GREEN.log'),dict(name='geometry',tests=7,red='logs/02_geometry_RED.log',failed_first_green='logs/02_geometry_GREEN.log',green='logs/02_geometry_GREEN_final.log'),dict(name='seeds',tests=4,red='logs/03_seeds_RED.log',green='logs/03_seeds_GREEN.log'),dict(name='solver repair',tests=1,red='logs/04_solver_repair_RED.log',green='logs/04_solver_repair_GREEN.log')],regression='logs/REGRESSION_18.log',replay='REPLAY_CHECK.json',old_r01_tests_not_recounted=True,no_tolerance_relaxation=True))
 js(R/'CONFIG_EXECUTED.json',dict(config_frozen_sha=sha(R/'CONFIG.json'),scientific_parameters_changed=False,numerical_amendment='ENGINEERING_AMENDMENT.json',affinity_formula='max(exp(-sumRGB2/(2*.12^2)),1e-5)/max(world_distance_p,1); floor is color affinity before distance division',source_images=2,target_images=2,target_height_seeds=0,no_source_or_ink_parameter_changes=True))
 (R/'REPORT_ZH.md').write_text('''# r02：粗块内部种子与跨视角界面传播

本轮科学结论 **NO_GO（精确分块）**，并非没有局部收益。Ficus部分盆沿比r01归属合理，但新增图传播不能完整归属叶冠，盆面也产生UNKNOWN碎点，暂不适合按精确组制作多风格NPR。建筑和头骨完成新深度观测诊断，主体门仍未通过；没有把它们的法线色图冒充多块分区。原C8、source GS、joint、r01全保持原样。本invocation仅r02，下一轮由runner另行resume。

## 真实新机制与对照
核验r01封存并实际看全图后，预先写METHOD_FREEZE_ZH/CONFIG。本轮不是再调高度切点，也不是v01图cut或v02 KMeans。r01固定粗层内部中央50%作为自动候选种子，每视图/类别2048，离alpha边界至少2px；这是假设性内部，不是人工GT。两构建图146662个真实可见像素构成图，四邻接以世界点间距<=4p约束；同位置不同相机必须depth差<=2p、往返<=1.5px、world差<=3p才连边。p=z/sqrt(fx*fy)，单位不是米。
主臂joint_rgb把RGB边界阻抗和31876条合格跨视角边加入图，求固定种子下的调和概率；independent_rgb去掉构建图跨边，joint_no_rgb仅去颜色权。三臂同源图、同种子、同局部几何图和标签预算。无锚连通片UNKNOWN；max概率>=.65且margin>=.2才赋类，概率是条件于图与种子的到达概率，**不是语义正确率**。保留图不使用新高度种子；从DEV/AUX冻结概率经可见投影传入，再在目标图做固定规则推理，不反馈修改训练图。independent对照仅在构建阶段无跨边，目标仍从两独立构建结果转移，不能称完全单视角方法。
算法依据为Grady2006作者全文§III A/B Eq1、8–12：[Random Walks for Image Segmentation](https://leogrady.net/wp-content/uploads/2017/01/grady2006random.pdf)。论文的图种子传播不保证自动语义部件；跨视角门、自动粗层种子及UNKNOWN是本轮适配。公开PDF首次TLS证书错误，单次curl -k获取并hash，未改全局配置。具体执行中1e-5是颜色亲和度下限，之后除世界距离因子，见CONFIG_EXECUTED明确歧义。

## Ficus：不是更多投票就修好了边界
实际四视图均检查。DEV与test79盆沿外圈从r01橙色转到蓝色，局部更接近盆体；**土面仍橙色**，上层枝干仍与叶冠角色混杂，未实现精准盆/木/叶语义。大片顶叶、低叶和盆面碎点变UNKNOWN，不能将这些灰色看作删除后更干净。原主体alpha范围逐像素保持，叶间空隙无填补，原C8所有毛刺仍存在。
图的限制可直接定位：联合图9299个连通分量；41367节点没有种子，88089只连到一种种子类，只有17206节点处于多类竞争分量。无种子就无法传播，单一标签分量无论颜色如何都只有该候选身份。去跨视角后无锚节点48056，说明跨边确实恢复了部分传播可达性，但没有等量带来新部件判别信息。

| 相机 | 主体像素 | 主臂UNKNOWN | 主臂vs无颜色不同像素 | 两臂均已赋类但类别不同 |
|---|---:|---:|---:|---:|
| train_r_80 |75408|21932|81|0|
| train_r_7 |71254|20567|70|0|
| test_r_14 |69003|23924|76|0|
| test_r_79 |79309|23378|763|0|

这反驳了“本轮RGB边界已经决定了精确身份”的强解释。对比去跨边臂，构建两图改变3616/3384像素，但双方已赋类者类别改变为0；test14/79分别只有2/94个。主要变化是UNKNOWN与已赋类的互换，而非修正错误部件边界。局部盆沿改善也在无颜色臂出现，不能归功于RGB识别。
本轮对所有方法统一用较严格2p+cycle可见资格重新评价：r01、r02三臂在DEV↔AUX/test14/test79均只有中/上两类满足双向资格；v02 RGB-only为0/1/0。r01旧报告的3对用了不同可见门，不能直接当退步数字。盆的少量共同可见像素通常100%同标签，但共同可见比例不足20%，因此是**证据覆盖不足**，不是负票证明盆身份错误。高一致度仍不能替代真实盆沿/叶片视觉门。

## 建筑与头骨：完成新的上层失败诊断，没有越门
使用原native RaDe浮点depth的2px差分与3×3稀疏邻域，完整K/W2C计算局部切向/法线代理。九点有效、跨度<=8p、切平面残差<=2p才记录方向；没有使用source最短cov轴，没有拟合或改GS。方向与共同up夹角<=20°只标局部upright，不自动认台面。
scan24 DEV有79376个局部upright像素，其中62119不在旧外围池；AUX为35842，其中15304在池外。局部水平观测并非完全没有，但白背景/地台方向出现明显卷曲条带和碎片，屋顶局部也可水平，旧错误立面与这些upright仅少量交集。证据不支持把整个白背景当单一可靠承托平面；也不证明存在可恢复真地台。主体A继续NO_GO。
scan65 DEV/AUX有218576/195426个upright像素，主要桌面在图上更可见，但颅顶、局部凹凸同样可能接近水平，桌面/背景也有方向条带。0036完整图保留顶盖、牙齿及桌面失败。方向是几何观测而不是主体语义，不能直接删除所有水平像素。因此A继续NO_GO，B/C/D均NOT_RUN。

## 工程修复、重放与来源边界
新18个测试通过，四个API切片实际RED→GREEN，包括病态弱连接链；不是重用历史20个测试冒充本轮。局部normal转float32导致严格解析角度失败，改为float64，未松容差。真实颜色图CG3000次收敛失败或概率越界，保留ENGINEERING文件；只对相同线性系统使用稀疏LU fallback，不改权重/边/种子/门，残差降到约1e-15。无颜色已通过的封存单元不重算覆盖。这是同轮工程修复，不是额外科学轮。
只读verify --replay逐数组精确重放3构建图模型、6目标推理、8 DTU方向图和15双向方法/视角对照；全部来源和旧main893py/12工作树HEAD/index/status核验。具体数与resources见REPLAY_CHECK。只读旧source/C8/joint图明确标reference：CPU fullSH/EWA非官方CUDA；图中诊断颜色仅可视化，不是source SH编辑或新joint模型。source/line索引仍独立，本轮没有source kernel归属或新Gaussian，C/D/NPR/视频全部0/NOT_RUN。
置信度灰度图原标题“grey UNKNOWN”不够精确：黑色是无锚概率0，灰是部分概率，真正UNKNOWN请看彩色分区中的灰覆盖；原封存图不覆盖，VISUAL_AUDIT记录该说明。无GT，所有统计不是accuracy/precision。12原相机均历史曝光，DTU为源GS训练视角；reserved仅预冻结对照，不叫blind。Ficus源vanilla+CPU条件plane camera-z，不能和DTU native RaDe或GT混称。

## 后续边界
本轮不推荐替代r01粗结构图，更不进入正式NPR。可以另冻一个**非局部种子条件外观**证伪：检查断连叶片是否有不依赖像素路径的新证据；必须保留土面/主干/暗叶混淆及无外观对照，不把材质当物理部件，不补种、不放松本轮图边。该机制尚未运行，runner下一invocation决定，07:40后只收尾，08:00截止。
''')
 (R/'RUN_COMMANDS.md').write_text('''# Actual r02 commands
All commands use readonly scientific Python `official_code_fix_v01/env/bin/python -B`, code cwd `gaer_c2l50_8build_overnight_npr_v01`. `env.py` restricts affinity to two available CPUs and numerical threads2; no GPU.

1. r01 `verify.py --readonly` → ROOT/r01_check_before_r02.json.
2. round02/freeze.py → frozen method, source hashes and rollback.
3. test_harmonic.py RED then GREEN; test_geometry.py RED, failed float32 GREEN, float64 GREEN; test_seeds.py RED/GREEN.
4. experiment.py --phase fit → FIT.log (two engineering failures retained).
5. test_solver_repair.py RED/GREEN; unittest discover -s round02 -p 'test_*.py' → REGRESSION_18.log.
6. experiment.py --phase fit → FIT_REPAIR.log (skip valid sealed no-RGB unit).
7. experiment.py --phase reserved → RESERVED.log.
8. dtu_diagnostic.py → DTU.log.
9. evaluate.py → EVALUATION.log; delivery.py → DELIVERY.log.
10. verify.py --readonly --replay → REPLAY_CHECK.json + logs/REPLAY.stderr.
11. finish.py --phase reports; local git add/commit ONLY round02; finish.py --phase seal.

Independent read-only replay:
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B reproduction/radegs_c2l50_8build_overnight_npr_v01/round02/verify.py --readonly --replay`
It reads current sealed arrays and checks hashes, never rewrites them. Do not rerun writing production entry into a sealed round. Stages skip verified seals; failure logs and r01 remain unchanged.
''')
 (R/'FORMAT_ZH.md').write_text('''# r02 诊断格式
B/<arm>/fit/GRAPH.npz：每view按row-major原mask像素排列；view_offsets分段，i/j是该联合像素节点索引，**不是source Gaussian ID**；seeds 0未锚/1下粗层/2中粗层/3上粗层，probability是调和soft概率。各view NPZ source_uv给精确原像素，labels/unknown/probability为原尺寸。目标新增prior_gamma/prior_probability，无高度seed；world由原source camera-z与完整相机可回放。
A_DIAGNOSTIC/<scene>/<view>/LOCAL_DEPTH：float64 normal/angle/planarity/extent，valid门，upright方向代理，peripheral/central旧采样范围和old_plane_signed_p；不是GS surface normal/主体mask/新plane。
evaluation：各方法同门双向投影，state0无效、1合格可见、2遮挡、3画外、4前方不一致、5cycle/world不合格。没有负票替代未见。
所有色图都是诊断显示，原C8线及source未变。source核软归属/多风格NPR NOT_RUN，勿把像素regionID当source_index或primitive_id。包相对路径、无symlink；MEMBERS统一members/path/sha256，hash独立核验。
''')
 # Small aspect-preserving English overview.
 items=[]
 for s in SCENES:
  v=DEV[s];rgb,_,a=raw(s,v)
  if s=='ficus':old=npz(R1/'B/ficus'/v/'profile.npz');new=view_result_local(v);a1=colors(rgb,old['labels'],old['unknown']);a2=colors(rgb,new['labels'],new['unknown']);tag='r02: fragmented regions / UNKNOWN'
  else:
   old=npz(R1/'A'/s/v/'SUBJECT.npz');new=npz(R/'A_DIAGNOSTIC'/s/v/'LOCAL_DEPTH.npz');lab=np.zeros(a.shape,np.uint8);lab[new['valid']]=2;lab[new['upright']]=1;a1=overlay(rgb,old['candidate'],old['unknown']);a2=colors(rgb,lab,(a>=.1)&~new['valid']);tag='r02: direction evidence, NOT parts'
  for label,im in [('Source',rgb),('r01',a1),(tag,a2)]:
   pi=Image.fromarray(np.uint8(np.clip(im,0,1)*255));pi.thumbnail((800,800));canvas=Image.new('RGB',(800,800),'white');canvas.paste(pi,((800-pi.width)//2,(800-pi.height)//2));items.append((s+' | '+label,np.asarray(canvas)/255))
 panel(R/'delivery/OVERVIEW.jpg',items,'Overnight r02 | Precise parts NO_GO | Local evidence retained','DTU subject gates unchanged; Ficus rim partly improved, crown coverage insufficient. No source edit or NPR style claim.',3)
 (CODE/'README.md').write_text('# Overnight r02\n\nActual seeded multiview harmonic propagation and DTU local-depth-direction diagnostics. 18 new tests; scientific NO_GO for precise parts. Original source/C8/r01 readonly. See HDD rounds/r02/REPORT_ZH.md and RUN_COMMANDS.md.\n\nverify.py --readonly --replay checks all sealed arrays, source hashes, protected worktrees. No source groups/styles or GS modifications. Future round must independently freeze a distinct hypothesis.\n')
def view_result_local(v):
 from experiment import view_result
 return view_result(v,'joint_rgb')
def archive(name,files):
 p=R/(name+'.tar.gz');assert not p.exists();members={}
 with tarfile.open(p,'w:gz',compresslevel=5) as tf:
  for f in sorted(files):
   rel=str(f.relative_to(R));assert not f.is_symlink() and not Path(rel).is_absolute() and '..' not in Path(rel).parts;members[rel]=dict(sha256=sha(f));tf.add(f,arcname=rel,recursive=False)
 with tarfile.open(p,'r:gz') as tf:
  assert set(tf.getnames())==set(members)
  for m in tf:
   assert m.isfile() and not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts;assert hashlib.sha256(tf.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
 js(R/(name+'.MEMBERS.json'),dict(members=members));(R/(name+'.tar.gz.sha256')).write_text(sha(p)+'  '+p.name+'\n');return dict(path=p.name,bytes=p.stat().st_size,members=len(members),sha256=sha(p),verified=True)
def finalseal():
 assert not (R/'ITERATION_STATUS.json').exists();assert json.loads((R/'REPLAY_CHECK.json').read_text())['fit_graph_replays']==3
 own=Path.cwd();commit=git(own,'rev-parse','HEAD');assert git(own,'status','--porcelain')=='';old=rollback();js(R/'ROLLBACK_AFTER.json',old);guard();js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=len(json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']),verification='REPLAY_CHECK.json',old=old));js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False))
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={str(p.relative_to(CODE)):sha(p) for p in CODE.iterdir() if p.is_file()}))
 (R/'ASTRA_FINAL.md').write_text(f'''# r02 已完成：精确分块 NO_GO

真实执行Ficus三臂×四历史相机、DTU两场景×四全图方向诊断。盆沿部分改善，但UNKNOWN叶冠/盆面碎片明显，颜色与跨视角尚未给出足够精确身份。C/D/source成员/NPR/视频未运行，没有新GS模型。原资产未改。
18新测试通过；只读3构建图/6目标/8方向图/15双向方法对照精确重放通过，旧main893py与12工作树不变。见REPORT_ZH.md、delivery/OVERVIEW.jpg、delivery/ficus_FOUR_VIEWS.jpg、delivery/RIM_test_r_79.jpg。
本地commit `{commit}`，无push/merge。下一轮只允许新机制冻结，不在此调用执行；建议见ITERATION_STATUS。runner保留07:40收尾/08:00停止规则。
''')
 status('COMPLETE',children=[],scientific_state='NO_GO',tests_passed=18,new_GS_models=0,styles=0)
 excluded={'ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json','RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in excluded and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 preview=[p for p in static if p.suffix in ['.jpg','.png'] or p.name in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json']]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',static)];js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=2,state='NO_GO',tests_passed=18,evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/COMPONENT_AUDIT.json','REPLAY_CHECK.json','STAGE_GATES.json'],source_commit=commit,next_hypothesis=NEXT,next_allowed=True,sealed=True,utc=now(),stages=json.loads((R/'STAGE_GATES.json').read_text()),new_GS_models=0,styles=0,children=[]))
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in ['RESULTS_MANIFEST.json','ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')];js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(files)}))
 from verify import run
 result=run(False);print(json.dumps(dict(packages=packs,verify=result,commit=commit),ensure_ascii=False,indent=2))
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['reports','seal'],required=True);a=p.parse_args();reports() if a.phase=='reports' else finalseal()
