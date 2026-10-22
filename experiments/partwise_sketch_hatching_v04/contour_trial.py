"""One frozen display comparison on real saved Ficus/Chair assets, CPU serial."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,time,subprocess
import numpy as np
from PIL import Image
from scipy import ndimage
from demo import load_asset,set_display,edit,save_frame,new_output
from media import contact,FFMPEG
from geometry import resize_camera

def arrays(path):
    with np.load(path) as f:return {k:f[k] for k in f.files}

def run(unit,phase,scene):
    unit=output_guard(unit);protocol=json.loads((unit/'PROTOCOL.json').read_text())
    if phase=='prepare':
        for key,entry in protocol['scenes'].items():
            source=Path(entry['asset'])
            assert all(sha(source/name)==h for name,h in entry['files'].items())
            base=unit/'assets'/key/'baseline';shutil.copytree(source,base)
            set_display(base,base.parent/'reduced',protocol['arms']['reduced'])
            edit(base,base.parent/'edited',2,{'angle':45.})
            set_display(base.parent/'edited',base.parent/'edited_reduced',protocol['arms']['reduced'])
        lib=Path(protocol['previous_unit'])/'build/libsource.so'
        (unit/'build').mkdir();shutil.copy2(lib,unit/'build/libsource.so')
        js(unit/'INPUT_LOCK.json',dict(protocol_sha256=sha(unit/'PROTOCOL.json'),libsource=dict(source=str(lib),sha256=sha(lib)),
            actual_sources={p.name:sha(p) for p in Path(__file__).parent.iterdir() if p.is_file()}))
    elif phase=='source':
        import model_adapter
        entry=protocol['scenes'][scene];source=entry['original']
        model_adapter.LIB_PATH=unit/'build/libsource.so'
        model=model_adapter.load_source(source['original_ply'],source['sha256'])
        out=new_output(unit/'source_model'/scene);rows=[]
        for i,stored_camera in enumerate(entry['cameras']):
            c=resize_camera(stored_camera,512)
            t=time.monotonic();r=model_adapter.render_source(model,c)
            np.savez_compressed(out/f'frame_{i:03d}.npz',**r)
            Image.fromarray(np.uint8(np.clip(r['rgb'],0,1)*255+.5)).save(out/f'frame_{i:03d}_rgb.png')
            rows.append(dict(camera=c,seconds=time.monotonic()-t));print(scene,c['view'],rows[-1]['seconds'],flush=True)
        js(out/'RECEIPT.json',dict(original=source,original_gaussians=model['audit']['count'],frames=rows,
            adapter_scope='CPU SH3 EWA render of original checkpoint; not official GPU equivalence or independent surface truth',libsource_sha256=sha(model_adapter.LIB_PATH)))
    elif phase=='static':
        for arm in ('baseline','reduced','edited','edited_reduced'):
            mesh,paths,meta=load_asset(unit/'assets'/scene/arm)
            out=new_output(unit/'renders'/scene/arm)
            rows=[save_frame(out,f'frame_{i:03d}',mesh,paths,meta,resize_camera(c,512)) for i,c in enumerate(protocol['scenes'][scene]['cameras'])]
            js(out/'RENDER_RECEIPT.json',dict(arm=arm,scene=scene,frames=rows,cold_loaded=True))
    elif phase=='motion':
        mesh,paths,meta=load_asset(unit/'assets/ficus/edited_reduced')
        for name in ('orbit','zoom'):
            out=new_output(unit/'renders'/name)
            rows=[save_frame(out,f'frame_{i:03d}',mesh,paths,meta,c) for i,c in enumerate(protocol[name])]
            js(out/'RENDER_RECEIPT.json',dict(scene='ficus',arm='edited_reduced',frames=rows,cold_loaded=True))
    elif phase=='metrics':
        rows=[];geometry=[]
        for key,entry in protocol['scenes'].items():
            base=unit/'assets'/key
            for arm in ('baseline','edited'):
                reduced=base/('reduced' if arm=='baseline' else 'edited_reduced')
                for f in (base/arm).iterdir():
                    if f.name!='asset.json' and f.is_file():assert sha(f)==sha(reduced/f.name)
            for name in ('mesh.npz','region_1.npz','region_3.npz'):assert sha(base/'baseline'/name)==sha(base/'edited'/name)
            assert sha(base/'baseline/region_2.npz')!=sha(base/'edited/region_2.npz')
            mesh,strokes,meta=load_asset(base/'baseline')
            geometry.append(dict(scene=key,faces=len(mesh['faces']),paths={str(k):int(len(np.unique(s['stroke_id']))) for k,s in strokes.items()},
                display_all_geometry_and_paths_byte_exact=True,edit_other_regions_byte_exact=True))
            items=[];edits=[]
            for i,c in enumerate(entry['cameras']):
                data={arm:arrays(unit/f'renders/{key}/{arm}/frame_{i:03d}_arrays.npz') for arm in ('baseline','reduced','edited','edited_reduced')}
                a,b=data['baseline'],data['reduced']
                for before,after in (('baseline','reduced'),('edited','edited_reduced')):
                    for field in ('hatch','depth','regions',*[f'layer_{k}' for k in strokes]):np.testing.assert_array_equal(data[before][field],data[after][field])
                    np.testing.assert_allclose(data[after]['contour'],data[before]['contour']*.35,atol=4e-8)
                row=dict(scene=key,view=c['view'],display_L1=float(np.abs(a['image']-b['image']).sum()),hatch_ink=float(a['hatch'].sum()),
                    hatch_ink_retained_fraction=1.,baseline_total_ink=float((1-a['image']).sum()),reduced_total_ink=float((1-b['image']).sum()),
                    baseline_contour_ink=float(a['contour'].sum()),reduced_contour_ink=float(b['contour'].sum()),
                    foreground_pixels=int((a['regions']>0).sum()),edits={})
                for before,after in (('baseline','edited'),('reduced','edited_reduced')):
                    x,y=data[before],data[after]
                    for field in ('depth','regions','contour','layer_1','layer_3'):np.testing.assert_array_equal(x[field],y[field])
                    delta=np.abs(x['image']-y['image']);target=x['regions']==2
                    band=ndimage.binary_dilation(target,iterations=2)&~ndimage.binary_erosion(target,iterations=2)
                    other=(x['regions']>0)&~target&~band;bg=(x['regions']==0)&~band
                    row['edits'][before]=dict(total_L1=float(delta.sum()),target_L1=float(delta[target].sum()),
                        far_other_L1=float(delta[other].sum()),background_L1=float(delta[bg].sum()),band_L1=float(delta[band].sum()),
                        far_changed_pixel_yx=np.argwhere((other|bg)&(delta>0)).tolist(),non_target_layers_exact=True)
                    assert row['edits'][before]['target_L1']>0
                for arm in data:
                    receipt=json.loads((unit/f'renders/{key}/{arm}/frame_{i:03d}.json').read_text())
                    assert receipt['bounds']['all_proxy_vertices_inside']
                rows.append(row)
                items.append((c['view']+' | original GS RGB',Image.open(unit/f'source_model/{key}/frame_{i:03d}_rgb.png')))
                for label,arm,suffix in [('Proxy','baseline','proxy'),('Authored regions','baseline','region_rgb'),('Contours 100%','baseline','image'),('Contours 35%','reduced','image')]:
                    items.append((label,Image.open(unit/f'renders/{key}/{arm}/frame_{i:03d}_{suffix}.png')))
                for label,arm in [('100% | before','baseline'),('100% | angle95 -> 45','edited'),('35% | before','reduced'),('35% | angle95 -> 45','edited_reduced')]:
                    edits.append((c['view']+' | '+label,Image.open(unit/f'renders/{key}/{arm}/frame_{i:03d}_image.png')))
            contact(unit/f'media/{key}_comparison.png',items,cols=5,size=512,title=key.title()+' | same geometry and hatch ink; only contour strength changes')
            contact(unit/f'media/{key}_local_edit.png',edits,cols=4,size=512,title=key.title()+' | real middle-region edit at both display strengths')
        js(unit/'metrics/COMPARISON.json',dict(geometry=geometry,frames=rows,all_static_complete=True,
            display_layer_contract='PASS',visual_quality='REQUIRES_DESCRIPTIVE_REVIEW',scientific_claim='H1/H2 not tested; proxy and manual regions unchanged'))
    elif phase=='media':
        records=[]
        for name in ('orbit','zoom'):
            folder=unit/'renders'/name;files=sorted(folder.glob('frame_*_image.png'))
            assert len(files)==len(protocol[name])
            assert all(json.loads((folder/f'frame_{i:03d}.json').read_text())['bounds']['all_proxy_vertices_inside'] for i in range(len(files)))
            contact(unit/f'media/{name}_all_frames.png',[(f'{name} {i:02d}',Image.open(f)) for i,f in enumerate(files)],cols=4,size=384,
                title='Ficus | contours 35%, fixed edited 3D paths | all actual frames')
            video=unit/f'media/{name}.mkv'
            encode=[str(FFMPEG),'-nostdin','-v','error','-threads','1','-filter_threads','1','-framerate','6','-i',str(folder/'frame_%03d_image.png'),'-c:v','ffv1','-level','3','-pix_fmt','bgr0','-threads','1',str(video)]
            e=subprocess.run(encode,capture_output=True,timeout=120);e.check_returncode()
            decode=[str(FFMPEG),'-nostdin','-v','error','-threads','1','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','-']
            d=subprocess.run(decode,capture_output=True,timeout=120);d.check_returncode()
            frames=np.frombuffer(d.stdout,np.uint8).reshape(-1,512,512,3);assert len(frames)==len(files)
            for a,f in zip(frames,files):np.testing.assert_array_equal(a,np.asarray(Image.open(f).convert('RGB')))
            records.append(dict(name=name,frames=len(files),all_decoded_exact=True,all_complete_objects=True,unique_images=len({sha(f) for f in files}),
                encode_command=encode,encode_returncode=e.returncode,decode_command=decode,decode_returncode=d.returncode,sha256=sha(video)))
        js(unit/'media/VIDEO_VALIDATION.json',dict(videos=records,scope='All frames decoded; no independent temporal-stability certification'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','source','static','motion','metrics','media']);p.add_argument('--scene',choices=['chair','ficus']);p.add_argument('--unit',type=Path,default=OUTPUT_ROOT/'units/unit_011');a=p.parse_args();run(a.unit,a.phase,a.scene)
