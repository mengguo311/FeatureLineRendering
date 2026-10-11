"""Package the completed, visually reviewed bounded CPU experiment."""
from pathlib import Path
import json,os,hashlib,shutil,tarfile,datetime,html,subprocess
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/astra_near_line_optimization_v01')
C=Path(__file__).resolve().parent
R=T/'final_v02_validated'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):
 p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');os.replace(tmp,p)
notes={
 'scan24_0000':('PARTIAL','楼体和底部比hardcut完整、屋顶碎纹减少；右/下长背景波纹仍强，S2不能解决。'),
 'scan24_0024':('PARTIAL','后侧楼体、连接立面与底部回收，屋顶更清楚；窗框有缺口，右侧仍有背景。'),
 'scan24_0048':('PARTIAL','山墙台阶与窗框保留，S2右背景减少；上方及右下仍有平行条纹。'),
 'scan37_0000':('PARTIAL','工具主形保留，多重环线减少；周围石面/背景线仍密，细节有损。'),
 'scan37_0024':('PARTIAL','回收hardcut裁掉的两只剪刀柄；S2上部波纹减少，左下背景仍强。'),
 'scan37_0048':('PARTIAL','S2保留弱视角剪刀柄与刃的较完整形状，上背景明显减少；刀刃内细线仍碎。'),
 'scan40_0000':('WEAK','主体底部恢复；背景条纹仍强，S2没有明确进一步改善。'),
 'scan40_0024':('PARTIAL','回收主体右侧/顶部，表面噪声少；细孔缺失，两侧背景仍在。'),
 'scan40_0048':('WEAK','整体盒状外形恢复；墙面细节简化，右下背景波纹未解决。'),
 'scan55_0000':('WEAK','主体体量回收，但细线破碎、背景残留，不作全面推荐。'),
 'scan55_0024':('WEAK','外形较hardcut完整；内部细结构过度简化，连续性不足。'),
 'scan55_0048':('NEGATIVE_FINE_STRUCTURE','细主体轮廓仍断裂，减少线数不等于更可读，S1/S2均不足。'),
 'scan63_0000':('WEAK','后侧果物回收；右侧大范围背景条纹仍主导，S2帮助有限。'),
 'scan63_0024':('PARTIAL','果物组合比hardcut完整，上背景减少；右/下波纹仍强，局部弧线断裂。'),
 'scan63_0048':('NEGATIVE_S2_BODY_LOSS','S2仍删除偏后主体，不推荐；S1保留更多但背景杂乱。拍摄中心先验不等于主体。'),
 'scan65_0000':('WEAK','头骨后侧/下部回收且碎纹少；右上背景仍强，颅缝细节缺失。'),
 'scan65_0024':('PARTIAL','回收较完整头形，背景减少；颅顶外轮廓仍有断口，牙齿细节简化。'),
 'scan65_0048':('PARTIAL','S2上背景明显减少，保留比hardcut更多侧面与下部；轮廓不完全，右侧仍杂乱。'),
}
m=json.loads((R/'RUN_MANIFEST.json').read_text());assert len(m['records'])==18
assert json.loads((T/'logs/13_validation.json').read_text())['validation']=='PASS'
review=[]
for r in m['records']:
 label=r['scene']+'_'+r['view'];grade,note=notes[label]
 review.append({'scene':r['scene'],'view':r['view'],'review_method':'actual view_image of final four-way comparison','image':r['comparison'],'image_sha256':sha(r['comparison']),'assessment':grade,'note_zh':note,'global_best_claim':False})
dump(T/'VISUAL_REVIEW.json',{'reviewed':18,'unconditional_all_views_acceptable':False,'results':review})
output_files=[{'path':str(p),'relative_path':str(p.relative_to(T)),'sha256':sha(p),'bytes':p.stat().st_size,'in_lightweight_archive':p.suffix!='.npz'} for p in sorted(R.rglob('*')) if p.is_file()]
manifest={'scope':'depth-derived line optimization; no training, mesh or GPU','method_variant_inputs':'official_code_fix_v01, with distinct native revisions retained',
 'method_variant_outputs':['S1_robust_soft_distance_v02','S2_robust_world_attention_multiview_v02'],
 'checkpoint':30000,'scenes':['scan24','scan37','scan40','scan55','scan63','scan65'],'views':['0000','0024','0048'],
 'unique_output_views':18,'new_native_blackwhite_images':36,'baseline_native_blackwhite_images':36,'comparisons':18,'support_panels':18,
 'visual_acceptance':'PARTIAL_WITH_NEGATIVE_VIEWS_NOT_UNIVERSAL','visual_review':str(T/'VISUAL_REVIEW.json'),
 'source_provenance_index':str(T/'PROVENANCE_INDEX.json'),'input_run_manifest':str(R/'RUN_MANIFEST.json'),
 'records':m['records'],'source_ledger':m['source_ledger'],'parameters':m['parameters'],'output_files':output_files,
 'output_file_count':len(output_files),'raw_float_response_maps_kept_on_HDD':True,'archive_excludes':['raw original depth','model','environment','large float response maps'],
 'code_files':{str(p):sha(p) for p in sorted(C.glob('*.py'))},'full_frame_native_size':[777,581],
 'line_width':'1px binary skeleton; no grayscale shadow lines','image_border_validity_guard_pixels':19,
 'none_of':['RGB-generated line','GT input','semantic segmentation','manual crop','3D ink identity claim'],
 'tests':{'count':16,'passed':16,'red_and_green_logs':str(T/'logs')},
 'validation':json.loads((T/'logs/13_validation.json').read_text())}
dump(T/'RESULTS_MANIFEST.json',manifest)
# All source camera metadata is small and directly downloadable.
meta=T/'camera_metadata';meta.mkdir(exist_ok=True)
for sc in manifest['scenes']:
 r=next(r for r in m['records'] if r['scene']==sc);shutil.copy2(r['camera_file'],meta/(sc+'_cameras_and_conventions.json'))
# Local gallery: no network, no image alteration, original PNG opens at native size.
items=[]
for r in m['records']:
 label=r['scene']+'_'+r['view'];note=notes[label][1]
 cells=''.join('<figure><figcaption>'+title+'</figcaption><a href="final_v02_validated/'+label+'/'+name+'.png"><img loading="lazy" src="final_v02_validated/'+label+'/'+name+'.png"></a></figure>' for name,title in [('D','原D'),('hardcut','已否定硬cut'),('S1','S1 · 结构优先候选'),('S2','S2 · 世界注意区域候选')])
 items.append('<section data-scene="'+r['scene']+'"><h2>'+label+'</h2><p>'+html.escape(note)+'</p><div class="row">'+cells+'</div><a href="final_v02_validated/'+label+'_fixedcamera_comparison.jpg">完整四方对照</a> · <a href="final_v02_validated/'+label+'_support.jpg">支持/权重图（不是语义分割）</a></section>')
page='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>深度线稿 18 视角对照</title><style>body{font:16px system-ui;margin:28px;color:#222}header{position:sticky;top:0;background:#fff;padding:10px 0;border-bottom:1px solid #ccc;z-index:1}section{border-bottom:1px solid #ccc;padding:24px 0}.row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}figure{margin:0}img{width:100%;height:auto}figcaption{padding:8px;background:#eee}a{color:#17518a}select{font-size:18px}h1{font-size:24px}</style><header><h1>主体完整性与背景杂线：真实深度线稿对照</h1><p>18个固定训练视角，参数一致。局部改善；S2仍有误删主体反例，不是通用最佳。点击图像查看原生1px PNG。</p><label>场景 <select id="scene"><option value="all">全部18视角</option>'''+''.join('<option>'+s+'</option>' for s in manifest['scenes'])+'''</select></label></header>'''+''.join(items)+'''<script>document.querySelector('#scene').onchange=function(){document.querySelectorAll('section').forEach(s=>s.hidden=this.value!=='all'&&s.dataset.scene!==this.value)};</script></html>'''
(T/'INDEX.html').write_text(page)
# Stage only our task deliverables; never stage raw original data or an environment.
delivery=T/'delivery';delivery.mkdir(exist_ok=False)
for name in ['ASTRA_ASSESSMENT_AND_PLAN_ZH.md','IMPLEMENTATION_REPORT_ZH.md','RESULTS_MANIFEST.json','VISUAL_REVIEW.json','PROVENANCE_INDEX.json','EVIDENCE_MANIFEST.json','INDEX.html']:
 shutil.copy2(T/name,delivery/name)
shutil.copytree(C,delivery/'code',ignore=shutil.ignore_patterns('__pycache__'))
for name in ['provenance','camera_metadata','logs']:shutil.copytree(T/name,delivery/name)
shutil.copytree(R,delivery/R.name,ignore=shutil.ignore_patterns('*.npz'))
# Include the failed initial six comparisons as negative controls, not all large arrays.
neg=delivery/'negative_pilot_v01';neg.mkdir()
for p in (T/'pilot_v01').glob('*_fixedcamera_comparison.jpg'):shutil.copy2(p,neg/p.name)
shutil.copy2(T/'pilot_v01/RUN_MANIFEST.json',neg/'RUN_MANIFEST.json');shutil.copytree(T/'pilot_v01/code',neg/'code')
# Human-readable file count and purpose; original negative evidence stays on HDD.
(delivery/'README_ZH.txt').write_text('打开 INDEX.html 查看18视角。final_v02_validated里有72张原生二值PNG（36新算法+36原baseline）及权重图。\n原始10GB级深度、环境和float响应不打包；全部真实路径和SHA见RESULTS_MANIFEST.json。\nnegative_pilot_v01是保留的首轮不足结果。S2在scan63/0048误删主体，不能统一称best。\n包SHA及最终交付状态见服务器同目录外置ASTRA_FINAL.md、DELIVERABLE.sha256，以免自引用hash。\n')
# Validate the actual package files and all local gallery targets before archiving.
assert len(list((delivery/R.name).glob('scan*/S1.png')))==18
assert len(list((delivery/R.name).glob('scan*/S2.png')))==18
import re
for target in re.findall(r'(?:src|href)="([^"]+)"',page):assert (delivery/target).is_file(),target
for p in delivery.rglob('*.json'):json.loads(p.read_text())
# No training/suite runner launched; the CPU worker completed normally.
status={'phase':'BOUNDED_LINE_OPTIMIZATION_DELIVERED','status':'COMPLETED_WITH_PARTIAL_VISUAL_IMPROVEMENT','scope':'depth-derived lines only',
 'method_variants':manifest['method_variant_outputs'],'completed_scenes':6,'completed_unique_views':18,'new_native_line_images':36,'baseline_line_images':36,
 'fixedcamera_comparisons':18,'visual_reviewed_views':18,'visual_acceptable_all_views':False,
 'selection':'S1 structure-priority candidate; S2 conditional alternative, rejected as universal replacement',
 'negative_examples':['scan63/0048 S2 body deletion','scan55/0048 fragmented fine structure','scan24/0000 persistent far background'],
 'tests_passed':16,'source_and_output_validation':'PASS','validation_counts':manifest['validation']['counts'],
 'remaining_scientific_limitations':['depth-overlapping background cannot be uniquely separated by current priors','disconnected/weak silhouette remains','no stable 3D ink or held-out claim'],
 'active_workers':[],'gpu_used':False,'background_jobs_started':False,'full_reproduction_resumed':False,
 'artifact_root':str(T),'result_manifest':str(T/'RESULTS_MANIFEST.json'),'archive_path':str(T/'DELIVERABLE.tar.gz'),
 'archive_checksum_sidecar':str(T/'DELIVERABLE.sha256'),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'disk_free_GiB':{'root':shutil.disk_usage('/').free/2**30,'HDD':shutil.disk_usage(T).free/2**30}}
dump(delivery/'STATUS.json',status)
files=[p for p in sorted(delivery.rglob('*')) if p.is_file()]
(delivery/'PACKAGE_CONTENTS.sha256').write_text(''.join(sha(p)+'  '+str(p.relative_to(delivery))+'\n' for p in files))
archive=T/'DELIVERABLE.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
 for p in sorted(delivery.rglob('*')):
  if p.is_file():tar.add(p,arcname='astra_near_line_optimization_v01/'+str(p.relative_to(delivery)),recursive=False)
assert archive.stat().st_size<45*1000*1000,archive.stat().st_size
with tarfile.open(archive,'r:gz') as tar:
 members=tar.getmembers();assert all(m.isfile() for m in members)
 expected={str(p.relative_to(delivery)):sha(p) for p in delivery.rglob('*') if p.is_file()}
 assert len(members)==len(expected)
 for member in members:
  rel=member.name.split('/',1)[1];assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
  assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==expected[rel]
h=sha(archive);(T/'DELIVERABLE.sha256').write_text(h+'  DELIVERABLE.tar.gz\n')
dump(T/'STATUS.json',status)
package={'status':'VERIFIED','archive_path':str(archive),'sha256':h,'bytes':archive.stat().st_size,'members':len(members),'all_member_hashes_match':True,'no_raw_depth_env_or_float_responses_in_archive':True}
dump(T/'PACKAGE_VALIDATION.json',package)
final=f'''# Astra 本轮实际交付\n\n已实现并真实执行两种CPU深度线方案，完成6场景×3固定视角=18组四方对照，36张新算法原生黑白PNG；16项CPU测试GREEN，168项输入文件SHA重核验及72张原生二值图检查PASS。所有18张最终对照均已实际view_image审查。\n\n结论是**局部改善，未全面解决**：相对硬cut回收主体，部分视角远背景减少。S1作为结构优先候选；S2是可选的更集中方案，不是通用best。scan63/0048的S2仍误删后侧主体，scan55/0048仍碎；没有把这些负结果删掉。无GPU、无新训练/mesh/cron；没有commit/push。\n\n先发给用户看的实际图（完整画面、四方同相机）：\n\n- `{R}/scan37_0048_fixedcamera_comparison.jpg`：回收剪刀柄，上背景减少。\n- `{R}/scan24_0024_fixedcamera_comparison.jpg`：楼体/底部恢复。\n- `{R}/scan65_0048_fixedcamera_comparison.jpg`：上背景减少，更多头骨侧面保留。\n- `{R}/scan63_0048_fixedcamera_comparison.jpg`：必须一并披露的S2误删反例。\n\n浏览入口：`{T}/INDEX.html`；各原生PNG、支持权重图、参数、相机与来源SHA见`{T}/RESULTS_MANIFEST.json`。实现、TDD真实RED/GREEN和详细逐场景限制见`{T}/IMPLEMENTATION_REPORT_ZH.md`。代码：`{C}`。\n\n交付包：`{archive}`\n\n大小：{archive.stat().st_size} bytes（{archive.stat().st_size/1000**2:.2f} MB），{len(members)}个成员逐个SHA验证。\n\nSHA256：`{h}`\n\n此文件是包外最终handoff，包内以独立PACKAGE_CONTENTS.sha256逐项校验，避免压缩包包含自身hash的循环。没有包含原始depth大包、环境或模型；大float响应仅保留在专属HDD。\n\n后续不建议继续缩浅深度阈值/提高稀疏度。当前缺陷是几何一致背景、偏离拍摄中心主体与连续轮廓表达之间的可分性；本次有界探索已结束，结果供用户视觉选择，未自动继续其它研究任务。\n'''
(T/'ASTRA_FINAL.md').write_text(final)
print(json.dumps(package,indent=2))
if __name__=='__main__':pass
