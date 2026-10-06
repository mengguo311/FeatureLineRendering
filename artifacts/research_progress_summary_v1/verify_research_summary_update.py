from pathlib import Path
import json,hashlib,re,subprocess,urllib.parse
R=Path('/home/u00134/3dgs_line/research_progress_summary_v1')
A=R/'artifacts/research_progress_summary_v1'
M=json.loads((A/'IMPORTED_20261006_SNAPSHOTS.json').read_text())
assert M['stage_count']==len(M['stages'])==9
assert M['file_count']==sum(s['count'] for s in M['stages'])
bytes_total=0
for s in M['stages']:
 assert s['count']==len(s['files'])
 for f in s['files']:
  d=(R/f['path']).read_bytes();bytes_total+=len(d)
  assert len(d)==f['bytes'],f['path']
  assert hashlib.sha256(d).hexdigest()==f['sha256'],f['path']
  assert hashlib.sha1(b'blob '+str(len(d)).encode()+b'\0'+d).hexdigest()==f['source_blob'],f['path']
selected=['README.md','docs/PROGRESS_ZH.md','docs/BRANCHES_ZH.md','docs/UPDATE_20261006_ZH.md','docs/ADVISOR_MEETING_PRINCIPLES_ZH.md']
links=[];images=[]
for file in selected:
 text=(R/file).read_text()
 assert '[SKILL_PRUNED]' not in text and '[REDACTED]' not in text
 for image,label,target in re.findall(r'(!?)\[([^\]]*)\]\(([^)]+)\)',text):
  if '://' in target or target.startswith('#'):continue
  path=urllib.parse.unquote(target.split('#')[0])
  p=(R/file).parent/path
  if not p.exists():
   rel=str(p.resolve().relative_to(R))
   subprocess.run(['git','-C',str(R),'cat-file','-e',':'+rel],check=True)
  links.append({'file':file,'target':target})
  if image:images.append(str(p.resolve().relative_to(R)))
assert len(images)==6
allowed=set(selected+['docs/MEETING_CITATIONS.json','docs/meeting_poster_evidence.txt'])
allowed_prefix=['artifacts/research_progress_summary_v1/']+[f'{kind}/{s["stage"]}/' for s in M['stages'] for kind in ['artifacts','experiments']]
status=subprocess.check_output(['git','-C',str(R),'status','--porcelain','-uall']).decode()
for l in status.splitlines():
 p=l[3:]
 assert p in allowed or any(p.startswith(q) for q in allowed_prefix),(l,'unexpected change')
assert not any(l.startswith(' D') or l.startswith('D ') for l in status.splitlines())
heads=subprocess.check_output(['git','-C',str(R),'ls-remote','git@github.com:mengguo311/FeatureLineRendering.git','refs/heads/*']).decode()
before=(A/'REMOTE_HEADS_BEFORE_UPDATE.txt').read_text()
assert heads==before,'external branch changed before our push; inspect rather than overwrite'
subprocess.run(['git','-C',str(R),'diff','--check','--',*selected],check=True)
subprocess.run(['git','-C',str(R),'diff','--cached','--check','--',*selected],check=True)
legacy_ws=subprocess.run(['git','-C',str(R),'diff','--cached','--check'],capture_output=True,text=True)
legacy_paths=sorted(set(l.split(':',1)[0] for l in legacy_ws.stdout.splitlines() if re.match(r'[^:]+:\d+:',l)))
assert all(any(p.startswith(f'{k}/{s["stage"]}/') for s in M['stages'] for k in ['artifacts','experiments']) for p in legacy_paths)
# Preserve original CSV CRLF, license text and patch indentation; never rewrite immutable evidence.
result={'inherited_whitespace_warnings_preserved':legacy_paths,'authored_doc_whitespace':'PASS','sparse_excluded_links_verified_in_git_index':True,'status':'PASS','science_rerun':False,'paused':True,'stage_count':len(M['stages']),'imported_files_checked':M['file_count'],'imported_bytes':bytes_total,'local_links_checked':len(links),'meeting_images_checked':len(images),'only_expected_paths_changed':True,'no_deletions':True,'all_remote_heads_unchanged_before_push':True,'old_summary_base':M['summary_base'],'checks':'full bytes SHA256 plus original Git blob SHA1; all selected docs local paths; Git diff whitespace and scoped edits','images':images}
(A/'UPDATE_20261006_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
