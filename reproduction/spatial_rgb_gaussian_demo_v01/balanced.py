import numpy as np

def evidence_weight(support,counter):
 return np.where(np.asarray(counter)>0,.40,np.where(np.asarray(support)>=2,1.,.70))

def main():
 import sys,json,time
 from pathlib import Path
 import demo,core
 T=core.TASK;D=T/'results_v2'
 if sys.argv[1]=='build':
  assert not (T/'BALANCED_ASSET_FREEZE.json').exists()
  records=[]
  for scene in demo.SCENES:
   src=demo.OUT/scene;dst=D/scene;dst.mkdir(parents=True,exist_ok=True);s=dict(np.load(src/'source_samples.npz'));raw=dict(np.load(src/'raw_gaussians.npz'));fused=dict(np.load(src/'fused_gaussians.npz'));n=len(raw['means']);other=np.flatnonzero(s['fused_id']<0);g=len(fused['means']);w=evidence_weight((s['votes']==1).sum(1),(s['votes']<0).sum(1));anchors=fused['source_anchor']
   a={}
   for key in raw:
    first=core.ink_covariance(s['tangent'][anchors],s['normal'][anchors],s['pixel'][anchors],False) if key=='covariance' else fused[key]
    second=raw[key][other].copy()
    if key=='opacity':second=second*w[other]
    a[key]=np.concatenate([first,second])
   membership=s['fused_id'].copy();membership[other]=np.arange(len(other))+g
   np.savez_compressed(dst/'balanced_gaussians.npz',**a);demo.save_ply(dst/'balanced_gaussians.ply',a);np.savez_compressed(dst/'balanced_provenance.npz',source_to_balanced_id=membership,source_weight=w)
   assert np.all(membership>=0);assert len(np.unique(membership))==len(a['means']);assert np.isfinite(a['means']).all();assert (np.linalg.eigvalsh(a['covariance'])>0).all()
   c=demo.cameras(scene)['0024'];v=demo.read(scene,'0024');im=core.render(a,c,v['z'],v['alpha']);b=dict(np.load(dst/'balanced_gaussians.npz'));np.testing.assert_array_equal(im,core.render(b,c,v['z'],v['alpha']));demo.saveimage(dst/'BUILD_ONLY_0024_balanced.png',im)
   row={'scene':scene,'gaussians':len(a['means']),'all_raw_samples_represented':n,'multisupported_merged_primitives':g,'single_unmerged_primitives':len(other),'reload_render_exact':True,'no_source_deleted':True,'weight_histogram':{str(x):int((w==x).sum()) for x in [.4,.7,1.]}};demo.writejson(dst/'BUILD_SUMMARY.json',row);records.append(row);demo.status('BALANCED_BUILD',current_scene=scene,models_created=6+len(records),heldout_content_read=False)
  files=[p for scene in demo.SCENES for p in (D/scene).glob('*.npz')]+[p for p in Path(__file__).parent.iterdir() if p.is_file()]
  demo.writejson(T/'BALANCED_ASSET_FREEZE.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'heldout_content_read':False,'summary':records,'files':[{'path':str(p),'sha256':demo.sha(p)} for p in files]})
 else:
  from PIL import Image,ImageDraw
  import subprocess,re
  freeze=json.loads((T/'BALANCED_ASSET_FREEZE.json').read_text())
  for r in freeze['files']:assert demo.sha(r['path'])==r['sha256'],r['path']
  for i,scene in enumerate(demo.SCENES):
   src=demo.OUT/scene;dst=D/scene;asset=dict(np.load(dst/'balanced_gaussians.npz'));cs=demo.cameras(scene)
   for v in (*demo.BUILD,*demo.HOLD):
    a=demo.read(scene,v);f=demo.detect(a);im=core.render(asset,cs[v],a['z'],a['alpha']);demo.saveimage(dst/(v+'_balanced_ink.png'),im);demo.saveimage(dst/(v+'_balanced_overlay.png'),im*a['rgb'])
    get=lambda arm:np.array(Image.open(src/(v+'_'+arm+'_ink.png'))).astype(np.float32)/255
    role='build' if v in demo.BUILD else 'selection HOLDOUT (not blind GS holdout)'
    demo.panel(dst/(v+'_comparison.jpg'),[('Original rendered RGB',a['rgb']),('Original spatial RGB soft ink',demo.boundary.ink(f['union'])),('RAW: all marked valid-depth pixels',get('raw')),('STRICT FUSED: multiview supported only',get('fused')),('BALANCED: no source deleted; uncertain attenuated',im),('BALANCED overlay on original RGB',im*a['rgb'])],scene+' | '+v+' | '+role,cols=3)
   arc=json.loads((src/'ARC_CAMERAS.json').read_text())['cameras'];frames=dst/'arc_frames';frames.mkdir(exist_ok=True)
   for j,c in enumerate(arc):
    im=core.render(asset,c);p=frames/(f'{j:03d}.png');demo.panel(p,[('BALANCED: includes uncertain source samples',im)],scene+' | balanced | NO original-scene occlusion',cols=1)
    third=Image.open(p);base=Image.open(src/'arc_frames'/(f'{j:03d}.png'));out=Image.new('RGB',(base.width+third.width,base.height),'white');out.paste(base,(0,0));out.paste(third,(base.width,0));out.save(p)
   video=dst/'three_arm_fixed_gaussian_arc.mp4';exe=demo.ffmpeg();cmd=[exe,'-y','-framerate','12','-i',str(frames/'%03d.png'),'-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
   with (dst/'VIDEO_LOG.txt').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
   r=subprocess.run([exe,'-i',str(video),'-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(dst/'DECODE_LOG.txt').write_text(r.stdout);counts=re.findall(r'frame=\s*(\d+)',r.stdout);assert r.returncode==0 and int(counts[-1])==33 and 'yuv420p' in r.stdout
   atoms=[]
   with video.open('rb') as f:
    while True:
     hdr=f.read(8)
     if len(hdr)<8:break
     sz=int.from_bytes(hdr[:4],'big');atoms.append(hdr[4:].decode('ascii'))
     if sz==1:sz=int.from_bytes(f.read(8),'big');f.seek(sz-16,1)
     elif sz>=8:f.seek(sz-8,1)
     else:break
   assert atoms.index('moov')<atoms.index('mdat')
   contact=Image.new('RGB',(2331,678*3),'white')
   for row,j in enumerate([0,16,32]):contact.paste(Image.open(frames/(f'{j:03d}.png')),(0,row*678))
   contact.save(dst/'ARC_FIRST_MIDDLE_LAST.jpg',quality=90)
   demo.writejson(dst/'RENDER_EVALUATION.json',{'frames':33,'fully_decoded':33,'h264_yuv420p_faststart':True,'atoms':atoms,'command':cmd,'fixed_asset_sha256':demo.sha(dst/'balanced_gaussians.npz'),'new_camera_original_scene_occlusion':False})
   demo.status('BALANCED_RENDER_COMPLETE',scenes_with_three_arms_rendered=i+1,models_rendered=6+i+1)
if __name__=='__main__':main()
