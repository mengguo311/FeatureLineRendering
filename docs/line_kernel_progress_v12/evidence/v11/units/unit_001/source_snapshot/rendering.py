"""Use the pinned Gaussian CPU EWA renderer, never draw a carrier."""
import limits
import importlib.util
import ast
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from io_tools import sha, same_bytes, write_json

def load_renderer(renderer_path, helper_files):
    for path, expected in helper_files.items():
        if sha(path) != expected: raise ValueError('helper hash mismatch: '+path)
    directory = str(Path(renderer_path).parent)
    if 'common' in sys.modules and Path(sys.modules['common'].__file__).resolve() != Path(directory)/'common.py':
        raise RuntimeError('unexpected legacy common module')
    sys.path.insert(0, directory)
    try:
        spec = importlib.util.spec_from_file_location('v11_pinned_gaussian_renderer', renderer_path)
        module = importlib.util.module_from_spec(spec)
        # Interface relocation only: byte-identical SH source is now in the
        # frozen new-source manifest rather than outside the parent's helper roots.
        pinned_sh = Path(__file__).with_name('sh_utils_pinned.py')
        if sha(pinned_sh) != '7d1ff267546390635e6d1f68c4f88c4a8b052482d5c9be1d32f06bc69e9a96e7':
            raise ValueError('vendored SH source mismatch')
        tree = ast.parse(Path(renderer_path).read_text(), filename=str(renderer_path))
        assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'SH_PATH' for t in n.targets)]
        if len(assignments) != 1: raise ValueError('unexpected renderer SH import schema')
        assignments[0].value = ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),
                                       args=[ast.Constant(value=str(pinned_sh))],keywords=[])
        ast.fix_missing_locations(tree)
        exec(compile(tree,str(renderer_path),'exec'),module.__dict__)
    finally:
        sys.path.remove(directory)
    return module

def subset(asset, rows):
    return {k: v[rows] for k,v in asset.items()}

def save_rgb(path, rgb):
    if not np.isfinite(rgb).all(): raise ValueError('nonfinite rendered RGB')
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.rint(np.clip(rgb,0,1)*255).astype(np.uint8)).save(path)

def crop_box(renderer, assets, rows, camera, pad=16):
    bounds=[]; invalid={}
    for name, asset in assets.items():
        uv,z,S=renderer.project_cov(asset['means'][rows], asset['covariance'][rows], camera, floor=.12**2)
        valid=(z>.2)&np.isfinite(uv).all(1)&np.isfinite(S).all((1,2))
        invalid[name]=int(np.count_nonzero(~valid))
        if np.any(valid):
            radius=3*np.sqrt(np.maximum(0,np.diagonal(S[valid],axis1=1,axis2=2)))
            bounds.append((uv[valid]-radius,uv[valid]+radius))
    if not bounds:
        return None, dict(reason='ALL_TARGET_PROJECTIONS_INVALID', invalid_counts=invalid)
    low=np.floor(np.vstack([x[0] for x in bounds]).min(0)-pad).astype(int)
    high=np.ceil(np.vstack([x[1] for x in bounds]).max(0)+pad).astype(int)
    raw=[int(low[0]),int(low[1]),int(high[0])+1,int(high[1])+1]
    w,h=camera['width'],camera['height']
    clipped=[max(0,min(w,raw[0])),max(0,min(h,raw[1])),max(0,min(w,raw[2])),max(0,min(h,raw[3]))]
    if clipped[2]<=clipped[0] or clipped[3]<=clipped[1]:
        return None, dict(reason='TARGET_BOX_OUTSIDE_FRAME', raw_box=raw, invalid_counts=invalid)
    return tuple(clipped), dict(raw_box=raw, clipped_box=clipped, clipped=raw!=clipped,
                               invalid_counts=invalid, pad_pixels=pad, coverage='all three target projected 3sigma boxes')

def labelled_panel(path, items, title, columns=3):
    # Images only come from actual Gaussian renders. Labels occupy separate margins.
    w=max(i.width for _,i in items);h=max(i.height for _,i in items)
    out=Image.new('RGB',(columns*w,48+((len(items)+columns-1)//columns)*(h+28)),'white')
    d=ImageDraw.Draw(out);d.text((6,8),title,fill='black')
    for n,(label,im) in enumerate(items):
        x=(n%columns)*w;y=48+(n//columns)*(h+28)
        d.text((x+4,y+4),label,fill='black');out.paste(im,(x,y+28))
    out.save(path)

def deliver_images(unit, renderer, assets, memory_assets, rows, cameras, paths, guard):
    unit=Path(unit);out=unit/'images';out.mkdir(exist_ok=True)
    receipts=[];panels=[];full_panels=[];boxes={};cold_checks=[]
    for camera in cameras:
        view=camera['view'];box,box_info=crop_box(renderer,assets,rows,camera)
        boxes[view]=box_info
        for stage,asset in assets.items():
            guard('render_'+stage+'_'+view+'_ISOLATED')
            isolated=renderer.render(subset(asset,rows),camera,background=(1,1,1),floor=.12**2)
            guard('render_cold_compare_'+stage+'_'+view)
            memory=renderer.render(subset(memory_assets[stage],rows),camera,background=(1,1,1),floor=.12**2)
            checks={k:same_bytes(isolated[k],memory[k]) for k in isolated}
            if not all(checks.values()): raise ValueError('cold-reload render mismatch')
            cold_checks.append(dict(stage=stage,view=view,fields_bitwise=checks))
            guard('render_'+stage+'_'+view+'_FULL')
            full=renderer.render(asset,camera,background=(1,1,1),floor=.12**2)
            for kind,result in [('ISOLATED',isolated),('FULL',full)]:
                base=out/(stage+'_'+view+'_'+kind+'.png');save_rgb(base,result['rgb'])
                info=dict(path=str(base.relative_to(unit)),stage=stage,view=view,kind=kind,
                          gaussian_asset=str(paths[stage]),asset_sha256=sha(paths[stage]),
                          alpha_sum=float(result['alpha'].sum()),alpha_max=float(result['alpha'].max()),
                          nonwhite_pixels=int(np.count_nonzero(np.any(result['rgb']<254/255,axis=2))),
                          alpha_over_1_255_pixels=int(np.count_nonzero(result['alpha']>1/255)),
                          renderer='pinned CPU EWA replica, not CUDA',camera_shape=[camera['width'],camera['height']],
                          same_3d_asset_across_views=True)
                if box is not None:
                    with Image.open(base) as image:
                        crop=image.crop(box)
                        crop_path=out/(base.stem+'_CROP.png');crop.save(crop_path)
                        large=crop.resize((crop.width*4,crop.height*4),Image.Resampling.NEAREST)
                        large_path=out/(base.stem+'_CROP_4X.png')
                        labelled_panel(large_path,[(stage+' '+view+' '+kind,large)],'4x nearest-neighbor display only; same crop',columns=1)
                        info.update(crop=str(crop_path.relative_to(unit)),crop_4x=str(large_path.relative_to(unit)))
                        (panels if kind=='ISOLATED' else full_panels).append((view+' '+stage+' 4x',large.copy()))
                receipts.append(info)
            write_json(unit/'RENDER_RECEIPTS.json',dict(images=receipts,crops=boxes,cold_render_checks=cold_checks,partial=True))
    if panels: labelled_panel(unit/'BEFORE_AFTER_TWO_VIEWS.png',panels,'Gaussian target: ORIGINAL | POSITION_ONLY | DERIVED; 4x display')
    if full_panels: labelled_panel(unit/'FULL_CONTEXT_TWO_VIEWS.png',full_panels,'Full-object Gaussian context, identical crop; 4x display')
    record=dict(images=receipts,crops=boxes,cold_render_checks=cold_checks,partial=False,
                saved_native_count=len(receipts),no_auxiliary_line_ink=True,no_source_surface_occlusion=True,
                original_colors_and_opacity=True,display_floor=.12**2)
    write_json(unit/'RENDER_RECEIPTS.json',record)
    return record
