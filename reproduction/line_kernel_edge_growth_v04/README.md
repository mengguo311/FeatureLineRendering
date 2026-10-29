# Frozen v04 carrier pilot

This is an archived, single-unit CPU postprocessing pilot. Its scientific decision and original configuration live in `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v04/units/unit_001`.

Only scan24 L0 and L1 completed. L2 was terminated at the frozen building compute budget before export. L3/L4, ficus and scan65 were not run. Do not rerun or overwrite this sealed unit. No long-edge growth success is claimed.

`core.py` separates finite carrier topology from many kernel supports. `runner.py` exports a complete scene/level and cold-loads original geometry; `driver.py` and the single `recovery_driver.py` record actual subprocess exits. `common.py` contains paths, resource limits, the configuration freeze and the AST-isolated CPU renderer loader. `finalize.py` audits completed outputs and creates delivery figures. `test_core.py` contains five small post-output regression tests.

The original implementation is preserved in the unit's `engineering_recovery_v1` directory. The recovery vectorized the same candidate-owner deduplication and batched the same projection score, without changing scientific thresholds. The original driver exited 143; L1's actual child exit was lost and remains UNKNOWN despite its complete checkpoint. Recovery L2 exited -15 at its time cap. The finalization subprocess exited 0.

## Output schema

- `MEMBERSHIP.npz`: every original row, original `line_kernel_id`, primary `edge_id` (-1 UNKNOWN), previous and baseline identity, current carrier ID, representative ID, reason, up to two auxiliary alternatives, provenance and provisional flag. L0 preserves original reason codes; later codes are 0 assigned, 1 dormant/insufficient support, 2 unresolved alternatives, 3 invalid source tangent.
- `GROUPS.json`: object containing `scene`, `level`, `p`, and `groups[]`. Lengths ending `_p` use world-per-source-pixel units, not calibrated localization uncertainty. Parent contributions are provenance, not truth.
- `CARRIERS.npz`: carrier IDs/versions, ragged finite knots, seedlet membership and interval unions. Knots and intervals are stored in original world units. Geometry here is auxiliary and is never rendered.
- `LINEAGE.json`: versioned two-input merges with host ID and output version. L1 records containment only. `CANDIDATES.json` records proposals, rejection reasons and costs; cumulative carrier versions are reconstructed through the DAG.
- `DISPLAY_GAUSSIANS.npz` and `DISPLAY.ply`: original kernels with membership colors only. All other source fields remain unchanged. Native PNGs use the original fixed cameras, opacity and width.
- `STATE.pkl`: trusted local continuation checkpoint; not a portable interchange format.

The per-level `fit_attempts` field counts bounded growth/pooling whole-group evaluations. L0 initialization fits are separately counted by `baseline_*` reasons. Initial baseline groups that fail new guards remain assigned and frozen.

## Verification limits

Duplicate interval union, curved/S paths, close parallel/depth-separated lines, T geometry, unsupported gaps and a real membership RED-to-GREEN fixture passed. Real fixtures do not supply physical edge truth. Native negative-case pictures show original pre-level carrier contexts; these can be smaller than an accumulated in-pass candidate. Their tiny projected footprints do not independently establish branch or depth correctness.

The final output report records incomplete stages, candidate caps, immutable-input checks and the weak 639+3 / 555+4 contributions in the largest new cross-parent groups. Those groups are not evidence of substantial edge extension.
