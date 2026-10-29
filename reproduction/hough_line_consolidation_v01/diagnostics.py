"""Diagnostics only: export fixed proposals and explain the real negative result."""
from pilotio import *
from core import fragments,sparse_hough
from real import board
from PIL import Image,ImageDraw

def main():
    guard(); d=OUT/'real_budgeted/scan24'; data=load_np(d/'input.npz'); meta=json.loads((d/'input_manifest.json').read_text()); fs=fragments(data)
    ids=np.concatenate([f['ids'] for f in fs if f['eligible']]); h=meta['h']; center=np.array(meta['center'])
    reg=json.loads((BASE/'REGISTRY.json').read_text())['scenes']['scan24']; c=next(c for c in reg['cameras'] if c['view']=='0000')
    original=Image.open(d/'figures/0000/C8_original_JOINT.png').convert('RGB'); items=[('Original C8 | joint occlusion',original)]
    palette=[(255,0,180),(0,220,255),(255,180,0),(50,230,60)]
    for method in ['H0','H1']:
        peaks,stats=sparse_hough(data,ids,weighted=method=='H1')
        scores=np.array([p[0] for p in peaks]); anchors=np.array([p[1] for p in peaks]); directions=np.array([p[2] for p in peaks])
        np.savez_compressed(d/method/'raw_vote_peaks.npz',score=scores,anchor_normalized=anchors,direction=directions,anchor_world=anchors*h+center)
        js(d/method/'raw_vote_metadata.json',dict(**stats,diagnostic_replay=True,parameters_changed=False,selected_final_hypotheses=0,note='Raw proposals exist; none pass whole-fragment support within shared 32 final-refiner attempts. No scientific retuning.'))
        im=original.copy();draw=ImageDraw.Draw(im)
        for i,(_,a,v) in enumerate(peaks[:4]):
            r=np.linalg.norm(np.cross(data['xyz'][ids]-a,v),axis=1); near=ids[r<=2]
            uv,z=project(data['xyz'][near]*h+center,c)
            for (xx,yy),zz in zip(uv,z):
                if zz>.2:draw.ellipse((xx-2,yy-2,xx+2,yy+2),fill=palette[i])
        items.append((method+' raw peak support | REJECTED',im))
    board(d/'figures/0000/NEGATIVE_RAW_PEAKS_FULL.jpg',items,'scan24 | Raw Hough votes did not produce accepted finite groups','Colored sample projections are X-RAY diagnostics. Final H0/H1 geometry equals original C8.',CFG['scan24_roi'])
    board(d/'figures/0000/NEGATIVE_RAW_PEAKS_ROI.png',[(label,im.crop(tuple(CFG['scan24_roi']))) for label,im in items],'scan24 | Rejected raw peak support','No accepted Hough group; no gap filled.')
    # A fixed seed/condition roster, not selected by which method looks best.
    rows=[]
    for case in CFG['synthetic_cases']:
        base=OUT/'synthetic/seed_0/clean'/case; x=load_np(base/'input.npz'); ims=[]
        original_x=x['xyz']; lo=original_x[:,:2].min(0)-3; span=np.maximum(original_x[:,:2].max(0)-lo+3,1)
        for method in ['B0','B1','B2','H0','H1']:
            g=load_np(base/method/'geometry.npz'); links=json.loads((base/method/'links.json').read_text())
            im=Image.new('RGB',(360,280),'white');dr=ImageDraw.Draw(im)
            def screen(points):return np.c_[10+(points[:,0]-lo[0])/span[0]*340,260-(points[:,1]-lo[1])/span[1]*240]
            for xx,yy in screen(original_x):dr.ellipse((xx-1,yy-1,xx+1,yy+1),fill=(190,190,190))
            for (xx,yy),gid in zip(screen(g['xyz']),g['groups']):
                col=(50,50,50) if gid<0 else palette[gid%len(palette)];dr.ellipse((xx-1,yy-1,xx+1,yy+1),fill=col)
            for link in links:
                p=screen(np.asarray(link['endpoints']));dr.line([tuple(p[0]),tuple(p[1])],fill=(255,0,180),width=1)
            ims.append((method+' | magenta = unconfirmed',im))
        target=OUT/'figures';target.mkdir(exist_ok=True)
        board(target/(case+'_seed0_clean.png'),ims,case+' | Synthetic backend XY diagnostic','Gray=input. All samples retained; magenta proposals are never confirmed or rendered as new geometry.')
    status('DIAGNOSTICS_DONE')
if __name__=='__main__': main()
