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
 assert not (R/'ITERATION_STATUS.json').exists();replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['native_arrays_checked']==24 and replay['match_replays']==9 and replay['crossfit_replays']==6 and replay['audit_replays']==6
 for f in ['REPORT_ZH.md','STAGE_GATES.json','NEXT_REVIEW.json','TEST_RESULTS.json','VISUAL_AUDIT.json']:assert (R/f).is_file()
 own=Path.cwd();commit=git(own,'rev-parse','HEAD');assert git(own,'status','--porcelain')=='';old=rollback();js(R/'ROLLBACK_AFTER.json',old);guard();js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=replay['source_files'],verification='REPLAY_CHECK.json',old=old));js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False))
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={p.name:sha(p) for p in CODE.iterdir() if p.is_file()}))
 gates=json.loads((R/'STAGE_GATES.json').read_text());nxt=json.loads((R/'NEXT_REVIEW.json').read_text());tests=json.loads((R/'TEST_RESULTS.json').read_text())['new_tests_passed']
 (R/'ASTRA_FINAL.md').write_text(f'''# r05 实际完成：{gates['overall']}

新机制是撤回被另一构建视角外观模型反驳的代理hard seed，逐类同预算random为对照，原r04 coupled只读baseline。三场景、四历史相机、两新臂共24原尺寸输出；6构建图、12目标推理、9双向方法对照。原source/C8未改，source GS成员/线成员/NPR均NOT_RUN。

具体视觉收益、误分和机制限制见REPORT_ZH.md与delivery/OVERVIEW.jpg。{tests}个本轮新测试和精确readonly重放通过；6个other-view模型预测也独立复算，图/一元等核心数组与r04相同。来源{replay['source_files']}个文件、旧893Python/12worktrees核验未变。commit `{commit}`，未push/merge。

本invocation只执行r05并退出，next_allowed={nxt['next_allowed']}。下一轮需另次resume重新冻结；本轮没有运行它。07:40开始收尾/08:00停止规则保持。
''')
 status('COMPLETE',children=[],scientific_state=gates['overall'],tests_passed=tests,new_GS_models=0,styles=0)
 exclude={'ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json','RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in exclude and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 refs={R/'figures'/s/DEV[s]/'FULL.jpg' for s in SCENES};preview=[p for p in files if ('delivery' in p.parts and p.suffix in ['.jpg','.png']) or p in refs or p.name in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json']]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',files)];js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=5,state=gates['overall'],tests_passed=tests,evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','mechanism_audit/COUNTS.json','REPLAY_CHECK.json','STAGE_GATES.json'],source_commit=commit,next_hypothesis=nxt['next_hypothesis'],next_allowed=nxt['next_allowed'],sealed=True,utc=now(),stages=gates,new_GS_models=0,styles=0,children=[]))
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in ['RESULTS_MANIFEST.json','ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')];js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(static)}))
 from verify import run
 print(json.dumps(dict(verify=run(False),packages=packs,commit=commit),indent=2))
if __name__=='__main__':main()
