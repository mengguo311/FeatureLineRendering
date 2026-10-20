"""Confirm completed validation data after its final stdout serialization error."""
import run_round003 as r
import json


def main():
    assert not (r.R/'CONFIRMATION.json').exists()
    r.verify_lock(); r.verify_prior(); r.resource_check()
    for name in ('VALIDATION_LOCK.json', 'RECOVERY_LOCK.json'):
        lock = json.loads((r.D/name).read_text())
        for p, digest in lock['sources'].items(): assert r.sha(r.W/p) == digest, p
        for p, digest in lock['evidence'].items(): assert r.sha(r.R/p) == digest, p
    receipt = json.loads((r.R/'VALIDATION_EXECUTION.json').read_text())
    assert receipt['returncode'] == 1
    log = (r.R/'runtime/validation_execution.log').read_text()
    assert 'line 119, in main' in log and 'print(json.dumps(validation, indent=2))' in log
    assert 'TypeError: Object of type int64 is not JSON serializable' in log
    assert r.sha(receipt['log']) == receipt['log_sha256']
    validation = json.loads((r.R/'VALIDATION.json').read_text())
    assert validation['validation_complete'] and validation['full_frames_checked'] == 60
    assert validation['same_id_distances_recomputed'] == 9843660
    assert validation['all_partition_checks'] and validation['all_images_byte_equal_prior']
    assert validation['all_saved_drift_rasters_match_no_wrap'] and validation['source_lock_verified']
    assert validation['metrics_sha256'] == r.sha(r.R/'metrics.json')
    detail = json.loads((r.R/'SUMMARY_DETAIL.json').read_text())
    metrics = json.loads((r.R/'metrics.json').read_text())
    for kind in ('orbit', 'zoom'):
        s = detail[kind]['0']; m = metrics['trajectories'][kind]
        assert abs(s['eligible_length']-m['eligible_length_frame_world']) < 1e-9
        for variant in ('baseline', 'drift', 'drop'):
            a = s['variants'][variant]; b = m['variants'][variant]
            assert abs(a['missing_fraction']-b['missing_fraction']) < 1e-12
            assert abs(sum(a['pair_events'].values())-1) < 1e-12
            for event in a['pair_events']: assert abs(a['pair_events'][event]-b['pair_events'][event]) < 1e-12
    result = {'confirmation_complete': True, 'original_validation_returncode': 1,
              'original_failure': 'final stdout JSON print after all validation files were written',
              'original_zoom_outer_returncode': 143, 'original_zoom_child_returncode': None,
              'full_validation_checks_complete': True, 'all_60_images_checked': True,
              'same_id_distances_checked': 9843660,
              'aggregate_summaries_consistent': True,
              'metrics_sha256_unchanged': r.sha(r.R/'metrics.json'),
              'validation_sha256_unchanged': r.sha(r.R/'VALIDATION.json'),
              'rerendered': False, 'rewrote_existing_data': False}
    r.write_json(r.R/'CONFIRMATION.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
