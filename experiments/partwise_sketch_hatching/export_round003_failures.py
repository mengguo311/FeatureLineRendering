"""List every baseline missing-support sample at the frozen 1.5px threshold."""
import run_round003 as r
import numpy as np
from PIL import Image, ImageDraw


def main():
    r.verify_lock(); r.resource_check()
    assert not (r.R/'MISSING_SUPPORT_SAMPLES.json').exists()
    s = dict(np.load(r.R/'samples.npz')); records = []; panels = []
    for kind, count in [('orbit', 36), ('zoom', 24)]:
        for i in range(count):
            z = np.load(r.R/'raw'/kind/f'{i:04d}.npz')
            bad = z['eligible_geometry'] & ~z['ambiguity'] & (z['distance'][0] > 1.5)
            indices = np.flatnonzero(bad)
            if not len(indices): continue
            for j in indices:
                owner = int(s['owner'][j])
                records.append({'trajectory': kind, 'frame': i, 'sample_global_index': int(j),
                                'stroke_id': str(s['stroke_ids'][owner]), 'part': int(s['parts'][j]),
                                'sample_within_stroke': int(j-s['offsets'][owner]),
                                'world_xyz': s['xyz'][j].tolist(), 'uv': z['uv'][j].tolist(),
                                'weight_world': float(s['weight'][j]),
                                'sample_depth': float(z['sample_depth'][j]),
                                'analytic_depth': float(z['expected_depth'][j]),
                                'same_id_support_distance_px': float(z['distance'][0, j]),
                                'same_id_support_offset_px': z['offset'][0, j].tolist()})
            im = Image.open(r.R/'frames'/kind/f'{i:04d}.png').convert('RGB')
            draw = ImageDraw.Draw(im)
            uv = z['uv'][indices]
            for x, y in uv: draw.ellipse((x-2, y-2, x+2, y+2), outline='red', width=1)
            lo = np.maximum(np.floor(uv.min(axis=0)).astype(int)-16, 0)
            hi = np.minimum(np.ceil(uv.max(axis=0)).astype(int)+17, 512)
            crop = im.crop((*lo, *hi)); crop.thumbnail((256, 256))
            panel = Image.new('RGB', (512, 286), 'white'); panel.paste(im.resize((256, 256)), (0, 30))
            panel.paste(crop, (256+(256-crop.width)//2, 30+(256-crop.height)//2))
            ImageDraw.Draw(panel).text((5, 8), f'{kind} {i:02d} | {len(indices)} missing support samples | full + native crop', fill='black')
            panels.append(panel)
    sheet = Image.new('RGB', (1024, ((len(panels)+1)//2)*286), 'white')
    for i, p in enumerate(panels): sheet.paste(p, ((i % 2)*512, (i//2)*286))
    sheet.save(r.R/'figures/missing_samples_all_views.png')
    result = {'scope': 'Every baseline eligible nonambiguous sample above frozen support radius; not whole-stroke disappearance or proven geometric root cause.',
              'sample_frame_count': len(records), 'affected_frame_count': len(panels),
              'affected_ids': sorted({x['stroke_id'] for x in records}), 'records': records}
    r.write_json(r.R/'MISSING_SUPPORT_SAMPLES.json', result)
    print({'sample_frame_count': len(records), 'affected_frames': len(panels), 'affected_ids': result['affected_ids']})


if __name__ == '__main__': main()
