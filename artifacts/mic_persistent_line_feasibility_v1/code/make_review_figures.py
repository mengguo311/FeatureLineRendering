"""Presentation of sealed run outputs only; no fitting or input selection."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from pipeline_io import ART, OUT, CFG, load_asset, sha, write_json


def main():
    load_asset(ART/'ASSET.json')
    paths = json.loads((OUT/'CONSTRUCTION_PATHS.json').read_text())['paths']
    diagnostics = json.loads((OUT/'MATCH_DIAGNOSTICS.json').read_text())
    selected = {p for item in diagnostics['attempts'] for p in item['path_ids']}
    sheet = Image.new('RGB', (1600, 1664), 'white')
    for i, key in enumerate(CFG['construction']):
        frame = Image.new('RGB', (800, 832), 'white')
        with Image.open(OUT/'frames'/key/'rgb.png') as source:
            frame.paste(source, (0, 32))
        draw = ImageDraw.Draw(frame)
        draw.text((8, 6), f'{key}: {len(paths[key])} automatic 2D paths (not 3D)', fill='black')
        draw.text((8, 18), 'Gray = retained scaffold; magenta = failed cycle candidate', fill='black')
        for p in paths[key]:
            xy = [(float(x), float(y)+32) for x, y in p['raw_points']]
            draw.line(xy, fill=(160, 160, 160), width=2)
        for p in paths[key]:
            if p['id'] in selected:
                xy = [(float(x), float(y)+32) for x, y in p['raw_points']]
                draw.line(xy, fill=(220, 0, 160), width=5)
        sheet.paste(frame, ((i%2)*800, (i//2)*832))
    target = ART/'media/construction_paths_and_failed_cycle.jpg'
    sheet.resize((1200, 1248), Image.Resampling.LANCZOS).save(target, quality=90)
    manifest = json.loads((ART/'FRAME_AUDIT.json').read_text())
    rows = [f for f in manifest['frames'] if f['key'] in CFG['evaluation']]
    c_sheet = Image.new('RGB', (1600, 208*4), 'white')
    for i, rec in enumerate(rows):
        with Image.open(rec['outputs']['panel']) as im:
            c_sheet.paste(im.resize((800, 208), Image.Resampling.LANCZOS), ((i%2)*800, (i//2)*208))
    ctarget = ART/'media/C8_contact.jpg'
    c_sheet.save(ctarget, quality=90)
    record = dict(scope='Presentation of already sealed/run outputs; no geometry or thresholds modified',
                  automatic_2d_diagnostic=str(target), selected_candidate_ids=sorted(selected),
                  selected_candidate_rule='all real triplet-cycle attempts, without result-based subset selection',
                  C_contact=str(ctarget), camera_keys=[r['key'] for r in rows],
                  files={str(p): sha(p) for p in [target, ctarget]})
    write_json(ART/'REVIEW_FIGURES.json', record)
    print('Review figures complete')


if __name__ == '__main__':
    main()
