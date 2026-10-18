from env import *
def main():
 prior=json.loads((ROOT/'r08_prior_verify.json').read_text());assert prior['manifest_verified'] and prior['packages_verified'];prev=json.loads((R7/'ITERATION_STATUS.json').read_text());assert prev['sealed'] and prev['next_allowed'] and prev['round']==7
 assert git(Path.cwd(),'rev-parse','HEAD')=='05fd7a23206069563f5e19dfcfa1370d1b557bfe';assert not (R/'METHOD_FREEZE.json').exists();R.mkdir(exist_ok=True);(R/'reviews').mkdir(exist_ok=True);(R/'logs').mkdir(exist_ok=True)
 js(R/'ROLLBACK_BEFORE.json',rollback());js(R/'RESOURCE_PREFLIGHT.json',guard())
 sources=json.loads((R7/'SOURCE_MANIFEST.json').read_text())['files']
 for p in R7.rglob('*'):
  if p.is_file() and p.name not in ['ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz'):sources[str(p)]=sha(p)
 for folder in ['round07','round03']:
  for p in (CODE.parent/folder).glob('*.py'):sources[str(p.resolve())]=sha(p)
 js(R/'SOURCE_MANIFEST.json',dict(files=sources,read_only=True))
 cfg=dict(round=8,mechanism='positive scalar intensity quotient of ORIGINAL cached RGB, not SH ablation',arms=['raw_rgb','rgb_floor','chromaticity','shuffled_chromaticity'],feature=dict(chroma='x/sum(x) for eligible samples only',floor_max_channel=.02,nonnegative=True,finite=True,shuffle_seed=1729,shuffle='each BUILD view across eligible seed rows, labels/UV unchanged; targets not shuffled'),scene_roster={s:views(s) for s in SCENES},fit_views={s:[DEV[s],AUX[s]] for s in SCENES},reserved=RES,classifier=dict(implementation='unchanged r03/density.py',bins=16,sigma=.75,threshold_quantile=.05,posterior=.65,margin=.2,view_and_class_mass_equal=True,seeds='original r03 proxy seed UV/labels',mask='exact r03 inference_mask; ineligible becomes UNKNOWN, no deletion'),expected=dict(models=12,predictions=48,ficus_matches=15),limits=dict(cpu=2,root_reserve_gib=1,hdd_reserve_gib=10,task_cap_gib=12,unit_seconds=300,round_minutes=40,latest_new_science_JST='07:40'),no_tuning=True,downstream='C/D/source-membership/NPR NOT_RUN',historically_exposed=True)
 js(R/'CONFIG.json',cfg)
 (R/'METHOD_FREEZE_ZH.md').write_text('''# r08 方法冻结：去除标量明暗的颜色比例对照

## 前轮证据与执行 GO
已核验r07状态、报告、OVERVIEW和Ficus盆负例；2247来源与893旧主Python、12旧worktree、所有封存成员通过只读校验。r07 DC在test_r_14减少盆高光被判木，但盆土/枝冠仍混，test_r_79 UNKNOWN增加；不是可用多部件成功。v02 K3/K5全图和A/B门亦已复查：建筑地台与屋顶同色、头骨桌面/暗骨粘连、Ficus盆吞干不能用配对个数认证。本轮HEAD05fd7a2，前轮commit及全部负结果只读。

新假设不是再次改K/平滑/graph/阈值，也不再次改SH：固定原source缓存RGB，取颜色比例 c(x)=x/(R+G+B)。对正标量a，在资格不变时c(ax)=c(x)。因此可直接证伪“整体明暗变化造成同一部件颜色分散”这一机制。它不是反照率、白平衡或物理光照校正；存储RGB不保证线性辐射，叠加高光、彩色照明、半透明混合不满足该模型。不同灰材质全部退化同一点是预注册反例，建筑白屋顶/白地台很可能无法分开。若真实实体边界没有改善，不能把颜色更平滑当成功。

## 四臂、输入、预算完全预冻
raw_rgb严格重放r03原RGB密度（含原全部seed）。rgb_floor采用与chroma完全相同的资格，只去掉不可靠近黑值，以分离门控与特征变化。chromaticity使用归一颜色。shuffled_chromaticity用每BUILD view seed1729排列合格seed特征，但保持原UV/labels，保留整体特征多重集/类别数量；目标推理仍真实chroma，不用目标图训练。它是故意破坏关联的null，不能叫增强。
统一资格finite、每通道非负、max(R,G,B)>=.02。0.02是预定数值稳定代理（非校准噪声），不因scene/图再改。低值保留为UNKNOWN，不当背景/不从mask删。禁止invalid除法及eps强制造颜色。每类别每view至少1合格seed，否则该arm工程NOT_READY，不回填/松门。三个新臂严格相同eligible seed数量及推理mask。原r03 16³ histogram、sigma=.75、class/view均等质量、5%自身密度门、posterior .65/margin .2保持。每臂重新fit自己的BUILD特征，不复用不匹配的旧density。
来源仅原C8关联的source RGB/alpha/camera-z缓存；DTU官方native RaDe777x581 COLMAP、Ficus vanilla GS+CPU plane proxy800²，世界单位非米。C8核/原source文件不改；无core-line标签输入。无需新渲染source，原v01 source/C8 xray/true joint图为明确标注的只读context，不冒称本轮生成联合模型。r07 DC只作既有强外观对照，r05图模型/v02 RGB-only为强历史对照。

## 相机、阶段与可负门
DEV DTU0000/Ficus train_r_80；AUX0024/train_r_7；reserved0012/0036、test_r_14/test_r_79。全历史曝光；DTU源GS训练view，不称blind。fit仅DEV+AUX，全部模型与BUILD图审后才统一reserved一次，不后验修改参数。12模型、48全尺寸预测、Ficus四臂+r05的15组DEV到AUX/reserved双向资格诊断。Ficus先end-to-end，再同方案DTU，单scene错误不吞其它。DTU两类只叫peripheral-horizontal/central-nonhorizontal seed proxies，绝不当真实前景语义；Ficus三类叫pot/wood/crown priors，不是GT。
A科学门仍是完整屋顶/牙齿、地台/桌面分离；B是Ficus盆/干/冠及叶间空隙完整、共同可见身份稳定。与raw、同floor RGB、r05/r07DC比较，更多UNKNOWN和更少墨不算提高。跨视图沿旧2p depth、1.5px roundtrip、3p world/可见20%/已知30点/unknown<=35%/dominance75%门不变，遮挡不负票。数字不是语义精度，颜色图是诊断，不是NPR风格。无人工GT不报accuracy。
本轮C线边界/D源软成员/正式NPR全部NOT_RUN。不会为了新颜色图绕过上游失败门。若仅一局部更好可PARTIAL，全部无效则NO_GO；必须同时保存暗部误伤、灰材质不可辨识、盆土/枝叶混合负例。最多本轮一次冻结实验，无调参回合。

## TDD、资源和停止
逐行为实际RED→GREEN：正标量不变、灰材质坍缩反例、加性高光不不变、低值/NaN/负值UNKNOWN、归一有限、原数组不变、null多重集与seed预算、fit拒reserved、原RGB精确重放、同mask全覆盖及不强赋标签。新测试与只读继承测试分开。独立verify重算12models/48predictions/15matches和原RGB数组、旧hash、封存单元。CPU2，单unit300秒、本轮40分钟，ROOT12GiB/root1/HDD10门；07:40必须收尾，08:00终止；本调用不启动r09。图片英文图例、中文报告；安全包、local commit无push。runtime AGENT_LAUNCH/ASTRA_RUNTIME_FINAL不静态封存。
''')
 js(R/'METHOD_FREEZE.json',dict(utc=now(),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),config_sha256=sha(R/'CONFIG.json'),prior_commit=git(Path.cwd(),'rev-parse','HEAD'),before_new_science=True))
 review('00_intensity_quotient_GO','独立机制及灰材质/暗部反例已冻结。执行许可不等科学成功。先TDD和Ficus双BUILD，不授予source标签或NPR资格。',[R7/'REPORT_ZH.md',R7/'delivery/OVERVIEW.jpg',R/'METHOD_FREEZE.json']);status('FROZEN',children=[])
if __name__=='__main__':main()
