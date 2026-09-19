"""Administrative aggregation of sealed per-scene measurements."""
import datetime,pathlib,sys,platform,subprocess
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];sys.path[:0]=[str(O/'code'),str(R)]
from cc_io import read_json,write_json,sha
from cc_report import markdown,core_verdict
cfg=read_json(O/'config.json');scenes=[]
for scene in cfg['scene_order']:
 m=read_json(O/f'evaluation/{scene}/metrics.json')
 keep=['scene','verdict','qualifier','segments','candidates','pairs','identities','image_tracks','gs_tracks','arms','gates','G5_gs_benefit','gate_inputs','yield_metrics','arm_counts','C_counts','repeat_counts','manual','candidate_summary']
 row={k:m[k] for k in keep};row.update(metrics_path=f'evaluation/{scene}/metrics.json',metrics_sha256=sha(O/f'evaluation/{scene}/metrics.json'),G0_verification='VERIFICATION.json',posterior_eligibility=cfg['scenes'][scene]['eligibility'],media=read_json(O/f'evaluation/{scene}/media.json'))
 row['heldout']={n:{s:{k:v for k,v in p.items() if k not in ['per_view','track_support']} for s,p in splits.items() if s in ['C','DEV']} for n,splits in m['predictions'].items()}
 row['repeatability']={n:{a:{k:v for k,v in d.items() if k not in ['forward_detail','backward_detail']} for a,d in rows.items()} for n,rows in m['repeatability'].items()}
 row['failure_buckets']=read_json(O/f'evaluation/{scene}/visual/failure_buckets.json');row['gs_benefit']=m['gs_benefit'];scenes.append(row)
for scene in ['drums','ficus']:
 scenes.append(dict(scene=scene,verdict='INSUFFICIENT_POSTERIOR_QUALITY',qualifier='NONE',posterior_eligibility=cfg['scenes'][scene]['eligibility'],executed=False))
totals={k:sum(r.get(k,0) for r in scenes) for k in ['segments','candidates','pairs','identities','image_tracks','gs_tracks','arms']}
totals.update(core_scenes=2,ineligible_stress_scenes=2,canonical_pngs=sum(r['media']['pngs'] for r in scenes[:2]),canonical_mp4s=sum(len(r['media']['videos']) for r in scenes[:2]),blinded_images=sum(r['media']['blinded_images'] for r in scenes[:2]),independent_reviews=0,qualified_controlled_repeats=18,independent_seed_repeats=1)
result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),prereg_commit=subprocess.check_output(['git','rev-parse','ea3e94d'],cwd=R,text=True).strip(),config_sha256=sha(O/'config.json'),core_verdict=core_verdict({r['scene']:r['verdict'] for r in scenes[:2]}),scenes=scenes,totals=totals,manual=dict(status='PENDING_INDEPENDENT_REVIEW',independent_review_count=0),limitations=['Detector distances are prediction proxies, not correspondence truth.','Main held-out gates retain all in-frame occluded samples; visibility strata are separate diagnostics.','GS is only a support veto; unchanged retained coordinates are not evidence for better geometry.','Matched-ink comparisons are incomparable at the frozen tolerance for every correspondence arm.','Internal challenge boxes do not separate shadows from highlights or certify semantics.','STOP applies to the single frozen minimal formulation, not all curve SfM.'],verification='VERIFICATION.json')
write_json(O/'results.json',result)
with (O/'RESULTS.md').open('x') as f:f.write(markdown(result))
import numpy,scipy,cv2,imageio_ffmpeg,torch
write_json(O/'setup/environment.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),numpy=numpy.__version__,scipy=scipy.__version__,opencv=cv2.__version__,torch=torch.__version__,imageio_ffmpeg=imageio_ffmpeg.__version__,ffmpeg=imageio_ffmpeg.get_ffmpeg_exe(),git=subprocess.check_output(['git','--version'],text=True).strip(),thread_policy='OMP/BLAS/MKL=1 during scientific execution',test_counts=dict(targeted=45,complete_repository=127)))
print(result['core_verdict'],totals)
