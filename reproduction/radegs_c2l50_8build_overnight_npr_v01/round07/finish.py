from env import *
import tarfile

def archive(name,files):
 p=R/(name+'.tar.gz');assert not p.exists();members={}
 with tarfile.open(p,'w:gz',compresslevel=5) as tf:
  for f in sorted(files):
   rel=str(f.relative_to(R));assert not f.is_symlink() and not Path(rel).is_absolute() and '..' not in Path(rel).parts;members[rel]=dict(sha256=sha(f));tf.add(f,arcname=rel,recursive=False)
 with tarfile.open(p,'r:gz') as tf:
  assert set(tf.getnames())==set(members)
  for m in tf:assert m.isfile() and not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and hashlib.sha256(tf.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
 js(R/(name+'.MEMBERS.json'),dict(members=members));(R/(name+'.tar.gz.sha256')).write_text(sha(p)+'  '+p.name+'\n');return dict(path=p.name,bytes=p.stat().st_size,members=len(members),sha256=sha(p),verified=True)

def main():
 assert not (R/'ITERATION_STATUS.json').exists();replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['render_replays']==36 and replay['model_replays']==9 and replay['prediction_replays']==36 and replay['match_replays']==12
 assert json.loads((R/'MECHANISM_REPLAY.json').read_text())['counts_exact']
 for n in ['REPORT_ZH.md','TEST_RESULTS.json','VISUAL_AUDIT.json','STAGE_GATES.json','NEXT_REVIEW.json']:assert (R/n).exists()
 own=Path.cwd();assert git(own,'status','--porcelain')=='';commit=git(own,'rev-parse','HEAD');js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False));old=rollback();js(R/'ROLLBACK_AFTER.json',old);js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=replay['source_files'],verification='REPLAY_CHECK.json',old=old));guard()
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={p.name:sha(p) for p in CODE.iterdir() if p.is_file()}));g=json.loads((R/'STAGE_GATES.json').read_text());nxt=json.loads((R/'NEXT_REVIEW.json').read_text());tests=json.loads((R/'TEST_RESULTS.json').read_text())
 (R/'ASTRA_FINAL.md').write_text(f'''# r07 已执行完成：PARTIAL

实际源GS颜色三臂fullSH/DC/DEV-anchor，三scene×四原尺寸相机×三臂=36 source-only真实渲染，9密度模型、36预测、12双向区域资格。原geometry/filter/opacity/排序完全不变，源文件/原C8不改。

DC减少Ficus盆高光的错误木质条纹，test14明显；test79未知增加、anchor退化。建筑屋顶/地台与头骨暗骨/桌面仍分不清。局部收益可确认，精确部件门未过，C/D/多风格NPR NOT_RUN，0新GS模型/视频。不能将DC视为albedo。

本轮25测试通过，36/9/36/12 readonly replay精确，{replay['source_files']}来源及旧893Python/12树保持。两个显示工程失败完整保留，最终用delivery/native/*/FULL_CORRECTED.jpg；混尺寸图只白边pad，无重采样。源index颜色数组仅证据，不是部件labels。

REPORT_ZH.md、delivery/OVERVIEW.jpg及三scene FOUR_VIEWS/坏例、PREVIEWS.tar.gz与DELIVERABLE.tar.gz为实际交付。commit `{commit}`，未push/merge。本invocation只r07，封存退出；候选标量照度不变量机制仅建议、未执行，07:40起收尾/08:00停止规则不变。
''')
 status('COMPLETE',children=[],scientific_state=g['overall'],tests_passed=tests['new_tests_passed'],new_GS_models=0,styles=0)
 exclude={'ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json','RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in exclude and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 preview=[p for p in files if (p.parent==R/'delivery' and p.suffix in ['.jpg','.png','.json']) or p.name in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json','ENGINEERING_LABEL_ADDENDUM.json']]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',files)];js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=7,state=g['overall'],tests_passed=tests['new_tests_passed'],evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','mechanism_audit/COUNTS.json','REPLAY_CHECK.json','STAGE_GATES.json','ENGINEERING_LABEL_ADDENDUM.json'],source_commit=commit,next_hypothesis=nxt['next_hypothesis'],next_allowed=nxt['next_allowed'],sealed=True,utc=now(),stages=g,new_GS_models=0,styles=0,children=[]))
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in ['RESULTS_MANIFEST.json','ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')];js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(static)}))
 from verify import run
 print(json.dumps(dict(verify=run(False),packages=packs,commit=commit),indent=2))
if __name__=='__main__':main()
