"""Derive one new resolved scene configuration; do not change sealed runtime."""
import argparse,ast,datetime,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];CODE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'));sys.path.insert(0,str(CODE/'runtime'))
from safety import atomic_json,sha256,verify_seal
from suite_scope import validate_config_scope
from result_review_v02 import validate_review
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');SUITE=H/'full_reproduction_v01/suite_execution_v01';ART=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True);ap.add_argument('--parent-config',type=Path,required=True);ap.add_argument('--parent-sha256',required=True);ap.add_argument('--review',type=Path,required=True);args=ap.parse_args()
 parent=args.parent_config.resolve();assert parent.is_relative_to(SUITE);assert sha256(parent)==args.parent_sha256
 c=json.loads(parent.read_text());old=json.loads(parent.read_text());scene=args.scene
 for p,d in c['immutable_files'].items():assert sha256(p)==d,p
 for stage in ['smoke','train','export']:assert verify_seal(Path(c['state_dir'])/(stage+'.seal.json'),stage,c['inputs'])
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=H/'sources/RaDe-GS',text=True).strip()
 datafile=SUITE/(scene+'_data_v01')/'DATA.json';data=json.loads(datafile.read_text());assert data['scene']==scene and data['raw_copy_hashes_equal']
 for p,d in {**data['training_hashes'],**data['evaluation_hashes']}.items():assert sha256(p)==d,p
 review=json.loads(args.review.read_text());validate_review(review,old['scene'])
 assert sha256(review['confirmed_negative_result'])==review['result_sha256']
 assert shutil.disk_usage('/').free>=10*1024**3 and shutil.disk_usage(H).free-12*1024**3>=50*1024**3
 state=SUITE/(scene+'_v01')/'state';model=H/'models'/(scene+'_paper_text_precision_v01_half_30k');assert not state.exists() and not model.exists()
 path=state/'runner_config.json';c.update(scene=scene,entry_id=data['entry_id'],data=data['prepared'],gt=data['evaluation_GT'],model=str(model),state_dir=str(state),log_dir=str(state.parent/'logs'),preflight_report=str(state/'preflight.json'),expected_scene={'views':data['images'],'initial_colmap_points':data['initial_COLMAP_points'],'half_resolution':data['half_resolution']},suite_parent_config=str(parent),suite_parent_config_sha256=sha256(parent),negative_result_review=str(args.review.resolve()),scientific_scope=f'One resolved DTU {scene} half30k entry; unchanged paper-text method; stop after its chain, no automatic next scene')
 replacements={old['data']:c['data'],old['model']:c['model'],old['gt']:c['gt'],str(parent):str(path)}
 for key in ['train_command','eval_command']:c[key]=[replacements.get(x,x) for x in c[key]]
 c['stage_commands']={s:[replacements.get(x,x) for x in argv] for s,argv in c['stage_commands'].items()};c['reports']={s:str(state/(s+'.report.json')) for s in c['stage_commands']}
 validate_config_scope(c)
 # Existing controls/kernel/source are unchanged and verified above. New scene
 # gets the same mandatory real baseline/paper/scene GPU smoke before training.
 extra=[Path(__file__),CODE/'result_review_v02.py',CODE/'test_result_review_v02.py',CODE/'prepare_dtu_entry.py',datafile,args.review.resolve(),Path(review['confirmed_negative_result'])]
 for p in extra:
  if p.suffix=='.py':ast.parse(p.read_text())
 manifest={'files':{str(p.resolve()):sha256(p) for p in extra},'parent_config_sha256':sha256(parent),'runtime_unchanged':True,'native_unchanged':c['inputs']['candidate_native'],'CPU_controls_test_receipt':str(SUITE/'cpu_tests/SUMMARY.json'),'real_GPU_smoke_required':True,'scientificdone':False}
 state.mkdir(parents=True);manifestfile=state/'scene_manifest.json';atomic_json(manifestfile,manifest)
 c['immutable_files'].update(manifest['files']);c['immutable_files'].update(data['training_hashes']);c['immutable_files'].update(data['evaluation_hashes']);c['immutable_files'][str(manifestfile)]=sha256(manifestfile)
 c['inputs'].update(data_manifest=sha256(datafile),scene_entry=c['entry_id'],scene_manifest=sha256(manifestfile),negative_result_review=sha256(args.review))
 preflight={'passed':True,'meaning':'source/native/data/protocol CPU guards verified; mandatory GPU smoke still pending','parent_config_sha256':sha256(parent),'previous_failure_preserved':str(Path(old['state_dir'])/'runner_state.json'),'new_method_changes':False,'fresh_model':str(model),'COLMAP_points':data['initial_COLMAP_points'],'views':data['images'],'root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(H).free,'estimated_next_scene_increment_GiB':12,'estimate_basis':'prior completed scene output/checkpoint footprint plus margin; no runtime guarantee','scientificdone':False,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};atomic_json(state/'preflight.json',preflight);c['immutable_files'][str(state/'preflight.json')]=sha256(state/'preflight.json');atomic_json(path,c)
 # Real constructor/preflight, no GPU query/spawn. State then explicitly waits.
 import suite_runner
 runner=suite_runner.PilotRunner(path,query=lambda:None)
 try:runner.tick(None);assert runner.child is None and runner.state['status']=='WAITING_FOR_LOW_LOAD_GPU'
 finally:runner.close()
 receipt={'scene':scene,'config':str(path),'sha256':sha256(path),'immutable_files':len(c['immutable_files']),'native_sha256':c['inputs']['candidate_native'],'command':[c['train_command'][0],str(CODE/'runtime/suite_runner.py'),'--config',str(path)],'tracker_command':[c['train_command'][0],str(CODE/'suite_progress.py'),'--config',str(path)],'boundary_observer_command':[c['train_command'][0],str(CODE/'boundary_snapshot.py'),'--config',str(path)],'train_command':c['train_command'],'CPU_construct_and_failed_query_no_launch_verified':True,'scientificdone':False};atomic_json(state.parent/'LAUNCH.json',receipt)
 out=ART/(scene+'_v01');out.mkdir();atomic_json(out/'LAUNCH.json',receipt);shutil.copy2(datafile,out/'DATA.json');shutil.copy2(manifestfile,out/'SCENE_MANIFEST.json');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
