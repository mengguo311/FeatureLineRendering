"""Read-only administrative verification; real TEST bytes are never opened."""
import collections,concurrent.futures,datetime,hashlib,json,pathlib,subprocess,sys
import numpy as np
import cv2,imageio_ffmpeg
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];sys.path[:0]=[str(O/'code'),str(R)]
import cc
from cc_io import read_json,write_json,sha,verify_seal,scene_inputs
from cc_evaluate import identity_certificate
from cc_report import verify_markdown,core_verdict,arm_gates
cfg=read_json(O/'config.json');results=read_json(O/'results.json');checks=[];detail={}
def check(name,passed,data=None):
 checks.append(dict(check=name,passed=bool(passed),detail=data))
 if not passed:print('FAILED',name,data,flush=True)
frozen_hash='43be7698069b27e36251e4cb377b4309a2e06fea39ee3329b101e0c8e75811fd'
check('frozen config exact',sha(O/'config.json')==frozen_hash==(O/'config.json.sha256').read_text().strip())
for file,key in [('PREREG.md','prereg_sha256'),('LITERATURE.md','literature_sha256'),('input_hashes.json','input_hashes_sha256')]:check('frozen '+file,sha(O/file)==cfg[key])
for p in ['config.json','PREREG.md','LITERATURE.md','input_hashes.json']:
 committed=subprocess.check_output(['git','show','ea3e94d:out/curve_correspondence_foundation/'+p],cwd=R)
 check('preregistered bytes '+p,hashlib.sha256(committed).hexdigest()==sha(O/p))
prereg_time=datetime.datetime.fromisoformat(subprocess.check_output(['git','show','-s','--format=%cI','ea3e94d'],cwd=R,text=True).strip())
statuses=[(p,read_json(p)) for p in (O/'setup').glob('*_exit.json')]
check('canonical scientific process count',len(statuses)==27,len(statuses))
check('all canonical processes exited zero',all(s['exit_code']==0 for _,s in statuses))
check('prereg commit precedes all scientific execution',all(prereg_time<datetime.datetime.fromisoformat(s['start_utc']) for _,s in statuses))
audit=read_json(O/'ACCESS_AUDIT.json');check('native access audit',audit['passed'] and audit['trace_count']==28 and not audit['forbidden_successes'] and not audit['unparsed_open_lines'],{k:audit[k] for k in ['trace_count','forbidden_successes','unparsed_open_lines','failed_execution_attempts']})
check('only archived display process failed',audit['failed_execution_attempts']==['attempt_00/lego_evaluation_exit.json'])
check('JSON Markdown byte consistency',verify_markdown(results,(O/'RESULTS.md').read_text()))
for key in ['segments','candidates','pairs','identities','image_tracks','gs_tracks','arms']:check('aggregate '+key,results['totals'][key]==sum(r.get(key,0) for r in results['scenes']))
check('core verdict per scene',results['core_verdict']==core_verdict({r['scene']:r['verdict'] for r in results['scenes'][:2]})=='STOP_CORRESPONDENCE')
check('manual pending zero independent reviews',results['manual']==dict(independent_review_count=0,status='PENDING_INDEPENDENT_REVIEW'))
for sc in cfg['scene_order']:
 info=cfg['scenes'][sc];base=O/'scenes'/sc;ev=O/'evaluation'/sc;m=read_json(ev/'metrics.json');row=next(r for r in results['scenes'] if r['scene']==sc);delta=info['eligibility']['delta'];box=np.array(info['eligibility']['box']);g=cfg['gates'];fit=cfg['fit']
 directories=[base/'F',base/'C',*[base/'repeats'/a for a in info['assets'] if a!='seed_1729'],ev,O/'visibility'/sc]
 for d in directories:check(sc+' seal '+str(d.relative_to(O)),verify_seal(d,read_json(d/'frozen.json')))
 check(sc+' F sealed before C/DEV',all(read_json(base/'F/frozen.json')['created_utc']<read_json(d/'allowlist.json')['created_utc'] for d in [base/'C',ev]))
 for split in ['F','C']:
  expected=sorted(scene_inputs(cfg,sc,split)['photos']);check(sc+' photo isolation '+split,sorted(read_json(base/split/'allowlist.json')['photo_inputs'])==expected)
 check(sc+' evaluator exact approved views',set(read_json(ev/'allowlist.json')['photo_inputs'])=={c['path'] for c in info['cameras'].values()})
 for a in info['assets'][1:]:check(sc+' repeat no photo '+a,read_json(base/f'repeats/{a}/allowlist.json')['photo_inputs']==[])
 check(sc+' all posterior routes enumerated',set(m['repeat_counts'])==set(info['assets'])-{'seed_1729'})
 check(sc+' qualified doses',len([a for a in m['repeat_counts'] if a!='seed_2718'])==9)
 check(sc+' independent seed eligibility',('seed_2718' in m['repeat_counts'])==bool(info['eligibility']['route_a']))
 check(sc+' counts exact',all(m[k]==row[k] for k in ['segments','candidates','pairs','identities','image_tracks','gs_tracks','arms']))
 Fcurves=read_json(base/'F/curves.json.gz');edges=read_json(base/'F/candidates.json.gz');random=read_json(base/'F/random_graph_edges.json.gz')
 check(sc+' extraction and candidate totals',len(Fcurves)==m['segments'] and len(edges)==m['candidates'] and sum(e['selected'] for e in edges)==m['pairs'])
 check(sc+' randomized graph preserves edge count',len(random)==sum(e['selected'] for e in edges))
 shifted=cc.shift_curves(Fcurves,cfg['splits']['F'],cfg['controls'])
 check(sc+' shifted null preserves complete ordered curve counts',len(shifted)==len(Fcurves) and all(len(shifted[k]['points'])==len(v['points']) and np.allclose(cc.arclength(shifted[k]['points']),cc.arclength(v['points'])) for k,v in Fcurves.items()))
 certs=[];geometry_checks=[]
 for split in ['F','C']:
  cams=scene_inputs(cfg,sc,split)['cameras'];candidates=read_json(base/split/'candidates.json.gz')
  files=[base/split/f'{a}.json.gz' for a in (m['arm_counts'] if split=='F' else ['image_only','gs'])]
  for p in files:
   arm=p.name[:-8];data=read_json(p);accepted=data['accepted']
   if arm in ['image_only','gs']:certs.append(identity_certificate(accepted,candidates,cfg['matching']) if accepted else True)
   for r in accepted:
    x=np.array(r['xyz']);cameras=[cams[v] for v in r['views']];angles=[cc.baseline_angles(q,cameras) for q in x]
    ok=np.isfinite(x).all() and len(x)>=fit['min_knots'] and np.ptp(r['root_arc'])>=fit['min_arc']-1e-8 and np.all((x>=box[0])&(x<=box[1])) and r['identity_frozen_before_fit'] and r['fit_rms']<=fit['rms_max'] and r['fit_tangent_median']<=fit['tangent_median_max']
    ok=ok and all(a[0]>=fit['baseline_max_min'] and (len(cameras)<3 or a[1]>=fit['baseline_second_min']) for a in angles)
    ok=ok and all(np.all(cc.project_jacobian(x,c['K'],c['w2c'])[1]>0) for c in cameras)
    if not arm.startswith('no_order'):ok=ok and all(np.all(np.diff(v)>0) or np.all(np.diff(v)<0) for v in r['maps'].values())
    geometry_checks.append(dict(split=split,arm=arm,id=r['id'],passed=bool(ok),minimum_largest_baseline=min(a[0] for a in angles),minimum_second_baseline=min(a[1] for a in angles) if len(cameras)>=3 else None))
 check(sc+' every accepted fit finite supported and nondegenerate',all(r['passed'] for r in geometry_checks),len(geometry_checks));detail[sc+'_geometry']=geometry_checks
 check(sc+' primary identity certificates',all(certs))
 original=read_json(base/'F/image_only.json.gz')['accepted'];gs=read_json(base/'F/gs.json.gz')['accepted']
 for records in [gs,*[read_json(base/f'repeats/{a}/gs.json.gz')['accepted'] for a in m['repeat_counts']]]:
  for r in records:
   parent=next(x for x in original if r['id'].startswith(x['id']+':gs:'));indices=[list(parent['root_arc']).index(x) for x in r['root_arc']]
   check(sc+' GS exact contiguous subset '+r['id'],np.array_equal(np.array(parent['xyz'])[indices],r['xyz']) and np.all(np.diff(indices)==1))
 for name in ['image_only','gs']:
  check(sc+' gate aggregation '+name,m['gates'][name]==arm_gates(m['gate_inputs'][name],g))
  check(sc+' nontrivial yield failed without averaging '+name,m['yield_metrics'][name]['separated_tracks']<g['min_tracks'] and not m['gates'][name]['G1'])
  for split in ['C','DEV']:
   primary=m['predictions'][name][split];controls={n:m['predictions'][n+('_gs' if name=='gs' else '')][split] for n in ['shifted','random_graph','pairwise','no_order']}
   check(sc+' control gate recomputation '+name+split,cc.null_gate(primary,controls,g)==m['gate_inputs'][name][split+'_null'])
  for tag,other in [('C_independent',read_json(base/f'C/{name}.json.gz')['accepted'])]:
   measured=cc.match_geometry(read_json(base/f'F/{name}.json.gz')['accepted'],other,delta,g)
   check(sc+' independent C matching '+name,measured==m['repeatability'][name][tag])
 summary=read_json(O/f'visibility/{sc}/summary.json')['arms']
 for name,splits in summary.items():
  for split,views in splits.items():
   for view,entry in views.items():
    prior=m['predictions'][name][split]['per_view'][view]
    check(sc+' visibility partition '+name+split+view,sum(r['samples'] for r in entry['strata'].values())==prior['samples'] and abs(entry['all_in_frame']['projected_length']-prior['projected_length'])<1e-8 and abs(entry['all_in_frame']['supported_length']-prior['supported_length'])<1e-8)
 key=read_json(ev/'visual/review_identity_key.json')
 check(sc+' blinded package bytes and separate key',len(key)==132 and all(sha(ev/'visual/blinded_review'/r['file'])==r['sha256']==sha(r['source']) for r in key) and not list((ev/'visual/blinded_review').glob('*.json')))
 media=read_json(ev/'media.json');check(sc+' media totals',media['pngs']==len(list((ev/'visual').rglob('*.png'))))
 duration=sum(r['elapsed_seconds'] for _,r in statuses if '--scene' in r['command'] and r['command'][r['command'].index('--scene')+1]==sc)
 if sc=='lego':duration+=read_json(O/'setup/attempt_00/lego_evaluation_exit.json')['elapsed_seconds']
 check(sc+' budget',duration<cfg['budget']['scientific_seconds_per_scene'],duration)
for sc in ['drums','ficus']:check(sc+' ineligibility explicit no stress generation',not cfg['scenes'][sc]['eligibility']['eligible'] and not (O/'scenes'/sc).exists())
check('display repair leaves numerical measurements byte identical',sha(O/'evaluation/lego/metrics.json')==sha(O/'attempts/evaluation_lego_00/metrics.json'))
for p in (O/'evaluation/lego').glob('*_samples.json.gz'):check('display repair samples '+p.name,sha(p)==sha(O/'attempts/evaluation_lego_00'/p.name))
preserved=read_json(O/'PRESERVED_INPUT_VERIFICATION.json')
def preserved_one(r):return dict(path=r['path'],passed=sha(r['path'])==r['expected_sha256'])
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:preservation=list(pool.map(preserved_one,preserved['records']))
check('previous archives remain byte identical after complete suite',all(r['passed'] for r in preservation),dict(files=len(preservation),failed=[r for r in preservation if not r['passed']],sealed_TEST_paths_not_opened=len(preserved['skipped_sealed_TEST'])))
check('all eight checkpoint hashes',len(cfg['frozen_posteriors'])==8 and all(sha(v['path'])==v['sha256'] for v in cfg['frozen_posteriors'].values()))
sources=read_json(O/'setup/repository_suite_source_hashes.json');check('complete suite exact source mirror',len(sources)==578 and all(sha(R/r['path'])==r['sha256']==sha(O/'setup/repository_suite'/r['path']) for r in sources))
refs=read_json(O/'setup/starting_refs.json');current=dict(line.split(' ',1)[::-1] for line in subprocess.check_output(['git','show-ref'],cwd=R,text=True).splitlines());check('every other branch preserved',all(current.get(k)==v for k,v in refs.items() if k not in ['refs/heads/curve-correspondence-foundation','refs/remotes/origin/curve-correspondence-foundation']))
changed=subprocess.check_output(['git','diff','--name-only','42158159a037fee1b14c5ba2d8a7e5271ec1bc36'],cwd=R,text=True).splitlines();check('no tracked changes outside experiment',all(p.startswith('out/curve_correspondence_foundation/') for p in changed))
tdd=[(p,read_json(p)) for p in (O/'tdd').glob('*.json')];reds=[r for p,r in tdd if r['phase']=='RED'];check('observed RED evidence',len(reds)==13 and all(r['exit_code']!=0 for r in reds),len(reds))
for prefix in ['01','02','03','04','05','06','07','08','09','10','11','12']:
 r=[r for p,r in tdd if p.name.startswith(prefix) and r['phase']=='GREEN' and r['exit_code']==0]
 check('RED before successful GREEN '+prefix,bool(r) and any(x['start_utc']<min(y['start_utc'] for y in r) for x in reds if x['label'].startswith(prefix)))
check('final targeted suite 45 passed',read_json(O/'tdd/final_targeted_with_visibility_REFACTOR.json')['exit_code']==0 and 'Ran 45 tests' in (O/'tdd/final_targeted_with_visibility_REFACTOR.txt').read_text())
check('complete repository suite 127 passed',read_json(O/'tdd/final_complete_runtime_fixed_VERIFY.json')['exit_code']==0 and 'Ran 127 tests' in (O/'tdd/final_complete_runtime_fixed_VERIFY.txt').read_text())
pngs=[p for p in O.rglob('*.png') if '/repository_suite/' not in str(p)]
def png(p):
 data=cv2.imread(str(p),cv2.IMREAD_UNCHANGED);return dict(path=str(p.relative_to(O)),passed=data is not None and data.size>0,shape=None if data is None else list(data.shape),sha256=sha(p))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:images=list(pool.map(png,pngs))
check('every experiment PNG decodes including failed attempt',all(r['passed'] for r in images),len(images));detail['pngs']=images
videos=[]
for p in O.rglob('*.mp4'):
 if '/repository_suite/' in str(p):continue
 reader=imageio_ffmpeg.read_frames(str(p),pix_fmt='rgb24');meta=next(reader);count=0
 for frame in reader:count+=1
 videos.append(dict(path=str(p.relative_to(O)),frames=count,meta=meta,sha256=sha(p),passed=count==120))
check('every MP4 decodes exactly 120 frames',len(videos)==14 and all(r['passed'] for r in videos),len(videos));detail['videos']=videos
check('canonical media totals in report',results['totals']['canonical_pngs']==2030 and results['totals']['canonical_mp4s']==14)
detail['checkpoint_hashes']=cfg['frozen_posteriors'];detail['unresolved_independent_review']=True
out=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=all(c['passed'] for c in checks),checks=checks,check_count=len(checks),failed=[c for c in checks if not c['passed']],details=detail,scope='Execution validity and integrity; scientific machine gates intentionally fail. Final manifest and git equality are checked separately after this file is frozen.')
write_json(O/(sys.argv[1] if len(sys.argv)>1 else 'VERIFICATION.json'),out);print('VERIFIED',out['passed'],'checks',len(checks),'PNGs',len(images),'MP4s',len(videos),flush=True)
