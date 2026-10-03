"""Fixed-world line rendering and complete, uncropped 49-camera media."""
import hashlib
import json
from pathlib import Path
import subprocess
import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

import fields
from pipeline_io import ART, OUT, CFG, SOURCE, load_asset, load_view, event, sha, write_json, geometry_hash


def project_independent_controls(xyz, camera):
    # Rendering transform kept direct so only geometry and calibration determine it.
    w = np.asarray(camera['w2c'], dtype=float)
    q = np.asarray(xyz, dtype=float) @ w[:3, :3].T+w[:3, 3]
    h = q @ np.asarray(camera['native_K'], dtype=float).T
    uv = h[:, :2]/np.where(np.abs(h[:, 2:3]) > 1e-15, h[:, 2:3], 1e-15)
    return uv, q[:, 2]


def paint(image, paths, camera, native, *, diagnostic=False):
    """Rasterize exact projected control segments; interpolate reciprocal Z.

    Camera near-plane clipping and depth-only per-pixel visibility do not modify
    stored vertices. A/C evidence is unavailable to this function.
    """
    output = image.copy()
    w = np.asarray(camera['w2c'], dtype=float)
    k = np.asarray(camera['native_K'], dtype=float)
    near = CFG['visibility']['near_plane']
    totals = dict(raster_samples=0, visible=0, occluded=0, uncertain=0, clipped_segments=0)
    for path in paths:
        xyz = np.asarray(path['controls_xyz'], dtype=float)
        cam = xyz @ w[:3, :3].T+w[:3, 3]
        color = CFG['render']['proposal_diagnostic_rgb'] if diagnostic else path['color_rgb']
        width = CFG['render']['fixed_width_px'] if diagnostic else int(path['width_px'])
        for left, right in zip(cam[:-1], cam[1:]):
            a, b = left.copy(), right.copy()
            if a[2] <= near and b[2] <= near:
                continue
            if a[2] <= near:
                a += ((near-a[2])/(b[2]-a[2]))*(b-a)
            if b[2] <= near:
                b += ((near-b[2])/(a[2]-b[2]))*(a-b)
            h = np.stack([a, b]) @ k.T
            uv = h[:, :2]/h[:, 2:3]
            clipped, first, last = cv2.clipLine((0, 0, 800, 800),
                tuple(np.clip(np.rint(uv[0]), -2**30, 2**30).astype(int)),
                tuple(np.clip(np.rint(uv[1]), -2**30, 2**30).astype(int)))
            if not clipped:
                continue
            totals['clipped_segments'] += 1
            mask = np.zeros((800, 800), np.uint8)
            cv2.line(mask, first, last, 255, width, cv2.LINE_8)
            yy, xx = np.nonzero(mask)
            if diagnostic:
                output[yy, xx] = color
                continue
            pixels = np.stack([xx, yy], axis=1).astype(float)
            delta = uv[1]-uv[0]
            t = np.clip(((pixels-uv[0]) @ delta)/max(float(delta @ delta), 1e-24), 0, 1)
            z = 1/((1-t)/a[2]+t/b[2])
            vis = fields.classify_visibility(native, pixels, z, CFG)
            shown = vis['visible']
            output[yy[shown], xx[shown]] = color
            totals['raster_samples'] += len(xx)
            for key in ['visible', 'occluded', 'uncertain']:
                totals[key] += int(vis[key].sum())
    return output, totals


def ink_image(ink):
    gray = np.rint(255*(1-np.clip(ink, 0, 1))).astype(np.uint8)
    return np.repeat(gray[..., None], 3, axis=2)


def save_png(path, array):
    Image.fromarray(array).save(path)


def panel(images, key, accepted_count):
    labels = ['RGB: cached SH0 / white background', f'pure fixed3D: {accepted_count} accepted paths',
              'residual2D: full original C', 'hybrid: full C + accepted fixed3D']
    result = Image.new('RGB', (3200, 832), 'white')
    draw = ImageDraw.Draw(result)
    for i, (array, label) in enumerate(zip(images, labels)):
        result.paste(Image.fromarray(array), (800*i, 32))
        draw.text((800*i+8, 8), key+' | '+label, fill='black')
    return result


def encode_video(frame_paths, target, width):
    binary = imageio_ffmpeg.get_ffmpeg_exe()
    height = 832 if width == 3200 else 416
    cmd = [binary, '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', '3200x832', '-r', str(CFG['render']['fps']), '-i', '-', '-an',
           '-vf', f'scale={width}:{height}', '-c:v', CFG['render']['codec'],
           '-crf', str(CFG['render']['crf']), '-pix_fmt', CFG['render']['pixel_format'],
           '-movflags', '+faststart', '-threads', '2', str(target)]
    log_path = OUT/'logs'/(target.stem+'_encode.log')
    with log_path.open('w') as log:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log, stderr=log)
        try:
            for file in frame_paths:
                with Image.open(file) as im:
                    proc.stdin.write(np.asarray(im.convert('RGB')).tobytes())
        finally:
            proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError('video encoding failed: '+str(log_path))
    return dict(path=str(target), bytes=target.stat().st_size, sha256=sha(target),
                width=width, height=height, expected_frames=33, fps=6, command=cmd,
                encoding_log=str(log_path))


def render_all():
    asset = load_asset(ART/'ASSET.json')
    proposals = load_asset(ART/'PROPOSALS.json')
    baseline_asset_sha = sha(ART/'ASSET.json')
    baseline_geo = asset['geometry_sha256']
    keys = CFG['construction']+CFG['validation']+CFG['evaluation']+[f'arc0_{i:03d}' for i in range(33)]
    outdir, media = OUT/'frames', ART/'media'
    outdir.mkdir(parents=True, exist_ok=True); media.mkdir(exist_ok=True)
    records, edit_frames = [], []
    event('render', 'begin', camera_count=len(keys), geometry_sha256=baseline_geo)
    for key in keys:
        # Verify/reload the same sealed world controls at every actual pose.
        current = load_asset(ART/'ASSET.json')
        assert current['geometry_sha256'] == baseline_geo and sha(ART/'ASSET.json') == baseline_asset_sha
        camera, native, responses = load_view('render', key)
        target = outdir/key; target.mkdir(exist_ok=True)
        rgb = np.rint(np.clip(native['rgb'], 0, 1)*255).astype(np.uint8)
        residual = ink_image(responses['C'])
        pure, visibility = paint(np.full_like(rgb, 255), current['paths'], camera, native)
        hybrid, _ = paint(residual, current['paths'], camera, native)
        overlay, _ = paint(rgb, current['paths'], camera, native)
        diagnostic, _ = paint(np.full_like(rgb, 255), proposals['paths'], camera, native, diagnostic=True)
        arrays = dict(rgb=rgb, pure3d=pure, residual2d=residual, hybrid=hybrid, overlay=overlay,
                      diagnostic=diagnostic, A=ink_image(responses['A']), C=residual)
        outputs = {}
        for name, array in arrays.items():
            filename = target/(name+'.png'); save_png(filename, array); outputs[name] = str(filename)
        composed = panel([rgb, pure, residual, hybrid], key, len(current['paths']))
        composed.save(target/'panel.png'); outputs['panel'] = str(target/'panel.png')
        projections, prop_projections = [], []
        for paths, listing in [(current['paths'], projections), (proposals['paths'], prop_projections)]:
            for p in paths:
                uv, z = project_independent_controls(p['controls_xyz'], camera)
                listing.append(dict(persistent_id=p['persistent_id'], uv=uv, z=z))
        records.append(dict(key=key, camera_path=str(SOURCE/'raw/mic'/key/'camera.json'),
                            geometry_sha256=baseline_geo, asset_sha256=baseline_asset_sha,
                            projections=projections, proposal_projections=prop_projections,
                            visibility=visibility, outputs=outputs,
                            output_sha256={k: sha(v) for k, v in outputs.items()}))
        if key in ['arc0_000', 'arc0_016', 'arc0_032']:
            composed.resize((1600, 416), Image.Resampling.LANCZOS).save(media/(key+'_comparison.jpg'), quality=90)
            proof = Image.new('RGB', (2400, 832), 'white'); draw = ImageDraw.Draw(proof)
            for i, (name, a) in enumerate([('A baseline', arrays['A']), (f"all proposals unoccluded: {len(proposals['paths'])}", diagnostic), ('pure3D on RGB', overlay)]):
                proof.paste(Image.fromarray(a), (i*800, 32)); draw.text((i*800+8, 8), key+' | '+name, fill='black')
            proof.resize((1200, 416), Image.Resampling.LANCZOS).save(media/(key+'_diagnostics.jpg'), quality=90)
            if current['paths']:
                edited = json.loads(json.dumps(current['paths']))
                edited[0]['width_px'] = 4; edited[0]['color_rgb'] = [220, 0, 200]
                assert geometry_hash(edited) == baseline_geo
                edit, _ = paint(np.full_like(rgb, 255), edited, camera, native)
                save_png(target/'edited_pure3d.png', edit)
                Image.fromarray(edit).save(media/(key+'_edit.jpg'), quality=90)
                edit_frames.append(dict(key=key, path=str(target/'edited_pure3d.png'),
                                        sha256=sha(target/'edited_pure3d.png'),
                                        geometry_sha256=geometry_hash(edited),
                                        changed_pixels=int(np.any(edit != pure, axis=2).sum())))
        print('rendered', key, flush=True)
        event('render', 'frame_complete', key=key, geometry_sha256=baseline_geo)
    arc = [r for r in records if r['key'].startswith('arc0_')]
    sheet = Image.new('RGB', (2400, 208*11), 'white')
    for i, r in enumerate(arc):
        with Image.open(r['outputs']['panel']) as im:
            sheet.paste(im.resize((800, 208), Image.Resampling.LANCZOS), ((i%3)*800, (i//3)*208))
    sheet.save(media/'arc33_contact.jpg', quality=88)
    videos = [encode_video([r['outputs']['panel'] for r in arc], OUT/'arc33_native3200.mp4', 3200),
              encode_video([r['outputs']['panel'] for r in arc], media/'arc33_telegram1600.mp4', 1600)]
    edit_report = dict(performed=bool(asset['paths']), reason='same first persistentID style at first/middle/last; world XYZ unchanged' if asset['paths'] else 'empty accepted asset; no edit demonstration fabricated', geometry_sha256=baseline_geo,
                       persistent_id=asset['paths'][0]['persistent_id'] if asset['paths'] else None,
                       frames=edit_frames,
                       visible_in_all_three=bool(edit_frames) and all(f['changed_pixels'] > 0 for f in edit_frames))
    write_json(ART/'FRAME_AUDIT.json', dict(frames=records, videos=videos, camera_count=len(records),
                                         panel_header_px=32, edit_demo=edit_report))
    event('render', 'complete', camera_count=len(records), video_count=len(videos), geometry_sha256=baseline_geo)
