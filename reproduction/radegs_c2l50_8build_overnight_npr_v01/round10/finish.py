from env import *
import tarfile

RUNTIME={'ASTRA_RUNTIME_FINAL.md','ASTRA_RECOVERY_RUNTIME_FINAL.md','AGENT_LAUNCH.json'}

def archive(name,files):
 p=R/(name+'.tar.gz');assert not p.exists();members={}
 with tarfile.open(p,'w:gz',compresslevel=5) as tf:
  for f in sorted(files):
   rel=str(f.relative_to(R));assert f.is_file() and not f.is_symlink() and not Path(rel).is_absolute() and '..' not in Path(rel).parts
   members[rel]=dict(sha256=sha(f));tf.add(f,arcname=rel,recursive=False)
 with tarfile.open(p,'r:gz') as tf:
  assert set(tf.getnames())==set(members)
  for m in tf:
   assert m.isfile() and not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
   assert hashlib.sha256(tf.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
 js(R/(name+'.MEMBERS.json'),dict(members=members));(R/(name+'.tar.gz.sha256')).write_text(sha(p)+'  '+p.name+'\n')
 return dict(path=p.name,bytes=p.stat().st_size,members=len(members),sha256=sha(p),verified=True)

def main():
 assert not (R/'ITERATION_STATUS.json').exists()
 replay=json.loads((R/'REPLAY_CHECK.json').read_text())
 assert [replay[k] for k in ['feature_views_replayed','model_replays','prediction_replays','match_replays','RGB_hist_exact_models','support_multisets_checked']]==[12,6,24,6,6,12] and replay['analytic_replayed']
 assert 'Ran 18 tests' in (R/'logs/09_regression.txt').read_text() and (R/'logs/09_regression.txt').read_text().rstrip().endswith('OK')
 assert not (R/'logs/12_verify.stderr').read_text()
 for n in ['REPORT_ZH.md','TEST_RESULTS.json','VISUAL_AUDIT.json','STAGE_GATES.json','NEXT_REVIEW.json','FINAL_REPORT_ZH.md','OVERNIGHT_INDEX.json','CLOSURE_ENGINEERING_RECEIPT.json']:assert (R/n).exists()
 own=Path.cwd();assert git(own,'status','--porcelain')==''
 commit=git(own,'rev-parse','HEAD');js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False))
 old=rollback();js(R/'ROLLBACK_AFTER.json',old);js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=replay['source_files'],verification='REPLAY_CHECK.json',old=old));guard()
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={p.name:sha(p) for p in CODE.iterdir() if p.is_file()}))
 g=json.loads((R/'STAGE_GATES.json').read_text());nxt=json.loads((R/'NEXT_REVIEW.json').read_text());tests=json.loads((R/'TEST_RESULTS.json').read_text())
 index=json.loads((R/'OVERNIGHT_INDEX.json').read_text());assert index['prior_rounds_verified']==9 and index['rounds'][-1]['round']==10
 # Keep the reviewed pre-commit index immutable. Its r10 entry explicitly resolves
 # source_commit through COMMIT_RECEIPT; final ITERATION_STATUS also records it.
 (R/'ASTRA_FINAL.md').write_text(f'''# r10 已执行：NO_GO；停止新科学轮

三场景各4历史视角，两新臂，共12特征视图、6密度模型、24分区、6Ficus双向资格实际运行并独立重放。18本轮测试通过；2次API真实RED/GREEN，不把历史测试计入。

有限支持在解析同薄物体换背景中使特征变化为0；真实Ficus盆底局部改善，盆缘/木枝仍缺。主臂与错位alpha互配2/1/1，等于r09；DTU全scene覆盖不能解决楼/地台、骨/桌身份。源核成员和正式多风格NPR均NOT_RUN，无新GS或原核改动。

3557来源、62单元、旧main893Python与12树通过检查。前9轮静态seal与包SHA复核；FINAL_REPORT_ZH与OVERNIGHT_INDEX保留每轮实际状态/负例，未重跑旧科学也未制造r11。当前没有充分证据再冻结独立科学机制，next_allowed=false。此停止不证明自动分块不可能。

本地commit `{commit}`，未push/merge。PREVIEWS/DELIVERABLE独立成员SHA及安全路径核验。原C8/joint仍为回退入口。root FINAL_REPORT_ZH/FINAL_OVERVIEW/ROUND_INDEX是本轮已完成证据的副本；runtime文件另存，不覆盖本报告。
''')
 status('COMPLETE',children=[],scientific_state=g['overall'],tests_passed=tests['new_tests_passed'],new_GS_models=0,styles=0,next_allowed=False)
 exclude=RUNTIME|{'RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in exclude and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 preview=[p for p in files if (p.parent==R/'delivery' and p.suffix in ['.jpg','.png','.json']) or p.name in ['REPORT_ZH.md','FINAL_REPORT_ZH.md','FINAL_OVERVIEW.jpg','OVERNIGHT_INDEX.json','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json'] or (p.name=='CONTEXT.jpg' and p.parent.name in ['0000','train_r_80'])]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',files)];js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=10,state=g['overall'],tests_passed=tests['new_tests_passed'],evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ANALYTIC.jpg','COUNTS.json','MATCH_COUNTS.json','REPLAY_CHECK.json','STAGE_GATES.json','FINAL_REPORT_ZH.md','OVERNIGHT_INDEX.json'],source_commit=commit,next_hypothesis=nxt['next_hypothesis'],next_allowed=False,sealed=True,utc=now(),stages=g,new_GS_models=0,styles=0,children=[],stop_reason=nxt['reason'],prior_rounds_static_verified=9))
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in (RUNTIME|{'RESULTS_MANIFEST.json'}) and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')]
 js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(static)}))
 from verify import run
 verified=run(False)
 # Publish copies only after round seal and safe packages pass; root files are new.
 published={}
 for src,name in [('FINAL_REPORT_ZH.md','FINAL_REPORT_ZH.md'),('FINAL_OVERVIEW.jpg','FINAL_OVERVIEW.jpg'),('OVERNIGHT_INDEX.json','ROUND_INDEX.json')]:
  q=ROOT/name;assert not q.exists();shutil.copyfile(R/src,q);assert sha(q)==sha(R/src);published[name]=dict(sha256=sha(q),sealed_source=str(R/src))
 js(ROOT/'FINAL_PUBLICATION.json',dict(round=10,source_commit=commit,round_seal_sha256=sha(R/'RESULTS_MANIFEST.json'),files=published,new_science_stopped=True,next_allowed=False,utc=now()))
 print(json.dumps(dict(verify=verified,packages=packs,commit=commit,published=published),indent=2))

if __name__=='__main__':main()
