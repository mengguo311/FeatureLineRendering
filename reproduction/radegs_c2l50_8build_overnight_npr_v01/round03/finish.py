from env import *
import tarfile
NEXT='在另一次resume先冻结互补证据耦合：r03非局部条件外观作为可拒绝的一元项，r02经深度/回投资格的局部与跨视角邻接作为成对约束；比较纯外观、纯传播及联合，检验可否同时保住断连叶与盆面连续性，避免盆亮纹归木干。不是调旧阈值/补高度种子；保持原相机、raw/掩码，固定解析控制选择相对权重，不看reserved调参。DTU主体仍NO_GO，可同机制先做小切片，但不得强填亮屋顶/暗牙齿；若无法不同机制证伪就STOP。'

def reports():
 replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert [replay[k] for k in ['model_replays','crossfit_replays','inference_replays','match_replays']]==[9,6,36,18]
 gates=dict(overall='PARTIAL',scientific_qualification='screen-space appearance signal only; precise upstream gates not passed',
  scan24=dict(A='NO_GO',appearance='MATERIAL_SEPARATION_ONLY',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'),
  scan65=dict(A='NO_GO',appearance='PARTIAL_BRIGHT_SUBJECT_AND_TABLE',B='NOT_RUN',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'),
  ficus=dict(A='GO_PROXY_INHERITED_UNCHANGED',B='PARTIAL',B_precision='NO_GO',benefit='disconnected leaf and crown-internal branch appearance evidence',failure='pot highlight/soil vs wood; unknown leaves; insufficient common visibility for pot',C='NOT_RUN',D='NOT_RUN',NPR='NOT_RUN'))
 js(R/'STAGE_GATES.json',gates);js(R/'SOURCE_ROLE_STATUS.json',dict(status='NOT_RUN',reason='Precise subject/part qualification not passed; frozen scope stops before C/D',source_kernel_memberships=0,new_gaussians=0,styles=0,original_C8_untouched=True))
 images=['figures/scan24/0000/FULL.jpg','figures/scan24/0000/SEEDS.jpg','figures/scan24/0036/FULL.jpg','figures/scan65/0000/FULL.jpg','figures/scan65/0036/FULL.jpg','figures/ficus/train_r_80/FULL.jpg','figures/ficus/train_r_7/CONTROLS.jpg','figures/ficus/test_r_14/FULL.jpg','figures/ficus/test_r_79/CONTROLS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/ficus_train_r_80_FAILURE.jpg','delivery/scan65_0036_FAILURE.jpg','delivery/OVERVIEW.jpg']
 js(R/'VISUAL_AUDIT.json',dict(inspected_with_actual_view_image=[dict(path=p,sha256=sha(R/p)) for p in images],reviewer='same execution context; not independent human GT',judgment=gates))
 review('03_science_PARTIAL_delivery_GO','真实三scene四视图已核读。Ficus较r02叶片覆盖和冠内木干有可读收益，强v02 RGB-only控制明显更碎；但盆面高光/土仍误为木干，精确B未过。两view相对单view改变的是赋类覆盖，双方已赋类像素无类别改变，不夸大为身份纠错。建筑屋顶与背景同类；头骨暗骨/牙齿同桌面或UNKNOWN，A不通过。C/D/NPR NOT_RUN。只读9模型/6交叉预测/36原尺寸推理/18配对重放及846来源/旧893py/12树通过，允许封存本轮。',[R/'REPLAY_CHECK.json',R/'delivery/ARM_DIFFERENCES.json',R/'VISUAL_AUDIT.json',R/'STAGE_GATES.json'])
 js(R/'TEST_RESULTS.json',dict(new_tests_passed=20,slices=[dict(name='conditional density',count=8,red='logs/01_density_RED.log',green='logs/01_density_GREEN.log'),dict(name='seed and image partition',count=7,red='logs/02_partition_RED.log',green='logs/02_partition_GREEN.log'),dict(name='visibility-conditioned evidence accounting',count=5,red='logs/03_evidence_RED.log',green='logs/03_evidence_GREEN.log')],regression='logs/REGRESSION_20.log',replay='REPLAY_CHECK.json',inherited_r02_geometry_not_counted_as_new=True,no_tolerance_relaxation=True))
 js(R/'CORE_COMPARE.json',dict(inherited_geometry=dict(original=str(CODE.parent/'round02/geometry.py'),original_sha256=sha(CODE.parent/'round02/geometry.py'),new_sha256=sha(CODE/'geometry.py'),identical=sha(CODE.parent/'round02/geometry.py')==sha(CODE/'geometry.py')),frozen_seed_source='r02 original source pixel seeds, not propagated labels',no_detector_or_C8_changes=True))
 (R/'REPORT_ZH.md').write_text('''# r03：非局部外观证据恢复了部分叶片，但还不能按精确组做NPR

本轮结论 **PARTIAL**。Ficus 相比r02有真实可见进展：原先因像素图断连而未知的叶片，大部分得到颜色证据；木干可以进入叶冠内部，不再只能由固定高度截成上下层。与此同时，盆面亮纹、土面与木干仍混淆，暗叶仍有UNKNOWN，因此精确部件门未过。建筑和头骨的完整主体门继续NO_GO。没有生成新source分组、修改原GS或制作多风格NPR；C8线和原联合模型保留，毛刺也原样展示。

## 为什么换机制
r02实际图和连通审计显示，41,367节点无种子，88,089节点只连接一种种子；去掉颜色之后，双方已赋类的像素没有类别变化。那时主要限制是传播能否到达，不能再靠调边权宣传语义改善。r03先核验r02封存，再写METHOD_FREEZE_ZH/CONFIG，改为从冻结的粗块内部种子估计**非局部类别条件RGB密度**。每个可见像素独立问“它的颜色被哪一类种子支持”，不要求与种子有像素路径，不输入target高度/位置，不强夹种子标签。这个可被反驳的变化是证据来源，不是减少线核或调K。

r03使用16³ RGB直方图，颜色空间平滑sigma=.75bin，1e-12下限后归一化；每view/class质量相同，再平均两构建图。q_k=h_k/sum(h_j)，仅max>=.65、margin>=.2且胜者密度达到构建种子5%分位才赋类。分位先每view计算再等view平均；重叠/未见颜色UNKNOWN。它不是校准语义后验。原float32 RGB不覆写，DTU部分native RGB略超过1，直方图索引饱和到端点bin；RGB_DOMAIN.json逐图记录，既无逐图对比度归一，也没有改原检线输入。

Ficus原种子像素直接读r02，两个构建视角每类2048，共12,288。来源是r01粗层中部50%，不是人工GT；冠种子可能含木枝。DTU两类仅是“外围局部水平色样本”和“中央非水平色样本”，每类/视角2048，来源r02合格局部depth方向；这只是主体候选可分性探针，不是正确前景标注。背景/屋顶同色、暗骨/桌面同色正是预冻反例。

统计思想核读[GrabCut作者公开全文](https://pub.ista.ac.at/~vnk/papers/grabcut_siggraph04.pdf) §2.1–2.2直方图/data term及§3颜色模型、人工修正。这里只取类别条件外观证据；没有执行其GMM/graph-cut迭代，没有人工trimap，不能继承论文分割质量，也不是论文复现。PDF/text来自此前公开封存，并记录hash。

## 真正执行的对照
pooled_rgb：DEV+AUX等view条件密度；dev_only：仅DEV，明确不是相同view/样本预算；shuffled_labels：两图同种子位置、数量和真实RGB，固定1729打乱标签，是同预算身份条件null。旁列r01粗高度、r02图传播和v02共享RGB-only K3强基线。没有重新运行旧方法伪装本轮结果。每scene四图、三臂，共36原尺寸推理；9模型和6次DEV↔AUX种子交叉预测。交叉预测与几何代理标签的一致性不是GT accuracy。
原subject/Ficus负空间mask逐像素不变；DTU在全scene有效alpha/depth内推理，不能称其为subject mask。12图全历史曝光，DTU为原GS训练视角；reserved只指预注册未参与本轮拟合的0012/0036、test_r_14/79，不是blind。原C8仍为8BUILD固定资产，本轮外观模型只用2实际图，不能说8份独立语义观测。

## Ficus：新信息可见，但边界仍错
四视图全图均实际检查。比r02，顶端、底部和侧面断开的叶片较多转为绿色，细木干可在叶冠内部保持橙色；v02 RGB-only把叶片/盆/干按材质明暗切碎，而本轮固定粗角色的条件外观更可读。盆体大部分也比r02碎点更完整。但是盆口和表面亮纹被橙色木干侵入；test_r_79土面仍被当木干，部分浅木/暗叶灰色UNKNOWN，不能正式编辑整个部件。

| 相机 | r02 UNKNOWN | r03 UNKNOWN | r02未知→r03有标签 | 相比单DEV新增有标签 |
|---|---:|---:|---:|---:|
| train_r_80 |21932|15998|15112|6324|
| train_r_7 |20567|15177|14485|17682|
| test_r_14 |23924|16514|17385|8608|
| test_r_79 |23378|14647|17680|9862|

这是覆盖诊断，**不是正确恢复像素数**；另有9178/9095/9975/8949个旧已赋类像素变UNKNOWN。主臂与单DEV双方均已赋类的位置，四图类别变化都是0：增加真实view主要扩展颜色覆盖，不证明纠正了身份。主臂与r02双方已赋类的位置有2465/2992/2851/2318个改变，既包括冠内木干的可读收益，也包括盆亮纹的错误。打乱标签三scene全部输出UNKNOWN，说明有信息来自种子类别与颜色关系，而不是显示程序硬涂三色。
同一严格可见门（depth2p/cycle1.5px/world3p）下，主臂DEV↔AUX只有木干1对通过；与test14/79各木干/冠2对。单DEV三组均1对，打乱0；r01/r02三组各2对。因此本轮视觉改善不能包装成数值配对全面提升。DEV→AUX冠已知配对主类97.9%，但763个可见中290未知（38.0%>冻结35%），拒绝资格；盆共同可见仅102/1116和109/1138，证据不足。未见/遮挡不作反对票，但也不能认证稳定。

## 建筑、头骨：分材料仍不是完整主体
scan24四图红砖立面与灰屋顶明显分成两类，但屋顶/白窗/白地台和背景共享外观，因此“背景类”吞屋顶；0036远处黑背景也有中央色类误入。种子可分不代表主体完整，A NO_GO，B/C/D不运行。不能将这两色改名“屋顶/墙体”绕过主体背景门。
scan65明亮颅顶与大部分桌面分离明显优于r01粘连图；但暗眼眶、牙齿、颌骨和颞侧阴影被归到桌面色或UNKNOWN，0036尤其明显。部分眼窝蓝色可能是真背景可见，部分是暗骨，当前证据不能逐处认证；完整主体A仍NO_GO。两种候选颜色分布重叠系数建筑.344、头骨.367，Ficus木干/冠.525，数值只是颜色统计，不是物理part距离或准确率。

## 当前可用性与下一步边界
Ficus的粗盆/木/叶外观层可作为**可逆图像诊断输入**，是本轮最有希望的结果；尚非固定3D源GS分组或NPR模型。若另开下一轮，可预冻互补耦合：r03条件外观给r02无种子分量提供可拒绝一元证据，r02深度合格的局部/跨view邻接约束连续盆面，比较纯外观、纯传播和联合，检验是否同时保叶与盆面一致。不能通过调当前阈值或高度补种强造成功。此方案**本轮未运行**。
原C8 line-only是XRAY参考，joint参考由旧CPU fullSH/EWA source+ink统一排序，非RGB乘墨迹；新色图只是诊断叠色，没有伪称joint编辑或风格结果。CPU非官方CUDA；DTU原native RaDe与Ficus vanilla+CPU plane-depth代理分别标注，世界单位非米。没有source ID软归属、新高斯、视频或NPR样式，均0/NOT_RUN。

## 可复核工程
20个本轮新测试，三个API切片均先真实ModuleNotFound RED再实现GREEN，整套回归通过；旧r02几何函数逐文件相同不重复算新测试。只读verify逐数组精确重放9密度模型、6交叉预测、36全图推理、18双向对照，846来源hash及旧主893 Python/12工作树HEAD/index/status不变。图表由实际数组生成并hash；无人工GT precision/accuracy。见REPLAY_CHECK、TEST_RESULTS、COUNTS、GATES、RUN_COMMANDS。所有结果含UNKNOWN/失败图，模型和原线均未改。
本invocation只执行r03，封存后退出让runner决定下一次resume；最晚07:40收尾、08:00停止约束不变。
''')
 (R/'FORMAT_ZH.md').write_text('''# r03 独立诊断格式
models/<scene>/<arm>/MODEL.npz：hist float64[K,16,16,16]，threshold[K]，classes；不是GS模型。*_SEEDS.npz给原native uv、proxy label和原尺寸seed_image，标签仅来自构建图，0未种。Ficus1下部盆先验/2中部木先验/3冠先验；DTU1外围水平外观/2中央非水平外观，不能改称语义GT。
inference/<scene>/<arm>/<view>/RESULT.npz：原尺寸labels、unknown、probability、density、inference_mask和source_uv。probability是归一化颜色似然，不是校准语义confidence。source_uv为像素，不是source Gaussian index；本轮不存在GS patch/role映射。原GS/source_index与C8 primitive_id从未混用。
crossfit包含对侧构建图seed预测；对照数字是proxy一致性不是accuracy。evaluation state0无效/1合格可见/2遮挡/3画外/4前方不一致/5cycle或world不合格，未见非负票。所有fields可从旧原始source RGB/alpha/depth+冻结模型readonly精确回放。
图中诊断叠色不是NPR或新joint render；FULL的原C8和true joint列都是明确标注只读旧参考。数据/图片unit各有SEAL；包members相对路径无link/../absolute，sha独立验证；不封存runner runtime文件。
''')
 (R/'RUN_COMMANDS.md').write_text('''# r03 actual commands
CWD: /home/u00134/3dgs_line/gaer_c2l50_8build_overnight_npr_v01
Python: /mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B
All code below is reproduction/radegs_c2l50_8build_overnight_npr_v01/round03. env.py limits task affinity/BLAS to2, no GPU, no shared modification.
1. round02/verify.py --readonly → ROOT/r03_prior_verify.json; git HEAD/status/diff and actual prior images read.
2. freeze.py → SOURCE_MANIFEST/METHOD/CONFIG/ROLLBACK_BEFORE.
3. test_density.py RED→GREEN8; test_partition.py RED→GREEN7.
4. experiment.py --phase fit → logs/FIT.log; actual three-scene build images reviewed.
5. experiment.py --phase reserved → logs/RESERVED.log; unchanged fixed parameters.
6. test_evidence.py RED→GREEN5; python -m unittest discover -s round03 -p 'test_*.py' → logs/REGRESSION_20.log.
7. evaluation.py → logs/EVALUATION.log; delivery.py → logs/DELIVERY.log.
8. verify.py --readonly --replay → REPLAY_CHECK.json; stderr logs/REPLAY.stderr.
9. finish.py --phase reports; local commit ONLY round03 using git add --sparse; finish.py --phase seal → ROOT/r03_seal_receipt.json.
Independent command:
`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B reproduction/radegs_c2l50_8build_overnight_npr_v01/round03/verify.py --readonly --replay`
It does not rewrite sealed artifacts. Production entry skips checked sealed units. No later stage, source-GS optimizer, model download, GPU or subagent ran.
''')
 (CODE/'README.md').write_text('# Overnight r03\n\nNonlocal rejectable seed-conditional RGB density. Real three-scene, four-view diagnostic with pooled/dev-only/shuffled controls. Twenty new TDD tests. Ficus PARTIAL; precise parts and DTU subjects not qualified. Original C8/source/joint immutable. No GS/source-group/style exports.\n\nSee HDD rounds/r03/REPORT_ZH.md. Run `verify.py --readonly --replay` for exact9 models/6 crossfit/36 inference/18 matches and protected-source checks. New round must freeze a distinct mechanism; this entry does not start another round.\n')

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
 assert not (R/'ITERATION_STATUS.json').exists();replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['inference_replays']==36
 own=Path.cwd();commit=git(own,'rev-parse','HEAD');assert git(own,'status','--porcelain')=='';old=rollback();js(R/'ROLLBACK_AFTER.json',old);guard();js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=replay['source_files'],verification='REPLAY_CHECK.json',old=old));js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False))
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={str(p.relative_to(CODE)):sha(p) for p in CODE.iterdir() if p.is_file()}))
 (R/'ASTRA_FINAL.md').write_text(f'''# r03 完成：Ficus外观证据PARTIAL，精确分组未通过

实际完成三场景×四历史相机×三臂=36全图推理，9条件模型、6构建图交叉预测、18双向对照。Ficus断连叶/冠内木干更可读，但盆高光和土仍串为木干；建筑屋顶/背景、头骨暗骨/桌面仍不能可靠分开。原C8/source/joint完全保留，C/D/NPR NOT_RUN，没有新GS或样式。
20新TDD测试通过；只读精确重放通过；846来源hash、旧893py/12树不变。本地commit `{commit}`，无push/merge。看delivery/OVERVIEW.jpg、各scene_FOUR_VIEWS.jpg、失败crop及REPORT_ZH.md。状态允许runner另次resume冻结互补一元外观+合格邻接的证伪机制；本轮不启动下一轮。
''')
 status('COMPLETE',children=[],scientific_state='PARTIAL',tests_passed=20,new_GS_models=0,styles=0)
 excluded={'ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json','RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in excluded and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 preview=[p for p in static if p.suffix in ['.jpg','.png'] or p.name in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json']]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',static)];js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=3,state='PARTIAL',tests_passed=20,evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ARM_DIFFERENCES.json','REPLAY_CHECK.json','STAGE_GATES.json'],source_commit=commit,next_hypothesis=NEXT,next_allowed=True,sealed=True,utc=now(),stages=json.loads((R/'STAGE_GATES.json').read_text()),new_GS_models=0,styles=0,children=[]))
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in ['RESULTS_MANIFEST.json','ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')];js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(files)}))
 from verify import run
 result=run(False);print(json.dumps(dict(packages=packs,verify=result,commit=commit),ensure_ascii=False,indent=2))
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--phase',choices=['reports','seal'],required=True);a=p.parse_args();reports() if a.phase=='reports' else finalseal()
