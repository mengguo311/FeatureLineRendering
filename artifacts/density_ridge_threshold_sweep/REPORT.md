# Frozen density-ridge threshold-relaxation comparison

**Relaxation restores some coherent bands, but also increasingly admits clutter. No threshold is selected as a scientific pass.** The 12-20% rows visibly recover cab/track/arm structure on Lego and rim/stand structure on Drums. Chair gains frame coverage early but increasingly fills with interior texture. Ficus gains pot/stem bands while canopy ink remains short, crowded or merged. At 35%, much of the extra response is texture, thickening and branching; it is not merely blank-area fill, but it is also not clean line recovery.

These are unblinded visual observations across the full frozen sweep. They do not change the masks or rescue the prior feasibility decision. Topological connectivity is not correctness, recall, or 3D persistence.

- [All-scene summary: opacity and flattening, every mask level](all_scenes_threshold_summary.png)
- Large focus sheets: [opacity](opacity_all_scenes_focus.png), [flattening](flattening_all_scenes_focus.png), each 5471 x 7462 pixels with 2x nearest-neighbor mask pixels, all four scenes and response/reference/6/12/20/35 rows.
- Seven-channel atlases: [Lego](lego_threshold_atlas.png), [Chair](chair_threshold_atlas.png), [Drums](drums_threshold_atlas.png), [Ficus](ficus_threshold_atlas.png). Each is 4878 pixels wide, with the fixed channel order and all six rows.
- [Frozen protocol](PROTOCOL.md), [metrics](metrics.json), [verification](verification.json), [visual review](visual_review.json), [preimplementation record](preregistration.json), [science hashes before inspection](science_hashes.json).

The summary is deliberately limited to the two focus channels to keep all five mask levels readable. All seven channels are present in every scene atlas. View/download figures at full resolution for cell text and narrow gaps. Cyan pixels are selected masks; the same dim saved color/density background appears at every mask level. Background recognizability is not evidence of mask recovery. Response rows show the saved full Hessian response inside support, using the original channel-pooled p99 display scale; display clipping does not change scores or selections. Response cells state ink is not applicable and print the actual support count.

## Frozen computation and reference

Only mask selection budget changed. The four verified ridge-grid NPZs were read directly; fields, Hessian response, NMS, support, broad_score, projection and checkpoints were neither recomputed nor altered. Per channel, saved positive ridge_scores on saved support are ranked over lego, chair, drums, ficus, descending with stable scene-then-row-major ties. The support total is 544,525 pixels. Budgets are floor(fraction x support):

| Pooled budget | Requested raw pixels per channel | Selected raw pixels per channel |
|---|---:|---:|
| 6% | 32,671 | 32,671 |
| 12% | 65,343 | 65,343 |
| 20% | 108,905 | 108,905 |
| 35% | 190,583 | 190,583 |

Every channel has sufficient positive candidates at every budget; no exhaustion or zero-score fill occurs. Cleanup only removes 8-connected components with area below 12. There is no baseline matching or second trim in the fresh sweep. Pooled thresholds, candidate counts, raw and clean scene counts, canvas/support coverage, components, fragments, widths and long-component ink fractions are all in metrics.json.

The reference is the saved ridge_clean from the committed 6% pooled exact-ink protocol, including its historical matching trim. Fresh 6% exactly reproduces saved ridge_raw and ridge_cleaned_unmatched for all 28 scene/channel pairs. Reference equals fresh 6% in color, axis, opacity, flattening and planarity. Fresh 6% restores 114 pixels in agreement (Lego 20, Chair 14, Drums 32, Ficus 48) and 20 in surface (Drums 12, Ficus 8); it removes none. Thus differences at the higher budgets are not an unreported change to field construction or a new baseline comparison.

## Actual coverage and topology

Each table entry is cleaned ink as a percentage of that scene's saved support, not the nominal pooled budget. Every figure cell also prints the exact ink/support counts. Scene support: Lego 114,910; Chair 171,055; Drums 149,246; Ficus 109,314.

| Scene / channel | Original final | Fresh 6% | Fresh 12% | Fresh 20% | Fresh 35% |
|---|---:|---:|---:|---:|---:|
| lego / color | 8.48% | 8.48% | 13.90% | 21.07% | 33.01% |
| lego / axis | 3.92% | 3.92% | 9.33% | 18.43% | 37.31% |
| lego / opacity | 8.20% | 8.20% | 16.23% | 25.91% | 38.75% |
| lego / flattening | 4.28% | 4.28% | 10.93% | 19.18% | 33.23% |
| lego / planarity | 2.64% | 2.64% | 8.66% | 17.71% | 33.68% |
| lego / agreement | 3.62% | 3.64% | 10.33% | 18.48% | 33.31% |
| lego / surface | 3.34% | 3.34% | 9.95% | 18.93% | 33.51% |
| chair / color | 4.59% | 4.59% | 9.49% | 16.24% | 30.53% |
| chair / axis | 2.46% | 2.46% | 6.64% | 14.09% | 29.78% |
| chair / opacity | 3.54% | 3.54% | 8.14% | 15.56% | 32.65% |
| chair / flattening | 1.88% | 1.88% | 4.70% | 10.83% | 31.01% |
| chair / planarity | 1.98% | 1.98% | 5.07% | 11.90% | 32.56% |
| chair / agreement | 1.86% | 1.86% | 4.65% | 11.49% | 32.09% |
| chair / surface | 1.81% | 1.81% | 4.53% | 10.62% | 31.88% |
| drums / color | 7.88% | 7.88% | 15.96% | 24.85% | 38.11% |
| drums / axis | 6.20% | 6.20% | 13.02% | 21.40% | 35.02% |
| drums / opacity | 9.69% | 9.69% | 17.17% | 24.81% | 35.56% |
| drums / flattening | 8.31% | 8.31% | 15.10% | 23.19% | 36.14% |
| drums / planarity | 8.14% | 8.14% | 14.81% | 22.53% | 34.95% |
| drums / agreement | 8.40% | 8.42% | 14.93% | 22.83% | 35.26% |
| drums / surface | 8.12% | 8.13% | 14.76% | 22.97% | 35.51% |
| ficus / color | 2.25% | 2.25% | 7.54% | 17.02% | 38.51% |
| ficus / axis | 12.53% | 12.53% | 20.64% | 28.09% | 39.48% |
| ficus / opacity | 1.69% | 1.69% | 5.41% | 13.06% | 32.54% |
| ficus / flattening | 10.38% | 10.38% | 19.43% | 29.38% | 40.01% |
| ficus / planarity | 12.16% | 12.16% | 21.71% | 30.17% | 38.84% |
| ficus / agreement | 11.09% | 11.14% | 20.48% | 29.84% | 39.60% |
| ficus / surface | 11.89% | 11.90% | 21.29% | 30.47% | 39.30% |

Pooled cleaned support ink ranges from 5.81-5.90% at the 6% request, 11.77-11.84% at 12%, 19.70-19.82% at 20%, and 34.69-34.75% at 35%. Per-scene cleanup retains at least 92.63% of raw ink across the entire sweep. Cleanup therefore does not explain away the added high-budget clutter.

Long-component fraction below is the percentage of ink in components with at least 24 skeleton pixels. Each cell reports **long % / components / fragments**; a fragment has fewer than 24 skeleton pixels. These definitions match the committed experiment.

| Scene / focus channel | Fresh 6% | Fresh 12% | Fresh 20% | Fresh 35% |
|---|---:|---:|---:|---:|
| lego / opacity | 72.9 / 108 / 73 | 80.0 / 159 / 113 | 89.0 / 142 / 98 | 95.3 / 99 / 62 |
| lego / flattening | 71.2 / 49 / 34 | 77.5 / 113 / 76 | 87.8 / 122 / 77 | 93.1 / 110 / 73 |
| chair / opacity | 85.3 / 42 / 25 | 77.3 / 112 / 86 | 84.1 / 175 / 123 | 91.9 / 196 / 149 |
| chair / flattening | 75.3 / 32 / 23 | 77.0 / 72 / 51 | 78.6 / 164 / 117 | 90.2 / 228 / 156 |
| drums / opacity | 72.3 / 172 / 122 | 83.2 / 183 / 121 | 89.2 / 157 / 102 | 91.8 / 188 / 116 |
| drums / flattening | 75.7 / 120 / 78 | 87.6 / 133 / 75 | 92.1 / 128 / 83 | 94.9 / 138 / 94 |
| ficus / opacity | 70.9 / 22 / 16 | 66.4 / 79 / 64 | 71.8 / 151 / 114 | 91.9 / 136 / 72 |
| ficus / flattening | 56.3 / 157 / 127 | 78.9 / 164 / 99 | 95.0 / 109 / 43 | 96.3 / 119 / 54 |

The high-budget connectivity gain is not a scientific success criterion. For example, Ficus flattening rises from 56.3% long-component ink at fresh 6% to 95.0% at 20% and 96.3% at 35%, while the canopy becomes a crowded network. Chair opacity initially drops from 85.3% to 77.3% long-component ink at 12% because more short responses enter. Component counts, fragmentation and skeleton-based fractions need not increase or decrease monotonically.

Raw and cleaned masks are nested across all 84 adjacent scene/channel/budget transitions at each stage: no previously selected pixel disappears. Mathematically the fixed area filter is monotone: any retained lower-budget component has area at least 12 and is contained in a higher-budget component of equal or larger area. Merging cannot make it fail the area test. Thus this cleanup cannot break nesting; a violation would be an implementation error and aborts the run. A second score trim or changing the cleanup rule could break that argument, but neither occurs here.

## Visual assessment of all channels

The original final and fresh 6% rows are visually identical in the focus channels; the small reference differences in agreement/surface are documented above. The following assessments compare every frozen level, not selected favorable crops. Any stated visual balance is an exploratory observation, not an optimized setting or pass.

### Lego

| Channel | Observation across the frozen sweep |
|---|---|
| color | 12% extends cab, arm and base bands; 20% adds repeated studs and small rim loops; 35% crowds the body/base. Some coherent return, with texture increasing faster at the high budget. |
| axis | The sparse 6% mask misses much of the body. 12-20% restores cab/arm outlines but also short irregular base and track responses; 35% is a dense network. More coverage does not make the axis response a clean contour map. |
| opacity | 12% substantially closes the track outline and extends the cab/arm; 20% adds detail but roughens the roof, base and joints. 35% fills the track interior and base with short loops. A visual balance around 12% is descriptive only. |
| flattening | 12-20% recovers long cab, arm, track and base bands that are broken at 6%. At 20% major arcs remain readable; 35% adds base texture and doubled/branched rims. The 12-20% range looks useful without establishing correctness. |
| planarity | 6% is severely incomplete on the track and cab. 12-20% restores recognizable bands; 35% mainly thickens and branches them and adds internal/base texture. Return is partly coherent, not solely fill. |
| agreement | 12-20% restores the lower track, cab and arm structure; 35% adds loops and busy base bands. Its progression closely resembles the other geometric scalar channels. |
| surface | 12-20% supplies missing track/cab/arm segments; 35% retains these but adds many short internal and base responses. The increase is useful initially and increasingly cluttered later. |

### Chair

| Channel | Observation across the frozen sweep |
|---|---|
| color | 12% strengthens the outer frame and central division, alongside seat texture already present at 6%. 20-35% increasingly fills the seat with a connected mesh; the high budget is not a cleaner outline. |
| axis | 12% adds scattered interior arcs and partial rim continuity; 20% increases rim coverage and texture together. At 35% the seat becomes a dense cyan mesh. A large connectivity gain is visually confounded by merging. |
| opacity | 6% already captures much of the outer right rim. 12% restores more outer frame and the central slot, but also interior arcs; 20% adds mostly seat texture, and 35% crowds both seat and back. 6-12% is a descriptive simplicity/coverage tradeoff. |
| flattening | 12% extends the frame and central slot with relatively sparse interior ink; 20% adds many short seat marks; 35% produces heavy textured fill. Around 12% looks cleaner than the denser alternatives, with incomplete left frame still visible. |
| planarity | 12% improves frame/slot coverage. 20% introduces substantial seat fragmentation and 35% fills both surfaces with a connected network. More response is not all useful geometric structure. |
| agreement | 12% adds frame/slot segments; 20% and especially 35% spend much of their added ink inside the seat. Outer structure persists but internal clutter dominates the late increments. |
| surface | 12% improves the frame and division with limited clutter; 20% adds short interior marks and 35% is dense. Similarity to the other geometric scalar channels remains strong. |

### Drums

| Channel | Observation across the frozen sweep |
|---|---|
| color | 12-20% recovers some drum/support arcs but cymbal rims remain incomplete, especially compared with geometric scalars. 35% eventually adds more outer rims along with very busy drum interiors and hardware. |
| axis | 12-20% adds drums and stand segments, but the upper cymbals remain poorly outlined until the high budget. 35% brings much texture and branching. Threshold relaxation cannot isolate clean rims uniformly. |
| opacity | 12% improves cymbal and drum arcs and several stand segments; 20% adds continuity with rougher, doubled rims and more hardware detail. 35% adds internal cymbal marks, loops and dense central clutter. The 12-20% range has a visible tradeoff, not a pass. |
| flattening | 12-20% gives the clearest added coherent return: cymbal ellipses, drum arcs and long stand bands. Some missing and doubled arcs remain. At 35% internal cymbal/drum marks and thick hardware clutter increase substantially. |
| planarity | 12-20% restores rim and stand continuity while preserving relatively empty cymbal interiors. 35% adds extensive drum/hardware texture and some interior marks. Initial added information is visibly line-like. |
| agreement | 12-20% makes cymbal, drum and tripod bands more continuous. 35% adds dense short branches on the central drums and hardware; long-component fraction alone overstates the benefit. |
| surface | 12-20% restores useful rim/stand segments much like flattening and planarity. At 35% the central assembly is much busier and band merging increases. |

### Ficus

| Channel | Observation across the frozen sweep |
|---|---|
| color | 6% is sparse and strongly fragmented. 12-20% recovers pot/stem pieces and more short canopy arcs; 35% turns the canopy and pot texture into a dense connected network. Some structure returns but clean leaf recovery is not demonstrated. |
| axis | Canopy ink is already busy at 6%. Higher budgets strengthen pot/stem bands while making canopy arcs merge into a thicket. 35% adds pot interior texture; increased long-component fraction does not resolve leaf identity. |
| opacity | 12-20% returns several coherent stems and more pot outline, but canopy additions remain sparse disconnected arcs. At 35% canopy coverage rises sharply and the pot outline closes, accompanied by heavy leaf/pot clutter. No budget gives clean full-plant line recovery. |
| flattening | 12% strengthens stems and adds canopy arcs; 20% closes the pot outline and connects many canopy branches. 35% mostly thickens/joins an already crowded canopy and adds pot texture. Pot/stem recovery is coherent; leaf-level structure remains ambiguous. |
| planarity | 12-20% returns pot/stem outlines, but already dense canopy responses merge and thicken. 35% adds pot texture and crowded leaf arcs. This is not evidence that more connected canopy ink is more correct. |
| agreement | 12-20% recovers pot/stem bands while connecting many short canopy arcs. 35% adds further fill/branching and pot texture; leaf separation is not recovered. |
| surface | 12-20% strengthens pot/stem bands and makes canopy ink highly connected; 35% adds limited clean structure beyond those bands, with more canopy and pot texture. No clean canopy sweet spot is established. |

## Verification and unchanged inputs

Tests were written before implementation and first failed because src.density_ridge_threshold_sweep.py did not exist. All **6 new tests** and **152 full-suite tests** pass. Tests cover exact pooled counts/ties, positive candidate exhaustion, nesting/repeatability, 8-connected area boundaries/merging, deliberate nonnesting rejection, and real-grid 6% reproduction before matching.

The independent verifier uses lexicographic score/index sorting to reconstruct every raw selection and an independent 8-connected label/area filter to reconstruct every cleanup. It recomputes all saved mask metrics, thresholds, counts, support coverage, cleanup retention, reference differences and nesting records. All output masks have boolean dtype and shape (4,7,H,W); reference is (7,H,W), support is (H,W). All numeric source/output arrays inspected are finite. Budgets and channel order are explicit NPZ entries.

A complete saved-grid selection/metrics/render rerun produced **14 byte-identical core files**: four mask NPZs, seven PNGs, metrics.json, science_hashes.json and PROTOCOL.md. Every curated copy matches. All **39 PNG copies/inspection images** decoded successfully. Hashes preserve **54 prior files**, including all four source NPZs, checkpoint PLYs, existing ridge artifacts and the original field/ridge code. Preimplementation protocol/tests are unchanged. No layout change was needed after inspection; all four new NPZs and metrics retain their pre-inspection hashes. Seven unique deliverable figures were inspected, plus four native-pixel focus detail sheets. The saved source grids were rerun through selection only; no field extraction was repeated.

## Scope and limitations

Relaxing selection cannot recover information that is already absent after field construction, Hessian gating, NMS or saved broadening. The full response context and eligible broad scores are different stages; 35% is not all Hessian response. Pooled thresholds allocate different ink to scenes and are not equal per-scene recall or coverage. Higher budgets mechanically make merging easier, so a topology gain alone is weak evidence of better lines. No fresh equal-ink baseline or threshold-specific accuracy test was run or claimed.

All results remain one 2D orthographic PCA projection, with depth superposition and no visibility control, from one seed/checkpoint per scene. The native long side is 640 pixels; enlarged figures add viewing scale, not information. Shared density coupling and similar scalar patterns remain confounded with density; no density-only ablation, ground-truth line labels, multi-view test, 3D persistence or independent blinded review is provided. Ficus leaf recovery is unresolved. These limitations cannot be fixed by labeling a visually appealing budget a scientific pass.

## Reproduction and inventory

Canonical masks, figures, metrics and logs: out/density_ridge_threshold_sweep/. Curated PNG/JSON/protocol/report: artifacts/density_ridge_threshold_sweep/. Only the canonical directory has a new narrow ignore rule. The raw NPZ keys are raw, clean, reference, support, budgets, channel_order, ordered by budget then channel. Figures display increasing saved y upward. Verification contains source/implementation/output SHA256 values and test-log hashes; preregistration.json contains the pre-run preservation hashes.

Implementation: src/density_ridge_threshold_sweep.py; scripts/render_density_ridge_threshold_sweep.py; scripts/verify_density_ridge_threshold_sweep.py; scripts/report_density_ridge_threshold_sweep.py; tests/test_density_ridge_threshold_sweep.py. Nothing was committed or pushed. Operational commands, environment and output inventory are also in /home/u00134/codex_astra_density_ridge_threshold_report.md.
