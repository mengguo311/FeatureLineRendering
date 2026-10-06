"""Read-only post-seal reference validity and common widths separated by edge kind."""
import sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/edge_control_lego_chair_v1/src'))
from runtime import ART,atomic_json,sha
from data import load_reference
from evidence import build_evidence

def main():
    data=json.loads((ART/'DATA_FREEZE.json').read_text());out={};lines=['','## 参考剖面可测率与内部/轮廓共同宽度','']
    for scene,s in data['scenes'].items():
        state=json.loads((ART/f'{scene}_FINAL.json').read_text());records=[]
        for role,entries in s['roles'].items():
            scores=state[{'edit-train':'train','dev':'dev','edit-holdout':'holdout'}[role]]
            for i,e in enumerate(entries):
                gt,aa=load_reference(e,ART/f'{scene}_DEV_MODEL_SEAL.json' if role=='edit-holdout' else None)
                evidence=build_evidence(gt,aa);expected=scores['B0']['views'][i]['reference_profiles'];assert [p['id'] for p in evidence['profiles']]==[p['id'] for p in expected]
                records.append({'role':role,'key':e['key'],'metadata':evidence['metadata'],'fixed_reference_profiles':len(expected),'internal_reference_profiles':sum(p['kind']=='internal' for p in expected),'outline_reference_profiles':sum(p['kind']=='outline' for p in expected),'empty_reference_widths_null':len(expected)==0,'read_after_authentic_dev_model_seal':role=='edit-holdout'})
        common=json.loads((ART/'results'/f'{scene}_common_profiles_edit-holdout.json').read_text());bykind={}
        for kind in ('internal','outline'):
            views=[]
            for i,commonview in enumerate(common['all_methods_common_profiles']):
                ref={p['id']:p for p in state['holdout']['B0']['views'][i]['reference_profiles']};ids={p for p in commonview['common_ids'] if ref[p]['kind']==kind}
                errors={name:float(np.mean([abs(p['width']-ref[p['id']]['width']) for p in score['views'][i]['profiles'] if p['id'] in ids])) if ids else None for name,score in state['holdout'].items()}
                views.append({'key':commonview['key'],'kind':kind,'common_count':len(ids),'common_ids':sorted(ids),'mean_absolute_width_error_px':errors})
            macro={name:float(np.mean([v['mean_absolute_width_error_px'][name] for v in views if v['common_count']>0])) if any(v['common_count']>0 for v in views) else None for name in state['holdout']}
            bykind[kind]={'common_count':sum(v['common_count'] for v in views),'common_valid_views':sum(v['common_count']>0 for v in views),'macro_per_view_width_error_px':macro,'views':views}
        out[scene]={'reference_validity':records,'holdout_common_width_by_kind':bykind,'width_encoding':'linear RGB via declared sRGB EOTF','proposal_validity_scope':'algorithm-proposed normal samples, capped768 tested reference proposals per view; not an edge census','holdout_original_TEST_images_read':False}
        lines.append(f'{scene.title()} 留出共同内部剖面 {bykind["internal"]["common_count"]} 条 / {bykind["internal"]["common_valid_views"]} 视角；共同轮廓剖面 {bykind["outline"]["common_count"]} 条 / {bykind["outline"]["common_valid_views"]} 视角。内部和轮廓宽度不混为一种物理边缘。')
        for kind in ('internal','outline'):
            m=bykind[kind]['macro_per_view_width_error_px']
            def fmt(x):return 'null' if x is None else f'{x:.6f}'
            lines.append(f'{kind} 共同宽度 MAE(px)：B0 {fmt(m["B0"])}、relative-cov {fmt(m["relative_cov"])}、ordinary-cov {fmt(m["relative_cov_ordinary"])}、band2d-cov {fmt(m["band2d_cov"])}。')
        lines.append('')
    atomic_json(ART/'PROFILE_VALIDITY_AND_COMMON.json',out)
    with (ART/'REPORT_ZH.md').open('a') as f:f.write('\n'.join(lines)+'\n所有20个参考相机的提案/拒绝/合格计数在 PROFILE_VALIDITY_AND_COMMON.json；此 CPU 只读复核在生产封印之后执行，核验固定剖面 ID 一致，没有产生新优化或方法选择。\n')
    print({s:{k:v['common_count'] for k,v in x['holdout_common_width_by_kind'].items()} for s,x in out.items()})

if __name__=='__main__':main()
