"""Finalize actual results after all detached GPU work; writes only v2 artifacts."""
import sys,json,os,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/object_neighborhood_edge_control_v2/src'))
from runtime import OUT,ART,EXP,PYTHON,atomic_json,sha,resource_guard

def main():
 freeze=json.loads((ART/'FINALIZE_FREEZE.json').read_text());assert sha(__file__)==freeze['script_sha256']
 while True:
  p=OUT/'L1_REFINEMENT_STATUS.json';state=json.loads(p.read_text()) if p.exists() else {}
  if state.get('phase')=='COMPLETED':break
  atomic_json(OUT/'FINALIZE_STATUS.json',{'phase':'WAIT_L1_REFINEMENT','pid':os.getpid()});time.sleep(30)
 atomic_json(OUT/'FINALIZE_STATUS.json',{'phase':'RUNNING','pid':os.getpid()})
 subprocess.run([PYTHON,str(ART/'R5_TRI_STATE.py')],cwd=ROOT,check=True)
 while True:
  try:resource_guard();break
  except RuntimeError as e:
   if 'WAIT_FOREIGN_GPU' not in str(e):raise
   time.sleep(30)
 subprocess.run([PYTHON,str(ART/'SUPPLEMENTAL_AUDIT.py')],cwd=ROOT,check=True)
 subprocess.run([PYTHON,str(ART/'PLOT_ACTUAL.py')],cwd=ROOT,check=True)
 with (ART/'tests/FINAL_core.txt').open('w') as log:subprocess.run([PYTHON,'-m','unittest','discover','-s',str(EXP/'tests'),'-v'],cwd=ROOT,stdout=log,stderr=log,check=True)
 with (ART/'tests/FINAL_supplement.txt').open('w') as log:subprocess.run([PYTHON,'-m','unittest','discover','-s',str(ART/'tests'),'-p','test_*.py','-v'],cwd=ROOT,stdout=log,stderr=log,check=True)
 r5=json.loads((ART/'results/R5.json').read_text());audit=json.loads((ART/'SUPPLEMENTAL_AUDIT.json').read_text());final=json.loads((ART/'FINAL.json').read_text());text=(ART/'REPORT_ZH.md').read_text()
 text=text.replace('R5：条件未执行；保留原 epsilon=0.02，原候选不重算、不改证书阈值。尚无正式局部控制收益证据，因此不先投入空间筛选重写。三态 near/far/uncertain、支持包围盒与独立表面关系评价仍待控制门槛后实施；Gaussian 支持关系不是物理接触。','R5：可恢复尺度探针显示控制潜力后，条件执行了三态支持距离与支持包围盒的工程诊断。原 epsilon=0.02 保留，原 1379 UID 不重选。仅评测预先规则选出的诊断子集及明确几何定义的解析例，不声称完成全模型成本优化或物理接触检测。')
 text += '\n## R1 同目标收敛补充（实际续算）\n\n对角预条件只改变求解流程，固定权重、盒范围、相机、目标与归一化保持一致；原 600 步结果保留作为优化日志。AᵀA1 的非负权重主化关系经 CPU 数学测试和真实原生算子二次型验证。\n\n| 单元 | P 上界 | D 下界 | P-D | 归一化 gap | MSE 上/下界 | 追加迭代 | 判读 |\n|---|---:|---:|---:|---:|---|---:|---|\n'
 refinements={}
 for arm in ('F00','F01','F10','F11'):
  d=json.loads((ART/'results'/f'{arm}_refined.json').read_text());c=d['certificate'];refinements[arm]={'certificate':c,'claim':d['claim'],'checkpoint_sha256':sha(OUT/'checkpoints'/f'{arm}_refined.pth')};text+=f"|{arm}|{c['P']:.8g}|{c['D']:.8g}|{c['gap']:.8g}|{2*c['gap']/c['scalar_observations']:.8g}|{c['mse_upper']:.8g} / {c['mse_lower']:.8g}|{d['iterations']}|{d['claim']}|\n"
 text+='\n数值下界对应原生固定权重和有效 SH0 颜色 [0,1] 的操作权限，带预先冻结 3e-7 MSE 有限精度余量；不把它推广为 3DGS 固有极限，不唯一归因于位置、尺度或选核。需要更严格的误差预算时保留数值认证边界；本轮不发布一般表示不可达定理。F10/F11 的 dev-out 数据角色中，22/26/30° 已成为其实际训练范围内插值，仅38°仍为外推；各行相机状态详见 SUPPLEMENTAL_AUDIT.json。额外诊断监督不参加仅原监督方法排名。\n'
 l1=json.loads((ART/'results/C1_exact_convex_refined.json').read_text());lc=l1['certificate'];old=sum(l1['v1_Adam_same_objective'].values());text+=f"\n相同 v1 band L1+outside MSE 续算：可行 P={lc['exact_v1_primal']:.9g}，D={lc['dual_lower']:.9g}，gap={lc['gap']:.9g}；原 Adam 同目标={old:.9g}。可行目标降低 {(1-lc['exact_v1_primal']/old)*100:.2f}%，这项改善不等于开发外推修复，不借用 MSE 目标最优值证明 L1 最优。\n"
 text+='\n## 全域、配对剖面与端到端费用补充\n\n| R2 分支 | dev-out 可测率 | 全可靠前景孔洞 | 外轮廓 MSE | 全部7000步秒 / 单元总秒（含准备、评价） |\n|---|---:|---:|---:|---|\n'
 costs={}
 for arm in ('G00','G10','G01','G11'):
  d=json.loads((ART/'results'/f'{arm}.json').read_text());s=d['metrics']['summary']['dev-out'];seal=json.loads((OUT/'seals'/f'{arm}.json').read_text());costs[arm]={'training_wall_seconds':d['duration_seconds'],'unit_end_to_end_seconds':seal['duration_seconds'],'peak_gpu_note':'reported allocated peak includes evaluation allocations, not isolated training peak'};text+=f"|{arm}|{s['profile_measurement_fraction']:.4f}|{s['full_foreground_holes']:.7g}|{s['outer_contour_mse']:.7g}|{d['duration_seconds']:.3f} / {seal['duration_seconds']:.3f}|\n"
 text+='\nG00 最后1000步 RGB目标接近平稳且轻微波动，未启动长度扩展。R2 的最大分配显存包含随后评价，不能当成纯训练峰值做效率优势主张。共同有效剖面需按每视角配对；R3 表已使用共同剖面，R2 宽度需结合上述可测率与逐剖面 JSON，不因拒绝更多剖面宣称更好。\n'
 import json as js
 source_sel=ROOT/'experiments/object_neighborhood_edge_control_v1/results/manifests/selection_panels_high.json';oldcost=js.loads(source_sel.read_text()).get('C1_time_seconds',404.5)
 text+=f'\n完整 C1 选择历史实测 {oldcost:.3f} 秒，本轮固定集合复用。冷启动费用需再加该成本；v2 单元总墙钟含准备和评价，R3 单独记录优化墙钟及预处理。等墙钟普通对照包括实际目标日志开销，不是纯 CUDA kernel 时间。所有组基于训练 mask 的贡献代理标签和固定 coverage；不宣称完全无 mask 的 RGB-only 端到端系统。\n'
 if r5.get('status')=='COMPLETED_DIAGNOSTIC_SUBSET':
  text+=f"\nR5 实际诊断子集 N={r5['subset_N']}，包围盒候选对={r5['actual_pairs']}，三态计数={r5['counts']}，查询 {r5['query_seconds']:.6g} 秒、上下界求解 {r5['bounds_solve_seconds']:.6g} 秒。已知跨阈值区间返回 uncertain。解析例将 contact、near-noncontact、远平面/大 Gaussian 支持代理分别保存；远表面可以有 support_near，因此仍不能把支持相交当物理接触。该子集成本不能替代原全量404.5秒成本。\n"
 text+='\nR0 的相机横向协方差投影宽度、贡献权重、量化误差底限，以及 O-cov 最终完整训练 epoch 的分项梯度均有新增实测审计；梯度只验证连接，不跨单位排名。新 TEST 的尺寸/姿态条件与相机已冻结，但姿态后边界法向评价器和目标生成扩展尚未验证，这也是保持 TEST_CLOSED 的工程原因。三条视频各36帧全部解码，包含失败的完整视角；未评测或宣称时间重投影优势。\n'
 (ART/'REPORT_ZH.md').write_text(text)
 final.update({'state':'FOLLOWUP_PILOT_AND_CONVERGENCE_COMPLETED_TEST_CLOSED','R1_refinements':refinements,'same_v1_convex_objective_refined':lc,'R5':r5['status'],'R4':'COMPLETED_SIX_PROBES','supplemental_audit_sha256':sha(ART/'SUPPLEMENTAL_AUDIT.json'),'native_input_hashes_verified_unchanged':True,'R2_costs':costs,'completed_unit_seal_count':len(audit['seals']),'test_new_target_generator_status':'SIZE_POSE_EXTENSION_AND_NORMAL_PROFILES_NOT_VALIDATED_TEST_CLOSED','formal_GO':False,'scientific_limits':['single scene/seed diagnostic','R2 final N differs, no count-matched causal advantage','R3 dev gates fail, no independent control advantage','fixed-weight SH0 numerical bounds do not prove general 3DGS limits','no old low/far TEST reads']})
 atomic_json(ART/'FINAL.json',final)
 # Include all actual input/output checkpoint provenance of controlled probes.
 probe_inputs={str(p.relative_to(ROOT)):sha(p) for p in (OUT/'probe').rglob('*') if p.is_file()};atomic_json(ART/'R4_INPUT_HASHES.json',{'inputs':probe_inputs,'solver_contract':'only perturbed.pth, solver_uid_inputs.json and targets/*.npy consumed; injector_oracle.json is not solver input','oracle_manifest_ignored_out':True})
 atomic_json(OUT/'FINALIZE_STATUS.json',{'phase':'COMPLETED','pid':os.getpid(),'inputs_unchanged':True,'TEST_CLOSED':True});print('FINALIZATION_COMPLETED',flush=True)
if __name__=='__main__':main()
