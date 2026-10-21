"""Frozen unit009 image contacts and fully decoded fixed-camera edit video.

Reads completed renders; does not invoke rendering or regenerate any paths.
Historical contact/video-audit helpers are imported only as read-only APIs.
"""
from common import OUT, FFMPEG, core, json, native, np, sha, write_json
import shutil
import subprocess

from PIL import Image
from run_unit002 import contact
from validate_unit004 import audit_video


UNIT = OUT.parent / 'unit_009'
VIEWS = (30, 120, 210, 300)
VERSIONS = (('baseline', 'Before: 48 paths'), ('edited', 'After: 24 paths'))


def copy_new(source, destination):
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def contact_new(paths, labels, destination, **kwargs):
    if destination.exists():
        raise FileExistsError(destination)
    contact(paths, labels, destination, **kwargs)


def media():
    lock = json.loads((UNIT / 'SOURCE_LOCK.json').read_text())
    for filename, expected in lock['files'].items():
        if sha(filename) != expected:
            raise ValueError(f'frozen source/input changed: {filename}')
    config = json.loads((UNIT / 'outputs/edited/config.json').read_text())
    figures = UNIT / 'figures'
    figures.mkdir(parents=True, exist_ok=True)
    full, full_titles, crops, crop_titles, stem, stem_titles = [], [], [], [], [], []
    provenance = []
    for azimuth in VIEWS:
        camera_path = UNIT / 'outputs/baseline/renders' / f'{azimuth:03}.json'
        camera = json.loads(camera_path.read_text())['camera']
        _, parts = core.analytic_reference(config['asset'], camera)
        height, width = parts.shape
        if (width, height) != (512, 512):
            raise ValueError('frozen unit009 media requires 512x512 renders')
        for version, title in VERSIONS:
            source = UNIT / 'outputs' / version / 'renders' / f'{azimuth:03}.png'
            full.append(source)
            full_titles.append(f'{title} | az {azimuth}')
        for part, name in ((1, 'shade'), (2, 'stem'), (3, 'base')):
            y, x = np.where(parts == part)
            if not len(x):
                raise ValueError(f'analytic part {name} is absent at azimuth {azimuth}')
            box = (max(0, int(x.min()) - 8), max(0, int(y.min()) - 8),
                   min(width, int(x.max()) + 9), min(height, int(y.max()) + 9))
            for version, title in VERSIONS:
                source = UNIT / 'outputs' / version / 'renders' / f'{azimuth:03}.png'
                destination = figures / f'{version}_{azimuth:03}_{name}.png'
                enlarged = figures / f'{version}_{azimuth:03}_{name}_enlarged.png'
                if destination.exists() or enlarged.exists():
                    raise FileExistsError(destination)
                with Image.open(source) as image:
                    if image.size != (width, height):
                        raise ValueError(f'wrong image size: {source}')
                    crop = image.crop(box)
                    crop.save(destination)
                    scale = 384 / max(crop.size)
                    size = tuple(max(1, round(value * scale)) for value in crop.size)
                    # Nearest-neighbor zoom exposes original raster samples;
                    # it does not smooth or reconstruct the thin stem hatches.
                    crop.resize(size, Image.Resampling.NEAREST).save(enlarged)
                crops.append(enlarged)
                crop_titles.append(f'{title} | {name} {azimuth}')
                if part == 2:
                    stem.append(enlarged)
                    stem_titles.append(f'{title} | stem az {azimuth}')
                provenance.append(dict(source=str(source), source_sha256=sha(source),
                                       camera=str(camera_path), box_xyxy=box, part=part,
                                       original_crop=str(destination), enlarged_crop=str(enlarged),
                                       zoom_scale=scale, interpolation='nearest'))
    contact_new(full, full_titles, figures / 'full_lamp_comparison.png', columns=2, thumb=512)
    contact_new(stem, stem_titles, figures / 'stem_comparison.png', columns=2, thumb=384)
    contact_new(crops, crop_titles, figures / 'all_parts_comparison.png', columns=6, thumb=384)

    frames = UNIT / 'frames/edit'
    if frames.exists():
        raise FileExistsError(frames)
    frames.mkdir(parents=True)
    sources, labels = [], []
    for index in range(24):
        version, title = VERSIONS[int(index >= 12)]
        destination = frames / f'{index:04}.png'
        copy_new(UNIT / 'outputs' / version / 'renders/030.png', destination)
        sources.append(destination)
        labels.append(f'{title} | frame {index:02}')
    contact_new(sources, labels, figures / 'edit_all_frames.png', columns=6, thumb=256)
    contact_new([sources[index] for index in (0, 12, 23)],
                ['First: Before 48', 'Middle: After 24', 'Last: After 24'],
                figures / 'edit_first_middle_last.png', columns=3, thumb=512)
    video = UNIT / 'videos/edit.mkv'
    if video.exists():
        raise FileExistsError(video)
    video.parent.mkdir(parents=True, exist_ok=True)
    runtime = UNIT / 'runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    command = [FFMPEG, '-v', 'error', '-threads', '1', '-filter_threads', '1',
               '-framerate', '12', '-i', str(frames / '%04d.png'), '-c:v', 'ffv1',
               '-level', '3', '-threads', '1', '-pix_fmt', 'bgr0', str(video)]
    encoded = subprocess.run(command, capture_output=True, timeout=90)
    (runtime / 'media_encode.log').write_bytes(encoded.stderr)
    write_json(UNIT / 'VIDEO_ENCODING.json', dict(command=command, returncode=encoded.returncode,
               frames=24, fps=12, size=[512, 512], edit_after_frame=11,
               scope='Fixed camera discrete edit, 12 before + 12 after; not orbit or temporal stability'))
    encoded.check_returncode()
    validation = audit_video(UNIT, FFMPEG, 'edit', sources)
    write_json(UNIT / 'VIDEO_VALIDATION.json', validation)
    write_json(UNIT / 'MEDIA_PROVENANCE.json', dict(crops=provenance,
               masks='Independent analytic lamp part labels using saved baseline cameras',
               changed_style='Stem density 48 -> 24 retained original paths',
               source_frames={str(path): sha(path) for path in sources},
               video_sha256=sha(video), all_24_frames_decoded_exact=validation['all_rgb_exact']))
    return dict(stage='media', done=True, decoded_frames=validation['decoded_frames'],
                all_rgb_exact=validation['all_rgb_exact'])


if __name__ == '__main__':
    try:
        print(json.dumps(native(media()), allow_nan=False))
    except Exception as error:
        failure = UNIT / 'MEDIA_FAILURE.json'
        if not failure.exists():
            write_json(failure, dict(error_type=type(error).__name__, message=str(error),
                                    partial_outputs_retained=True))
        raise
