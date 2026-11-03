"""Full-row delivery preserving the replayed control versions."""
from runtime_io import *
from pair_delivery import export_overlap,enrich
from paired_delivery import evidence_rows
from scene_policy import diagnostics

def crop_all(paths,outputs):
    images=[]
    for path in paths:
        with Image.open(path) as im:images.append(im.convert('RGB'))
    arr=[np.asarray(im) for im in images]
    assert all(x.shape==arr[0].shape for x in arr)
    mask=np.logical_or.reduce([np.any(x<254,axis=2) for x in arr]);yy,xx=np.where(mask)
    if not len(xx):return dict(empty=True,bbox=None,crops=[],native_paths=list(map(str,paths)))
    h,w=mask.shape;box=[max(0,int(xx.min())-16),max(0,int(yy.min())-16),min(w,int(xx.max())+17),min(h,int(yy.max())+17)]
    for im,out in zip(images,outputs):
        crop=im.crop(box);crop=crop.resize((crop.width*4,crop.height*4),Image.Resampling.NEAREST)
        if not Path(out).exists():atomic(out,lambda f,im=crop:im.save(f,format='PNG'))
    return dict(empty=False,bbox=box,scale=4,interpolation='nearest',touches_native_boundary=bool(xx.min()==0 or yy.min()==0 or xx.max()==w-1 or yy.max()==h-1),crops=list(map(str,outputs)),native_paths=list(map(str,paths)))

def render_diagnostics(unit,c,d,saved,selection,render,cams,guard,binding):
    base=Path(unit)/('scenes/'+c['scene']);root=base/'diagnostics';root.mkdir(parents=True,exist_ok=True)
    if not (root/'SELECTION.json').exists():js(root/'SELECTION.json',selection)
    images={a:[] for a in saved};crops=[]
    for case in selection['cases']:
        guard();core=evidence_rows(d,case['core_carriers']);halo=evidence_rows(d,case['evidence_carriers'])
        rowpath=root/(case['case_id']+'_ROWS.npz')
        if not rowpath.exists():nz(rowpath,core_rows=core,evidence_rows=halo,core_carriers=np.array(case['core_carriers']),evidence_carriers=np.array(case['evidence_carriers']),incident_record_ids=np.array(case['incident_record_ids']))
        for kind,rr in [('GROUP',core),('CONTEXT',halo)]:
            for cam in cams:
                pair=[];outc=[]
                for arm,(m,_) in saved.items():
                    guard();out=base/'stages'/arm/'diagnostics';out.mkdir(parents=True,exist_ok=True)
                    name=case['case_id']+'_'+kind+'_'+cam['view'];path=out/(name+'.png');pair.append(path);outc.append(out/(name+'_CROP4.png'))
                    if not path.exists():
                        sub={k:d['asset'][k][rr] for k in ('means','covariance','opacity')};sub['colors']=colors(m['edge_id'][rr])
                        save_image(path,render(sub,cam,(1,1,1),.0144)['rgb'])
                    images[arm].append(str(path.relative_to(base/'stages'/arm)))
                guard();receipt=crop_all(pair,outc);receipt.update(case_id=case['case_id'],kind=kind,view=cam['view']);crops.append(receipt)
                if not receipt['empty']:
                    for arm,path in zip(saved,outc):images[arm].append(str(path.relative_to(base/'stages'/arm)))
        # Versioned diagnostic progress; complete prior cases survive later failure.
        cp=root/(case['case_id']+'_CHECKPOINT.json')
        if not cp.exists():js(cp,dict(complete=True,config_sha256=binding,rows_sha256=sha(rowpath),images={str(p.relative_to(unit)):sha(p) for a in saved for p in (base/'stages'/a/'diagnostics').glob(case['case_id']+'*.png')}))
    if not (root/'CROPS.json').exists():js(root/'CROPS.json',dict(records=crops,rule='union RGB8<254, pad16 clip 4xnearest; no camera change'))
    return images
