"""Post-evaluation readback and native-scale figures; never alter scientific outputs."""
import runtime
from runtime import js,sha
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from run_h2 import UNIT,CODE,VIEWS,ARMS
from linked_asset import npz,load_asset

def panel(path,rows):
    w=384;h=412;canvas=Image.new('RGB',(len(rows[0])*w,len(rows)*h),'white');draw=ImageDraw.Draw(canvas)
    for y,row in enumerate(rows):
        for x,(title,source) in enumerate(row):
            image=Image.open(source).convert('RGB');assert image.size==(384,384)
            canvas.paste(image,(x*w,y*h+28));draw.text((x*w+5,y*h+5),title,fill='black')
    canvas.save(runtime.output_guard(path))

def main():
    media=UNIT/'media';media.mkdir(exist_ok=True)
    for mode in ('natural','matched'):
        rows=[]
        for view in VIEWS:
            tag=view.removeprefix('orbit_').removesuffix('_5.1')
            row=[(tag+' | Original GS',UNIT/f'renders/{view}/reference/source.png')]
            row.extend((tag+' | '+name+' | '+mode,UNIT/f'renders/{view}/{mode}/{name}/hybrid.png') for name in ARMS)
            rows.append(row)
        panel(media/(mode.upper()+'_COMPARISON.png'),rows)
    rows=[]
    for view in VIEWS:
        tag=view.removeprefix('orbit_').removesuffix('_5.1')
        row=[(tag+' | Fixed structure',UNIT/f'renders/{view}/reference/structure.png')]
        row.extend((tag+' | '+name+' own hatch',UNIT/f'renders/{view}/natural/{name}/target_ink.png') for name in ARMS)
        rows.append(row)
    panel(media/'WHOLE_LAYERS.png',rows)
    rows=[]
    for view in VIEWS:
        row=[(view+' | '+name+' conventional proxy',UNIT/f'renders/{view}/natural/{name}/proxy.png') for name in ARMS]
        rows.append(row)
    panel(media/'PROXY_REFERENCE.png',rows)
    # Exact array/PNG readback and fixed-array invariants.
    checks=[];compact=[]
    for view in VIEWS:
        m=json.loads((UNIT/f'renders/{view}/METRICS.json').read_text());reference=npz(UNIT/f'inputs/cache/{view}/FRAME.npz')
        first=None
        for mode in ('natural','matched'):
            for arm in ARMS:
                folder=UNIT/f'renders/{view}/{mode}/{arm}';f=npz(folder/'FRAME.npz')
                if first is None:first=f
                for key in ('source','paper','support','structure','guide','contour','seat','regions','depth'):
                    np.testing.assert_array_equal(f[key],first[key])
                for key in ('source','paper','support'):np.testing.assert_array_equal(f[key],reference[key])
                for file,array in [('hybrid.png',f['hybrid']),('target_ink.png',1-f['target_ink']),('structure.png',1-f['structure']),('proxy.png',1-f['combined_ink'])]:
                    a=np.asarray(array)
                    if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
                    np.testing.assert_array_equal(np.array(Image.open(folder/file)),np.uint8(np.clip(a,0,1)*255+.5))
                q=m['metrics'][mode][arm];regions=q['regions']
                compact.append(dict(view=view,mode=mode,arm=arm,rgb_effect=q['target_rgb_effect'],own_ink=q['own_target_ink_mass'],whole_ink=q['whole_ink_mass'],
                    boundary_hatch=regions['boundary_band']['own_ink_mass'],interior_coverage=regions['necessary_interior']['own_coverage_fraction'],
                    interior_ink=regions['necessary_interior']['own_ink_mass'],target_coverage=regions['target']['own_coverage_fraction'],
                    far_other_absolute=regions['far_other']['absolute_source_L1'],far_background_absolute=regions['far_background']['absolute_source_L1'],
                    far_other_policy_delta=regions['far_other']['policy_vs_original_U_L1'],far_background_policy_delta=regions['far_background']['policy_vs_original_U_L1'],
                    visible_length_natural_strength=q['visible_length']))
        checks.append(dict(view=view,all_fixed_arrays_equal=True,all160_policy_PNGs_check='four PNGs x two modes x four policies per view'))
    for filename,root in [('INPUT_LOCK.json',UNIT),('SOURCE_LOCK.json',CODE),('DERIVED_LOCK.json',UNIT)]:
        for name,h in json.loads((UNIT/filename).read_text()).items():assert sha(root/name)==h,(filename,name)
    assert sha(UNIT/'DECISION.json')==json.loads((UNIT/'PROTOCOL.json').read_text())['decision_sha256']
    cold=json.loads((UNIT/'cold_original/RENDER_RECEIPT.json').read_text())
    assert all(cold['reload_comparison'].values())
    js(UNIT/'READBACK.json',dict(views=checks,policy_images_checked=160,input_source_derived_locks_unchanged=True,decision_unchanged=True,
        cold_original=cold,metrics_note='visible_length samples are at natural strength in both mode records; matched actual pixel coverage/ink/RGB are independently measured at the matched factor',
        image_scope='Full384x384 policy images; panel places them at native scale, no crop/contrast enhancement'))
    js(UNIT/'SUMMARY_METRICS.json',compact)
    print(json.dumps(compact,default=runtime.json_default))
if __name__=='__main__':main()
