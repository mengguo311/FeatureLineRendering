#!/usr/bin/env python3
"""Layout-only native-resolution G1 mechanism contact sheets."""
from pathlib import Path
import numpy as np
import cv2


def mechanism_maps(raw,native):
    d=lambda k:raw['diagnostics.'+k]
    l=lambda k:raw['layers.'+k]
    alpha=native['native_alpha'];A=d('A');off=raw['events.offsets'];sizes=np.diff(off)
    first=np.zeros(len(sizes));valid=sizes>0
    first[valid]=((raw['events.ids'][off[:-1][valid]].astype('i8')*2654435761)%256)/255
    maps=[('native alpha',alpha),('captured alpha',A),('missing native alpha',alpha-A),('replay tail alpha',l('tail_alpha')),
          ('K /128',sizes.reshape(A.shape)/128),('first ID hash (not evidence)',first.reshape(A.shape)),
          ('front depth /8',d('z_front')/8),('expected depth /8',d('z_mean')/8),
          ('median depth /8',d('z_50')/8),('depth variance /.1',d('z_var')/.1),('ID entropy /log128',d('H_id')/np.log(128)),
          ('ID Hellinger turnover',d('D_id')),('W1/local scale (display clipped)',d('D_zdist')),('local scale /.1',l('local_scale')/.1),
          ('layer count /8',l('layer_count')/8),('layer overflow alpha',l('overflow_mass'))]
    maps.extend((f'layer {i+1} mass',l('retained_mass')[...,i]) for i in range(4))
    maps.extend((f'layer {i+1} depth /8',l('retained_depth')[...,i]/8) for i in range(4))
    maps.extend([('layer count transition /8',d('layer_count_transition')/8),('front mass transition',d('front_mass_transition')),
                 ('stable split support',d('stable_split')),('directed ordering consistency',d('ordering_consistency')),
                 ('native foreground alpha >=.5',(alpha>=.5).astype('f8')),('target .90 reached',(A>=.9*alpha).astype('f8')),
                 ('native final transmittance',1-alpha),('retained/native alpha',l('retained_mass').sum(-1)/np.maximum(alpha,1e-12))])
    return maps


def diagnostic_sheet(path,views):
    rows=[]
    for items in zip(*views):
        tiles=[]
        for title,field in items:
            h,w=field.shape[:2];tile=np.full((h+44,w,3),255,'u1')
            rgb=np.repeat(field[...,None],3,axis=-1) if field.ndim==2 else field
            tile[44:]=np.round(np.clip(rgb,0,1)*255).astype('u1')[...,::-1]
            cv2.putText(tile,title,(8,29),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,0,0),1,cv2.LINE_AA)
            tiles.append(tile)
        rows.append(np.hstack(tiles))
    if not cv2.imwrite(str(path),np.vstack(rows),[cv2.IMWRITE_PNG_COMPRESSION,6]):raise RuntimeError('PNG encoding failed')


def main():
    import argparse,hashlib,json,sys
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args();run=args.run.resolve();root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
    from src.foundation import freeze_json,restrict_filesystem
    if not (run/'GATES.json').is_file():raise ValueError('complete G1 run required')
    output=run/'diagnostics';output.mkdir(exist_ok=False)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    science=sorted(p for folder in ['native','raw','final'] for p in (run/folder).glob('*') if p.suffix in ['.json','.npz'])+[run/'NORMALIZATION.json',run/'GATES.json']
    sources=[Path(__file__).resolve(),*sorted((root/'src').glob('*.py'))]
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys')]
    readonly=[*science,*sources,*[p.resolve() for p in runtime if p.exists()]]
    policy=dict(readonly=[str(p) for p in readonly],writable=[str(output),'/dev'],source_hashes={str(p):sha(p) for p in sources},bootstrap_files=[str(run/f) for f in ['native','raw','final']],stage='G1_LAYOUT',photographs=[])
    freeze_json(output/'allowlist.json',policy);restrict_filesystem(readonly,[output,'/dev'])
    before={str(p.relative_to(run)):sha(p) for p in science};panels=[]
    for scene in ['lego','chair','drums','ficus']:
        views=[]
        for view in [1,27,53,79]:
            with np.load(run/'raw'/f'{scene}_{view}_full.npz') as raw,np.load(run/'native'/f'{scene}_{view}.npz') as native:
                views.append([(f'{scene} v{view} {name}',field) for name,field in mechanism_maps(raw,native)])
        for group in range(4):
            path=output/f'{scene}_mechanisms_{group}.png'
            diagnostic_sheet(path,[maps[group*8:group*8+8] for maps in views]);panels.extend(title for maps in views for title,field in maps[group*8:group*8+8])
            print('G1 mechanism sheet',path.name,flush=True)
        del views
    after={str(p.relative_to(run)):sha(p) for p in science}
    if before!=after:raise ValueError('layout changed scientific bytes')
    record=dict(science_unchanged=True,science_sha256=before,panels=panels,png_sha256={p.name:sha(p) for p in sorted(output.glob('*.png'))},display='Native resolution, fixed scales in labels, grayscale clipped only for display; raw arrays unchanged.')
    (output/'LAYOUT.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')


if __name__=='__main__':main()
