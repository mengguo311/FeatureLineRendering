from env import *
import tarfile

def archive(name,files):
 p=R/(name+'.tar.gz');assert not p.exists();members={}
 with tarfile.open(p,'w:gz',compresslevel=5) as tf:
  for f in sorted(files):
   rel=str(f.relative_to(R));assert not f.is_symlink() and not Path(rel).is_absolute() and '..' not in Path(rel).parts;members[rel]=dict(sha256=sha(f));tf.add(f,arcname=rel,recursive=False)
 with tarfile.open(p,'r:gz') as tf:
  assert set(tf.getnames())==set(members)
  for m in tf:
   assert m.isfile() and not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts;assert hashlib.sha256(tf.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
 js(R/(name+'.MEMBERS.json'),dict(members=members));(R/(name+'.tar.gz.sha256')).write_text(sha(p)+'  '+p.name+'\n');return dict(path=p.name,bytes=p.stat().st_size,members=len(members),sha256=sha(p),verified=True)

def main():
 assert not (R/'ITERATION_STATUS.json').exists();replay=json.loads((R/'REPLAY_CHECK.json').read_text());assert replay['native_arrays_checked']==48 and replay['match_replays']==24
 for name in ['REPORT_ZH.md','STAGE_GATES.json','NEXT_REVIEW.json','TEST_RESULTS.json','VISUAL_AUDIT.json']:assert (R/name).is_file()
 own=Path.cwd();commit=git(own,'rev-parse','HEAD');assert git(own,'status','--porcelain')=='';old=rollback();js(R/'ROLLBACK_AFTER.json',old);guard();js(R/'SOURCE_AFTER.json',dict(unchanged=True,files=replay['source_files'],verification='REPLAY_CHECK.json',old=old));js(R/'COMMIT_RECEIPT.json',dict(commit=commit,branch=git(own,'branch','--show-current'),pushed=False,merged=False))
 dst=R/'code';dst.mkdir(exist_ok=True)
 for f in CODE.iterdir():
  if f.is_file() and f.suffix in ['.py','.md']:shutil.copyfile(f,dst/f.name)
 js(R/'CODE_FREEZE.json',dict(commit=commit,files={str(p.relative_to(CODE)):sha(p) for p in CODE.iterdir() if p.is_file()}))
 gates=json.loads((R/'STAGE_GATES.json').read_text());nxt=json.loads((R/'NEXT_REVIEW.json').read_text());tests=json.loads((R/'TEST_RESULTS.json').read_text())['new_tests_passed']
 (R/'ASTRA_FINAL.md').write_text(f'''# r04 已执行并封存：{gates['overall']}

三场景、四固定历史相机、四臂共48原尺寸标签输出，12构建图模型、24目标图推理、24双向对照。新机制为冻结r03条件外观与经深度资格的邻接图耦合；旧C8、source、joint均不改。
具体科学结论及失误见REPORT_ZH.md、STAGE_GATES.json和delivery/OVERVIEW.jpg；灰色UNKNOWN不删除原图或线。未输出源GS语义组或NPR样式，C/D/NPR NOT_RUN。
{tests}本轮新测试通过，readonly重放及来源/旧工作树核验见REPLAY_CHECK.json。commit `{commit}`，无push/merge。图、数据和代码包可重放。此invocation只执行r04并退出，下一次resume是否允许为{nxt['next_allowed']}；没有启动r05。
''')
 status('COMPLETE',children=[],scientific_state=gates['overall'],tests_passed=tests,new_GS_models=0,styles=0)
 excluded={'ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json','RESULTS_MANIFEST.json','ITERATION_STATUS.json','PACKAGES.json'}
 static=[p for p in R.rglob('*') if p.is_file() and p.name not in excluded and 'mplconfig' not in p.parts and not p.name.endswith(('.tar.gz','.sha256','.MEMBERS.json'))]
 reference_figs={R/'figures'/s/DEV[s]/'FULL.jpg' for s in SCENES}
 preview=[p for p in static if ('delivery' in p.parts and p.suffix in ['.jpg','.png']) or p in reference_figs or p.name in ['REPORT_ZH.md','ASTRA_FINAL.md','FORMAT_ZH.md','STAGE_GATES.json']]
 packs=[archive('PREVIEWS',preview),archive('DELIVERABLE',static)];js(R/'PACKAGES.json',packs);guard()
 js(R/'ITERATION_STATUS.json',dict(round=4,state=gates['overall'],tests_passed=tests,evidence_files=['REPORT_ZH.md','METHOD_FREEZE_ZH.md','delivery/OVERVIEW.jpg','delivery/ficus_FOUR_VIEWS.jpg','delivery/scan24_FOUR_VIEWS.jpg','delivery/scan65_FOUR_VIEWS.jpg','delivery/ARM_DIFFERENCES.json','REPLAY_CHECK.json','STAGE_GATES.json'],source_commit=commit,next_hypothesis=nxt['next_hypothesis'],next_allowed=nxt['next_allowed'],sealed=True,utc=now(),stages=gates,new_GS_models=0,styles=0,children=[]))
 files=[p for p in R.rglob('*') if p.is_file() and p.name not in ['RESULTS_MANIFEST.json','ASTRA_RUNTIME_FINAL.md','AGENT_LAUNCH.json'] and 'mplconfig' not in p.parts and not p.name.endswith('.tar.gz')];js(R/'RESULTS_MANIFEST.json',dict(members={str(p.relative_to(R)):dict(sha256=sha(p)) for p in sorted(files)}))
 from verify import run
 result=run(False);print(json.dumps(dict(packages=packs,verify=result,commit=commit),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
