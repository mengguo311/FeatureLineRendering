"""Freeze TRAIN byte inventory before any model acquisition; no image decoding."""
import hashlib
import json
from pathlib import Path
import struct
import datetime

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts/hybrid_raster_trained_models_v1'
SCENES = ['hotdog', 'materials', 'mic', 'ship']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def record(path):
    path = Path(path)
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def main():
    scenes = {}
    for scene in SCENES:
        root = Path('/home/u00134/cglib/data/full') / scene
        path = root / 'transforms_train.json'
        meta = json.loads(path.read_text())
        assert len(meta['frames']) == 100
        files = []
        for i, frame in enumerate(meta['frames']):
            rel = Path(frame['file_path'])
            assert not rel.is_absolute() and '..' not in rel.parts and rel.parts[0] == 'train'
            image = root / (str(rel) + '.png')
            assert image.resolve().is_relative_to((root / 'train').resolve())
            with image.open('rb') as f:
                header = f.read(24)
            assert header[:8] == b'\x89PNG\r\n\x1a\n'
            width, height = struct.unpack('>II', header[16:24])
            assert (width, height) == (800, 800)
            files.append(dict(index=i, relative_path=str(rel) + '.png', width=width, height=height,
                              **record(image)))
        scenes[scene] = dict(metadata=record(path), train_images=files, train_count=100,
                             source_pixels_decoded=False, camera_angle_x=meta['camera_angle_x'],
                             checkpoint_destinations={str(n): str(ROOT / f'out/hybrid_raster_trained_models_v1/training/{scene}/seed_1729/checkpoints/point_cloud/iteration_{n}/point_cloud.ply') for n in [7000, 30000]})
    prior = Path('/home/u00134/3dgs_line/tier1')
    references = [prior / 'scripts/multiscene_train_entry.py', prior / 'scripts/run_multiscene_training.py']
    references += [prior / 'out/multiscene_foundation/training/lego/seed_1729' / p for p in ['entry.json', 'manifest.json', 'checkpoints/cfg_args']]
    references += [ROOT / 'artifacts/hybrid_raster_extra_models_v1' / p for p in ['PROTOCOL.md', 'REPORT.md', 'INPUTS.json', 'INHERITED_LOCK.json']]
    old = Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2')
    references += [old / 'artifacts/hybrid_raster_evidence_v2' / p for p in ['PROTOCOL.md', 'REPORT.md', 'REPRODUCE.md']]
    lockpath = old / 'out/hybrid_raster_evidence_v2/LOCK.json'
    lock = json.loads(lockpath.read_text())
    references += [old / p for p in lock['config']['sources']]
    references += [old / 'artifacts/direct_curve_global_fit_probe/freeze.py', lockpath]
    value = dict(schema='train-freeze-npr-inputs-v1', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 base_commit='fef9b8566b9fc3aa42a8639b336987b302041c99', selected_scenes=SCENES,
                 expected_frames=196, frames_per_scene=49, F=[1,14,27,41,53,67,79,93], C=[7,21,33,47,59,73,86,99],
                 scenes=scenes, references=[record(p) for p in references],
                 predeclared_cameras=record(ART / 'transport/PREDECLARED_CAMERAS.json'),
                 inherited_lock=record(lockpath), scientific_parameter_hash=lock['parameter_hash'],
                 C_scope='All C participate in photometric GS TRAIN; held out only from NPR fitting. No blind generalization claim.',
                 arc_resolution='Deterministic checkpoint quantile-center arc C7->C33, 33 unique; exact matrices commit/push after checkpoint freeze and before any NPR render.')
    dest = ART / 'INPUTS.json'
    if dest.exists():
        raise RuntimeError('Refuse to overwrite frozen INPUTS')
    dest.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    (ART / 'INHERITED_LOCK.json').write_bytes(lockpath.read_bytes())
    print(json.dumps(dict(path=str(dest), sha256=sha(dest), scenes=SCENES, train_files=400)))


if __name__ == '__main__':
    main()
