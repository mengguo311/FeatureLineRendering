from common import *
import argparse,copy,resource
from build import prepare_scene,save_graph
from primitive import sample_graph,sampling_layout
from differentiable import torch,derive,render_sparse,class_loss
from PIL import Image,ImageDraw,ImageFont
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)

def show_panel(path,items,title,cols=2,scale=1,subtitle='Fixed new 3D Gaussians; exact camera / original soft target'):
    h=max(a.shape[0] for _,a in items)*scale;w=max(a.shape[1] for _,a in items)*scale
    canvas=Image.new('RGB',(cols*w,70+((len(items)+cols-1)//cols)*(h+35)),'white');d=ImageDraw.Draw(canvas);d.text((10,10),title,font=FONT,fill='black');d.text((10,37),subtitle,font=FONT,fill='black')
    for i,(label,a) in enumerate(items):
        if a.ndim==2:a=np.repeat(a[...,None],3,2)
        im=Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5));im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
        x=i%cols*w;y=70+i//cols*(h+35);d.text((x+8,y+7),label,font=FONT,fill='black');canvas.paste(im,(x,y+35))
    canvas.save(path,quality=93)

def optimize(graph,nodes,layout,aa,ff,cs,dst,roi,steps):
    anchors=torch.tensor(nodes['points'],dtype=torch.float64);bound=torch.tensor(nodes['bounds'],dtype=torch.float64);ix=torch.tensor(nodes['node_index']);delta=torch.zeros_like(anchors,requires_grad=True)
    width=torch.tensor([g['width'] for g in graph],dtype=torch.float64,requires_grad=True);opacity=torch.tensor([g['opacity'] for g in graph],dtype=torch.float64,requires_grad=True)
    opt=torch.optim.Adam([{'params':[delta],'lr':.04},{'params':[width],'lr':.015},{'params':[opacity],'lr':.025}]);history=[];start=time.time()
    targets={};known={};windows={}
    for v in BUILD:
        window=CFG['roi_windows'][v] if roi else [0,0,cs[v]['width'],cs[v]['height']];windows[v]=window;x0,y0,x1,y1=window
        targets[v]=torch.tensor(ff[v]['dark'][y0:y1,x0:x1],dtype=torch.float64);a=aa[v];k=np.isfinite(a['z'])&(a['z']>0)&np.isfinite(a['alpha'])&(a['alpha']>=.5);known[v]=torch.tensor(k[y0:y1,x0:x1])
    logfile=dst/'optimization.jsonl'
    with logfile.open('w') as log:
        for it in range(sum(steps)+1):
            final=it==sum(steps);joint=it>=steps[0];opt.zero_grad(set_to_none=True);values={}
            for v in BUILD:
                cp=(anchors+bound[:,None]*delta)[ix];a=derive(cp,width if joint else width.detach(),opacity if joint else opacity.detach(),graph,layout)
                out=render_sparse(a,cs[v],aa[v]['z'],aa[v]['alpha'],windows[v]);loss=class_loss(out,targets[v],known[v]);values[v]=float(loss.detach());(loss/3).backward()
                del out,loss,a,cp
            anchor=.002*(delta**2).sum(1).mean();regular=anchor+.0001*opacity.mean()+.002*((width-.45)**2).mean()
            if not joint:regular=anchor
            regular.backward();objective=float(np.mean(list(values.values()))+regular.detach().item())
            row={'iteration':it,'phase':'joint' if joint else 'geometry','objective':objective,'camera_losses':values,'max_geometry_shift_pixel':float((torch.linalg.vector_norm(delta.detach(),dim=1)*.75).max()),'elapsed_s':time.time()-start,'width_mean':float(width.detach().mean()),'opacity_mean':float(opacity.detach().mean()),'delta_gradient_norm':float(torch.linalg.vector_norm(delta.grad))}
            assert np.isfinite(objective) and torch.isfinite(delta.grad).all();history.append(row);log.write(json.dumps(row)+'\n');log.flush()
            if it%4==0 or final:print('opt',dst.name,row,flush=True)
            if final:break
            opt.step()
            with torch.no_grad():
                delta/=torch.linalg.vector_norm(delta,dim=1,keepdim=True).clamp_min(1);width.clamp_(.25,.65);opacity.clamp_(.02,.95)
            if it%8==0:np.savez_compressed(dst/'optimization_checkpoint.npz',delta=delta.detach().numpy(),width=width.detach().numpy(),opacity=opacity.detach().numpy(),iteration=it)
    points=(anchors+bound[:,None]*delta).detach().numpy();control=points[nodes['node_index']]
    for i,g in enumerate(graph):g['control']=control[i];g['width']=float(width[i].detach());g['opacity']=float(opacity[i].detach())
    nodes['points']=points
    return history

def reload_graph(path,metadata):
    a=dict(np.load(path));graph=copy.deepcopy(metadata)
    for i,g in enumerate(graph):
        for k in ['control','pixel','normal','opacity','width']:g[k]=a[k][i]
    return graph

def run_scene(scene,roi=False,resume_render=False):
    guard();name=scene+('_roi' if roi else '_full');dst=T/'results'/name;dst.mkdir(parents=True,exist_ok=True)
    if (dst/'SEAL.json').exists():raise RuntimeError('Already sealed; refusing rerun')
    status(('RESUME_RENDER_' if resume_render else 'BUILDING_')+name,status='IN_PROGRESS',childPIDs=[os.getpid()],failure=None);start=time.time()
    if resume_render:
        checkpoint=json.loads((dst/'POST_OPTIMIZATION_CHECKPOINT.json').read_text())
        for filename,s in checkpoint['files'].items():assert sha(dst/filename)==s,filename
        hist=[json.loads(line) for line in (dst/'optimization.jsonl').read_text().splitlines()];assert hist[-1]['iteration']==sum(CFG['roi_steps'] if roi else CFG['full_steps'])
        metadata=json.loads((dst/'optimized_graph.json').read_text())['primitives'];p=dict(np.load(dst/'optimized_primitives.npz'));graph=[]
        for i,g in enumerate(metadata):
            graph.append({'control':p['control'][i],'type':str(p['type'][i]),'pixel':p['pixel'][i],'normal':p['normal'][i],'opacity':float(p['opacity'][i]),'width':float(p['width'][i]),'kind':str(p['kind'][i]),'members':g['source_segments'],'views':[BUILD.index(v) for v in g['source_views']],'fit_error_pixel':g['fit_error_pixel']})
        nodes={k:p[k] for k in ['points','node_index','bounds']};l=dict(np.load(dst/'sampling_layout.npz'));layout=tuple(l[k] for k in ['primitive_id','arc_t','basis','derivative_basis','spacing']);initial=dict(np.load(dst/'initial_gaussians.npz'));final=dict(np.load(dst/'optimized_gaussians.npz'));summary=json.loads((dst/'BUILD_SUMMARY.json').read_text());cs=demo.cameras(scene);aa={v:demo.read(scene,v) for v in BUILD};ff={v:{'dark':np.load(dst/f'{v}_maps.npz')['darkness']} for v in BUILD}
        summary['postprocessing_resumed_without_reoptimization']=True
    else:
        graph,nodes,aa,ff,cs,summary=prepare_scene(scene,dst,roi);layout=sampling_layout(graph);initial=save_graph(dst,graph,nodes,layout,'initial');summary['derived_gaussians']=len(initial['means'])
        np.savez_compressed(dst/'sampling_layout.npz',primitive_id=layout[0],arc_t=layout[1],basis=layout[2],derivative_basis=layout[3],spacing=layout[4]);js(dst/'BUILD_SUMMARY.json',summary)
        print('MODEL_READY',name,summary,flush=True);status('OPTIMIZING_'+name,childPIDs=[os.getpid()])
        hist=optimize(graph,nodes,layout,aa,ff,cs,dst,roi,CFG['roi_steps'] if roi else CFG['full_steps']);final=save_graph(dst,graph,nodes,layout,'optimized')
    assert np.isfinite(final['means']).all() and (np.linalg.eigvalsh(final['covariance'])>0).all()
    restored=reload_graph(dst/'optimized_primitives.npz',graph);regenerated=sample_graph(restored,layout)
    for k in final:np.testing.assert_array_equal(final[k],regenerated[k])
    js(dst/'ASSET_FREEZE.json',{'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':{p.name:sha(p) for p in sorted(dst.glob('*.npz'))},'holdout_content_used':False})
    status('RENDERING_'+name,childPIDs=[os.getpid()]);metrics={}
    balanced=dict(np.load(O/'results_v2'/scene/'balanced_gaussians.npz'))
    if roi:
        raw=dict(np.load(V3/'roi_pilot/roi_all_pixel_raw.npz'));v3fit_path=list((V3/'roi_pilot').glob('*fit*.npz'))[0];v3fit=dict(np.load(v3fit_path))
    for v in BUILD+(HOLD if not roi else ()):
        if v not in aa:aa[v]=demo.read(scene,v);ff[v]=demo.detect(aa[v])
        a=aa[v];c=cs[v];D=ff[v]['dark'];r0=core.render(initial,c,a['z'],a['alpha']);r1=core.render(final,c,a['z'],a['alpha']);rebuilt=core.render(regenerated,c,a['z'],a['alpha']);np.testing.assert_array_equal(r1,rebuilt)
        for lab,r in [('initial',r0),('optimized',r1)]:demo.saveimage(dst/f'{v}_{lab}_ink.png',r)
        demo.saveimage(dst/f'{v}_original_spatial.png',1-D);demo.saveimage(dst/f'{v}_rgb_reference.png',a['rgb']);demo.saveimage(dst/f'{v}_optimized_overlay.png',a['rgb']*(.3+.7*r1))
        k=np.isfinite(a['z'])&(a['z']>0)&np.isfinite(a['alpha'])&(a['alpha']>=.5)
        metrics[v]={}
        for lab,r in [('initial',r0),('optimized',r1)]:
            pred=1-r[...,0];pos=D>.2;neg=(D<.05)&k
            metrics[v][lab]={'mean_darkness':float(pred.mean()),'positive_mse':float(((pred[pos]-D[pos])**2).mean()),'offline_mse':float(((pred[neg]-D[neg])**2).mean()),'positive_uncovered_fraction':float((pred[pos]<.05).mean())}
        if roi:
            x0,y0,x1,y1=CFG['roi_windows'][v];crop=lambda x:x[y0:y1,x0:x1]
            items=[('Original Spatial soft target',crop(1-D)),('All-pixel v03 fixed ROI',crop(core.render(raw,c,a['z'],a['alpha']))),('v03 fixed geometry / negative',crop(core.render(v3fit,c,a['z'],a['alpha']))),('Structure initialization',crop(r0)),('Structure GEOMETRY + width + opacity',crop(r1))]
            show_panel(dst/f'{v}_comparison.jpg',items,scene+' FIXED ROI; same window as v03; 3 build sources',cols=3,scale=3)
        else:
            old=core.render(balanced,c,a['z'],a['alpha']);demo.saveimage(dst/f'{v}_old_balanced_ink.png',old)
            show_panel(dst/f'{v}_comparison.jpg',[('Original Spatial soft target',1-D),('Old balanced / 3 source views',old),('Structure initialization',r0),('Structure optimized',r1)],scene+' / '+v+(' BUILD' if v in BUILD else ' CONSTRUCTION HOLDOUT, not blind'),cols=2)
    # Recheck differentiable/native renderer on the exact final ROI; no numerical
    # approximation is hidden behind compilation-only validation.
    if roi:
        v='0000';cp=torch.tensor(np.array([g['control'] for g in graph]),dtype=torch.float64);ww=torch.tensor([g['width'] for g in graph],dtype=torch.float64);oo=torch.tensor([g['opacity'] for g in graph],dtype=torch.float64)
        with torch.no_grad():pred=render_sparse(derive(cp,ww,oo,graph,layout),cs[v],aa[v]['z'],aa[v]['alpha'],CFG['roi_windows'][v]).numpy()
        x0,y0,x1,y1=CFG['roi_windows'][v];native=1-core.render(final,cs[v],aa[v]['z'],aa[v]['alpha'])[y0:y1,x0:x1,0];error=float(abs(pred-native).max());assert error<2e-6
        summary['final_torch_native_max_error']=error
    summary.update(asset_regeneration_exact=True,reload_render_bitexact=True,optimization_initial=hist[0],optimization_final=hist[-1],runtime_seconds=time.time()-start,peak_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,geometry_actually_changed=bool(np.max(abs(final['means']-initial['means']))>1e-10),gaussian_mean_shift_scene_max=float(np.max(np.linalg.norm(final['means']-initial['means'],axis=1))),metrics=metrics)
    js(dst/'RESULTS.json',summary);seal(dst)
    state=json.loads((T/'STATUS.json').read_text());units=state.get('completed_units',[])+[name];status('UNIT_COMPLETE',childPIDs=[],completed_units=units,last_completed=name,status='IN_PROGRESS')
    print('UNIT_COMPLETE',name,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True,choices=['scan24','scan65','scan63']);p.add_argument('--roi',action='store_true');p.add_argument('--resume-render',action='store_true');a=p.parse_args()
    try:run_scene(a.scene,a.roi,a.resume_render)
    except BaseException as e:
        status('FAILED_'+a.scene,status='ENGINEERING_NOT_READY',childPIDs=[],failure=repr(e));raise
