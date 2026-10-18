from env import *
def main():
 out=ROOT/'audit';out.mkdir(exist_ok=True);sources=[BASE/'REGISTRY.json',OLD/'CASE_FREEZE.json',ROOT.parent/'c2l50_8build_surface_partition_v01/REPORT_ZH.md'];counts={};cf=json.loads((OLD/'CASE_FREEZE.json').read_text());js(ROOT/'CASE_FREEZE.json',cf)
 for s in SCENES:
  paths=[linepath(s)/n for n in ['gaussians.npz','gaussians.ply','parents.json','SHARED_CONTROL_AND_SAMPLING.npz','LENGTH_AND_PARENT.npz','OBSERVATIONS.npz']];sources+=paths
  ps=json.loads(paths[2].read_text());lay=npz(paths[3]);g=npz(paths[0]);src=Path(registry()[s]['model']);assert sha(src)==registry()[s]['model_sha256'];sources.append(src)
  x=(lay['control'][lay['control_index']]*lay['basis'][:,:,None]).sum(1);np.testing.assert_array_equal(x,g['means']);lens=[];closed=0;zero=0;rat=[];ncomp=[]
  for i,p in enumerate(ps):
   lo,hi=lay['parent_control_offsets'][i];P=lay['control'][lo:hi];Q=np.asarray(p['control']);expected=P if not p['closed'] else np.r_[P,P[:1]];np.testing.assert_array_equal(Q,expected)
   L=float(np.linalg.norm(np.diff(Q,axis=0),axis=1).sum());lens.append(L/p['pixel']);zero+=L<1e-12;closed+=bool(len(Q)>2 and np.linalg.norm(Q[-1]-Q[0])<1e-12);rat.append(float(np.linalg.norm(Q[-1]-Q[0])/max(L,1e-15)));ncomp.append(1)
  counts[s]=dict(source=len(read_ply(src)),ink=len(g['means']),parents=len(ps),closed_exact=closed,zero_length=zero,multiple_components=0,topology='each production parent is one sequential C0 polyline; separate parents never merged by coordinate proximity',reference_length_quantiles=np.quantile(lens,[0,.25,.5,.75,.9,.99,1]).tolist(),endpoint_gap_over_arc_quantiles=np.quantile(rat,[0,.1,.5,.9,1]).tolist(),source_multiplicity={str(k):sum(len(p['source_views'])==k for p in ps) for k in sorted(set(len(p['source_views']) for p in ps))})
  for v in [DEV[s],AUX[s]]+RESERVED[s]:sources.append(rawpath(s,v))
  v=DEV[s];c=cam(s,v);raw=npz(rawpath(s,v));ink=render(g,c,[1]*3,.0144)['rgb'];rgb=raw['rgb'];im=Image.fromarray(np.uint8(np.clip(rgb,0,1)*255));dr=ImageDraw.Draw(im)
  for case in cf['cases']:
   if case['scene']!=s:continue
   uv=case.get('target_uv');
   if uv is not None:
    x,y=uv;dr.rectangle((x-48,y-48,x+48,y+48),outline='yellow',width=2);dr.text((x-46,y-46),case['case'],fill='red')
  save(out/f'{s}_rgb.jpg',rgb);save(out/f'{s}_ink.jpg',ink);panel(out/f'{s}_INPUT.jpg',[('Frozen source RGB; inherited case windows',np.asarray(im)/255),('Original C8 Gaussian ink (xray, no source occlusion)',ink)],s+' | topology preflight',f'parents {len(ps)} | exact closed {closed} | no modified line geometry')
  print(s,counts[s],flush=True)
 js(ROOT/'TOPOLOGY_AUDIT.json',counts);js(ROOT/'SOURCE_MANIFEST.json',dict(files={str(p):sha(p) for p in sources},scientific_line_input='original arms/C only'))
 state('INPUT_AUDIT_COMPLETE',completed_scenes=3)
if __name__=='__main__':main()
