"""Freeze a single-view GAER contour into real world-coordinate 3D tubes.
Depth is a contribution-weighted Gaussian-center proxy, NOT recovered surface depth.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import torch,cv2,trimesh
from scipy.ndimage import median_filter,distance_transform_edt
from PIL import Image,ImageDraw
from core import ray_points,supported_depth,tube_mesh,glb_bytes

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/gaer_fixed_contour_asset_v01'
P=json.loads((OUT/'PROTOCOL.json').read_text())
UP=Path('/home/u00134/3dgs_line/gaer_object_contours_v01')
BUFFER=Path('/home/u00134/3dgs_line/gaer_attribution_buffer_v01')
sys.path.insert(0,str(BUFFER/'experiments/gaer_attribution_buffer_v01'))
sys.path.insert(0,str(BUFFER/'out/gaer_attribution_buffer_v01/native/patched'))
import importlib.util
binary_path=BUFFER/'out/gaer_attribution_buffer_v01/torch_extensions/gaer_native_C/gaer_native_C.so'
spec=importlib.util.spec_from_file_location('gaer_native_C',str(binary_path))
binary=importlib.util.module_from_spec(spec);spec.loader.exec_module(binary)
sys.modules['gaer_fixed_native._C']=binary
init=BUFFER/'out/gaer_attribution_buffer_v01/native/patched/diff_gaussian_rasterization/__init__.py'
spec=importlib.util.spec_from_file_location('gaer_fixed_native',str(init),submodule_search_locations=[str(init.parent)])
native=importlib.util.module_from_spec(spec);sys.modules['gaer_fixed_native']=native;spec.loader.exec_module(native)
import types,math
shim=types.ModuleType("runtime");shim.ART=OUT;shim.DATA_FREEZE=OUT/"unused_data_freeze.json"
shim.sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
shim.digest=lambda obj:hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()
shim.atomic_json=lambda p,obj:Path(p).write_text(json.dumps(obj))
sys.modules["runtime"]=shim
from src.scene_io import load_model,make_settings
FREEZE=json.loads((UP/"artifacts/gaer_object_contours_v01/INPUT_FREEZE.json").read_text())
ALL=FREEZE["scenes"]
def camera_for(cfg,key):
    record=next(c for c in cfg["cameras"] if c["key"]==key)
    fx=record["width"]/(2*math.tan(record["FoVx"]/2));fy=record["height"]/(2*math.tan(record["FoVy"]/2))
    return types.SimpleNamespace(record=record,width=record["width"],height=record["height"],fx=fx,fy=fy,cx=(record["width"]-1)/2,cy=(record["height"]-1)/2,matrix=lambda:torch.tensor(record["w2c"],dtype=torch.float64))
assert P['construction_view']=='r_33' and P['source_commit']=='e174e9fcda71f3b328e5e44b668d11f1dda7da3d'
results=[]
for name in P['scenes']:
    dst=OUT/name;dst.mkdir(parents=True,exist_ok=True)
    cfg=ALL[name];scene=load_model(cfg)
    cam=camera_for(cfg,'r_33')
    settings=make_settings(native,cam.record)
    with torch.no_grad():
        native_result=native.GaussianRasterizer(settings)(**scene,attribution=True,K=32)
        rgb,radii,ids_t,w_t=native_result[:4];alpha_t=native_result.accumulated_alpha
    ids=ids_t.cpu().numpy().astype(np.int64);weights=w_t.cpu().numpy().astype(np.float64)
    if ids.shape==(32,cam.height,cam.width):ids=np.moveaxis(ids,0,-1);weights=np.moveaxis(weights,0,-1)
    assert ids.shape==(cam.height,cam.width,32),ids.shape
    alpha=alpha_t.cpu().numpy().squeeze();assert alpha.shape==(cam.height,cam.width)
    rgb0=rgb.cpu().numpy().transpose(1,2,0)
    strength=np.load(UP/f'artifacts/gaer_object_contours_v01/downloads/{name}/r_33/C_style.npz')['strength'].astype(np.float64)
    means=scene["means3D"].cpu().numpy().astype(np.float64)
    w2c=cam.matrix().cpu().numpy().astype(np.float64)
    pc=means@w2c[:3,:3].T+w2c[:3,3]
    K=np.array([[cam.fx,0,cam.cx],[0,cam.fy,cam.cy],[0,0,1]],dtype=np.float64)
    mask=(alpha>=0.5).astype(np.uint8)
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    curves=[];pixel_curves=[];depth_records=[];anchor_records=[]
    fallback=0;sample_count=0;fraction=[];cut_count=0;discarded_points=0
    for contour in contours:
        xy=contour[:,0,:].astype(np.float64)[::P['sample_stride_pixels']]
        if len(xy)<P['minimum_component_points']:continue
        x=xy[:,0].astype(int);y=xy[:,1].astype(int)
        ii=ids[y,x];ww=weights[y,x].copy()
        valid_ids=(ii>=0)&(ii<len(means));ii=np.clip(ii,0,len(means)-1);ww[~valid_ids]=0
        ss=strength[ii];zz=pc[ii,2]
        depths=supported_depth(zz,ww,ss)
        fallback+=int(np.sum((ww*ss).sum(1)<=1e-10));sample_count+=len(xy)
        fraction.extend((ww.sum(1)/np.maximum(alpha[y,x],1e-10)).tolist())
        depths=median_filter(depths,size=5,mode='nearest')
        points=ray_points(xy,depths,K,w2c)
        scale=float(np.nanmedian(depths)/cam.fx*P['sample_stride_pixels'])
        valid=np.isfinite(points).all(1)&(depths>0)
        breaks=np.zeros(len(points),bool);breaks[0]=True
        breaks[1:]=(~valid[1:])|(~valid[:-1])|(np.linalg.norm(np.diff(points,axis=0),axis=1)>8*scale)
        starts=np.flatnonzero(breaks);ends=np.r_[starts[1:],len(points)]
        cut_count+=int(breaks.sum()-1)
        for start,end in zip(starts,ends):
            if end-start<P['minimum_component_points'] or not valid[start:end].all():
                discarded_points+=end-start;continue
            p=points[start:end];pixels=xy[start:end]
            if start==0 and end==len(points) and np.linalg.norm(p[-1]-p[0])<=8*scale:
                p=np.vstack((p,p[0]));pixels=np.vstack((pixels,pixels[0]))
            curves.append(p);pixel_curves.append(pixels);depth_records.extend(depths[start:end].tolist())
        effective=ww*ss
        use_fallback=effective.sum(1)<=1e-10;effective[use_fallback]=ww[use_fallback]
        winners=ii[np.arange(len(ii)),np.argmax(effective,axis=1)]
        anchor_records.append({'pixels':xy.tolist(),'dominant_original_ids':winners.tolist(),'proxy_depths':depths.tolist(),'captured_mass_fraction':(ww.sum(1)/np.maximum(alpha[y,x],1e-10)).tolist()})
    assert curves and depth_records,'No admissible fixed 3D curve'
    radius=float(np.median(depth_records)/cam.fx*0.65)
    vertices,faces=tube_mesh(curves,radius,8)
    assert np.isfinite(vertices).all() and len(faces)>0
    glb=glb_bytes(vertices,faces);(dst/'fixed_contour.glb').write_bytes(glb)
    obj=['# GAER fixed 3D contour tubes. Original world coordinates; Z-up. Depth proxy, not certified surface.']
    obj+=['v %.9g %.9g %.9g'%tuple(v) for v in vertices]
    obj+=['f %d %d %d'%tuple(f+1) for f in faces]
    (dst/'fixed_contour.obj').write_text('\n'.join(obj)+'\n')
    line_obj=['# True static 3D polylines; use tube GLB/OBJ if the importer ignores OBJ l records.'];offset=1
    for i,p in enumerate(curves):
        line_obj.append(f'o curve_{i}')
        line_obj+=['v %.12g %.12g %.12g'%tuple(v) for v in p]
        line_obj.append('l '+' '.join(str(j) for j in range(offset,offset+len(p))))
        offset+=len(p)
    (dst/'centerlines.obj').write_text('\n'.join(line_obj)+'\n')
    geometry={'scene':name,'source_camera':'r_33','coordinate_system':'original 3DGS world Z-up','surface_depth_certified':False,'camera_independent_after_export':True,'tube_radius':radius,'curves':[p.tolist() for p in curves]}
    (dst/'CENTERLINES.json').write_text(json.dumps(geometry,ensure_ascii=False))
    (dst/'ANCHORS.json').write_text(json.dumps(anchor_records))
    loaded=trimesh.load(dst/'fixed_contour.glb',force='scene',process=False)
    mesh=next(iter(loaded.geometry.values()))
    assert np.array_equal(np.asarray(mesh.vertices,dtype=np.float32),vertices)
    assert np.array_equal(mesh.faces,faces)
    loaded_obj=trimesh.load(dst/'fixed_contour.obj',force='mesh',process=False)
    assert len(loaded_obj.faces)==len(faces) and np.isfinite(loaded_obj.vertices).all()
    doc_len=int.from_bytes(glb[12:16],'little');doc=json.loads(glb[20:20+doc_len])
    assert 'animations' not in doc and 'matrix' not in doc['nodes'][0] and len(doc['meshes'])==1
    errors=[]
    for p,xy in zip(curves,pixel_curves):
        q=p@w2c[:3,:3].T+w2c[:3,3]
        projected=q@K.T;projected=projected[:,:2]/projected[:,2,None]
        errors.extend(np.linalg.norm(projected-xy,axis=1).tolist())
    reprojection=float(np.max(errors));assert reprojection<1e-5
    (dst/'fixed_geometry_sha256.txt').write_text(hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest()+'\n')
    inspection=[];rows=[]
    for view in ['r_33']+P['inspection_only_views']:
        vc=camera_for(cfg,view)
        if view=='r_33':v_rgb=rgb0;v_alpha=alpha
        else:
            st=make_settings(native,vc.record)
            with torch.no_grad():
                result=native.GaussianRasterizer(st)(**scene,attribution=True,K=1)
                vr=result.rgb;va=result.accumulated_alpha
            v_rgb=vr.cpu().numpy().transpose(1,2,0);v_alpha=va.cpu().numpy().squeeze()
        M=vc.matrix().cpu().numpy().astype(np.float64)
        line=Image.new('RGB',(800,800),'white');draw=ImageDraw.Draw(line)
        samples=[]
        for curve in curves:
            q=curve@M[:3,:3].T+M[:3,3]
            xy=np.column_stack((vc.fx*q[:,0]/q[:,2]+vc.cx,vc.fy*q[:,1]/q[:,2]+vc.cy))
            for j in range(len(xy)-1):
                if q[j,2]>0 and q[j+1,2]>0:draw.line([tuple(xy[j]),tuple(xy[j+1])],fill=(20,20,20),width=2)
            samples.extend(xy[q[:,2]>0].tolist())
        vmask=(v_alpha>=.5).astype(np.uint8);vcont,_=cv2.findContours(vmask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        edge=np.zeros((800,800),np.uint8);cv2.drawContours(edge,vcont,-1,1,1)
        distance=distance_transform_edt(edge==0)
        uv=np.asarray(samples);inside=(uv[:,0]>=0)&(uv[:,0]<800)&(uv[:,1]>=0)&(uv[:,1]<800)
        px=np.rint(uv[inside]).astype(int);px=np.clip(px,0,799)
        ds=distance[px[:,1],px[:,0]]
        inspection.append({'view':view,'role':'construction' if view=='r_33' else 'inspection_only_not_used_for_fit','distance_to_exterior_p95_px':float(np.percentile(ds,95)) if len(ds) else None,'in_frame_fraction':float(inside.mean()),'occlusion_removal':False})
        original=Image.fromarray(np.uint8(np.clip(v_rgb,0,1)*255))
        overlay=original.copy();ink=np.asarray(line).min(2)<128;arr=np.asarray(overlay).copy();arr[ink]=[220,30,30];overlay=Image.fromarray(arr)
        row=Image.new('RGB',(2400,830),'white');row.paste(original,(0,30));row.paste(line,(800,30));row.paste(overlay,(1600,30));ImageDraw.Draw(row).text((8,8),f'{name} / {view} | original RGB | SAME FIXED 3D lines, x-ray | overlay',fill='black');rows.append(row)
        line.save(dst/f'fixed_projection_{view}.png')
    panel=Image.new('RGB',(2400,len(rows)*830),'white')
    for i,row in enumerate(rows):panel.paste(row,(0,i*830))
    panel.resize((1440,int(panel.height*1440/panel.width))).save(dst/'fourview_fixed_3d_preview.png')
    audit={'scene':name,'static_3d_asset':True,'scientific_status':'single-view fixed 3D candidate; multiview silhouette NOT certified','vertices':len(vertices),'triangles':len(faces),'curves':len(curves),'curve_points':sum(len(c) for c in curves),'tube_radius_world':radius,'native_top_k':32,'sampled_boundary_points':sample_count,'style_zero_mass_fallback_points':fallback,'depth_discontinuity_cuts':cut_count,'discarded_points':int(discarded_points),'captured_contribution_fraction_min':float(np.min(fraction)),'captured_contribution_fraction_median':float(np.median(fraction)),'construction_reprojection_max_px':reprojection,'serialization_roundtrip_pass':True,'obj_parse_pass':True,'fixed_glb_sha256':hashlib.sha256(glb).hexdigest(),'inspection':inspection}
    (dst/'EXPORT_AUDIT.json').write_text(json.dumps(audit,indent=2));results.append(audit)
    print(json.dumps(audit),flush=True)
    del scene,ids_t,w_t,alpha_t,rgb;torch.cuda.empty_cache()
(OUT/'RESULTS.json').write_text(json.dumps(results,indent=2))
