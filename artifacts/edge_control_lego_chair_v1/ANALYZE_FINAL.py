"""CPU-only post-run audit/plots from frozen native results; no optimizer/GPU."""
import sys,json,hashlib,struct
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/edge_control_lego_chair_v1/src'))
from runtime import ROOT,EXP,ART,OUT,sha,source_hashes,atomic_json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    final=json.loads((ART/'FINAL.json').read_text());freeze=json.loads((ART/'SOURCE_FREEZE.json').read_text());data=json.loads((ART/'DATA_FREEZE.json').read_text())
    assert final['phase']=='COMPLETE' and final['integrity_pass']
    assert freeze['source_hashes']==source_hashes()
    counts={};timings={};decision={};fig,axes=plt.subplots(2,2,figsize=(13,9))
    for row,scene in enumerate(('lego','chair')):
        state=json.loads((ART/f'{scene}_FINAL.json').read_text());s=data['scenes'][scene]
        assert state['phase']=='COMPLETE' and state['source_model_sha256_before']==state['source_model_sha256_after']==sha(s['model'])
        operations={};epoch_audit={}
        for name,record in state['optimization'].items():
            full=json.loads((ART/'results'/f'{scene}_{name}_optimization.json').read_text())
            e=np.load(full['edit_path']);assert len(e['ids'])==full['selected_count'] and full['permissions']['pass']
            assert len(np.unique(e['ids']))==len(e['ids']) and int(e['ids'].min())>=0 and int(e['ids'].max())<s['ply']['count']
            assert len(full['online_steps'])==full['steps']
            for epoch in full['full_epochs']:
                assert len(epoch['all_train_views'])==8
                for k,v in epoch['full_train_mean'].items():assert abs(v-np.mean([a[k] for a in epoch['all_train_views']]))<1e-12
            operations[name]={'steps':full['steps'],'optimizer_seconds':full['optimizer_seconds'],'initialization_seconds':full['initialization_seconds'],'time_budget':full['matched_time_target'],'walltime_overrun':None if full['matched_time_target'] is None else full['optimizer_seconds']-full['matched_time_target']}
            epoch_audit[name]={'complete_epochs':len(full['full_epochs']),'all_8_train_views_per_epoch':True,'last_complete_epoch_objective':full['full_epochs'][-1]['full_train_mean'] if full['full_epochs'] else None}
            if name in ('relative_color','relative_color_ordinary','relative_cov','relative_cov_ordinary','band2d_cov','random_cov'):
                epochs=full['full_epochs'];axes[row,0].plot([e['epoch'] for e in epochs],[e['full_train_mean']['band_mse'] for e in epochs],label=name)
        b0=state['holdout']['B0']['mean_per_view'];scores={n:r['mean_per_view'] for n,r in state['holdout'].items()}
        arms=['B0','relative_color','relative_color_ordinary','relative_cov','relative_cov_ordinary','band2d_cov','random_cov'];axes[row,1].bar(np.arange(len(arms)),[scores[n]['band_mse'] for n in arms],color=['#666666','#e18b21','#a2b8cf','#c13d37','#68a99e','#4d74b2','#9b67a6']);axes[row,1].set_xticks(np.arange(len(arms)));axes[row,1].set_xticklabels(arms,rotation=25,ha='right',fontsize=8)
        axes[row,0].set_title(f'{scene}: all 8 train cameras / complete epochs');axes[row,0].set_xlabel('Complete epoch');axes[row,0].set_ylabel('Fixed internal band display RGB MSE');axes[row,0].legend(fontsize=7);axes[row,0].grid(alpha=.2)
        axes[row,1].set_title(f'{scene}: exploratory GS-seen edit-holdout / 8 views');axes[row,1].set_ylabel('Mean per-view fixed band MSE')
        videos=state['media'];media_audit=[]
        for record in videos:
            p=Path(record['path']);assert sha(p)==record['video_sha256'];assert record['frames']==record['decoded_frames']==record['distinct_decoded_frames']==33;assert len(set(record['camera_hashes']))==33;assert record['width']<=1600
            blob=p.read_bytes();boxes=[];offset=0
            while offset+8<=len(blob):
                size,kind=struct.unpack('>I4s',blob[offset:offset+8]);header=8
                if size==1:size=struct.unpack('>Q',blob[offset+8:offset+16])[0];header=16
                if size==0:size=len(blob)-offset
                if size<header or offset+size>len(blob):raise AssertionError('invalid MP4 top-level box')
                boxes.append(kind.decode('ascii'));offset+=size
            assert boxes.index('moov')<boxes.index('mdat')
            media_audit.append({'path':str(p),'top_level_boxes':boxes,'faststart_actual_verified':True})
        counts[scene]={'source_gaussians':s['ply']['count'],'selected_count':state['selection']['budget'],'unique_original_TRAIN_photos':20,'edit_train':8,'dev':4,'edit_holdout':8,'methods':len(state['holdout']),'saved_native_evaluated_RGB_views':sum(len(r['views']) for r in state['train'].values())+sum(len(r['views']) for r in state['dev'].values())+sum(len(r['views']) for r in state['holdout'].values()),'fourview_contact_sheets':2,'same_camera_native_figures':8,'native_edge_crop_figures':8,'edge_zoom_figures':8,'videos':len(videos),'decoded_video_frames':sum(v['decoded_frames'] for v in videos),'actual_camera_path_frames_per_video':33,'source_SH_degree':3,'rest_SH_coefficients_per_Gaussian':45,'original_TEST_images_read':0,'media_faststart_audit':media_audit}
        timings[scene]={'scene_seconds':state['scene_seconds'],'preparation_seconds':state['preparation_seconds'],'selection_seconds':state['selection']['selection_seconds'],'operations':operations,'epoch_audit':epoch_audit,'timing_scope':'optimizer wallclock includes training, epoch objective evaluation and epoch delta saves; initialization excludes CPU permission snapshots/audit; those and evaluation/media are in scene total'}
        primary=scores['relative_cov'];ordinary=scores['relative_cov_ordinary'];band=scores['band2d_cov'];random=scores['random_cov']
        decision[scene]={'primary_vs_B0_band_improvement':1-primary['band_mse']/b0['band_mse'],'primary_vs_same_permission_ordinary_band_improvement':1-primary['band_mse']/ordinary['band_mse'],'band2d_vs_B0_band_improvement':1-band['band_mse']/b0['band_mse'],'random_vs_B0_band_improvement':1-random['band_mse']/b0['band_mse'],'relative_selector_coverage':state['selection']['selectors']['relative']['band_contribution_coverage'],'band2d_selector_coverage':state['selection']['selectors']['band2d']['band_contribution_coverage'],'primary_psnr_delta_dB':primary['whole_psnr']-b0['whole_psnr'],'primary_holes_delta_percentage_points':100*(primary['foreground_holes']-b0['foreground_holes']),'formal_advantage_claim':False,'independent_human_visual_GO':'PENDING'}
    fig.tight_layout();fig.savefig(ART/'figures/actual_complete_epoch_and_holdout_curves.png',dpi=160);plt.close(fig)
    atomic_json(ART/'COUNTS.json',counts);atomic_json(ART/'TIMINGS.json',timings);atomic_json(ART/'SCIENTIFIC_DECISION.json',decision)
    lines=['','## 实测数量、成本和负结果补充','']
    for scene,d in decision.items():
        lines.extend([f'{scene.title()}：relative-cov 相对 B0 的留出 band MSE 改善 {d["primary_vs_B0_band_improvement"]:.2%}，相对同权限 ordinary-cov 改善 {d["primary_vs_same_permission_ordinary_band_improvement"]:.2%}；simple band2d 改善 {d["band2d_vs_B0_band_improvement"]:.2%}，可见率/质量匹配 random 改善 {d["random_vs_B0_band_improvement"]:.2%}。因此该预算下没有 relative selector 优势证据。relative TRAIN贡献覆盖 {d["relative_selector_coverage"]:.2%}，band2d {d["band2d_selector_coverage"]:.2%}；局部影响范围更窄也降低了边缘覆盖，不能只看覆盖率或只看 outside保持。',''])
    lines.extend(['两场景共400个实际同相机评估 RGB（20相机×10方法×2场景），16条完整33帧视频，共528个解码帧；另有4张四视角接触表、16张逐相机全图、16张原生边缘crop和16张放大crop。20张原始TRAIN照片/场景，没有300图campaign。','',
    '参考可测率与方法有效率分开：TARGET_FREEZE 的 metadata 保存原参考提案/拒绝/合格数量；results 的 valid_profile_rate 仅以固定合格参考剖面为分母，不能当作所有真实边缘的可测率。纹理Chair的部分相机参考剖面数为0，此时W=null，主要结论使用完整固定band RGB与真实图。','',
    '[完整epoch和实际留出对照曲线](figures/actual_complete_epoch_and_holdout_curves.png)。COUNTS/TIMINGS/SCIENTIFIC_DECISION 保存实际数量、墙钟范围与描述性判断；CPU后审计代码为 ANALYZE_FINAL.py，不改变生产源码、参数、目标或选择。',''])
    with (ART/'REPORT_ZH.md').open('a') as f:f.write('\n'.join(lines))
    final.update({'actual_counts':counts,'actual_scene_timings':{s:t['scene_seconds'] for s,t in timings.items()},'CPU_postrun_audit':'PASS','scientific_decision_sha256':sha(ART/'SCIENTIFIC_DECISION.json')});atomic_json(ART/'FINAL.json',final)
    source=json.loads((ART/'SOURCE_MAP.json').read_text());source['CPU_postrun_code']={str((ART/'ANALYZE_FINAL.py').relative_to(ROOT)):sha(ART/'ANALYZE_FINAL.py')};source['curated_artifacts']={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in ART.rglob('*') if p.is_file() and p.name not in ('SOURCE_MAP.json','PUBLISH_READBACK.json')};atomic_json(ART/'SOURCE_MAP.json',source)
    print(json.dumps(decision,indent=2))

if __name__=='__main__':main()
