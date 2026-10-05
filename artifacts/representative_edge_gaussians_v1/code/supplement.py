"""Report actual evidence counts, broad-band scope and timings; no new selection."""
from io_utils import *
import numpy as np,json,datetime

def stage():
 counts={};bands={};totals=[]
 for scene in CFG['scenes']:
  counts[scene]={};bands[scene]=[]
  for f in frames(scene,'F'):
   x=json.loads((OUT/scene/'F'/f['key']/'COUNTS.json').read_text());counts[scene][f['key']]=dict(camera_hash=f['camera_hash'],raw_sha256=f['raw_sha256'],**x)
  for c in ('color','geometry','outline'):
   totals.append(dict(scene=scene,class_name=c,**{kind:sum(v['counts'][kind][c] for v in counts[scene].values()) for kind in ['fine','major','detail']},chunks=sum(v['chunks'][c]['chunks'] for v in counts[scene].values())))
  for f in frames(scene,'C'):
   d=OUT/scene/'evaluation'/f['key'];z=load(d/'projection.npz');e=load(d/'evidence.npz');alpha=z['alpha'];fg=alpha>=.08;bands[scene].append(dict(key=f['key'],band_alpha_fraction=float(1-alpha[e['offedge']].sum()/alpha[fg].sum())))
 oldpath=SRC/'out/gaussian_edge_attribution_v1/mic/NORMALIZATION.json';old=json.loads(oldpath.read_text());norm=json.loads((OUT/'NORMALIZATION.json').read_text());oldnorm=old.get('normalization',old)
 value=dict(per_F_counts=counts,F_pixel_instance_totals=totals,C_band_scope=bands,normalization=dict(old_sigma1=oldnorm,new_sigmas=norm['scales'],old_path=str(oldpath),old_sha256=sha(oldpath),new_path=str(OUT/'NORMALIZATION.json'),new_sha256=sha(OUT/'NORMALIZATION.json')))
 atomic(ART/'EVIDENCE_COUNTS.json',value)
 events=[json.loads(line) for line in (OUT/'EVENTS.jsonl').read_text().splitlines()];native=[]
 for p in [OUT/'native/logs/RENDER_TIMES.jsonl',OUT/'native/evaluation_logs/RENDER_TIMES.jsonl']:
  native.extend(json.loads(line) for line in p.read_text().splitlines())
 stage_ranges={}
 for prefix in ['S1','S2','S3','S4','MEDIA']:
  es=[e for e in events if e['phase'].startswith(prefix) or e.get('stage','').startswith(prefix)]
  if es:
   first=min(e['utc'] for e in es);last=max(e['utc'] for e in es);stage_ranges[prefix]=dict(first_utc=first,last_utc=last,span_seconds=(datetime.datetime.fromisoformat(last)-datetime.datetime.fromisoformat(first)).total_seconds())
 initial=datetime.datetime.fromisoformat('2026-10-04T23:11:34+00:00');now=datetime.datetime.now(datetime.timezone.utc);timing=dict(initial_start_utc=initial.isoformat(),delivered_before_utc=now.isoformat(),wall_seconds_so_far=(now-initial).total_seconds(),initial_wall_budget_seconds=5400,stage_event_spans=stage_ranges,native_actual_calls=len(native),native_cuda_synchronized_sum_seconds=sum(r['cuda_synchronized_wall_seconds'] for r in native),native_timing_includes='CUDA calls only, not Python preprocessing/I/O/guards; stages spanned separately',cpu_threads=2,K64_build_seconds=json.loads((OUT/'native/top64/BUILD.json').read_text())['seconds'],space=guard())
 atomic(ART/'RUN_TIMINGS.json',timing)
 report=(ART/'REPORT_ZH.md').read_text();lines=['## S1 实际像素与分块计数','', '下表是八F逐视图逐类像素实例之和，允许同位置多类出现；不是3D边缘数，不以少数成功。所有16张F预览及逐视图计数留out并列入ledger。','', '| 场景 | 类 | fine像素实例 | MAJOR像素实例 | DETAIL像素实例 | chunks |','|---|---|---:|---:|---:|---:|']
 for r in totals:lines.append(f"| {r['scene']} | {r['class_name']} | {r['fine']} | {r['major']} | {r['detail']} | {r['chunks']} |")
 lines+=['','| 类 | 旧sigma1 P99 | 新sigma.8 P99 | 新sigma1.6 P99 | 新sigma3.2 P99 |','|---|---:|---:|---:|---:|']
 for c,name in enumerate(['color','geometry','outline']):lines.append(f"| {name} | {oldnorm['scales'][name]:.7g} | {norm['scales'][0][c]:.7g} | {norm['scales'][1][c]:.7g} | {norm['scales'][2][c]:.7g} |")
 lines+=['', '旧/new均是MicF正值ROI P99，平滑尺度与证据合同不同导致具体归一化值不同；没有从Materials或C/arc重估。旧文件路径与SHA256另列EVIDENCE_COUNTS.json。', '']
 for scene in CFG['scenes']:lines.append(f"{scene} 的新MAJOR/DETAIL union 2px带占C foreground alpha质量均值为 {np.mean([r['band_alpha_fraction'] for r in bands[scene]])*100:.2f}%。分母是alpha>=.08前景alpha，与历史81.49%广union口径不同；不能直接当作改善量。新证据带仍较广，本轮未通过C缩窄它。")
 lines+=['','']
 report=report.replace('## S2 截断完整性与校准','\n'.join(lines)+'## S2 截断完整性与校准')
 report+='\n## 实际耗时与资源\n\n'+f"截至{timing['delivered_before_utc']}，本轮wall {timing['wall_seconds_so_far']/60:.1f}分钟（预算90分钟），native实际{len(native)}次调用，CUDA同步调用耗时合计{timing['native_cuda_synchronized_sum_seconds']:.2f}秒；这不是总wall或全部GPU占用。K64隔离编译{timing['K64_build_seconds']:.2f}秒。CPU线程2，阶段时间与空间余量见RUN_TIMINGS.json。\n"
 report=report.replace('更改。\n## 负结果','更改。\n\n## 负结果');(ART/'REPORT_ZH.md').write_text(report)
 final=json.loads((ART/'FINAL.json').read_text());final.update(actual_evidence_counts_sha256=sha(ART/'EVIDENCE_COUNTS.json'),actual_timings=timing,native_checks=dict(calibrated_expanded_F=32,matched_available_K=64,calibrated_full_native_poses=98,all_fields_alpha_depth_exact=True,allones_max_abs=max(json.loads(p.read_text())['allones_alpha_max_abs'] for s in CFG['scenes'] for p in (OUT/s/'evaluation').glob('*/METRICS.json')),captured_mass_bound_F=16),F_seal_unchanged_resume_check=load_json(OUT/'RESUME_CHECK.json'));atomic(ART/'FINAL.json',final)

def load_json(p):return json.loads(Path(p).read_text())
if __name__=='__main__':stage()
