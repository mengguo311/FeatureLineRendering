"""Guard revision 2: monotone fitted transition anchored at finite-band endpoints.

The first inverse-composition window created a small synthetic reverse slope.
This revision retains the frozen two-side profiles and eliminates the normal
taper: the NEW monotone logistic is normalized to the OLD fit's band endpoints.
Tangential confidence blending remains conservative. Clipping/exterior/nonedge
guards are unchanged. This is post hoc engineering validation, not a blind win.
"""
import copy,json,sys
from pathlib import Path
import cv2,numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/image_space_edge_foundation_v1/src'))
from runtime import ART,OUT,sha,atomic_json,unit,guard
from campaign import npz,allfiles
from boundary import analyze,DEFAULT
from fixtures import fixtures
from presentation import save_image,panel_sheet
from POST_CONTROL_GUARD import guarded

def sigmoid(s):return 1/(1+np.exp(np.clip(-s,-60,60)))
def anchored(original,profiles,factor):
    p=profiles;h,w=original.shape[:2];acc=np.zeros_like(original);weight=np.zeros((h,w),np.float32)
    ids=np.flatnonzero(p['valid']&(p['quality']>.35)&(p['width']>=1.5)&(p['residual']<.035)&(p['plateau_variance']<.0005))
    for j in ids:
        center=p['xy'][j]+p['normal'][j]*p['center'][j];n=p['normal'][j];width=p['width'][j]
        radius=min(8.,max(2.,width*1.25))
        x0=max(0,int(center[0]-radius-2));x1=min(w,int(center[0]+radius+3));y0=max(0,int(center[1]-radius-2));y1=min(h,int(center[1]+radius+3))
        yy,xx=np.mgrid[y0:y1,x0:x1];dx=xx-center[0];dy=yy-center[1];s=dx*n[0]+dy*n[1];t=-dx*n[1]+dy*n[0]
        window=(abs(s)<radius)&(abs(t)<1.1)
        a=sigmoid(s*4.394449/width);b=sigmoid(s*4.394449/(width*factor))
        al,ar=sigmoid(-radius*4.394449/width),sigmoid(radius*4.394449/width)
        bl,br=sigmoid(-radius*4.394449/(width*factor)),sigmoid(radius*4.394449/(width*factor))
        new=al+(ar-al)*(b-bl)/(br-bl)
        correction=(new-a)[...,None]*p['signed_contrast'][j]
        old=original[y0:y1,x0:x1];lo=np.minimum(p['minus'][j],p['plus'][j]);hi=np.maximum(p['minus'][j],p['plus'][j])
        correction=np.clip(old+correction,lo,hi)-old
        ww=np.maximum(0,1-abs(t)/1.1)*window*p['quality'][j]
        acc[y0:y1,x0:x1]+=correction*ww[...,None];weight[y0:y1,x0:x1]+=ww
    delta=np.clip(acc/np.maximum(weight[...,None],1.),-.08,.08);out=original+delta;band=weight>0
    out[~band]=original[~band]
    return out.astype(np.float32),band,len(ids)

def fixture_checks():
    records=[];directory=OUT/'anchored_synthetic';media=ART/'synthetic/anchored_control'
    for name in ['width','color_step']:
        im,truth=fixtures()[name];r=analyze(im,DEFAULT);outputs={'original':im};p=r['profiles']
        record=dict(name=name,known_width=truth['width'],arms={})
        d=im[64,-1]-im[64,0]
        def fraction(a):return (a[64]-im[64,0])@d/(d@d)
        def width(a):return float(np.interp(.9,fraction(a),np.arange(128))-np.interp(.1,fraction(a),np.arange(128)))
        record['original_width']=width(im)
        for arm,factor in [('sharpen',.65),('soften',1.5)]:
            out,band,used=anchored(im,p,factor);out,rejected=guarded(im,out,band,r['raw'],np.ones(im.shape[:2],np.float32))
            f=fraction(out);diff=abs(out-im)
            assert np.diff(f).min()>=-1e-6 and f.min()>=-1e-6 and f.max()<=1.000001
            assert np.array_equal(out[~band],im[~band]) and diff.max()<=.080001
            record['arms'][arm]=dict(width=width(out),min_fraction_slope=float(np.diff(f).min()),outside_max=float(diff[~band].max(initial=0)),max_delta=float(diff.max()),profiles_used=used)
            outputs[arm]=out;outputs[arm+'_band']=band
        assert record['arms']['sharpen']['width']<record['original_width']<record['arms']['soften']['width']
        npz(directory/(name+'.npz'),**outputs);records.append(record)
        panel_sheet([('known original',im),('anchored width x.65',outputs['sharpen']),('anchored width x1.5',outputs['soften'])],media/(name+'.png'),size=256)
    return dict(status='PASS',records=records,files=allfiles(directory,media))

def scene_control(scene,role='fixed'):
    records=[];panels=[];directory=OUT/'guarded_RGB_v2'/scene/role;media=ART/'media'/scene/'guarded_RGB_v2'/role
    freeze=json.loads((ART/'PRODUCTION_FREEZE.json').read_text())
    for v in freeze['scenes'][scene]['groups'][role]:
        key=v['key'];guard(scene+'/anchored_control/'+role+'/'+key)
        if role=='fixed':base=OUT/'fixed_fields'/scene/key
        else:base=OUT/'dev_fields'/scene/key
        p=dict(np.load(base/'profiles.npz'));f=np.load(base/'fields.npz');z=np.load(OUT/'raw'/scene/role/key/'native.npz');im=z['rgb'];alpha=z['alpha']
        interior=cv2.erode((alpha>.995).astype(np.uint8),np.ones((23,23),np.uint8)).astype(bool);xy=p['xy'].astype(int)
        p['valid']=p['valid']&interior[xy[:,1],xy[:,0]];outputs={'original':im,'alpha':alpha};record=dict(key=key,arms={})
        for arm,factor in [('sharpen',.65),('soften',1.5)]:
            candidate,band,used=anchored(im,p,factor);out,rejected=guarded(im,candidate,band,f['raw'],alpha)
            outputs[arm]=out;outputs[arm+'_band']=band;diff=abs(out-im)
            new=((out<0)|(out>1))&~((im<0)|(im>1));assert not new.any()
            assert diff.max()<=.080001 and np.array_equal(out[~band],im[~band]) and diff[f['raw']<.02].max(initial=0)==0
            record['arms'][arm]=dict(profiles_used=used,max_delta=float(diff.max()),outside_max=float(diff[~band].max(initial=0)),nonedge_max=float(diff[f['raw']<.02].max(initial=0)),
                  changed_pixels=int(np.any(diff>0,2).sum()),new_clipped_values=0,alpha_unchanged=True)
            save_image(media/key/(arm+'.png'),out)
        npz(directory/(key+'.npz'),**outputs)
        panels.extend([(key+' native',im),(key+' anchored x.65',outputs['sharpen']),(key+' anchored x1.50',outputs['soften']),(key+' 8x bounded delta',np.clip(.5+8*(outputs['sharpen']-im),0,1))])
        records.append(record)
    panel_sheet(panels,media/'fourview_RGB_control.jpg',columns=4,size=800,title='Anchored monotone profiles + strict guards / post hoc engineering revision / stylization only')
    return dict(scene=scene,role=role,records=records,files=allfiles(directory,media),scientific_scope='post hoc engineering fix, no blind repair superiority')

def run():
    source=sha(__file__);deps=sha(ART/'POST_CONTROL_GUARD.py');prod=sha(ART/'PRODUCTION_FREEZE.json')
    devfreeze=source+deps+prod
    unit('anchored_control_synthetic',devfreeze,fixture_checks)
    for scene in ['lego','chair']:unit(scene+'_anchored_control_dev',devfreeze,lambda scene=scene:scene_control(scene,'dev'))
    p=ART/'ANCHORED_CONTROL_FREEZE.json';freeze=dict(source_sha256=source,guard_dependency_sha256=deps,original_production_freeze_sha256=prod,
        rule='finite-band new monotone logistic normalized to old fitted endpoint values; tangential confidence averaging; original residual retained; fixed no-clip/nonedge/alpha guards',
        DEV_and_known_truth_validation_before_corrected_fixed_application=True,heldout_status='already seen during original run; this engineering fix is post hoc',
        original_fields_and_videos_unchanged=True)
    if p.exists():assert json.loads(p.read_text())==freeze
    else:atomic_json(p,freeze)
    for scene in ['lego','chair']:unit(scene+'_anchored_control_fixed',sha(p),lambda scene=scene:scene_control(scene,'fixed'))
if __name__=='__main__':run()
