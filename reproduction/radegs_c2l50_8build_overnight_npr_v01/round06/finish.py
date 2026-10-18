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
 assert not (R/'ITERATION_STATUS.json').exists();replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['shape_replays']==12 and replay['model_replays']==3 and replay['prediction_replays']==12 and replay['match_replays']==12
 for n in ['REPORT_ZH.md','TEST_RESULTS.json','VISUAL_AUDIT.json','STAGE_GATES.json','NEXT_REVIEW.json']:assert (R/n).exists()
 own=Path.cwd();assert git(own,'status','--porcelain')=='';commit=git(own,'rev-parse','HEAD');js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False));old=rollback();js(R/'ROLLBACK_AFTER.json',old);js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=replay['source_files'],verification='REPLAY_CHECK.json',old=old));guard()
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={p.name:sha(p) for p in CODE.iterdir() if p.is_file()}));g=json.loads((R/'STAGE_GATES.json').read_text());nxt=json.loads((R/'NEXT_REVIEW.json').read_text());tests=json.loads((R/'TEST_RESULTS.json').read_text())
 (R/'ASTRA_FINAL.md').write_text(f'''# r06 已执行完成：NO_GO

新机制为source-only负空间形态补充RGB条件密度，含同预算打乱形态null。三scene十二张真实原尺寸形态测量；Ficus三臂四视角共十二预测。DTU主体资格失败，部件分类NOT_RUN。Ficus主要增加UNKNOWN，冠内木未改善，test79木质双向资格丢失；不推荐替换r04/r05已有粗结构。

{tests['new_tests_passed']}本轮新测试通过，1个小尺度饱和解析负例明确保留（非通过）；12形态/3模型/12预测/12匹配readonly精确重放通过，{replay['source_files']}来源与旧893源码/12树保持。新GS模型、source角色、线组、多风格NPR/视频均0，旧C8/source/joint完整。

完整实图：delivery/OVERVIEW.jpg、三个FOUR_VIEWS及Ficus失败crop；解释与局限REPORT_ZH.md。commit `{commit}`，未push/merge。r06封存后退出，不在本invocation启动r07。下一轮仅候选SH角度外观分解，尚未执行；07:40起收尾规则保持。
''')
 status('COMPLETE',children=[],scientific_state=g['overall'],tests_passed=tests['new_tests_passed'],expected_negative=1,new_GS_models=0,styles=0)
 exclude={'ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json','RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in exclude and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 preview=[p for p in files if ('delivery' in p.parts and p.suffix in ['.jpg','.png']) or p.name in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json','FEATURE_OVERLAP.jpg']]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',files)];js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=6,state=g['overall'],tests_passed=tests['new_tests_passed'],expected_negative_tests=1,evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','mechanism_audit/COUNTS.json','REPLAY_CHECK.json','STAGE_GATES.json'],source_commit=commit,next_hypothesis=nxt['next_hypothesis'],next_allowed=nxt['next_allowed'],sealed=True,utc=now(),stages=g,new_GS_models=0,styles=0,children=[]))
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in ['RESULTS_MANIFEST.json','ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')];js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(static)}))
 from verify import run
 print(json.dumps(dict(verify=run(False),packages=packs,commit=commit),indent=2))
if __name__=='__main__':main()
