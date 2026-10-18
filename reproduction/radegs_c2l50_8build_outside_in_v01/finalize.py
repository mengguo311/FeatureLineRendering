from env import *
import tarfile,io

def safe(n):
 p=Path(n);return not p.is_absolute() and '..' not in p.parts and len(p.parts)>0

def package(name,paths):
 paths=sorted(set(paths));members={}
 for p in paths:
  assert p.is_file() and not p.is_symlink();n=str(p.relative_to(ROOT));assert safe(n);members[n]=dict(sha256=sha(p))
 side=ROOT/(name+'.MEMBERS.json');js(side,dict(members=members));archive=ROOT/(name+'.tar.gz')
 with tarfile.open(archive,'w:gz') as t:
  for p in paths:t.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
 with tarfile.open(archive,'r:gz') as t:
  got=t.getmembers();assert len(got)==len(members)
  for m in got:
   assert m.isfile() and safe(m.name) and not m.issym() and not m.islnk();h=hashlib.sha256(t.extractfile(m).read()).hexdigest();assert h==members[m.name]['sha256']
 h=sha(archive);(ROOT/(archive.name+'.sha256')).write_text(h+'  '+archive.name+'\n');return dict(path=archive.name,bytes=archive.stat().st_size,sha256=h,members=len(members),all_member_hashes_verified=True)

def prepare():
 v=json.loads((ROOT/'VERIFY_REPLAY.json').read_text());assert v['source_files']==88 and len(v['replayed_joint'])==3 and len(v['replayed_masks'])==4 and v['B_hierarchy_replays']==12
 assert 'Ran 26 tests' in (ROOT/'TEST_RESULTS.log').read_text() and '\nOK\n' in (ROOT/'TEST_RESULTS.log').read_text()
 review('07_delivery_GO','GO交付已执行的有界pilot和负结果，不代表科学分区成功。26项本轮测试通过；只读回放3scene joint与4mask bitexact、12层级一致、144+9全N校准，893旧Python和9保护worktree未变。A建筑/头骨NO_GO，Ficus A GO/B NO_GO；C/D NOT_RUN。可以本branch仅提交新源码、封存图/配置/报告及安全包；不继续研究或模型生成。',[ROOT/'VERIFY_REPLAY.json',ROOT/'TEST_RESULTS.log',ROOT/'REPORT_ZH.md'])
 js(ROOT/'TEST_RESULTS.json',dict(new_tests=26,inherited_tests_counted=0,slices=dict(core=9,protocol=8,regression=4,hierarchy=5),RED=['RED_CORE.log','RED_PROTOCOL.log','RED_HIERARCHY.log','negative_engineering/ASSERTION_DEPTH_STEP_RED.log'],GREEN=['GREEN_CORE.log','GREEN_PROTOCOL.log','GREEN_HIERARCHY_V01.log','REGRESSION_ANALYTIC.log','TEST_RESULTS.log'],known_engineering_failure_fixed_before_real_B=True))
 before={}
 for n in ['SOURCE_MANIFEST.json','DEPENDENCY_MANIFEST.json','ADDITIONAL_DEPENDENCIES.json']:before.update(json.loads((ROOT/n).read_text())['files'])
 after={p:sha(p) for p in before};assert before==after;js(ROOT/'SOURCE_AFTER.json',dict(files=after,unchanged=True));js(ROOT/'ROLLBACK_AFTER.json',rollback())
 js(ROOT/'CODE_FREEZE.json',dict(files={str(p.relative_to(CODE)):sha(p) for p in sorted(CODE.iterdir()) if p.is_file()}))
 (ROOT/'RUN_COMMANDS.md').write_text('''# 实际命令与退出记录

工作树：`/home/u00134/3dgs_line/gaer_c2l50_8build_outside_in_v01`，branch `gaer-c2l50-8build-outside-in-v01`。
以下 python 均为只读科学env `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B`；脚本位于新reproduction子目录。所有子命令由工具session监督并等待返回，没有daemon/cron。CPU affinity≤2。

1. `preflight.py` → PREFLIGHT.log，0。只读输入/旧树hash/论文获取。
2. `freeze.py` → FREEZE.log，0。OUTLINE/CONFIG/PLAN_SEAL先于新mask。
3. `test_core.py` → RED_CORE.log，1（缺新API）；实现后GREEN_CORE.log，0，9项。
4. `run_stage_a.py --phase dev` → DEV_EXECUTION.log，0，3真实DEV单元。
5. `test_protocol.py` → RED_PROTOCOL.log，1；实现后GREEN_PROTOCOL.log，0，8项。
6. `review_dev.py` → DEV_REVIEW.log，0；`run_stage_a.py --phase remaining` → REMAINING_EXECUTION.log，0，9单元。
7. `test_regression.py` → REGRESSION_ANALYTIC.log，0，4项；`evaluate_transfer.py` → TRANSFER_EXECUTION.log，0，48臂/视角对。
8. `review_a.py` → REVIEW_A.log，0，仅Ficus GO B；`test_hierarchy.py` → RED_HIERARCHY.log，1缺API；首次实现GREEN_HIERARCHY.log实际1，depth-step断言失败，文件名不代表成功。保留v00和负日志。修复后GREEN_HIERARCHY_V01.log，0，5项。
9. `run_stage_b.py` → B_EXECUTION.log，0，Ficus4视角×3臂，36层级图；`finish_science.py` → SCIENCE_STOP.log，0，停止科学阶段；`matched_scope.py` →0，已有标签解释图。
10. `test_runner.py` → TEST_RESULTS.log，0，共26新测试；`verify.py --readonly --replay` → VERIFY_REPLAY.json/stderr，0。未改封存unit。
11. `finalize.py prepare` →交付评估/保护核验；本地git只add本任务新源码、commit，无push/merge；`finalize.py package` →安全路径/成员hash检查。

复核使用 `verify.py --readonly --replay`。它只输出JSON，不修补旧结果；如保存新日志，不覆盖已封存VERIFY_REPLAY。一次性freeze/review脚本拒绝覆写。Stage A对已完成unit检查seal后跳过。不要在当前封存root重跑B生产脚本。全部旧模型/环境只是依赖路径，不进入归档。
''')
 final='''# ASTRA_FINAL

已完成一次真实三场景outside-in pilot；中文大纲在结果前冻结。12原尺寸相机A候选/对照/真joint，Ficus条件B12视角-臂单元、36层级图，负结果全部保留。

- scan24：A NO_GO。亮屋顶面漏选，0036白地台误入；B/C/D NOT_RUN。
- scan65：A NO_GO。暗骨面/牙齿附近漏选，桌面误入；B/C/D NOT_RUN。
- Ficus：A主体proxy GO；B NO_GO。DEV/AUX主层级跨视角大区配对0，不能稳定分为盆/干/叶群；C/D NOT_RUN。

26本轮测试通过。3scene新joint与4mask readonly replay bitexact；12B层级和48A transfer回放一致；144+9 all-N查询校准；88直接依赖hash、旧893Python及9受保护worktree HEAD/index/status未变。无源GS/原线修改，无新GS模型/物理primitive、source正式区域标签、视频或mesh。CPU近似非官方CUDA、Ficus深度非native RaDe，历史视角非blind。

图：delivery/OVERVIEW.jpg、三scene *_FOUR_VIEWS.jpg、B_MATCH_SCOPE.jpg。报告：REPORT_ZH.md、OUTLINE_ZH.md、FORMAT_ZH.md。下载：PREVIEWS.tar.gz与DELIVERABLE.tar.gz，SHA与独立MEMBERS随附。新branch仅本地commit，见COMMIT.json；不push/merge。完成一个pilot后停止，没有第四阶段或自动下一方向。
'''
 (ROOT/'ASTRA_FINAL.md').write_text(final)
 state('COMPLETE',status='PARTIAL',children=[],completed_pilots=1,expected_pilots=1,completed_scenes=3,stage_A=dict(scan24='NO_GO',scan65='NO_GO',ficus='GO_PROXY_ONLY'),stage_B=dict(scan24='NOT_RUN',scan65='NOT_RUN',ficus='NO_GO'),stage_C='NOT_RUN',stage_D='NOT_RUN',no_automatic_continuation=True,tests_passed=26)


def pack():
 guard();snap=ROOT/'code';snap.mkdir(exist_ok=True)
 for p in CODE.iterdir():
  if p.is_file():shutil.copyfile(p,snap/p.name)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=CODE).decode().strip();status=subprocess.check_output(['git','status','--porcelain'],cwd=CODE).decode();assert not status;js(ROOT/'COMMIT.json',dict(branch='gaer-c2l50-8build-outside-in-v01',head=commit,local_only=True,pushed=False,merged=False,clean=True))
 excluded={'AGENT_LAUNCH.json','ASTRA_RUNTIME_FINAL.md','stdout.log','stderr.log','launch.py','setup_remote.py','RESULTS_MANIFEST.json','PACKAGE_INDEX.json'}
 files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name not in excluded and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json')) and 'mplconfig' not in p.parts]
 for p in files:assert not p.is_symlink()
 js(ROOT/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(ROOT)):dict(sha256=sha(p)) for p in files},excluded_runtime=sorted(excluded),source_hashes=str(ROOT/'SOURCE_AFTER.json')))
 overview=list((ROOT/'delivery').glob('*.jpg'));docs=[ROOT/n for n in ['REPORT_ZH.md','OUTLINE_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','COUNTS.json','STAGE_A_GATE.json','STAGE_B_GATE.json','B_SCOPE_CLARIFICATION_ZH.md']]
 previews=package('PREVIEWS',overview+docs)
 deliver=package('DELIVERABLE',files+[ROOT/'RESULTS_MANIFEST.json']);assert previews['bytes']<20*2**20;js(ROOT/'PACKAGE_INDEX.json',dict(packages=[previews,deliver],resources=guard(),postseal_shipping_receipt=True))
 print(json.dumps([previews,deliver],indent=2))
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','package']);a=p.parse_args();prepare() if a.action=='prepare' else pack()
