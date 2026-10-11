"""Static delivery assembly; excludes parent launcher and mutable handoff files."""
from pathlib import Path
import hashlib,json,tarfile,shutil,datetime,ast,subprocess
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/structure_primitive_demo_v04')
W=Path(__file__).resolve().parent
MUTABLE={'STATUS.json','ASTRA_FINAL.md','AGENT_LAUNCH.json','launch.py','PROMPT.txt','stdout.log','stderr.log','wrapper.log','RESULTS_MANIFEST.json','PACKAGE_VERIFICATION.json','HANDOFF_SHA256.json','DELIVERABLE.tar.gz','DELIVERABLE.tar.gz.sha256','PREVIEWS.tar.gz','PREVIEWS.tar.gz.sha256','package.log'}
DIRECTORIES={'code','code_versions','vendor','delivery_sources','literature','results','synthetic','roi_fair_comparison','provenance_refined','media_corrected','portable_verification','logs','geometry_replay','failed_attempt02','interrupted_attempt01'}

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def selected(p):
    r=p.relative_to(T)
    if r.parts[0]=='media_corrected' and 'frames' in r.parts:return False
    if r.parts[0]=='geometry_replay' and p.name=='segments.pkl':return False
    if r.parts[0] in ('failed_attempt02','interrupted_attempt01') and p.suffix=='.npz':return False
    return True

def main():
    assert shutil.disk_usage(T).free>10*2**30 and shutil.disk_usage('/').free>2**30
    assert sum(p.stat().st_size for p in T.rglob('*') if p.is_file())<15*2**30
    code=T/'code';code.mkdir(exist_ok=True)
    for p in W.iterdir():
        if p.is_file() and p.suffix in ('.py','.md'):
            if p.suffix=='.py':
                ast.parse(p.read_text());r=subprocess.run(['git','diff','--no-index','--check','/dev/null',str(p)],capture_output=True,text=True)
                assert r.returncode in (0,1) and not r.stdout and not r.stderr
            shutil.copy2(p,code/p.name)
    output=[]
    for p in sorted(T.rglob('*')):
        if not p.is_file() or p.is_symlink():continue
        r=p.relative_to(T)
        if p.name in MUTABLE or '__pycache__' in r.parts:continue
        if len(r.parts)>1 and r.parts[0] not in DIRECTORIES:continue
        if len(r.parts)==1 and p.suffix not in ('.json','.md','.csv'):continue
        output.append({'path':str(r),'absolute_path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'packaged':selected(p)})
    for r in output:
        if r['path'].endswith('.json'):json.loads((T/r['path']).read_text())
    manifest={'format':1,'root':str(T),'status':'HONEST_NEGATIVE','full_scene_count':3,'ROI_count':1,'videos':3,'decoded_frames':99,'source_records':json.loads((T/'SOURCE_FREEZE.json').read_text()),'outputs':output,'output_count':len(output),'packaged_output_count':sum(x['packaged'] for x in output),'mutable_files_excluded':sorted(MUTABLE),'remote_omissions':'frames PNG, large own segment replay cache, failed/interrupted map NPZ; all preserved remotely; per-unit SEAL includes remote-only members','parent_launcher_logs_excluded':True,'method':'structure_primitive_v04; frozen 3 build views; independent experiment inspired by papers, not faithful reproduction'}
    (T/'RESULTS_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    indexed={r['path']:r for r in output};verification=[]
    for name,preview in [('DELIVERABLE',False),('PREVIEWS',True)]:
        members=[r['path'] for r in output if r['packaged'] and (not preview or (Path(r['path']).suffix in ('.jpg','.mp4') and 'code_versions' not in r['path']) or r['path'] in {'REPORT_ZH.md','ASTRA_PLAN_ZH.md','ASSET_FORMAT_ZH.md','COUNTS.csv','EXPERIMENT_STATUS.json','VISUAL_INSPECTION.json'})]
        members.append('RESULTS_MANIFEST.json');path=T/(name+'.tar.gz')
        with tarfile.open(path,'w:gz',compresslevel=6) as tar:
            for rel in members:tar.add(T/rel,arcname=T.name+'/'+rel,recursive=False)
        checked=0
        with tarfile.open(path,'r:gz') as tar:
            for item in tar:
                assert item.isfile() and '..' not in Path(item.name).parts and not item.name.startswith('/')
                rel=str(Path(item.name).relative_to(T.name));expected=sha(T/'RESULTS_MANIFEST.json') if rel=='RESULTS_MANIFEST.json' else indexed[rel]['sha256']
                h=hashlib.sha256();f=tar.extractfile(item)
                for b in iter(lambda:f.read(2**20),b''):h.update(b)
                assert h.hexdigest()==expected,rel;checked+=1
        assert checked==len(members);digest=sha(path);(T/(name+'.tar.gz.sha256')).write_text(digest+'  '+path.name+'\n')
        verification.append({'path':str(path),'sha256':digest,'bytes':path.stat().st_size,'members_verified':checked,'all_member_hashes_match':True})
        print(name,path.stat().st_size,checked,digest,flush=True)
    (T/'PACKAGE_VERIFICATION.json').write_text(json.dumps({'packages':verification,'manifest_sha256':sha(T/'RESULTS_MANIFEST.json'),'code_AST_whitespace_passed':True,'packaged_json_parse_passed':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')

if __name__=='__main__':main()
