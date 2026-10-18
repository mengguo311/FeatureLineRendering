from env import *
import re
if __name__=='__main__':
 verify=json.loads((ROOT/'VERIFY_REPLAY.log').read_text());assert verify['ok'];guard()
 # Scan ONLY task-owned source, with no credential reads; print no matched values.
 hits=[]
 for p in CODE.iterdir():
  if not p.is_file():continue
  t=p.read_text();
  if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9]{24,}',t):hits.append(p.name)
 assert not hits,hits
 js(ROOT/'SECRET_SCAN.json',dict(scope='task-owned code only',credential_files_read=False,matches=hits,passed=True))
 js(ROOT/'ROLLBACK_AFTER.json',verify['protected_worktrees']);sources=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())['files'].copy();sources.update(json.loads((ROOT/'SOURCE_IMPLEMENTATION_AUDIT.json').read_text())['files']);js(ROOT/'SOURCE_AFTER.json',dict(unchanged=True,files={p:sha(p) for p in sources},compared_count=len(sources)))
 js(ROOT/'CODE_FREEZE.json',dict(files={p.name:sha(p) for p in CODE.iterdir() if p.is_file()},parent_base='24622a61f1c3b1c6d0ca6b42aee8276b4db57587'))
 js(ROOT/'TEST_RESULTS.json',dict(new_total=28,round1=8,round2=12,round3=8,passed=True,log_sha256=sha(ROOT/'TEST_RESULTS.log'),red_logs=[str(p.relative_to(ROOT)) for p in ROOT.glob('round*/tests/RED*.log')],green_logs=[str(p.relative_to(ROOT)) for p in ROOT.glob('round*/tests/GREEN*.log')],threshold_relaxations=0,round2_text_erratum='round2/ERRATA_TEST_COUNT.md',inherited_tests_not_counted_as_new=True))
 js(ROOT/'EXECUTION_EXITS.json',dict(units=[dict(unit=n,exit_code=x,log=path) for n,x,path in [('preflight',0,'PREFLIGHT.log'),('round1',0,'round1/EXECUTION.log'),('round2_models',0,'round2/EXECUTION.log'),('round2_plots',0,'round2/PLOTS.log'),('round3',0,'round3/EXECUTION.log'),('round3_plots',0,'round3/PLOTS.log'),('new_tests',0,'TEST_RESULTS.log'),('readonly_replay',0,'VERIFY_REPLAY.log'),('delivery_mixed_resolution_v00',1,'DELIVERY_PLOTS.log'),('delivery_padding_v01',0,'DELIVERY_PLOTS_GREEN.log')]],all_children_awaited=True,expected_TDD_RED_nonzero=True))
 (ROOT/'delivery_failures/EXPLANATION_ZH.md').write_text('交付总览首版把DTU777x581与Ficus800x800传入要求同形状的panel，触发AssertionError。原失败代码、日志、校准图保留。仅展示层修复：白边填充到800x800，不缩放/拉伸native图，不改任何科学数组/阈值；v01输出另目录。不是第四轮科学迭代。\n')
 review('05_delivery_GO_local_commit_and_package','''三轮严格结束，源责任分组科学NO_GO，诊断工程可交付。28新测试、三scene只读数组/整图source回放、313来源hash和893旧Python/保护worktree已过。实际查看OVERVIEW及scan65 source校准图，CPU差异显示而非掩盖。混合分辨率总览的展示工程失败已保留，以padding修复无科学变化。GO仅允许本地commit本任务源码、封存报告与安全打包；不得push/merge或启动第四轮。''',[ROOT/'TEST_RESULTS.log',ROOT/'VERIFY_REPLAY.log',ROOT/'OVERVIEW.jpg',ROOT/'REPORT_ZH.md',ROOT/'SECRET_SCAN.json'])
 (ROOT/'ASTRA_FINAL.md').write_text('''# 三轮实验交付

恰好3轮、3场景完成；已停止，无自动后续。原科学输入只读C2L50+8BUILD arms/C/source，未使用core筛选标签。

结果：R1条件射线深度纠偏PARTIAL，但与null同增；R2原线22局部模型仅3候选、跨视角0，NO_GO；R3冻结原线patch8次保留验证0通过，7可比不符/1未观测，NO_GO。源责任对局部排序敏感而聚合深度变化较小，不能把sourceID责任直接当稳定物理面片。没有证据说明物体无局部面，只是本方案不具备正式NPR划分资格。

实际产物：176条件测量单元、88局部责任/角色NPZ与诊断点PLY、88排序验证单元、44完整CASE板及配套总88轮次图。28新增测试通过，313来源hash和893旧Python/保护worktree未变，三scene数组与source整图bitexact回放通过，原fullSH/filter/+Inf语义未改。无新训练/mesh/新GS模型/正式NPR修改。所有病例及负结果保留，scan24 roof_marks仍UNAVAILABLE。

报告 REPORT_ZH.md；总览 OVERVIEW.jpg；逐轮 round1/ROUND1_REPORT_ZH.md、round2/ROUND2_REPORT_ZH.md、round3/ROUND3_REPORT_ZH.md；原ID映射 round2/models；只读复验入口 code/verify.py --readonly --replay（工作树实际目录见RUN_COMMANDS）。PREVIEWS.tar.gz与DELIVERABLE.tar.gz及各SHA256/MEMBERS；PACKAGE_INDEX记录实际大小/hash，完整文件与源码清单RESULTS_MANIFEST。所有路径位于本任务HDD根。提交仅新branch，LOCAL_COMMIT.json记录实际HEAD；无push/merge。

科学NO_GO不是工程未执行；第三轮后只完成验证/包装，不启动第四轮。保留原C8/joint作为可直接使用的回退资产。
''')
 for rd in ['round1','round2','round3']:
  if not (ROOT/rd/'SEAL.json').exists():seal(ROOT/rd)
 state('COMPLETE',completed_rounds=3,status='HONEST_NEGATIVE',scientific_verdict='NO_GO_FORMAL_PRIMITIVE',engineering='VALID',children=[],no_automatic_continuation=True,round4_started=False,new_GS_models=0)
