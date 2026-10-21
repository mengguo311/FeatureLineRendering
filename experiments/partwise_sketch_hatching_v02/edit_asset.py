"""Runnable part editor for saved mesh/barycentric assets; explicit CPU latency."""
from common import *
import argparse
import copy
import time
from renderer import render
from PIL import Image

def apply_edit(mesh, strokes, cfg, part, angle=0., width=None, spacing_scale=1., length_scale=1., crossing=None):
    """Regenerate only target part when path parameters change; preserve other IDs.

    Spacing scale controls area seed density via count / scale**2. It is a
    density proxy, not a minimum-distance/Poisson spacing guarantee.
    """
    if part not in (1,2,3) or spacing_scale <= 0 or length_scale <= 0:
        raise ValueError('valid part and positive scales required')
    changed = copy.deepcopy(cfg)
    if width is not None: changed['widths_by_part'][str(part)] = float(width)
    regenerate = angle != 0 or spacing_scale != 1 or length_scale != 1 or crossing is not None
    start = time.perf_counter()
    if regenerate:
        counts = copy.deepcopy(cfg['strokes']['counts_by_part'])
        counts[str(part)] = max(1, round(counts[str(part)] / spacing_scale**2))
        changed['strokes']['counts_by_part'] = counts
        changed['strokes']['length_by_part'][str(part)] *= length_scale
        style = 'mixed' if crossing is None else ('cross' if crossing else 'parallel')
        new = walker.generate_strokes(mesh, changed, style, only_part=part, angle=angle, counts=counts)
        edited = sorted([s for s in strokes if s['part'] != part] + new, key=lambda s:s['id'])
    else:
        edited = list(strokes)
    receipt = dict(part=part,angle_delta_deg=angle,width_px=width,spacing_scale=spacing_scale,
                   length_scale=length_scale,crossing=crossing,regenerated_parts=[part] if regenerate else [],
                   regeneration_seconds=time.perf_counter()-start,
                   non_target_exact=core.stroke_digest([s for s in strokes if s['part']!=part]) == core.stroke_digest([s for s in edited if s['part']!=part]))
    return edited, changed, receipt

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--part',type=int,choices=[1,2,3],required=True)
    ap.add_argument('--angle',type=float,default=0.)
    ap.add_argument('--width',type=float)
    ap.add_argument('--spacing-scale',type=float,default=1.)
    ap.add_argument('--length-scale',type=float,default=1.)
    ap.add_argument('--crossing',choices=['on','off'])
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    output=Path(args.output).resolve()
    if OUT not in output.parents: raise ValueError('output must be below current unit')
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    mesh,strokes,cfg=load_inputs()
    start=time.perf_counter()
    edited,config,record=apply_edit(mesh,strokes,cfg,args.part,args.angle,args.width,args.spacing_scale,args.length_scale,
                                  None if args.crossing is None else args.crossing=='on')
    result=render(mesh,edited,config)
    record['regeneration_and_render_seconds']=time.perf_counter()-start
    Image.fromarray(np.uint8(np.rint(result['image']*255))).save(output/'image.png')
    core.save_strokes(output/'strokes.npz',edited)
    write_json(output/'config.json',config)
    write_json(output/'EDIT.json',record)
    print(json.dumps(native(record)))

if __name__=='__main__': main()
