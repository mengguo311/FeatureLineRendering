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
 assert [replay[k] for k in ['feature_views_replayed','model_replays','prediction_replays','match_replays','raw_exact_models','raw_exact_predictions']]==[12,12,48,15,3,12]
 assert 'Ran 19 tests' in (R/'logs/10_regression.txt').read_text() and (R/'logs/10_regression.txt').read_text().rstrip().endswith('OK')
 assert not (R/'logs/13_verify.stderr').read_text()
 for n in ['REPORT_ZH.md','TEST_RESULTS.json','VISUAL_AUDIT.json','STAGE_GATES.json','NEXT_REVIEW.json','TDD_CONTRACT_CORRECTIONS.json']:assert (R/n).exists()
 own=Path.cwd();assert git(own,'status','--porcelain')==''
 commit=git(own,'rev-parse','HEAD');js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False))
 old=rollback();js(R/'ROLLBACK_AFTER.json',old);js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=replay['source_files'],verification='REPLAY_CHECK.json',old=old));guard()
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={p.name:sha(p) for p in CODE.iterdir() if p.is_file()}))
 g=json.loads((R/'STAGE_GATES.json').read_text());nxt=json.loads((R/'NEXT_REVIEW.json').read_text());tests=json.loads((R/'TEST_RESULTS.json').read_text())
 (R/'ASTRA_FINAL.md').write_text(f'''# r09 实际完成：NO_GO

三scene、四历史视角、原RGB/真实texture/打乱texture/texture-only四臂，12特征缓存、12密度模型、48推断、15Ficus双向资格均已执行。19项本轮新测试通过，保留两次真实模块RED及两次测试契约错误；不把历史测试算新测试。

真实纹理更能分开BUILD代理种子，但建筑屋顶碎裂、头骨桌面误入、Ficus盆缘及细干损失。主臂Ficus互配2/1/1，raw1/2/2、打乱2/2/1、r05为2/2/2；数量不是语义成功。三scene精确门未过，C/D/source软成员/多风格NPR NOT_RUN。

独立readonly replay为12特征/12模型/48预测/15匹配；4752个null块多重集exact。{replay['source_files']}来源、旧main893Python与12受保护工作树保持。新增GS模型0，修改source/ink0，无GPU、训练、推送或合并。

图 delivery/OVERVIEW.jpg、三scene_FOUR_VIEWS.jpg和负例，完整数据/报告及PREVIEWS/DELIVERABLE安全包含独立SHA与MEMBERS。本地commit `{commit}`。本调用只r09，封存后退出；下一候选“局部窗口有效支持”未执行，须runner另行批准与冻结，07:40起收尾/08:00硬停。
''')
 status('COMPLETE',children=[],scientific_state=g['overall'],tests_passed=tests['new_tests_passed'],new_GS_models=0,styles=0)
 exclude=RUNTIME|{'RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in exclude and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 # Files are enumerated before archive creation. No sourceGS/checkpoint/env included.
 preview=[p for p in files if (p.parent==R/'delivery' and p.suffix in ['.jpg','.png','.json']) or p.name in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json'] or (p.name=='CONTEXT.jpg' and p.parent.name in ['0000','train_r_80'])]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',files)]
 js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=9,state=g['overall'],tests_passed=tests['new_tests_passed'],evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','COUNTS.json','MATCH_COUNTS.json','REPLAY_CHECK.json','STAGE_GATES.json','TDD_CONTRACT_CORRECTIONS.json'],source_commit=commit,next_hypothesis=nxt['next_hypothesis'],next_allowed=nxt['next_allowed'],sealed=True,utc=now(),stages=g,new_GS_models=0,styles=0,children=[]))
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in (RUNTIME|{'RESULTS_MANIFEST.json'}) and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')]
 js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(static)}))
 from verify import run
 print(json.dumps(dict(verify=run(False),packages=packs,commit=commit),indent=2))

if __name__=='__main__':main()
