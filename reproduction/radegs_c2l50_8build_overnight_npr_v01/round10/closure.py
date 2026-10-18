from env import *

MECHANISMS=[
 ('上方向、支撑平面与粗横截面','Ficus盆/裸干/冠出现可读粗层；等高度null亦能配对，非语义认证。'),
 ('可见跨视角稀疏图传播','无种子和单类分量占主导，背景/部件身份没有新增证据。'),
 ('非局部RGB条件证据','补回叶片及断连区域，但高光盆纹、土面、冠内木枝混淆。'),
 ('图连续性与外观一元联合','当前更有用的粗结构诊断：叶冠、盆、裸干及颅骨主体更连续；精确门仍失败。'),
 ('独立另一BUILD反驳后撤回硬种子','真实改变约束；多数冲突仍被邻接/外观支配，未恢复关键部件。'),
 ('负空间与局部形态厚度','投影形态和覆盖混杂，薄叶/枝与冠仍难分，DTU无合格主体mask。'),
 ('full SH / DC / 固定方向颜色干预','DC改善盆高光条纹，冠内木枝与保留视角退化；不是完整材料/部件恢复。'),
 ('像素明暗商归一化','头骨暗区局部改善；Ficus盆全部拒绝、木类近乎消失。容量中断后完成同轮工程续接。'),
 ('局部RGB纹理布局','代理种子更可分，真实盆缘/木枝与建筑屋顶更不完整。'),
 ('有限alpha支持归一化','解析背景污染被阻止，真实主臂未改善部件互配；r10 NO_GO。')]

def main():
 assert not (R/'OVERNIGHT_INDEX.json').exists()
 guard();rows=[]
 for i in range(1,10):
  p=ROOT/'rounds'/f'r{i:02}';st=json.loads((p/'ITERATION_STATUS.json').read_text());assert st['round']==i and st['sealed']
  manifest=json.loads((p/'RESULTS_MANIFEST.json').read_text())['members']
  for n,x in manifest.items():
   f=p/n;assert not Path(n).is_absolute() and '..' not in Path(n).parts and f.is_file() and not f.is_symlink() and sha(f)==x['sha256'],(i,n)
  packs=[]
  package_index=p/('PACKAGE_INDEX.json' if i==1 else 'PACKAGES.json')
  package_rows=json.loads(package_index.read_text())
  if i==1:package_rows=package_rows['packages']
  for x in package_rows:
   q=p/x['path'];assert q.is_file() and sha(q)==x['sha256'],q;packs.append(dict(path=str(q),sha256=x['sha256']))
  rows.append(dict(round=i,state=st['state'],tests_passed=st['tests_passed'],source_commit=st['source_commit'],status_sha256=sha(p/'ITERATION_STATUS.json'),manifest_sha256=sha(p/'RESULTS_MANIFEST.json'),static_members_checked=len(manifest),report_path=str(p/'REPORT_ZH.md'),report_sha256=sha(p/'REPORT_ZH.md'),packages_sha_checked=packs,mechanism=MECHANISMS[i-1][0],finding=MECHANISMS[i-1][1],previous_science_reexecuted_here=False))
 rows.append(dict(round=10,state='NO_GO',tests_passed=18,source_commit=None,source_commit_receipt='COMMIT_RECEIPT.json',report_path=str(R/'REPORT_ZH.md'),report_sha256=sha(R/'REPORT_ZH.md'),replay_path=str(R/'REPLAY_CHECK.json'),mechanism=MECHANISMS[9][0],finding=MECHANISMS[9][1],seal_completed_only_when_iteration_status_exists=True))
 js(R/'OVERNIGHT_INDEX.json',dict(rounds=rows,prior_rounds_verified=9,prior_tests_not_rerun_or_recounted_as_new=True,expected_latest_round=10,new_rounds_after_r10=0,stop_new_science=True,reason='No sufficiently justified independent mechanism under current frozen observations and automatic identity proxies; no parameter-only r11.',utc=now()))
 items=[]
 from experiment import result
 for s in SCENES:
  v=DEV[s];rgb,_,_=raw(s,v);g=npz(R4/'B'/s/'coupled'/'fit'/(v+'.npz'))
  a=result(s,v,'alpha_texture');items.extend([(s+'/'+v+' | Original source RGB',rgb),('r04 coupled | coarse diagnostic only',colors(rgb,g['labels'],g['unknown'])),('r10 supported texture | NO_GO',colors(rgb,a['labels'],a['unknown']))])
 from delivery import pad
 panel(R/'FINAL_OVERVIEW.jpg',pad(items),'Completed evidence | coarse readability improves; precise identity remains unqualified','All historical DEV frames. Fixed diagnostics, not multi-style GS. Weak views and failures remain in each round report.',3)
 table='\n'.join('| r%02d | %s | %s | %s | %d |'%(x['round'],x['mechanism'],x['state'],x['finding'],x['tests_passed']) for x in rows)
 (R/'FINAL_REPORT_ZH.md').write_text('''# 夜间实验终验：粗分块有进展，精确部件与同模型多风格NPR尚未达标

本次持续任务实际执行了r01—r10；不是十次成功分区。各轮保留独立冻结、程序、对照、全图、测试及负结果。r08出现模型容量中断，随后同轮续接完成封存，未改名成新增科学轮。r10在真实三场景结果后判NO_GO，完成终验后停止新科学；没有启动r11或用阈值微调填满到08:00。当前没有足够证据支持另一项独立身份机制，不等于证明未来方法不可能。

## 现在可以用什么
**正式回退入口仍是原C2L50+8BUILD arms/C及原source+line joint。** 原线与源高斯均保留，不重采样、不移动、不调SH/opacity/filter。夜间新增的是分区诊断数组与可复算对照，未产生认证源核软组或正式多风格模型。

**Ficus：r04联合图的粗结构最值得保留为后续诊断起点。** 相比单RGB及断连图，叶片、盆体和裸干更连续，叶间负空间保持。但冠内木枝被冠吞、盆土误当木、盆高光横纹仍错；互配的木/冠不等于完整盆—干—冠认证。r07 DC对盆面高光有局部收益，也会恶化枝冠及保留视角，不能直接拼成一个已执行的最佳模型。

**scan65：r04主体候选更连贯，r08暗区有局部改善；完整A仍失败。** 牙齿、暗颅/孔洞、桌面接触关系没有可靠分开，因此没有正式颅—面颌分组。**scan24：没有合格A。** 屋顶/白窗框/地台的共同外观和支撑方向混杂贯穿各轮；彩色面积大不是找回完整建筑。

## 每轮真实证据索引
| 轮次 | 独立机制 | 封存科学状态 | 主要观察与边界 | 当轮新测试通过 |
|---|---|---|---|---:|
'''+table+'''

测试按轮保留，不把合计称为互不重复的语义测试。r04求解工程修复保持同方程及数值门；r06预期负例另列；r08容量续接和草稿校正单独留证；r09测试契约修正记录原失败。完整日志、真实RED/GREEN范围及容差说明以各轮TEST_RESULTS和REPORT为准。此次终验重查前九轮静态manifest与包SHA，没有声称重跑十轮全部科学求解。

## 最新r10说明了什么
真实变量是只在原alpha支持下计算局部RGB梯度/张量，避免把无覆盖背景卷入。解析同一薄物体换背景，归一特征变化0，而无条件变化0.60837；实现的因果干预成立。实际DTU全scene alpha接近1，无法隔离楼/地台或骨/桌。Ficus有低alpha背景，盆底局部恢复却仍盆缘未知、冠内木丢失；主臂和错位alpha的跨视角配对均2/1/1，与r09相同。有限支持不足以恢复部件身份，不能由解析成功跳到NPR。

本轮6新模型、24新分区、12特征视图、6双向资格全部只读精确复算；18新测试通过，62单元seal通过。r10 SOURCE_MANIFEST的3557项来源及旧main893 Python、12受保护工作树HEAD/status/index核验未变。各轮数组是代理标签，不是逐物理面的GT分类准确率；UNKNOWN不应直接删模型。

## 为什么现在不做正式多风格
目标需要同一joint模型中的source软成员与固定线成员能跨视角解释一致。当前误分来自可见身份的不充分，而不仅是线是否闭合或局部颜色是否平滑。source alpha是scene覆盖，协方差不是认证法线，核ID责任受排序影响；纯重复投影不能提供独立部件真值。上游A/B没有通过的场景没有进入C线边界资格或D源核归属，更没有在错误分块上做漂亮风格。NPR正式输出为0，不能把2D区域着色或旧joint图当多风格成功。

后续若用户另授权，优先补可独立验证的少量部件身份约束/评价证据，或新的无歧义跨视角观测机制；先对固定难例验证完整边界与负空间，再检验source软责任。不建议继续无新证据地换K、sigma、阈值或传播强度。本轮没有采集标注、下载模型或偷偷引入这种外部输入。

## 获取与复核
本目录REPORT_ZH是r10详细报告，FINAL_OVERVIEW是原RGB/r04粗候选/r10的同相机完整画面对照，delivery包含三场景四视角与坏例。OVERNIGHT_INDEX给出所有旧轮报告、commit与hash，原各轮PREVIEWS/DELIVERABLE完整保留。r10 PREVIEWS含本终验报告与图，DELIVERABLE含新代码、冻结、日志、数组和来源依赖；不打包原GS或旧env。

相机全历史曝光，DTU为原GS训练视角，不叫blind/GS-heldout；DTU为native RaDe缓存，Ficus为vanilla GS+CPU深度代理。原joint是CPU fullSH/EWA统一排序，不声称官方CUDA等价。没有push/merge、新模型下载、GPU、训练、mesh或源核编辑。最终本地commit与包封存以COMMIT_RECEIPT、ITERATION_STATUS和RESULTS_MANIFEST为准；runtime输出不进静态seal。本调用到此收尾退出，不启动新轮。
''')
 review('05_close_existing_evidence_GO','允许只读汇总实际r01—r10，不将旧测试重算新数，不新运行r11。前九轮状态sealed、成员hash和原包SHA核验通过。r10科学NO_GO，粗结构局部收益保留；正式源核分组和多风格NOT_RUN。',[R/'OVERNIGHT_INDEX.json',R/'FINAL_REPORT_ZH.md'])
 print(json.dumps(dict(prior_rounds_verified=9,static_members_checked=sum(x.get('static_members_checked',0) for x in rows),summary=str(R/'FINAL_REPORT_ZH.md'),new_science=False),indent=2))

if __name__=='__main__':main()
