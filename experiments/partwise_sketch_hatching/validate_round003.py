"""Data-only full audit of frozen raw arrays and descriptive pooled summaries."""
import run_round003 as r
import temporal_audit as ta
import json
import numpy as np
from PIL import Image


def main():
    r.verify_lock(); r.resource_check()
    assert not (r.R/'VALIDATION.json').exists()
    samples = dict(np.load(r.R/'samples.npz'))
    w = samples['weight']; n = len(w); owner = samples['owner']
    selected_drop = samples['selected_drop'][owner]
    summaries = {}; checked_distances = 0; checked_frames = 0
    for kind, count in [('orbit', 36), ('zoom', 24)]:
        metric = json.loads((r.R/(kind+'_metrics.json')).read_text())
        assert len(metric['frames']) == count and len(metric['pairs']) == count-1
        frame_acc = {str(k): {'all_length': 0., 'visible_length': 0., 'eligible_length': 0.,
                              'ambiguous_length': 0., 'exclusion_length': {str(c): 0. for c in range(1, 6)},
                              'eligible_stroke_ids': set(), 'total_stroke_ids': set(),
                              'finite_d': [[], [], []], 'finite_w': [[], [], []],
                              'missing_length': [0., 0., 0.], 'pair_residual': [[], [], []],
                              'pair_weights': [[], [], []], 'pair_common_length': 0.,
                              'pair_common_samples': 0, 'events': [dict.fromkeys(['both_detected', 'disappearance', 'reappearance', 'both_missing'], 0.) for _ in range(3)]}
                     for k in (0, 1, 2, 3)}
        previous = None
        for i in range(count):
            r.resource_check()
            z = dict(np.load(r.R/'raw'/kind/f'{i:04d}.npz'))
            assert len(z['uv']) == n and z['distance'].shape == (3, n)
            original = np.asarray(Image.open(r.P/'frames'/kind/f'{i:04d}.png'))
            current = np.asarray(Image.open(r.R/'frames'/kind/f'{i:04d}.png'))
            np.testing.assert_array_equal(original, current)
            assert z['overlap_count'].shape == (512, 512)
            xy = z['identified_xy'].astype(int); sid = z['identified_owner']
            assert np.all(z['overlap_count'][xy[:, 1], xy[:, 0]] == 1)
            assert np.all(z['hatch'][xy[:, 1], xy[:, 0]]/255. > .04)
            assert np.all(z['eligible_geometry'] == (z['exclusion_code'] == 0))
            eligible = z['eligible_geometry'] & ~z['ambiguity']
            expected_drift = ta.shift_image(z['hatch'], 6, 6) if i % 2 else z['hatch']
            np.testing.assert_array_equal(z['drift_hatch'], expected_drift)
            # Re-query all observed per-ID sparse support; no coordinate-only shortcut.
            for j in range(len(samples['stroke_ids'])):
                lo, hi = samples['offsets'][j:j+2]; pixels = xy[sid == j]
                for v in range(3):
                    pixels_v = pixels
                    if v == 1 and i % 2:
                        pixels_v = pixels + [6, 6]
                        pixels_v = pixels_v[(pixels_v[:, 0] < 512) & (pixels_v[:, 1] < 512)]
                    if v == 2:
                        if i % 3 == 1 and samples['selected_drop'][j]: pixels_v = np.empty((0, 2), int)
                        else: pixels_v = pixels_v[z['drop_hatch'][pixels_v[:, 1], pixels_v[:, 0]]/255. > .04]
                    dd, oo = ta.match_support(z['uv'][lo:hi], pixels_v)
                    np.testing.assert_allclose(dd, z['distance'][v, lo:hi], rtol=0, atol=0)
                    np.testing.assert_allclose(oo, z['offset'][v, lo:hi], rtol=0, atol=0, equal_nan=True)
                    checked_distances += hi-lo
            if i % 3 == 1:
                assert np.all(np.isinf(z['distance'][2, selected_drop]))
            for k in (0, 1, 2, 3):
                a = frame_acc[str(k)]
                mask = np.ones(n, bool) if k == 0 else samples['parts'] == k
                good = eligible & mask
                excluded = sum(int((mask & (z['exclusion_code'] == c)).sum()) for c in range(1, 6))
                ambiguous = mask & z['eligible_geometry'] & z['ambiguity']
                assert int(mask.sum()) == excluded + int(ambiguous.sum()) + int(good.sum())
                a['all_length'] += float(w[mask].sum()); a['visible_length'] += float(w[mask & z['visible']].sum())
                a['eligible_length'] += float(w[good].sum()); a['ambiguous_length'] += float(w[ambiguous].sum())
                a['eligible_stroke_ids'].update(map(int, np.unique(owner[good])))
                a['total_stroke_ids'].update(map(int, np.unique(owner[mask])))
                for c in range(1, 6): a['exclusion_length'][str(c)] += float(w[mask & (z['exclusion_code'] == c)].sum())
                for v in range(3):
                    finite = good & np.isfinite(z['distance'][v])
                    a['finite_d'][v].append(z['distance'][v, finite]); a['finite_w'][v].append(w[finite])
                    a['missing_length'][v] += float(w[good & (z['distance'][v] > 1.5)].sum())
                if previous is not None:
                    common = good & previous['eligible_geometry'] & ~previous['ambiguity']
                    a['pair_common_length'] += float(w[common].sum()); a['pair_common_samples'] += int(common.sum())
                    for v in range(3):
                        first, second = previous['distance'][v] <= 1.5, z['distance'][v] <= 1.5
                        events = {'both_detected': first & second, 'disappearance': first & ~second,
                                  'reappearance': ~first & second, 'both_missing': ~first & ~second}
                        assert sum(int((common & b).sum()) for b in events.values()) == int(common.sum())
                        for event, b in events.items(): a['events'][v][event] += float(w[common & b].sum())
                        both = common & first & second
                        a['pair_residual'][v].append(np.linalg.norm(z['offset'][v, both]-previous['offset'][v, both], axis=1))
                        a['pair_weights'][v].append(w[both])
            checked_frames += 1; previous = z
        result = {}
        for k, a in frame_acc.items():
            den = a['eligible_length']; pairden = a['pair_common_length']
            out = {key: a[key] for key in ('all_length', 'visible_length', 'eligible_length', 'ambiguous_length', 'exclusion_length', 'pair_common_length', 'pair_common_samples')}
            out['ever_eligible_strokes'] = len(a['eligible_stroke_ids']); out['total_strokes'] = len(a['total_stroke_ids'])
            out['eligible_fraction_of_visible'] = den/a['visible_length'] if a['visible_length'] else None
            out['eligible_fraction_of_all'] = den/a['all_length'] if a['all_length'] else None
            out['variants'] = {}
            for v, name in enumerate(('baseline', 'drift', 'drop')):
                dd, ww = np.concatenate(a['finite_d'][v]), np.concatenate(a['finite_w'][v])
                detected = dd <= 1.5
                out['variants'][name] = {'missing_fraction': a['missing_length'][v]/den if den else None,
                                         'finite_distance_px': ta.weighted_stats(dd, ww),
                                         'detected_distance_px': ta.weighted_stats(dd[detected], ww[detected]),
                                         'pair_events': {e: val/pairden if pairden else None for e, val in a['events'][v].items()},
                                         'pair_event_length': a['events'][v],
                                         'pair_residual_px': ta.weighted_stats(np.concatenate(a['pair_residual'][v]), np.concatenate(a['pair_weights'][v]))}
            result[k] = out
        summaries[kind] = result
    r.write_json(r.R/'SUMMARY_DETAIL.json', summaries)
    validation = {'validation_complete': True, 'full_frames_checked': checked_frames,
                  'same_id_distances_recomputed': checked_distances, 'all_partition_checks': True,
                  'all_images_byte_equal_prior': True, 'all_saved_drift_rasters_match_no_wrap': True,
                  'prior_seal_reverified': r.verify_prior(), 'source_lock_verified': True,
                  'metrics_sha256': r.sha(r.R/'metrics.json'), 'resources': r.resource_check(),
                  'note': 'Data-only validation; no new renders, thresholds, exclusions, or replacement evidence.'}
    r.write_json(r.R/'VALIDATION.json', validation)
    print(json.dumps(validation, indent=2))


if __name__ == '__main__': main()
