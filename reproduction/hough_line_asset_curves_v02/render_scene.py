from runtime import *
from core import unit
from PIL import Image,ImageDraw,ImageFont

def save_image(p,a):Image.fromarray(np.uint8(np.round(np.clip(a,0,1)*255))).save(p)
def validate(scene,name):
    fmt,_=renderer_modules();folder=OUT/scene/name;inp=BASE/'arms/C/scenes'/scene/'full'
    a=load_np(folder/'gaussians.npz');o=load_np(inp/'gaussians.npz');s=load_np(inp/'SHARED_CONTROL_AND_SAMPLING.npz')
    c=load_np(folder/'curves.npz');ledger=load_np(folder/'ledger.npz');raw=fmt.read_ply(folder/'gaussians.ply');old=fmt.read_ply(inp/'gaussians.ply');act=fmt.activate(raw)
    n=len(o['means']);assert len(raw)==n==len(a['means']);assert ledger['processed'].all()
    for k in ('opacity','colors','primitive_id','internal_piece_id','arc_t'):np.testing.assert_array_equal(a[k],o[k])
    np.testing.assert_array_equal(a['line_kernel_id'],np.arange(n));np.testing.assert_array_equal(c['source_line_kernel_id'],np.arange(n))
    for k in old.dtype.names:
        if k not in ('x','y','z','rot_0','rot_1','rot_2','rot_3'):np.testing.assert_array_equal(raw[k],old[k])
        np.testing.assert_array_equal(raw[k][ledger['retained']],old[k][ledger['retained']])
    np.testing.assert_array_equal(a['means'][ledger['retained']],o['means'][ledger['retained']]);np.testing.assert_array_equal(a['covariance'][ledger['retained']],o['covariance'][ledger['retained']])
    me=float(np.max(abs(act['means']-a['means'])));ce=float(np.max(np.linalg.norm(act['covariance']-a['covariance'],axis=(1,2))/np.linalg.norm(a['covariance'],axis=(1,2))))
    assert me<2e-6 and ce<3e-6,(me,ce)
    assert np.max(abs(act['opacity']-a['opacity']))<1e-7
    eig0=np.linalg.eigvalsh(o['covariance']);eig=np.linalg.eigvalsh(a['covariance']);assert np.max(abs(eig-eig0)/eig0)<1e-12
    assert eig.min()>0
    error=0.;newt=np.empty((n,3))
    for lo in range(0,n,65536):
        hi=min(n,lo+65536);B=c['control'][c['kernel_curve_index'][lo:hi]];t=c['kernel_t'][lo:hi,None];v=1-t
        q=v**3*B[:,0]+3*v*v*t*B[:,1]+3*v*t*t*B[:,2]+t**3*B[:,3]
        d=3*v*v*(B[:,1]-B[:,0])+6*v*t*(B[:,2]-B[:,1])+3*t*t*(B[:,3]-B[:,2]);newt[lo:hi]=unit(d)
        error=max(error,float(np.max(abs(q-a['means'][lo:hi]))))
    assert error<1e-10,error
    oldt=unit((s['control'][s['control_index']]*s['derivative_basis'][:,:,None]).sum(1))
    disp=float((np.linalg.norm(a['means']-o['means'],axis=1)/s['pixel']).max())
    ang=float(np.degrees(np.arccos(np.clip(np.sum(newt*oldt,axis=1),-1,1))).max());assert disp<=.75+1e-9 and ang<=15+1e-6
    pair=s['piece_control_indices'];start=c['original_piece_start'];end=c['original_piece_stop']-1
    np.testing.assert_array_equal(c['control'][:,0],s['control'][pair[start,0]])
    np.testing.assert_array_equal(c['control'][:,3],s['control'][pair[end,1]])
    js(folder/'RELOAD_VERIFY.json',dict(all_checks_pass=True,kernels=n,fixed_PLY_fields_exact=True,fixed_NPZ_fields_exact=True,retained_geometry_exact=True,
       covariance_eigenvalues_relative_error=float(np.max(abs(eig-eig0)/eig0)),ply_means_max_abs=me,ply_covariance_relative=ce,
       curve_reconstruction_error=error,max_displacement_pixel=disp,max_rotation_deg=ang,original_support_endpoints_exact=True,
       cold_process=True,source_model_read=False,files={p.name:sha(p) for p in folder.iterdir() if p.is_file()}))
    return act

def main(scene):
    start=time.monotonic();check_budget(180);fmt,renderer=renderer_modules()
    cams=json.loads((OUT/'CAMERAS.json').read_text())[scene];dest=OUT/scene/'figures';dest.mkdir(exist_ok=True)
    arrays={};timings=[]
    for name in ('ORIGINAL','DIRECT','HOUGH'):
        asset=validate(scene,name)
        for c in cams:
            check_budget(180);st=time.monotonic();result=renderer.render(asset,c,background=CFG['background'],floor=CFG['render_floor'])
            image=result['rgb'];v=c['view'];save_image(dest/f'{v}_{name}.png',image);np.savez_compressed(dest/f'{v}_{name}_render.npz',rgb=image,alpha=result['alpha'])
            arrays[(v,name)]=image;timings.append(dict(method=name,view=v,seconds=time.monotonic()-st,kernels=len(asset['means'])))
            print('RENDERED',scene,v,name,round(timings[-1]['seconds'],2),flush=True)
    measures=[]
    for c in cams:
        v=c['view'];h,w=arrays[(v,'ORIGINAL')].shape[:2]
        board=Image.new('RGB',(w*3,h+84),'white');draw=ImageDraw.Draw(board)
        draw.text((12,8),f'{scene} / {v} | Complete dedicated line-Gaussian asset',fill='black')
        draw.text((12,28),'White background | fixed cameras, opacity and widths | no source-surface occlusion',fill='black')
        for j,name in enumerate(('ORIGINAL','DIRECT','HOUGH')):
            draw.text((j*w+12,57),name,fill='black');board.paste(Image.fromarray(np.uint8(np.round(np.clip(arrays[(v,name)],0,1)*255))),(j*w,84))
        board.save(dest/f'{v}_COMPARISON.png')
        for name in ('DIRECT','HOUGH'):
            delta=arrays[(v,name)]-arrays[(v,'ORIGINAL')]
            measures.append(dict(view=v,method=name,mean_abs_rgb_change=float(abs(delta).mean()),max_abs_rgb_change=float(abs(delta).max()),pixels_changed_over_1_255=int((abs(delta).max(2)>1/255).sum())))
        d=arrays[(v,'HOUGH')]-arrays[(v,'DIRECT')]
        measures.append(dict(view=v,method='HOUGH_MINUS_DIRECT',mean_abs_rgb_change=float(abs(d).mean()),max_abs_rgb_change=float(abs(d).max()),pixels_changed_over_1_255=int((abs(d).max(2)>1/255).sum())))
    js(OUT/scene/'RENDER_METRICS.json',dict(timings=timings,differences=measures,renderer='existing CPU EWA approximation, native line Gaussian fields',source_surface_occlusion=False,no_source_GS_loaded=True))
    js(OUT/scene/'COMPLETE.json',dict(complete=True,utc=now(),reload_checks_pass=True,full_asset=True,views=[c['view'] for c in cams],render_seconds=time.monotonic()-start))
    status=json.loads((OUT/'STATUS.json').read_text());states=status['scenes'];states[scene]='COMPLETE';state('SCENE_COMPLETE',scenes=states,scene=scene)
if __name__=='__main__':main(sys.argv[1])
