# Observed vertical TDD ledger

Each RED preceded the corresponding production implementation. Failed GREEN/setup attempts remain in JOURNAL.jsonl; they are not counted as passes. The additional global two-span recovery validation passed without requiring a code change and is not represented as an observed RED.

| Slice | Behavior | RED log / exit | Final GREEN log / exit |
|---|---|---|---|
| 01 | `test_fixed_cubic_projection_and_native_centers` | 002_RED01.log / 1 | 003_GREEN01.log / 0 |
| 02 | `test_union_saturates_reassigns_and_unknown_cannot_hide` | 004_RED02.log / 1 | 005_GREEN02.log / 0 |
| 03 | `test_complete_evidence_native_mapping_and_depth_boundary` | 006_RED03.log / 1 | 008_GREEN03_FIXED.log / 0 |
| 04 | `test_visibility_and_independent_local_objective` | 009_RED04.log / 1 | 010_GREEN04.log / 0 |
| 05 | `test_local_matching_cannot_win_by_deleting_its_span` | 011_RED05.log / 1 | 012_GREEN05.log / 0 |
| 06 | `test_regularization_redundancy_and_synthetic_recovery` | 013_RED06.log / 1 | 014_GREEN06.log / 0 |
| 07 | `test_proposals_keep_empty_cells_and_share_three_starts` | 015_RED07.log / 1 | 016_GREEN07.log / 0 |
| 08 | `test_native_quantiles_are_ten_fifty_ninety_and_calibrated` | 017_RED08.log / 1 | 018_GREEN08.log / 0 |
| 09 | `test_partition_access_and_native_preparation` | 019_RED09.log / 1 | 020_GREEN09.log / 0 |
| 10 | `test_native_census_keeps_empty_cells_and_fixed_geometry` | 021_RED10.log / 1 | 022_GREEN10.log / 0 |
| 11 | `test_fit_runner_seals_all_arms_starts_and_never_decodes_C` | 023_RED11.log / 1 | 024_GREEN11.log / 0 |
| 12 | `test_gpu_sampler_deterministic_gradient` | 025_RED12.log / 1 | 027_GREEN12_FIXED.log / 0 |
| 13 | `test_temporal_and_ambiguity_counts_do_not_reward_empty_ink` | 031_RED13.log / 1 | 032_GREEN13.log / 0 |
| 14 | `test_playable_complete_media_and_drawing_disagreement` | 033_RED14.log / 1 | 035_GREEN14_FIXED.log / 0 |
| 15 | `test_evaluation_requires_seal_and_keeps_every_frame_and_cell` | 036_RED15.log / 1 | 040_GREEN15_FIXED.log / 0 |
| 16 | `test_depth_reference_temporal_motion_has_identity_zero_and_detects_pop` | 038_RED16.log / 1 | 039_GREEN16.log / 0 |
| 17 | `test_depth_scale_is_neighbor_difference_not_median_residual` | 041_RED17.log / 1 | 043_GREEN17.log / 0 |
| 18 | `test_final_native_stroke_width_is_one_point_five` | 048_RED18.log / 1 | 049_GREEN18.log / 0 |
| 19 | `test_verification_detects_geometry_and_metric_tampering` | 050_RED19.log / 1 | 051_GREEN19.log / 0 |
| 20 | `test_foreground_census_uses_alpha_not_expanded_outline` | 055_RED20.log / 1 | 056_GREEN20.log / 0 |
| 21 | `test_double_line_pairs_and_detached_runs_are_counted` | 058_RED21.log / 1 | 059_GREEN21.log / 0 |
| 22 | `test_media_verification_decodes_all_frames_and_rejects_wrong_count` | 060_RED22.log / 1 | 061_GREEN22.log / 0 |
| 23 | `test_doubling_counts_dense_spans_beyond_same_id_neighbors` | 066_RED23.log / 1 | 067_GREEN23.log / 0 |
| 24 | `test_ambiguity_compares_all_equally_good_data_fits` | 071_RED24.log / 1 | 072_GREEN24.log / 0 |

## Resume engineering regressions (2026-09-29)

- RED25: cutoff fixture returns alpha 0 instead of stock 0.003921806812286377 under the preserved CPU replay (080_RED25.log). GREEN25: CUDA replay passes the cutoff/quantile fixture (081_GREEN25.log). GREEN25_STOCK_ORACLE: unchanged upstream FORWARD::render independently validates synthetic anisotropic, cutoff and saturation cases, with exact RGB/alpha equality and poisoned stock-buffer independence (084_GREEN25_STOCK_ORACLE.log). Full actual Lego frame also matches exactly; all 82 domain records are verified separately.
- RED26: scheduler behavior contracts fail before the scheduler exists (086_RED26.log); GREEN26 validates independence of subsequent scene fits from Lego evaluation failure, exclusive atomic JSON publication, blocked partial fits, and validation/preservation of sealed assets (087_GREEN26.log). The real legacy orchestration failure and preserved logs supply the observed motivation; the new scheduler does not change science.
- 088_RESUME_COMPLETE_SUITE_226.log: complete native-open-traced suite, 226 tests, one expected nested-strace skip, otherwise passing. SUITE_ACCESS_AUDIT_RESUME_226.json reports zero forbidden successful opens and no unparsed calls. The V2 calibration provenance allowlist adds only upstream forward.cu after the complete per-frame calibration succeeded but its aggregate source read was denied; full scene calibrations and audits run under that final policy.
