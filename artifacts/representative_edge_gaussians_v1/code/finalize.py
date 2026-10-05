"""Create actual-count Chinese delivery, complete media, hashes and resumable status."""
import json,shutil,subprocess,hashlib,datetime,traceback
from pathlib import Path
import numpy as np
from PIL import Image
from io_utils import *
import visuals
from media_helpers import make_contact,encode_video,_save

def records(scene):
 return [json.loads(p.read_text()) for p in sorted((OUT/scene/'evaluation').glob('*/METRICS.json')) if (p.parent/'SEAL.json').exists()]
def means(records,arm,count):
 rows=[m for r in records for m in r['metrics'] if m['arm']==arm and m['count']==count]
 return {key:float(np.mean([m[key] for m in rows if m[key] is not None])) if any(m[key] is not None for m in rows) else None for key in ['major_coverage','detail_coverage','offedge_alpha_fraction','offedge_selected_mass_fraction','visible_mass','Q_weighted_distance_to_evidence_pixels']},len(rows)
def fmt(x):return '未运行' if x is None else f'{x:.4f}'
def frontier(scene,rs,path):
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 s=load(OUT/scene/'assets/scorebank.npz');selection=json.loads((OUT/scene/'assets/selected_ids.json').read_text());fig,axs=plt.subplots(1,3,figsize=(15,4.5))
 labels=dict(A='A old independent',B='B new independent',C='joint lambda0',D='joint lambda.1',E='joint lambda.3');colors=dict(A='black',B='gray',C='tab:blue',D='tab:orange',E='tab:green')
 for arm in labels:
  u=s[arm+'_utility_curve'];cost=s[arm+'_cumulative_nonedge_cost'];axs[0].plot(np.arange(1,len(u)+1),u,label=labels[arm],color=colors[arm]);axs[1].plot(cost,u,color=colors[arm],label=labels[arm])
  cr=[r for r in rs if r['phase']=='C'];xs=[];ys=[]
  for b in selection['budgets']:
   count=min(b,len(s[arm+'_ordered_ids']));m,n=means(cr,arm,count)
   if n:xs.append(m['offedge_alpha_fraction']);ys.append(m['major_coverage'])
  if xs:axs[2].plot(xs,ys,'o-',color=colors[arm],label=labels[arm])
 axs[0].set(xlabel='original ID count (F prefixes)',ylabel='balanced F utility, demand .5 full alpha');axs[1].set(xlabel='F additive offedge cost',ylabel='balanced F utility');axs[2].set(xlabel='C native offedge alpha fraction',ylabel='C major coverage (all8 views mean)')
 for ax in axs:ax.grid(alpha=.25)
 axs[0].legend(fontsize=8);fig.suptitle(scene+' | frozen all lambdas, original mass, no C tuning');fig.tight_layout();guard(8*1024**2);path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=180);plt.close(fig)

def video_content_audit(info):
 # Independently decode every video; title/footer are excluded from RGB content checks.
 import cv2
 cap=cv2.VideoCapture(info['path']);full=[];rgb=[];sizes=[]
 while True:
  ok,frame=cap.read()
  if not ok:break
  h,w=frame.shape[:2];x1=int(w*.2);y0=int(round(h*84/1768));y1=int(round(h*884/1768));roi=frame[y0:y1,:x1]
  full.append(hashlib.sha256(frame.tobytes()).hexdigest());rgb.append(hashlib.sha256(roi.tobytes()).hexdigest());sizes.append([w,h])
 cap.release();assert len(full)==33 and len(set(full))==33 and len(set(rgb))==33
 return dict(decoded_count=33,distinct_full_frames=33,distinct_RGB_content_without_labels=33,RGB_content_sha256=rgb,full_frame_sha256=full,dimensions=sizes[0],consistent_dimensions=len(set(map(tuple,sizes)))==1)

def coverage_match_panels(scene,rs):
 selection=json.loads((OUT/scene/'assets/selected_ids.json').read_text());paths=[]
 for record in rs:
  if record['phase'] not in ('F','C'):continue
  key=record['key'];spec=next(f for f in INPUTS['scenes'][scene]['frames'] if f['key']==key);raw=read(scene,spec,'MEDIA_F_SELECTED_COVERAGE_MATCH');d=OUT/scene/'evaluation'/key
  q=load(d/'projection.npz')['Q'];e=load(OUT/scene/('F' if record['phase']=='F' else 'evaluation')/key/'evidence.npz');chosen=[];labels=[]
  for arm in 'ABCDE':
   count=selection['coverage_match_counts'][arm]
   if count is None:continue
   index=next(j for j,f in enumerate(record['fields']) if f['arm']==arm and f['count']==count);chosen.append(q[:,:,index]);labels.append(arm+' F匹配前缀 | '+str(count)+' IDs')
  path=d/'coverage_matched.jpg';visuals.comparison(path,raw,e,np.stack(chosen,-1),labels,scene+' '+key+' | 前缀只由F选择；当前视图未强行匹配覆盖')
  if record['phase']=='C':paths.append(path)
 if paths:
  guard(48*1024**2);return make_contact(paths,ART/'figures'/(scene+'_C_coverage_match.jpg'),tile_width=1600,columns=2)
 return None

def scene_media(scene,rs):
 d=OUT/scene/'media';curated=ART/'figures';curated.mkdir(exist_ok=True);d.mkdir(parents=True,exist_ok=True);media={'coverage_matched_C_contact':coverage_match_panels(scene,rs)}
 allkeys=[f['key'] for f in INPUTS['scenes'][scene]['frames']];valid={r['key'] for r in rs};ordered=[k for k in allkeys if k in valid];paths=[OUT/scene/'evaluation'/k/'comparison.jpg' for k in ordered]
 if paths:
  guard(96*1024**2);media['all_views_contact']=make_contact(paths,curated/(scene+'_all_views.jpg'),tile_width=1600,columns=2)
 ckeys=[f['key'] for f in frames(scene,'C') if f['key'] in valid]
 if ckeys:
  guard(48*1024**2);media['C_contact']=make_contact([OUT/scene/'evaluation'/k/'comparison.jpg' for k in ckeys],curated/(scene+'_C8.jpg'),tile_width=1600,columns=2)
 fkeys=[f['key'] for f in frames(scene,'F') if f['key'] in valid]
 if fkeys:
  guard(48*1024**2);media['F_contact']=make_contact([OUT/scene/'evaluation'/k/'comparison.jpg' for k in fkeys],d/'F8.jpg',tile_width=1600,columns=2)
 source=OUT/scene/'F/F_041/preview.jpg'
 if source.exists():guard(source.stat().st_size);shutil.copyfile(source,curated/(scene+'_F041_evidence.jpg'));media['F_evidence']=dict(path=str(curated/(scene+'_F041_evidence.jpg')),sha256=sha(curated/(scene+'_F041_evidence.jpg')))
 arc=[f['key'] for f in frames(scene,'arc')];ap=[OUT/scene/'evaluation'/k/'comparison.jpg' for k in arc]
 if all(k in valid for k in arc):
  guard(96*1024**2);media['arc_first_mid_last']=make_contact([ap[0],ap[16],ap[-1]],curated/(scene+'_arc_first_mid_last.jpg'),tile_width=2400,columns=1)
  guard(96*1024**2);media['arc_all33_contact']=make_contact(ap,d/'arc_all33.jpg',tile_width=1600,columns=2)
  for name,width in [('native',None),('telegram1600',1600)]:
   guard(128*1024**2);v=encode_video(ap,d/('arc33_'+name+'.mp4'),width=width,fps=CFG['video_fps']);v['content_audit']=video_content_audit(v);v['camera_hashes']=[f['camera_hash'] for f in frames(scene,'arc')];v['RGB_original_content_hashes']=[next(r['rgb_content_sha256'] for r in rs if r['key']==k) for k in arc];assert len(set(v['RGB_original_content_hashes']))==33;media['video_'+name]=v
   if name=='telegram1600':guard(Path(v['path']).stat().st_size);q=ART/'media'/scene/Path(v['path']).name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(v['path'],q);v['curated_path']=str(q);v['curated_sha256']=sha(q)
 else:media.update(video_native=None,video_telegram1600=None,actual_arc_frames=sum(k in valid for k in arc),requested_arc_frames=33)
 frontier(scene,rs,curated/(scene+'_frontier.png'));media['frontier']=dict(path=str(curated/(scene+'_frontier.png')),sha256=sha(curated/(scene+'_frontier.png')))
 atomic(d/'MEDIA.json',media);event('MEDIA_COMPLETE',scene=scene,actual_poses=len(rs),actual_arc=sum(r['phase']=='arc' for r in rs));return media

def summarize(scene,rs):
 sp=OUT/scene/'assets/selected_ids.json';selection=json.loads(sp.read_text()) if sp.exists() else None;meta=json.loads((OUT/scene/'assets/ASSET.json').read_text()) if sp.exists() else None
 result=dict(scene=scene,requested_pose_count=49,actual_pose_count=len(rs),actual_counts={p:sum(r['phase']==p for r in rs) for p in ['F','C','arc']},asset=meta,selection_path=str(sp) if sp.exists() else None,standard=[],coverage_matched=[],projection_kind='FULL_NATIVE_ORIGINAL_T' if rs else None)
 if selection:
  for phase in ['F','C']:
   rr=[r for r in rs if r['phase']==phase]
   for b in selection['budgets']:
    for arm in ['A','B','C','D','E']:
     count=min(b,selection['arms'][arm]['actual_prefix_length']);m,actual=means(rr,arm,count);result['standard'].append(dict(phase=phase,budget=b,arm=arm,count=count,actual_views=actual,metrics=m if actual else None))
   for arm,count in selection['coverage_match_counts'].items():
    m,actual=means(rr,arm,count) if count is not None else ({},0);result['coverage_matched'].append(dict(phase=phase,arm=arm,count=count,F_target=selection['coverage_match_F_target'],actual_views=actual,metrics=m if actual else None))
  q=ART/'assets'/scene;q.mkdir(parents=True,exist_ok=True);guard(sp.stat().st_size);shutil.copyfile(sp,q/'selected_ids.json');shutil.copyfile(OUT/scene/'assets/ASSET.json',q/'ASSET.json')
 atomic(ART/('SUMMARY_'+scene+'.json'),result);return result

def report(summaries,complete,media):
 lines=['# 代表性原始 Gaussian 支持组：实际实验报告','', '本轮实际运行固定 vanilla30k 模型的独立多尺度证据、扩展贡献、联合固定ID选择和原生全模型T属性投影。当前模型为 **gpt-6.1-sol / xhigh**；基点 `.codex/config.toml` 为 **gpt-6-astra / ultra**，历史结果不改名。科学对象是固定原始Gaussian ID组，不是几何边缘恢复。','',f"S0协议提交 `2b980d1807c7f22fdfbd7b186a44830c955c505d`、测试日志提交 `9595396b7736412353eeb9a5cfd210efe678a411` 已经SSH推送并读回。S0封条 `{sha(ART/'S0_SEAL.json')}`；全部F选择封条 `{sha(OUT/'F_SELECTION_SEAL/SEAL.json') if (OUT/'F_SELECTION_SEAL/SEAL.json').exists() else '未完成'}`。",'', '## S0—S4 实际阶段','', '| 场景 | S1 F证据 | S2共同容量 | S3五组预算 | S4 F / C / arc 原生姿态 | expanded eligible / unknown |','|---|---:|---:|---|---|---|']
 for s in summaries:
  scene=s['scene'];fcount=len(list((OUT/scene/'F').glob('*/SEAL.json')));a=s['asset'];counts=s['actual_counts'];lines.append(f"| {scene} | {fcount}/8 | {complete.get('available_K')} | {CFG['budgets'][scene] if a else '未运行'} | {counts['F']}/8 / {counts['C']}/8 / {counts['arc']}/33 | {str(a['eligible'])+' / '+str(a['unknown']) if a else '未运行'} |")
 lines+=['','实际合成CPU测试：S0 8项RED→GREEN，G0扩展共13项通过（pixel/world单位、独立NMS、短组件/DETAIL、raw fullalpha需求、原始ID、饱和冗余、泄漏早停、输出约束）。独立CPU从保存的raw foreground CSR重算每场景64个ID的B分子/分母及offedge成本；全网格质量只交叉核对per-view统计，不冒称独立CUDA实现。native与媒体校验和人类科学验收分开。','','## 管线原则与证据差异','','RGB/depth/alpha三类各用自身梯度方向NMS；sigma=0.8/1.6/3.2 px，Mic八F各尺度各类正值ROI P99，Materials/C/arc原样继承。masked log median-depth沿用历史双层平滑处理，有效深度尺度不同于单次Gaussian。旧sigma=1.0与新多尺度不是相同证据合同。任意>=2尺度2px内支持形成MAJOR，原0.8 fine未持久响应完整保存DETAIL；短母组件>=3px保留其所有32px空间格片段。1/2px证据保留但不进入chunk目标。每chunk强度归一后等重，每视图/类1/24，空类不转赠。空间块不是自动恢复的物理曲线；网罩与材质纹理仍可跨尺度持久。旧广union/81.49% Mic C alpha容差区域只作历史背景，不是新MAJOR目标。','','逐像素需求=0.5×原始full alpha，矩阵保存真实alphaT/demand；U=Σomega min(Σselected alphaT/demand,1)。全foreground网格保留非边缘反证，离MAJOR或DETAIL union>2px为offedge；成本为每F offedge mean(w/fullalpha)，八F均值。A历史TOP4 baseline_union独立排名，B新MAJOR+expanded贡献独立比率，C/D/E联合贪心λ=0/.1/.3。B分子为Σomega w/fullalpha，分母为等视图foreground mean(w/fullalpha)，可大于1，不是概率。三λ及三档固定预算全部显示；无C选英雄参数。懒堆增益按剩余需求精确更新；泄漏使目标可能非单调，不声称经典单调greedy保证。','','## S2 截断完整性与校准','','| K | 实际校准F | 通过门槛F | 最低weighted MAJOR mass | 最低MAJOR ray p10 |','|---|---:|---:|---:|---:|']
 for audit in complete.get('audits',[]):
  rr=audit['rows'];lines.append(f"| {audit['K']} | {len(rr)}/16 | {sum(r['coverage']['gate_pass'] for r in rr)}/16 | {min(r['coverage']['major']['captured_mass_fraction'] for r in rr):.6f} | {min(r['coverage']['major']['p10'] for r in rr):.6f} |")
 lines+=['', 'TOP32失败视图及K64扩展真实记录见 COMPLETENESS.json。冻结操作门槛为每F weighted MAJOR mass>=.95且MAJOR射线p10>=.90，ROI alpha>=.08；全部通过也不等于数学全部贡献。完整归因始终 **FULL_ATTRIBUTION_UNDETERMINED**，所有选择是最后共同可用K的条件结果。每F/类foreground、MAJOR、DETAIL、offedge的mean/p10/p05/min/剩余质量保留；unobserved核不是nonedge。完整native投影与截断归因严格区分。','', '原始RGB/alpha/depth/median-depth与缓存逐元素按原冻结容差校准；前4 ID完全一致、w和depth按原容差。S4全一属性≈alpha，全部field bank的alpha/depth/median-depth与原RGB遍历完全相同。全原模型核位置、形状、opacity、排序保持；未删除核。属性黑底Q=Σ原始alphaT×固定ID指示量；原RGB白底SH0 clipped DC、kernel_size0，高阶45个SH系数未参与渲染，不能当完整材质反射验证。native alpha<=.99、alpha<1/255跳过、T<1e-4提前终止；“完整native”以这些定义为限。','', '## 所有预算的C定量结果（实际视图均值）','', '| 场景 | 预算 / 实际IDs | arm | C视图 | MAJOR需求覆盖 | DETAIL需求覆盖 | offedge alpha贡献比例 | offedge占selected质量 |','|---|---|---|---:|---:|---:|---:|---:|']
 for s in summaries:
  for row in s['standard']:
   if row['phase']!='C':continue
   m=row['metrics'] or {};lines.append(f"| {s['scene']} | {row['budget']} / {row['count']} | {row['arm']} | {row['actual_views']} | {fmt(m.get('major_coverage'))} | {fmt(m.get('detail_coverage'))} | {fmt(m.get('offedge_alpha_fraction'))} | {fmt(m.get('offedge_selected_mass_fraction'))} |")
 lines+=['','需求覆盖是渲染证据处所需alpha支持的饱和效用，不是真实边缘准确率。offedge alpha比例是Σoffedge Q / Σoffedge alpha；selected漏出比例分母是Σ全图Q。两个分母不同；不能只看漏出占比或少核数。完整逐视图、class/chunk、宽度、原始mass结果与F/C前沿保留。','','## 仅F选择的coverage-match点','', '| 场景 | arm | 固定IDs | F目标U | C实际views | C MAJOR覆盖 | C offedge alpha比例 |','|---|---|---:|---:|---:|---:|---:|']
 for s in summaries:
  for row in s['coverage_matched']:
   if row['phase']!='C':continue
   m=row['metrics'] or {};lines.append(f"| {s['scene']} | {row['arm']} | {row['count']} | {row['F_target']:.5f} | {row['actual_views']} | {fmt(m.get('major_coverage'))} | {fmt(m.get('offedge_alpha_fraction'))} |")
 lines+=['','这些点仅用F最短前缀选择，C没有重新匹配覆盖。跨视图C覆盖可以偏离目标，应报告差异。所有标准预算是同数量比较，早停时另有实际同数量基线；本轮实际早停情况见ASSET与selection JSON。','','## 负结果、工程结论与科学范围','','成功诊断需同预算覆盖不崩塌且漏出下降，本报告直接展示两者，不因C调阈值。Gaussian整核足迹可能宽、含非边缘支持，不能用投影剪裁或逐视图mask伪造细线。ink宽度仅area(Q>threshold)/独立ridge像素数与Q加权到证据距离，单位px，不是物理边缘宽度。outline始终视角相关；geometry只是深度/遮挡证据；核在不可见视图不作为负例。未知核不被判nonedge。','', '模型视觉观察与人类验收另存VISUAL_REVIEW_ZH.md；**独立人类科学结论PENDING**。C是归因构造留出，GS训练见过全部TRAIN；旧媒体/demo已知，不称盲测。未使用人工标注、mesh、TEST、重训、中心连接、曲线拟合或几何P/R。未宣称时序优势或第三方方法复现。','', '内核来自第三方RaDe分支，历史阶段独立插桩，本轮复用TOP32及隔离容量扩展；不是原创RaDe。方法受weighted coverage/set-cover式饱和效用与已有贡献提升启发，不提出未经证明的新颖性或研究博客主张。历史audited core/native/media复制到本阶段，源码来源及SHA256在SOURCE_MAP。','', '## 实际交付与复现','']
 for s in summaries:
  scene=s['scene'];lines.append(f"- **{scene}**：[全部视图](figures/{scene}_all_views.jpg) · [全部C](figures/{scene}_C8.jpg) · [arc首中末](figures/{scene}_arc_first_mid_last.jpg) · [F选定覆盖匹配C图](figures/{scene}_C_coverage_match.jpg) · [F/C全部λ前沿](figures/{scene}_frontier.png) · [Telegram1600视频](media/{scene}/arc33_telegram1600.mp4) · [固定ID JSON](assets/{scene}/selected_ids.json)。")
 lines+=['', f'实际大型数组、native视频及逐姿态原始投影保留于 `{OUT}`，精确路径/每文件SHA256见 SOURCE_MAP.json；不修改旧demo/report。媒体保留native800所有完整帧，不cut arc；原始gain1，非匹配墨量。每段H264/yuv420p/+faststart，33帧逐帧解码，去标题RGB内容互异、相机hash/尺寸核验。图组12张（每场景6张），完整C所有预算单帧原始图留out。', '', '[复现步骤](REPRODUCE.md)、[协议](PROTOCOL.md)、[机器FINAL](FINAL.json)、[来源ledger](SOURCE_MAP.json)。STATUS原子记录实际阶段；plain runner按per-pose seal恢复；未运行不是0，工程阻碍如实记录。']
 (ART/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')

def stage():
 verify_s0();guard();complete=json.loads((OUT/'COMPLETENESS.json').read_text()) if (OUT/'COMPLETENESS.json').exists() else {};ss=[];mm={}
 for scene in CFG['scenes']:
  rs=records(scene);ss.append(summarize(scene,rs));mm[scene]=scene_media(scene,rs) if (OUT/scene/'assets/SEAL.json').exists() else None
 for name in ['COMPLETENESS.json','INDEPENDENT_CPU_AUDIT.json','NATIVE_CAPTURED_MASS_AUDIT.json']:
  if (OUT/name).exists():shutil.copyfile(OUT/name,ART/name)
 report(ss,complete,mm);final=dict(schema='representative-fixed-gaussian-final-v1',created_utc=utc(),model='gpt-6.1-sol',reasoning_effort='xhigh',historical_base_model='gpt-6-astra',historical_base_effort='ultra',base_sha=CFG['base_sha'],S0_commit='2b980d1807c7f22fdfbd7b186a44830c955c505d',F_selection_seal_sha256=sha(OUT/'F_SELECTION_SEAL/SEAL.json') if (OUT/'F_SELECTION_SEAL/SEAL.json').exists() else None,scenes=ss,media=mm,actual_pose_count=sum(s['actual_pose_count'] for s in ss),requested_pose_count=98,operational_completeness_gate=complete.get('operational_gate_pass'),mathematically_full_attribution='FULL_ATTRIBUTION_UNDETERMINED',human_science_verdict='PENDING',out_root=str(OUT),budget=guard(),cpu_tests=13,independent_cpu_audit=(ART/'INDEPENDENT_CPU_AUDIT.json').exists(),method_limits=['fixed original Gaussian ID support, not geometric edge recovery','C/arc not blind or GS-unseen','K-truncated attribution residuals remain','SH0 only, higher SH ignored','no temporal superiority or third-party method replication claim'])
 final['engineering_GO']=final['actual_pose_count']==98 and all(v and v.get('video_native') and v.get('video_telegram1600') for v in mm.values()) and final['independent_cpu_audit']
 atomic(ART/'FINAL.json',final);event('DELIVERY_GENERATED',actual_pose_count=final['actual_pose_count'],engineering_GO=final['engineering_GO'])
if __name__=='__main__':
 try:stage()
 except Exception as e:event('ENGINEERING_STOP',requested_phase='finalize',error=str(e),traceback=traceback.format_exc());raise
