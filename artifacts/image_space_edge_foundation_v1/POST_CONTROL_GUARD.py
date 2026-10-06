"""Explicit post-production RGB guard revision. Frozen spatial outputs untouched.

Original full-SH RGB can exceed 1 before display clipping. A valid local color
fit does not by itself prevent NEW display clipping. Reject such corrections;
also reset low-evidence plateaus and exterior pixels. No parameters are tuned
against image quality scores. This is a post hoc engineering fix, not a fresh
heldout scientific result.
"""
import hashlib,json,os,sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/image_space_edge_foundation_v1/src'))
from runtime import ART,OUT,sha,atomic_json,unit,digest
from campaign import npz,allfiles
from presentation import save_image,panel_sheet

def guarded(original,candidate,band,raw,alpha):
    out=candidate.copy()
    baseline_clipped=np.any((original<0)|(original>1),axis=2)
    new_clip=np.any(((out<0)|(out>1))&~((original<0)|(original>1)),axis=2)
    rejection=new_clip|baseline_clipped|(raw<.02)|(alpha<.995)|~band
    out[rejection]=original[rejection]
    return out,rejection

def scene_guard(scene):
    panels=[];records=[];directory=OUT/'guarded_RGB'/scene;media=ART/'media'/scene/'guarded_RGB'
    for key in ['r_000','r_008','r_018','r_030']:
        source=OUT/'fixed_fields'/scene/key;z=np.load(source/'rgb_controls.npz');f=np.load(source/'fields.npz');original=z['original'];alpha=z['alpha']
        outputs={'original':original,'alpha':alpha};row={'key':key,'arms':{}}
        for arm in ['sharpen','soften']:
            out,rejected=guarded(original,z[arm],z[arm+'_band'],f['raw'],alpha)
            outputs[arm]=out;outputs[arm+'_band']=z[arm+'_band'];outputs[arm+'_rejected']=rejected
            new=((out<0)|(out>1))&~((original<0)|(original>1))
            raw_new=((z[arm]<0)|(z[arm]>1))&~((original<0)|(original>1));diff=abs(out-original)
            assert not new.any() and np.array_equal(out[~z[arm+'_band']],original[~z[arm+'_band']])
            assert diff.max()<=.080001 and diff[f['raw']<.02].max(initial=0)==0
            row['arms'][arm]=dict(candidate_new_clipped_values=int(raw_new.sum()),guarded_new_clipped_values=int(new.sum()),
                candidate_reverted_pixels=int(np.any(abs(out-z[arm])>0,axis=2).sum()),changed_pixels=int(np.any(diff>0,axis=2).sum()),
                max_delta=float(diff.max()),outside_max=float(diff[~z[arm+'_band']].max(initial=0)),nonedge_max=float(diff[f['raw']<.02].max(initial=0)),
                alpha_unchanged=True,source_control_sha256=sha(source/'rgb_controls.npz'))
            save_image(media/key/(arm+'.png'),out)
        npz(directory/(key+'.npz'),**outputs)
        save_image(media/key/'original.png',original)
        panels.extend([(key+' original native RGB',original),(key+' guarded width x.65',outputs['sharpen']),
                       (key+' guarded width x1.50',outputs['soften']),(key+' 8x bounded delta',np.clip(.5+8*(outputs['sharpen']-original),0,1))])
        records.append(row)
    panel_sheet(panels,media/'fourview_guarded_RGB_control.jpg',columns=4,size=800,title='Post hoc strict guard / screen-space stylization only / original candidates preserved')
    return dict(scene=scene,records=records,status='GUARDS_PASS_STYLIZATION_ONLY',parameter_tuning=False,post_hoc_engineering_fix=True,files=allfiles(directory,media))

def run():
    freeze=dict(source_sha256=sha(__file__),original_production_freeze_sha256=sha(ART/'PRODUCTION_FREEZE.json'),
                rule='reject newly clipped corrections, pre-existing clipped pixels, raw response <.02, nonforeground, and outside exact fit band',
                role='post hoc deterministic engineering guard revision; no re-fitting/re-selection of spatial foundation',
                candidate_scientific_status='NO-GO if any new clipped value; preserved in original outputs')
    p=ART/'POST_CONTROL_FREEZE.json'
    if p.exists():assert json.loads(p.read_text())==freeze
    else:atomic_json(p,freeze)
    for scene in ['lego','chair']:unit(scene+'_guarded_RGB',sha(p),lambda scene=scene:scene_guard(scene))
if __name__=='__main__':run()
