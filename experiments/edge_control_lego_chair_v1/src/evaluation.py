import time
from collections import Counter
import numpy as np
import torch
from runtime import OUT,result,guard,event,sha
from adapter import render,alpha,selected_contribution
from preparation import save_png
from evidence import profile_metrics

def region_mse(a,b,mask):
    mask=np.asarray(mask,float);return float(((a-b)**2*mask[:,:,None]).sum()/max(mask.sum()*3,1))
def evaluate_view(model,v,ids,output):
    with torch.no_grad():
        torch.cuda.synchronize();start=time.perf_counter();im=render(model,v['camera']);aa=alpha(model,v['camera']);torch.cuda.synchronize();seconds=time.perf_counter()-start
        selected=selected_contribution(model,v['camera'],ids)
    rgb=im.cpu().numpy().transpose(1,2,0);gt=v['gt'].cpu().numpy().transpose(1,2,0);base=v['b0'].cpu().numpy().transpose(1,2,0);a=aa.cpu().numpy();target=v['aa'].cpu().numpy();e=v['evidence'];band=e['internal_band'];nonband=e['nonband'];fg=target;reliable=e['reliable'];outline=e['outline_band']
    holes=(a<.95)&reliable
    def fraction(mask):return float((holes*mask).sum()/max((reliable*mask).sum(),1))
    profiles=profile_metrics(rgb,e['profiles']);reference=profile_metrics(gt,e['profiles'])
    paired=[abs(p['width']-q['width']) for p,q in zip(profiles,reference) if p['valid'] and q['valid']]
    mse=float(np.mean((rgb-gt)**2));metric={'key':v['key'],'camera_hash':v['entry']['camera_hash'],'whole_mse':mse,'whole_psnr':float(-10*np.log10(max(mse,1e-20))),'band_mse':region_mse(rgb,gt,band),'nonband_gt_mse':region_mse(rgb,gt,nonband),'outside_damage':region_mse(rgb,base,nonband),'foreground_mse':region_mse(rgb,gt,fg),'outline_rgb_mse':region_mse(rgb,gt,outline),'outline_alpha_mse':float(((a-target)**2*outline).sum()/max(outline.sum(),1)),'foreground_holes':fraction(np.ones_like(a)),'band_holes':fraction(band),'nonband_holes':fraction(nonband),'native_render_rgb_alpha_seconds':seconds,'width_mean_abs_error':float(np.mean(paired)) if paired else None,'profile_count':len(profiles),'valid_profile_count':sum(p['valid'] for p in profiles),'valid_profile_rate':sum(p['valid'] for p in profiles)/max(len(profiles),1),'profile_rejections':dict(Counter(p['reason'] for p in profiles if not p['valid'])),'profiles':profiles,'reference_profiles':reference,'display_clipped_fraction':float(np.mean((rgb<0)|(rgb>1))),'reference_annotation':'original Blender TRAIN RGBA AA coverage; no part/Gaussian identity'}
    save_png(output/'rgb.png',rgb);save_png(output/'alpha.png',np.repeat(a[:,:,None],3,axis=2))
    sel=selected.cpu().numpy();np.savez_compressed(output/'native.npz',rgb=rgb,alpha=a,selected_full_model_T=sel)
    metric['native_npz_sha256']=sha(output/'native.npz')
    return metric
def evaluate(scene,arm,model,views,ids,role):
    guard(f'{scene}/{arm}/evaluate/{role}');records=[]
    for v in views:
        output=OUT/scene/'evaluation'/role/arm/v['key'];output.mkdir(parents=True,exist_ok=True)
        records.append(evaluate_view(model,v,ids,output))
    keys=['whole_mse','whole_psnr','band_mse','nonband_gt_mse','outside_damage','foreground_mse','outline_rgb_mse','outline_alpha_mse','foreground_holes','band_holes','nonband_holes','width_mean_abs_error','valid_profile_rate','native_render_rgb_alpha_seconds']
    summary={k:float(np.mean([r[k] for r in records if r[k] is not None])) if any(r[k] is not None for r in records) else None for k in keys}
    record={'scene':scene,'arm':arm,'role':role,'views':records,'mean_per_view':summary,'metric_encoding':'display native PNG loss; width linear via sRGB EOTF','scope':'exploratory GS-TRAIN seen; no formal independent TEST'}
    result(f'{scene}_{arm}_{role}',record);return record
def common_profiles(scene,role,methods):
    b=methods['B0'];out=[]
    for i,v in enumerate(b['views']):
        ref={p['id']:p for p in v['reference_profiles']};common=set(k for k,p in ref.items() if p['valid'])
        for method in methods.values():common&={p['id'] for p in method['views'][i]['profiles'] if p['valid']}
        values={name:float(np.mean([abs(p['width']-ref[p['id']]['width']) for p in met['views'][i]['profiles'] if p['id'] in common])) if common else None for name,met in methods.items()}
        out.append({'key':v['key'],'common_ids':sorted(common),'count':len(common),'common_mean_absolute_width_error':values})
    record={'scene':scene,'role':role,'all_methods_common_profiles':out,'macro_means':{name:float(np.mean([v['common_mean_absolute_width_error'][name] for v in out if v['common_mean_absolute_width_error'][name] is not None])) if any(v['common_mean_absolute_width_error'][name] is not None for v in out) else None for name in methods},'missing_widths_are_null':True}
    result(f'{scene}_common_profiles_{role}',record);return record
