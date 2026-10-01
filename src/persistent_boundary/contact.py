"""Present only preregistered TRAIN-F frames for intent annotation; no C/DEV/TEST reads."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

F_INDICES = (1, 14, 27, 41, 53, 67, 79, 93)


def build_f_contact_sheet(root, scene, output, tile_width=400, columns=4):
    """Decode the fixed F list and return exact source paths for access audit."""
    if scene not in ('lego', 'chair'):
        raise ValueError('only preregistered Lego/Chair TRAIN scenes allowed')
    root, output = Path(root), Path(output)
    metadata = json.loads((root / 'data/full' / scene / 'transforms_train.json').read_text())
    tiles, sources = [], []
    for index in F_INDICES:
        name = Path(metadata['frames'][index]['file_path']).name
        if name != f'r_{index}':
            raise ValueError(f'camera index/name disagreement for F {index}: {name}')
        source = root / 'data/full' / scene / 'train' / f'r_{index}.png'
        with Image.open(source) as raw:
            rgba = raw.convert('RGBA')
        background = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        height = round(rgba.height * tile_width / rgba.width)
        tile = background.convert('RGB').resize((tile_width, height), Image.LANCZOS)
        tiles.append(tile)
        sources.append(str(source))
    label_height = 24
    image_height = tiles[0].height
    if any(t.height != image_height for t in tiles):
        raise ValueError('nonuniform TRAIN-F image shape')
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * tile_width, rows * (image_height + label_height)), 'white')
    draw = ImageDraw.Draw(sheet)
    for cell, (index, tile) in enumerate(zip(F_INDICES, tiles)):
        x = (cell % columns) * tile_width
        y = (cell // columns) * (image_height + label_height)
        draw.text((x + 4, y + 4), f'{scene} TRAIN-F r_{index}', fill='black')
        sheet.paste(tile, (x, y + label_height))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    return {'scene': scene, 'frame_indices': list(F_INDICES), 'sources': sources,
            'contact_sheet': str(output), 'size': list(sheet.size), 'role': 'annotation_input_only'}
