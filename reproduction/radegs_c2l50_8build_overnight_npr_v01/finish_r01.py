from env import *
import tarfile
REPORT='''# 通宵实验 r01：方向资格与可见截面结构

本轮结论 **PARTIAL**。Ficus 从颜色碎块进展到可读的盆体—裸露主干—展开冠层候选；但盆沿仍被划入中层，精确部件门未过，不能据此开始多风格 NPR。建筑和头骨主体门仍 NO_GO。原始 C2L50+8BUILD arms/C、source GS、joint 及旧全部实验没有改动。下一轮只能在新冻结机制下继续；本 invocation 不启动 r02。

## 新机制与研究边界
v02 建筑支撑平面实为立面，头骨桌面粘连，Ficus 的共享颜色/位置模型不具备部件拓扑。本轮新增独立的相机姿态信息：从8个原BUILD相机的right向量求使 Σ(right·up)² 最小的共同up，按screen-up定方向。DTU姿态残差2.606°，Ficus接近0；这只是upright代理，不是实测重力。
背景平面必须与up夹角≤20°，原平面距离/支持量/中央分离阈值全部保持v02冻结值，精化后也复查方向。Ficus主体范围沿用真实isolated alpha资格，非全scene alpha语义mask。随后仅对它，用两构建图真实source depth回投样本测量沿up的可见截面跨度，尝试识别“宽—窄—宽”结构，完全不读RGB颜色来拟合部件，也不读取C8线生成mask。没有KMeans、watershed、泛RGB种子graph-cut或旧阈值调参。

研究核读了 Braunstein/Hoffman/Saidpour 1989作者公开PDF的第817页与825页：[原文](https://sites.socsci.uci.edu/~ddhoff/1989-22-PartsExpTest.pdf)。其结果区分负曲率极小与仅仅狭窄点，并提醒旋转曲面实验的适用范围。本轮截面瓶颈不是该minima规则的复现，也不能由论文认证为语义部件。1984 MIT全文访问429，只有元数据/摘要，不声称读到全文。PDF是扫描件，pdftotext空白，实际用页面图阅读；SOURCES_ACCESS原下载状态和LITERATURE_READING.json共同说明。

## 冻结条件与实际执行
原C8线核458490/279616/285956、source核596467/317817/284835保持不变。科学图像只用DEV+AUX：DTU0000/0024，Ficus train_r_80/train_r_7。额外8BUILD相机仅贡献姿态轴，不能说用了8幅新独立图像证据。reserved固定0012/0036及test_r_14/test_r_79，不参与fit/阈值/切点，所有视角历史曝光，DTU也属于源GS训练相机，非blind。
DTU是原native RaDe camera-z；Ficus是vanilla GS CPU条件平面depth代理，非GT。输入float32原RGB/alpha/z、完整fx/fy/cx/cy/W2C与整数像素中心，世界单位非米。原source/C8/真正统一排序joint的图复用v01封存CPU参考，并清楚标记read-only reference；没有把RGB乘线冒充joint，也没有声称本轮重新生成源模型。CPU fullSH/EWA仍非官方CUDA。

## 建筑：拒绝错误身份，但未得到可靠主体
原v02平面与up相差87.576°，因此确实被本轮方向资格挡住。在相同768个三点假设中，165个方向合格，但没有同时过原覆盖/中央资格；方向合格假设最好的双视角最小外围支持为12.783%，低于冻结15%。所有四视图只输出UNKNOWN，不伪造新地台，不将UNKNOWN当背景删主体。
这证实“外围大平面身份缺少方向约束”是旧误认的一部分，同时反驳“加方向就足以分出主体”。不能推论场景没有真实地台：现有外围采样和单平面观测模型未能资格化它。所有假设/角度/覆盖与原平面角度存于delivery/scan24_PLANE_HYPOTHESES.npz及PLANE_AUDIT.json，未降低支持阈值挽救。A NO_GO，B/C/D/NPR NOT_RUN。

## 头骨：方向不是真正首因
原v02平面与up只差4.418°。768假设中648方向合格、372同时通过池内支持/中央筛查；最终源mask在四相机逐像素与v02相同。暗骨/牙齿相对v01仍较完整，但桌面残片和大UNKNOWN带没有改善，0036也保留失败。原深度/支撑平面残差与对象/桌面接触带身份仍是未解决问题；不能靠重新解释同一张图说本轮成功。A NO_GO，B/C/D/NPR NOT_RUN。

## Ficus：真实三大结构候选，边界仍不够精确
主体alpha范围原样保留叶间孔隙与细枝。两构建图各4459个真实可见深度样本，总8918；沿共同up在1%..99%高度范围取32分析bin，每视角每bin至少8点，测量水平5%..95%跨度。全bin都有两视角支持。描述量平滑仅作用截面宽度，不改RGB/depth/线；枚举两个变点、每段至少4bin。共同切点[7,16]；DEV单独[8,16]、AUX[7,16]，符合冻结≤3bin一致门。
三段宽度代理约0.464、0.282、1.166原世界单位；中/下0.608、中/上0.242，三段相对单段log-SSE下降88.5%。这些只是可见截面特征，不是物理半径/实心体积或分类准确率。
实际四视图比v02 K3/RGB-only更容易读出蓝色盆体、橙色裸露干、绿色冠层，且等高度三等分对照把更大片下部叶片划入中层、主干底部划入盆层。可认为本轮对粗结构内部有视觉收益，不能因为总门失败抹去这个进展。
不过自动切点并未落在盆的真实rim：test79土面/盆沿橙色，train80盆肩有UNKNOWN横带；冠层交界是水平粗切面，上层包含高处枝干，绝非“全部木质干 vs 全部叶”的语义分割。test14盆底部分着色来自同高度映射，**不是增加构建视角观测或证明该处source责任**；当前只有高度范围未知门，没有v02的完整三维已观测邻域资格，必须揭示该差异。薄叶/空域保留，但顶底分位之外仍UNKNOWN。图像上看起来更完整也可能来自这个不同的归属先验。

| 冻结对照 | DEV↔AUX | DEV↔test14 | DEV↔test79 |
|---|---:|---:|---:|
| r01截面结构 | 3 | 3 | 3 |
| 相同3标签预算：固定高度三等分 | 3 | 3 | 3 |
| v02共享XYZ/Lab/width K3（旧参考） | 1 | 2 | 1 |

所有新配对都有真实depth投影可见性检查，遮挡/前方不一致/画外/未知分别列出；同色不作为对应依据。但固定三等分也通过，说明这些统计部分来自共同世界高度定义，不能认证语义部件。瓶颈模型主要比三等分更合理地定位粗主体内部，不是从3个配对证明物理三部件。跨相机真正可用于NPR的精确边界门仍 NO_GO；允许的结论是可读内部 PARTIAL。

## 实物、失败保护和下一轮建议
已完成三场景×4原尺寸A图、Ficus两臂×4区域图、6组双向配对，26个独立sealed units。模型、原UV/world样本、height/profile、原候选/UNKNOWN、原/新同图及错误放大全部保留。原C8长刺仍出现在参考ink/joint，未删核或调透明度藏掉。没有新Gaussian、source group、NPR风格或视频；C/D均NOT_RUN，不用漂亮诊断色代替joint多风格。
20本轮测试通过：upright4、support4、section7、matching5；四个API slice先实际RED后GREEN，未放宽数值容差。不是把历史测试充本轮，也不是声称每条断言单独红绿。只读replay重算3个A模型/12张A、Ficus profile与8张B、6组双向配对，数组精确一致。406只读来源文件、旧main893个Python及12工作树HEAD/index/status核验不变，见REPLAY_CHECK.json。CPU2、无需GPU/训练/新模型。各阶段资源远低于12GiB。

下一轮可冻结**从粗块可信内部出发的跨视角界面传播**：以本轮盆体/裸露干/冠层内部为候选种子，利用source-only真实可见像素的局部RGB/depth边界及世界锚定邻接确定盆沿、枝冠接口，比较无外观/无多视角对照；不能只是手调本轮切点。先修精确大区B，不直接赋source核，不提前NPR。DTU暂只作支撑采样资格/可见层诊断，不再放宽半径或z裁切。该建议尚未执行，runner需在下一invocation重新评估冻结。07:40以后只收尾，08:00截止。
'''
def write_new(name,text):
 p=R/name;assert not p.exists();p.write_text(text.strip()+'\n')
def prepare():
 v=json.loads((R/'REPLAY_CHECK.json').read_text());assert (v['A_replays'],v['B_replays'],v['match_replays'])==(12,8,6)
 review('06_R01_SEAL_GO','GO只限本轮文档/安全包/本地提交。真实source406、旧893Python/12工作树及全部数组复算通过。科学状态PARTIAL，精确部件与NPR不合格。允许runner在07:40前以新冻结界面传播假设续轮，不在本invocation启动。',[R/'REPLAY_CHECK.json',R/'STAGE_GATES.json',R/'delivery/FICUS_RIM_test_r_79.jpg'])
 write_new('REPORT_ZH.md',REPORT)
 write_new('FORMAT_ZH.md','''# r01格式
A/<scene>/model：相机upright和背景plane代理；SUBJECT.npz为native candidate/unknown及signed_plane_distance_p。NaN表示无plane或无效深度，不得当0。
B/ficus/model：OBSERVATIONS有原UV/world/view_id，PROFILE有各视角32bin的width/count与共同valid，MODEL给自动切点/数学资格。不是GS核或真面。
B/<view>/profile.npz与equal_thirds.npz：labels0未分配，1下部宽块、2中间窄块、3上部展开；语义身份未认证。unknown独立，联合A mask区分背景。world_height仅实际query像素，不是source_index。
matches保存每采样UV的target_uv/z、state（0unknown/1visible/2occluded/3outside/4front-inconsistent）与target_label；未知/遮挡不反票。
没有source软region，不存在可发布的多风格joint新资产；原source/C8不动。reference joint是已验证的原CPU fullSH/EWA统一排序只读输出。
RESULTS_MANIFEST和包MEMBERS统一{members:{relative:{sha256}}}。不含absolute/../links。ITERATION_STATUS属于sealed结果；ASTRA_RUNTIME_FINAL和AGENT_LAUNCH等外部runner文件排除。''')
 write_new('RUN_COMMANDS.md','''# r01实际命令
工作树 /home/u00134/3dgs_line/gaer_c2l50_8build_overnight_npr_v01，代码 reproduction/radegs_c2l50_8build_overnight_npr_v01。
Python均 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B；共享环境只读。
执行顺序：preflight_r01.py → freeze_r01.py；test_upright.py RED/GREEN；test_support.py RED/GREEN；run_a.py --phase fit；test_section.py RED/GREEN；run_a.py --phase reserved；run_b.py --phase fit；test_match.py RED/GREEN；run_b.py --phase reserved；matching.py；diagnose_r01.py；总20测试；verify.py --readonly --replay；finish_r01.py prepare；本地commit；finish_r01.py package；verify.py --readonly。
测试命令：python -B -m unittest discover -s reproduction/radegs_c2l50_8build_overnight_npr_v01 -p 'test_*.py' -v。
独立复算用verify.py --readonly --replay，不覆盖已封存stdout/数据。每scene/view有SEAL，writer不应重跑到sealed输出。code快照可复现r01，后续轮不得改变本轮封存证据。文献PDF pdftotext为空，实际另渲染第1/9页读取。
''')
 write_new('ASTRA_FINAL.md','''# 第1轮已真实执行
PARTIAL：Ficus粗块内部比v02颜色簇更可读；自动截面切点跨两构建图一致，4视图均有盆/裸露干/冠层候选。但盆沿混入干、上层包含枝，精确部件B NO_GO。等高度三等分也有3配对，不能用配对数宣称准确。建筑A全UNKNOWN（错误立面被拒绝但无合格地台），头骨A与v02相同；其余阶段未跑。NPR/source分组0。
20项本轮测试、12A/8B/6匹配只读重算通过；406源文件/893旧Python/12保护工作树未变。实际图见delivery/OVERVIEW.jpg、ficus_B_FOUR_VIEWS.jpg及盆沿反例。报告REPORT_ZH.md。
本轮封存后退出，由runner在07:40前核验后决定新假设续轮；本invocation没有执行第二轮，不宣称通宵任务已全部完成。''')
 js(R/'TEST_RESULTS.json',dict(passed=20,new_tests=20,inherited_counted=0,vertical_slices=4,red_kind='missing API/module before implementing each slice',tolerances_relaxed=False,log_sha256=sha(R/'TEST_RESULTS.log')))
 js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=v['sources'],verification_sha256=sha(R/'REPLAY_CHECK.json')));js(R/'ROLLBACK_AFTER.json',v['old'])
 js(R/'CODE_FREEZE.json',dict(files={p.name:sha(p) for p in sorted(CODE.iterdir()) if p.is_file()}));status('ROUND_01_COMPLETE_AWAIT_PACKAGE',children=[],scientific_state='PARTIAL')

def safe(n):
 assert n and not Path(n).is_absolute() and '..' not in Path(n).parts and '\\' not in n;return n
def bundle(name,paths):
 p=R/(name+'.tar.gz');assert not p.exists();members={safe(str(f.relative_to(R))):dict(sha256=sha(f)) for f in paths}
 with tarfile.open(p,'w:gz') as t:
  for f in paths:assert f.is_file() and not f.is_symlink();t.add(f,arcname=str(f.relative_to(R)),recursive=False)
 with tarfile.open(p,'r:gz') as t:
  seen=[]
  for m in t.getmembers():
   safe(m.name);assert m.isfile() and not m.issym() and not m.islnk();h=hashlib.sha256();f=t.extractfile(m)
   while True:
    b=f.read(2**20)
    if not b:break
    h.update(b)
   assert h.hexdigest()==members[m.name]['sha256'];seen.append(m.name)
  assert len(seen)==len(members) and set(seen)==set(members)
 js(R/(name+'.MEMBERS.json'),dict(members=members));h=sha(p);(R/(name+'.tar.gz.sha256')).write_text(h+'  '+p.name+'\n');return dict(path=p.name,sha256=h,bytes=p.stat().st_size,member_count=len(members))
def package():
 rollback();guard();p=R/'code';assert not p.exists();p.mkdir()
 for f in CODE.iterdir():
  if f.is_file():shutil.copyfile(f,p/f.name)
 commit=git(CODE,'rev-parse','HEAD');assert commit!='82d0a4eba1b6452aabcc77e742de33b8306af236';js(R/'COMMIT.json',dict(commit=commit,branch=git(CODE,'branch','--show-current'),local_only=True,push=False,merge=False))
 nowdt=datetime.datetime.now(datetime.timezone.utc);wrap=datetime.datetime.fromisoformat('2026-10-19T07:40:00+09:00');allowed=nowdt<wrap
 status('ROUND_01_SEALED',children=[],scientific_state='PARTIAL',next_by_supervisor_only=True)
 js(R/'ITERATION_STATUS.json',dict(round=1,state='PARTIAL',tests_passed=20,evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_B_FOUR_VIEWS.jpg','delivery/FICUS_RIM_test_r_79.jpg','REPLAY_CHECK.json','STAGE_GATES.json'],source_commit=commit,next_hypothesis='在Ficus已有粗块可信内部建立跨视角source-only像素/世界锚定种子图，用局部RGB/depth界面传播而非调高度切点修正盆沿与枝冠交界；无外观/无跨视角强对照。仍属于B精确界面验证，不直接进入C/D/NPR。DTU先诊断背景层采样资格与残差分布，不再放宽旧plane阈值。',next_allowed=allowed,sealed=True,utc=now(),stages=json.loads((R/'STAGE_GATES.json').read_text()),new_GS_models=0,styles=0))
 excludes={'ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json','RESULTS_MANIFEST.json','PACKAGE_INDEX.json','mplconfig'}
 files=[f for f in sorted(R.rglob('*')) if f.is_file() and not f.is_symlink() and f.relative_to(R).parts[0] not in excludes and not f.name.endswith(('.tar.gz','.tar.gz.sha256','.MEMBERS.json'))]
 js(R/'RESULTS_MANIFEST.json',dict(members={str(f.relative_to(R)):dict(sha256=sha(f)) for f in files}))
 previews=[f for f in files if f.relative_to(R).parts[0]=='delivery' and f.suffix=='.jpg']+[R/'REPORT_ZH.md',R/'ASTRA_FINAL.md',R/'B/ficus/model/PROFILE.png']
 rows=[bundle('PREVIEWS',previews),bundle('DELIVERABLE',files+[R/'RESULTS_MANIFEST.json'])];js(R/'PACKAGE_INDEX.json',dict(packages=rows,resources=guard(),runtime_exclusions=['ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json','supervisor runtime outside round'],package_receipt_not_self_sealed=True));print(json.dumps(rows,indent=2))

if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','package']);a=p.parse_args();prepare() if a.phase=='prepare' else package()
