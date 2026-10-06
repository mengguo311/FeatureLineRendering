"""Post-hoc fixed geometry projection only; never modifies graph assets."""
import hashlib,json,shutil,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import imageio_ffmpeg
import runtime as rt
from core import project

COLORS={'A':(20,120,210),'B':(215,45,40)}
def line_image(xyz,edges,camera,background=None,arm='A'):
    im=background.copy() if background is not None else Image.new('RGB',(800,800),'white')
    uv,z=project(xyz,camera);d=ImageDraw.Draw(im)
    for a,b in edges:
        if z[a]>0 and z[b]>0 and np.isfinite(uv[[a,b]]).all():
            d.line([tuple(uv[a]),tuple(uv[b])],fill=COLORS[arm],width=2)
    return im,uv,z

def center_image(xyz,mask,camera):
    im=Image.new('RGB',(800,800),'white');d=ImageDraw.Draw(im);uv,z=project(xyz,camera)
    colors={1:(230,110,25),2:(25,110,230),3:(150,40,170)}
    for p,depth,m in zip(uv,z,mask):
        if depth>0 and np.isfinite(p).all():d.ellipse((p[0]-1.5,p[1]-1.5,p[0]+1.5,p[1]+1.5),fill=colors[int(m)])
    return im

def labeled_panels(images,labels,title):
    panel=Image.new('RGB',(800*len(images),850),'white');d=ImageDraw.Draw(panel)
    d.text((8,5),title,fill='black')
    for j,(im,label) in enumerate(zip(images,labels)):
        d.text((800*j+8,27),label,fill='black');panel.paste(im,(800*j,50))
    return panel

def encode_and_decode(frame_dir,path):
    exe=imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([exe,'-hide_banner','-loglevel','error','-y','-framerate','12','-i',str(frame_dir/'%03d.png'),'-frames:v','33',
        '-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
    # Independent full decode: stream to avoid holding all video pixels in RAM.
    p=subprocess.Popen([exe,'-hide_banner','-loglevel','error','-threads','2','-i',str(path),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    framebytes=1600*850*3;pending=b'';hashes=[]
    while True:
        b=p.stdout.read(framebytes-len(pending))
        if not b:break
        pending+=b
        if len(pending)==framebytes:hashes.append(hashlib.sha256(pending).hexdigest());pending=b''
    error=p.stderr.read().decode();rc=p.wait()
    assert rc==0 and not pending and len(hashes)==33,(rc,len(hashes),error)
    data=path.read_bytes();assert 0<=data.find(b'moov')<data.find(b'mdat')
    assert len(set(hashes))==33,'decoded duplicate frames'
    probe=subprocess.check_output([exe,'-hide_banner','-i',str(path)],stderr=subprocess.STDOUT,text=True) if False else subprocess.run([exe,'-hide_banner','-i',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stderr
    assert 'h264' in probe and 'yuv420p' in probe
    return dict(path=rt.rel(path),sha256=rt.sha(path),encoder=exe,encoder_sha256=rt.sha(exe),codec='H264',pixel_format='yuv420p',faststart=True,
        fps=12,width=1600,height=850,decoded_frames=33,decoded_unique_frames=33,decoded_frame_sha256=hashes,full_decode=True,
        line_display_width_px=2,xray=True,hidden_line_removal=False,native_tube_mesh_render=False,world_tube_width_validation=False)

def spatial_plot(scene,xyz,g,dst):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Line3DCollection
    fig=plt.figure(figsize=(18,6));center=(xyz.min(0)+xyz.max(0))/2;span=float(np.ptp(xyz,axis=0).max())*.54
    for j,arm in enumerate(['A','B','PCA']):
        ax=fig.add_subplot(1,3,j+1,projection='3d')
        ax.scatter(*xyz.T,s=.7,c='gray',alpha=.25)
        if arm=='PCA':
            segments=np.stack([xyz-g['tangent']*g['local_scale'][:,None]*.5,xyz+g['tangent']*g['local_scale'][:,None]*.5],axis=1)
            colors=plt.cm.viridis(g['linearity']);ax.add_collection3d(Line3DCollection(segments,colors=colors,linewidths=.6))
        else:ax.add_collection3d(Line3DCollection(xyz[g[arm]],colors=np.array(COLORS[arm])/255,linewidths=.5))
        ax.set(xlim=(center[0]-span,center[0]+span),ylim=(center[1]-span,center[1]+span),zlim=(center[2]-span,center[2]+span),xlabel='world X',ylabel='world Y',zlabel='world Z')
        ax.set_box_aspect((1,1,1));ax.view_init(elev=23,azim=-55);ax.set_title(scene+' '+arm+(' unoriented tangents, NOT normals' if arm=='PCA' else ' kernel-space candidates'))
    fig.tight_layout();fig.savefig(rt.scoped(dst/'true_3d_graph_PCA.png'),dpi=140);plt.close(fig)

def viewer(data):
    template=(rt.EXP/'viewer_template.html').read_text()
    rt.scoped(rt.ART/'media'/'viewer_3d.html').write_text(template.replace('__DATA__',json.dumps(data,separators=(',',':'))))

def main():
    rt.guard('posthoc_media_start')
    f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());results=json.loads((rt.ART/'RESULTS.json').read_text())
    audit={};view_data={}
    asset_hashes={str(p):rt.sha(p) for p in (rt.ART/'assets').rglob('*') if p.is_file()}
    for scene,rec in f['scenes'].items():
        rt.guard(scene+'_posthoc_media')
        asset=rt.ART/'assets'/scene;g=np.load(asset/'FULL_GRAPH.npz');xyz=g['xyz'];ids=g['ids'];mask=g['source_view_mask']
        dst=rt.ART/'media'/scene;dst.mkdir(parents=True,exist_ok=True)
        spatial_plot(scene,xyz,g,dst)
        view_data[scene]=dict(xyz=xyz.tolist(),ids=ids.tolist(),A=g['A'].tolist(),B=g['B'].tolist(),tangent=g['tangent'].tolist(),scale=g['local_scale'].tolist(),linearity=g['linearity'].tolist(),source_mask=mask.tolist(),radius=float(g['radius']))
        rows=[];checks=[]
        for c in rec['cameras']:
            out=dst/c['key'];out.mkdir(exist_ok=True)
            source=rec['backgrounds'][c['key']];assert rt.sha(source['path'])==source['sha256']
            shutil.copyfile(source['path'],rt.scoped(out/'original_RGB_SH3.png'))
            rgb=Image.open(source['path']).convert('RGB');assert rgb.size==(800,800)
            centers=center_image(xyz,mask,c);images=[rgb,centers];labels=['Original full SH3 RGB (prior native)','Exact original kernel centers (x-ray)']
            for arm in ['A','B']:
                im,uv,z=line_image(xyz,g[arm],c,arm=arm);im.save(rt.scoped(out/(arm+'_xray.png')));images.append(im);labels.append(arm+' SAME fixed graph / 2px x-ray')
                inside=(z>0)&(uv[:,0]>=0)&(uv[:,0]<800)&(uv[:,1]>=0)&(uv[:,1]<800)
                e=g[arm];px=np.linalg.norm(uv[e[:,0]]-uv[e[:,1]],axis=1)
                checks.append(dict(scene=scene,view=c['key'],arm=arm,camera_sha256=c['camera_sha256'],inspection_only=c['key'] in ['r_1','r_14'],formal_blind=False,
                    centers_in_frame=int(inside.sum()),nodes=len(xyz),edges=len(e),pixel_length_quantiles={str(q):float(np.percentile(px,q)) for q in [0,50,95,100]} if len(px) else {},
                    endpoints_positive_depth=int(((z[e[:,0]]>0)&(z[e[:,1]]>0)).sum()),geometry_sha256=results[scene]['arms'][arm]['geometry_sha256'],image_feedback=False,hidden_line_removal=False))
            for arm in ['A','B']:
                overlay,_,_=line_image(xyz,g[arm],c,rgb,arm);overlay.save(rt.scoped(out/(arm+'_RGB_overlay.png')));images.append(overlay);labels.append(arm+' on RGB / x-ray / hidden lines retained')
            centers.save(rt.scoped(out/'selected_centers_xray.png'))
            row=labeled_panels(images,labels,scene+' / '+c['key']+' | static original-ID graph; 2px centerline presentation, no tube render')
            row.save(rt.scoped(out/'inspection.png'));rows.append(row)
        panel=Image.new('RGB',(4800,3400),'white')
        for j,row in enumerate(rows):panel.paste(row,(0,850*j))
        panel.save(rt.scoped(dst/'four_camera_inspection_FULL.png'))
        panel.resize((2400,1700)).save(rt.scoped(dst/'four_camera_inspection_preview.png'))
        rt.write_json(dst/'FOUR_CAMERA_AUDIT.json',checks)
        arc=dst/'arc';frames=arc/'frames';frames.mkdir(parents=True,exist_ok=True)
        camera_hashes=[];frame_records=[];projected=[];depths=[];thumbs=[]
        for item in rec['arc']:
            j=item['index'];c=item['camera'];camera_hashes.append(rt.digest(c['w2c']))
            assert rt.sha(item['path'])==item['sha256']
            rgb=Image.open(item['path']).convert('RGB');assert rgb.size==(800,800)
            a,uv,z=line_image(xyz,g['A'],c,rgb,'A');b,_,_=line_image(xyz,g['B'],c,rgb,'B');projected.append(uv);depths.append(z)
            panel=labeled_panels([a,b],['A / fixed original-ID graph','B / same frozen PCA/mutual graph'],scene+f' / actual camera {j:02d} {c["key"]} | 2px centerline projection / X-RAY / no hidden-line removal')
            p=frames/f'{j:03d}.png';panel.save(rt.scoped(p));thumbs.append(panel.resize((400,212)))
            frame_records.append(dict(index=j,camera_key=c['key'],camera_sha256=c['camera_sha256'],matrix_sha256=camera_hashes[-1],source_RGB_sha256=item['sha256'],frame_sha256=rt.sha(p),
                A_geometry_sha256=results[scene]['arms']['A']['geometry_sha256'],B_geometry_sha256=results[scene]['arms']['B']['geometry_sha256'],fixed_vertex_count=len(xyz),no_reselection=True,no_deformation=True))
        assert len(frame_records)==33 and len(set(camera_hashes))==33
        np.savez_compressed(rt.scoped(arc/'ALL_CAMERA_PROJECTIONS.npz'),original_ids=ids,xyz=xyz,uv=np.array(projected),camera_depth=np.array(depths),w2c=np.array([a['camera']['w2c'] for a in rec['arc']]))
        strip=Image.new('RGB',(1200,212*11),'white')
        for j,thumb in enumerate(thumbs):strip.paste(thumb,(j%3*400,j//3*212))
        strip.save(rt.scoped(arc/'ALL_33_FRAMES.png'))
        rt.guard(scene+'_video_encode')
        video=encode_and_decode(frames,rt.scoped(arc/'A_B_fixed_graph_33.mp4'))
        rt.write_json(arc/'FRAME_MANIFEST.json',dict(frames=frame_records,distinct_actual_cameras=33,all_frames_preserved=True,cameras_prior_GS_research_seen=True,video=video))
        audit[scene]=dict(video=video,frame_count=33,unique_camera_count=33,four_camera_views=4,graph_frozen_before_media=True)
        print(scene,'four views + 33 real cameras complete, decoded',video['decoded_frames'],flush=True)
    viewer(view_data)
    changed=[p for p,h in asset_hashes.items() if rt.sha(p)!=h];assert not changed,changed
    rt.write_json(rt.ART/'MEDIA_AUDIT.json',dict(scenes=audit,asset_hashes_before_media=asset_hashes,assets_unchanged_after_all_projection=True))
    rt.guard('all_media_complete')
if __name__=='__main__':main()
