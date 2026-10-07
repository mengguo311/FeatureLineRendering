"""Stage-1 metadata inventory only. No scientific imports, image decoding or GPU calls."""
from pathlib import Path
import collections
import datetime
import json
import struct

OUT = Path(__file__).resolve().parents[2] / "artifacts/radegs_paper_reproduction_v01/evidence/local_metadata.json"
TRAIN_ROOT = Path('/home/u00134/3dgs_line/hybrid_raster_trained_models_v1/out/hybrid_raster_trained_models_v1/training')
REAL_ROOT = Path('/home/u00134/3dgs_line/tier1/data/realcap')


def image_header(path):
    with path.open('rb') as f:
        b = f.read(26)
        if b[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', b[16:24])
            return {'width': w, 'height': h, 'format': 'PNG', 'bit_depth': b[24], 'color_type': b[25]}
        f.seek(0)
        if f.read(2) != b'\xff\xd8':
            return {'format': 'unrecognized'}
        while True:
            byte = f.read(1)
            if not byte:
                return {'format': 'JPEG', 'error': 'no SOF'}
            if byte != b'\xff':
                continue
            marker = f.read(1)
            while marker == b'\xff':
                marker = f.read(1)
            if marker in (b'\xd8', b'\xd9'):
                continue
            n = struct.unpack('>H', f.read(2))[0]
            if marker[0] in [0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf]:
                depth, h, w, channels = struct.unpack('>BHHB', f.read(6))
                return {'width': w, 'height': h, 'format': 'JPEG', 'bit_depth': depth, 'channels': channels}
            f.seek(n - 2, 1)


def ply_header(p):
    if not p.exists():
        return {'path': str(p), 'exists': False}
    lines = []
    with p.open('rb') as f:
        for _ in range(256):
            line = f.readline(1024).decode('ascii', errors='replace').rstrip()
            lines.append(line)
            if line == 'end_header':
                break
    return {'path': str(p), 'exists': True, 'bytes': p.stat().st_size, 'header': lines, 'body_read': False}


def colmap_metadata(root):
    p = root / 'sparse/0'
    record = {'path': str(root), 'files': {x.name: x.stat().st_size for x in p.iterdir() if x.is_file()}}
    models = {0: ('SIMPLE_PINHOLE', 3), 1: ('PINHOLE', 4), 2: ('SIMPLE_RADIAL', 4), 3: ('RADIAL', 5), 4: ('OPENCV', 8), 5: ('OPENCV_FISHEYE', 8)}
    cameras = []
    with (p / 'cameras.bin').open('rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]
        for _ in range(n):
            cid, mid, w, h = struct.unpack('<iiQQ', f.read(24))
            name, count = models[mid]
            params = struct.unpack('<' + 'd' * count, f.read(8 * count))
            cameras.append({'id': cid, 'model_id': mid, 'model': name, 'width': w, 'height': h, 'params': params})
    record['cameras'] = cameras
    entries = []
    with (p / 'images.bin').open('rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]
        for _ in range(n):
            fields = struct.unpack('<idddddddi', f.read(64))
            name = bytearray()
            while True:
                c = f.read(1)
                if not c or c == b'\0':
                    break
                name.extend(c)
            points = struct.unpack('<Q', f.read(8))[0]
            f.seek(points * 24, 1)
            entries.append({'id': fields[0], 'camera_id': fields[-1], 'name': name.decode(), 'qvec_shape': [4], 'tvec_shape': [3], 'points2d_count': points})
        record['images_bin_consumed_bytes'] = f.tell()
    record['registered_image_count'] = len(entries)
    record['registered_image_sample'] = entries[:3]
    with (p / 'points3D.bin').open('rb') as f:
        record['sparse_point_header_count'] = struct.unpack('<Q', f.read(8))[0]
    images = sorted(x for x in (root / 'images').iterdir() if x.suffix.lower() in ['.jpg', '.jpeg', '.png'])
    record['image_file_count'] = len(images)
    record['missing_registered_images'] = [e['name'] for e in entries if not (root / 'images' / e['name']).is_file()]
    hist = collections.Counter(json.dumps(image_header(x), sort_keys=True) for x in images)
    record['all_image_header_histogram'] = [{'header': json.loads(k), 'count': v} for k, v in hist.items()]
    record['geometry_gt_candidates'] = {name: (root / name).exists() for name in [root.name.title()+'.ply',root.name.title()+'.json',root.name.title()+'_COLMAP_SfM.log',root.name.title()+'_trans.txt']}
    record['pointcloud_ply'] = ply_header(p / 'points3D.ply')
    return record


def synthetic_subset(scene):
    root = TRAIN_ROOT / scene / 'seed_1729/data'
    rec = {'scene': scene, 'path': str(root), 'classification': 'existing_vanilla_training_subset_not_full_benchmark'}
    rec['direct_entries'] = [{'name': p.name, 'mode': oct(p.lstat().st_mode & 0o777), 'symlink_target': str(p.readlink()) if p.is_symlink() else None} for p in root.iterdir()]
    rec['split_files'] = {split: (root / ('transforms_' + split + '.json')).is_file() for split in ['train', 'val', 'test']}
    data = json.loads((root / 'transforms_train.json').read_text())
    rec['metadata_keys'] = list(data)
    rec['frame_count'] = len(data['frames'])
    rec['camera_angle_x'] = data['camera_angle_x']
    rec['first_frame_keys'] = list(data['frames'][0])
    rec['all_transforms_are_4x4'] = all(len(x['transform_matrix']) == 4 and all(len(row) == 4 for row in x['transform_matrix']) for x in data['frames'])
    # Only the explicitly linked TRAIN directory under the inventory roots is followed.
    # No traversal of the source's siblings, VAL, TEST, or other /home users.
    rec['symlink_scope'] = 'follow explicit owned train link only; no source parent traversal'
    images = sorted((root / 'train').glob('*.png'))
    rec['train_png_count'] = len(images)
    rec['missing_frame_files'] = [x['file_path'] for x in data['frames'] if not (root / (x['file_path'] + '.png')).is_file()]
    hist = collections.Counter(json.dumps(image_header(x), sort_keys=True) for x in images)
    rec['all_image_header_histogram'] = [{'header': json.loads(k), 'count': v} for k, v in hist.items()]
    rec['cached_initialization_ply'] = ply_header(root / 'points3d.ply')
    rec['trained_checkpoint'] = ply_header(TRAIN_ROOT / scene / 'seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply')
    return rec


def main():
    out = {'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'method': 'stdlib file enumeration, struct headers, JSON schema only; no pixel decoding, tensor imports, numerical experiments or large-file hashing', 'real_scenes': [], 'synthetic_subsets': [], 'other_checkpoint_headers': []}
    for relative in ['tandt/truck', 'tandt/train', 'db/playroom', 'db/drjohnson']:
        out['real_scenes'].append(colmap_metadata(REAL_ROOT / relative))
    for scene in ['hotdog', 'materials', 'mic', 'ship']:
        out['synthetic_subsets'].append(synthetic_subset(scene))
    for scene in ['lego', 'chair', 'ship', 'truck']:
        out['other_checkpoint_headers'].append(ply_header(Path('/home/u00134/3dgs_line/tier1/out') / ('2dgs_' + scene) / 'point_cloud/iteration_30000/point_cloud.ply'))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print('Written', OUT)
    for r in out['real_scenes']:
        print(r['path'], r['image_file_count'], r['registered_image_count'], r['all_image_header_histogram'])
    for r in out['synthetic_subsets']:
        print(r['scene'], r['frame_count'], r['split_files'], r['all_image_header_histogram'])


if __name__ == '__main__':
    main()
