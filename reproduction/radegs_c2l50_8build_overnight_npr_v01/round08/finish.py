from env import *
import tarfile
RUNTIME={'ASTRA_RUNTIME_FINAL.md','ASTRA_RECOVERY_RUNTIME_FINAL.md','AGENT_LAUNCH.json'}
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
 assert not (R/'ITERATION_STATUS.json').exists();replay=json.loads((R/'RECOVERY_REPLAY_CHECK.json').read_text());assert replay['model_replays']==12 and replay['prediction_replays']==48 and replay['match_replays']==15 and replay['raw_exact_predictions']==12 and replay['raw_exact_models']==3
 assert 'Ran 20 tests' in (R/'logs/14_recovery_regression.txt').read_text() and (R/'logs/14_recovery_regression.txt').read_text().rstrip().endswith('OK');assert not (R/'logs/15_recovery_verify.stderr').read_text()
 for n in ['REPORT_ZH.md','TEST_RESULTS.json','VISUAL_AUDIT.json','STAGE_GATES.json','NEXT_REVIEW.json','CORRECTION_RECEIPT.json']:assert (R/n).exists()
 own=Path.cwd();assert git(own,'status','--porcelain')=='';commit=git(own,'rev-parse','HEAD');js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False));old=rollback();js(R/'ROLLBACK_AFTER.json',old);js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=replay['source_files'],verification='RECOVERY_REPLAY_CHECK.json',old=old));guard()
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={p.name:sha(p) for p in CODE.iterdir() if p.is_file()}));g=json.loads((R/'STAGE_GATES.json').read_text());nxt=json.loads((R/'NEXT_REVIEW.json').read_text());tests=json.loads((R/'TEST_RESULTS.json').read_text())
 (R/'ASTRA_FINAL.md').write_text(f'''# r08 已实际完成并恢复封存：PARTIAL / 精确分块NO_GO

本轮原RGB / 同资格RGB / chromaticity / shuffled四臂，三scene×四历史视角=48原尺寸预测，12密度模型、15双向区域资格。不是新GS或NPR模型；原C8/source几何和全部旧资产保持。

头骨阴影局部形态较完整，但牙/颧部/桌面仍混。建筑屋顶与地台同类。Ficus四view盆类0、主干大部UNKNOWN，不能推荐该全局明暗归一化替代原方案。C/D/多风格NPR NOT_RUN。

用户报告监督器06:31因模型capacity退出；恢复调用未重开科学轮，实际复跑20测试与只读12/48/15 replay。{replay['source_files']}来源、旧main893Python和12worktree核验不变。未封存报告“12图floor标签一致”更正为10/12，两例7817/3个像素变化，原草稿与更正票据保留，数据/参数不改。

实际交付 REPORT_ZH.md、delivery/OVERVIEW.jpg、三scene_FOUR_VIEWS.jpg及负例、48 NPZ、PREVIEWS.tar.gz/DELIVERABLE.tar.gz和独立MEMBERS/SHA。commit `{commit}`，仅本地，无push/merge。此调用仅r08并退出；下一假设局部纹理布局只建议未运行，runner决定后续，07:40起收尾/08:00硬停。
''')
 status('COMPLETE',children=[],scientific_state=g['overall'],tests_passed=tests['new_tests_passed'],new_GS_models=0,styles=0,recovery=True)
 exclude=RUNTIME|{'RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in exclude and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 preview=[p for p in files if (p.parent==R/'delivery' and p.suffix in ['.jpg','.png','.json']) or p.name in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json','CORRECTION_RECEIPT.json'] or (p.name=='CONTEXT.jpg' and p.parent.name in ['0000','train_r_80'])]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',files)];js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=8,state=g['overall'],tests_passed=tests['new_tests_passed'],evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','COUNTS.json','REPLAY_CHECK.json','RECOVERY_REPLAY_CHECK.json','STAGE_GATES.json','CORRECTION_RECEIPT.json'],source_commit=commit,next_hypothesis=nxt['next_hypothesis'],next_allowed=nxt['next_allowed'],sealed=True,utc=now(),stages=g,new_GS_models=0,styles=0,children=[],recovery=True))
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in (RUNTIME|{'RESULTS_MANIFEST.json'}) and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')];js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(static)}))
 from verify import run
 print(json.dumps(dict(verify=run(False),packages=packs,commit=commit),indent=2))
if __name__=='__main__':main()
