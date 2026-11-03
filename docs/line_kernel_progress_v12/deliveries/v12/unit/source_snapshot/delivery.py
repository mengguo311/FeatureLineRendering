"""Full assets first, all four fixed quadrants; saved Gaussian images only."""
import limits
from pathlib import Path
import numpy as np
from PIL import Image
from rendering import save_rgb, labelled_panel, crop_box, subset
from io_tools import write_json, sha, same_bytes

def quadrants(width,height):
    x=[0,width//2,width];y=[0,height//2,height]
    return [(x[i],y[j],x[i+1],y[j+1]) for j in range(2) for i in range(2)]

def deliver(unit, renderer, cold, memory, cameras, paths, ledger, guard):
    unit=Path(unit);out=unit/'images';out.mkdir(exist_ok=True)
    receipts=[];checks=[];full_items=[];full_images={};quad_records=[]
    for cam in cameras:
        view=cam['view']
        for stage in ['ORIGINAL','FULL_POSITION_ONLY']:
            guard('full_render_'+stage+'_'+view)
            a=renderer.render(cold[stage],cam,background=(1,1,1),floor=.12**2)
            guard('cold_render_check_'+stage+'_'+view)
            b=renderer.render(memory[stage],cam,background=(1,1,1),floor=.12**2)
            comparison={k:same_bytes(a[k],b[k]) for k in a}
            if not all(comparison.values()):raise ValueError('full cold/memory render mismatch')
            checks.append(dict(stage=stage,view=view,fields_bitwise=comparison))
            path=out/f'{stage}_{view}_FULL.png';save_rgb(path,a['rgb'])
            im=Image.open(path).convert('RGB');full_images[(stage,view)]=im
            full_items.append((view+' '+stage,im))
            receipts.append(dict(path=str(path.relative_to(unit)),stage=stage,view=view,
                rows=len(cold[stage]['means']),asset_sha256=sha(paths[stage]),
                alpha_sum=float(a['alpha'].sum()),alpha_max=float(a['alpha'].max()),
                nonwhite_pixels=int(np.count_nonzero(np.any(a['rgb']<254/255,axis=2))),
                alpha_over_1_255_pixels=int(np.count_nonzero(a['alpha']>1/255)),
                shape=[cam['width'],cam['height']],all_unknown_and_competitors_included=True))
            write_json(unit/'RENDER_RECEIPTS.json',dict(images=receipts,cold_checks=checks,partial=True))
        # Full-frame comparison has priority over all supplemental ROIs.
        labelled_panel(unit/'FULL_MODEL_BEFORE_AFTER_TWO_VIEWS.png',full_items,
                       'FULL MODEL: ORIGINAL | FULL_POSITION_ONLY; native frames; UNKNOWN retained',columns=2)
        items=[]
        for k,box in enumerate(quadrants(cam['width'],cam['height'])):
            for stage in ['ORIGINAL','FULL_POSITION_ONLY']:
                crop=full_images[(stage,view)].crop(box)
                path=out/f'{stage}_{view}_Q{k+1}.png';crop.save(path)
                enlarged=crop.resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST)
                path2=out/f'{stage}_{view}_Q{k+1}_2X.png'
                labelled_panel(path2,[(stage+' '+view+' Q'+str(k+1),enlarged)],'2x nearest-neighbor display only',columns=1)
                items.append((f'Q{k+1} {stage}',enlarged))
                quad_records.append(dict(view=view,stage=stage,quadrant=k+1,box=box,
                    crop=str(path.relative_to(unit)),display=str(path2.relative_to(unit))))
        labelled_panel(unit/f'FIXED_FOUR_QUADRANTS_{view}_2X.png',items,'All four fixed quadrants, 2x display, ORIGINAL | FULL_POSITION_ONLY',columns=2)
    worst=sorted([r for r in ledger if r['status']=='SUCCESS'],key=lambda r:(-r['maximum_displacement_p'],r['group_id']))[:3]
    cases=[]
    for r in worst:
        rows=np.asarray(r['rows'],dtype=np.int64);gid=r['group_id']
        for cam in cameras:
            guard('worst_'+str(gid)+'_'+cam['view'])
            box,info=crop_box(renderer,cold,rows,cam,pad=16);items=[];contexts=[]
            for stage in ['ORIGINAL','FULL_POSITION_ONLY']:
                isolated=renderer.render(subset(cold[stage],rows),cam,background=(1,1,1),floor=.12**2)
                path=out/f'WORST_{gid}_{stage}_{cam["view"]}_ISOLATED.png';save_rgb(path,isolated['rgb'])
                if box is not None:
                    crop=Image.open(path).convert('RGB').crop(box)
                    items.append((stage,crop.resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST)))
                    ctx=full_images[(stage,cam['view'])].crop(box)
                    contexts.append((stage,ctx.resize((ctx.width*2,ctx.height*2),Image.Resampling.NEAREST)))
            if items:
                labelled_panel(unit/f'WORST_{gid}_{cam["view"]}_ISOLATED_2X.png',items,'Worst maximum displacement group, fixed box; 2x display',columns=2)
                labelled_panel(unit/f'WORST_{gid}_{cam["view"]}_CONTEXT_2X.png',contexts,'Complete-object context, fixed box; 2x display',columns=2)
            cases.append(dict(group_id=gid,view=cam['view'],maximum_displacement_p=r['maximum_displacement_p'],crop=info))
    record=dict(images=receipts,cold_checks=checks,quadrants=quad_records,worst_cases=cases,
        native_full_images=4,partial=False,backend='pinned CPU Gaussian EWA replica, not CUDA',
        floor=.12**2,unknown_retained=True,no_source_surface_occlusion=True,no_auxiliary_curve_ink=True)
    write_json(unit/'RENDER_RECEIPTS.json',record);return record
