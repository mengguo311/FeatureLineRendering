# Multiscene foundation results

**Verdict: UNDETERMINED.**

Both routes were executed under the frozen protocol. No local scientific conclusion is inferred from an ineligible posterior.

All eight frozen 400px parent reconstruction quality prerequisites failed. Controlled RGB equivalence is reported independently but cannot override the registered parent-quality requirement. A separate Lego TRAIN1 diagnostic found official 800px rendering downsampled to400 gives33.779945dB/SSIM0.981650; direct official400 gives24.965185dB/0.875092; the frozen K400 convention gives23.451554dB/0.778988. The official and native renderers agree within4.77e-7 when given the same canonical camera. This identifies resolution dependence and a half-pixel convention mismatch as protocol/evaluation limitations, not evidence against hypothesis B. The explicitly post-hoc diagnostic then covered all eight seeds and all frozen views/backgrounds (table below); Drums remains weak even there. No diagnostic metric overrides eligibility. The preregistered validity stop was reached in every scene.

## Totals

- training_expected: 8
- training_complete: 8
- seeds_eligible: 0
- doses_expected: 36
- doses_measured: 36
- doses_rgb_passed: 35
- doses_qualified: 34
- doses_invariance_eligible: 0
- quality_view_background_rows: 512
- controlled_view_background_rows: 1152
- independent_pair_rows: 256
- posthoc_diagnostic_rows: 512
- local_probe_scenes: 0
- certified_manual_scenes: 0
- generated_mp4s: 0

## Scene gates

| Scene | Verdict | Route A eligible | Route B eligible | G0 | G1 | G2 machine | G2 manual | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|---|
| lego | UNDETERMINED | False | False | INVALID | NOT_EVALUATED | NOT_EVALUATED | UNCERTIFIED | NOT_EVALUATED | NOT_EVALUATED | UNCERTIFIED |
| chair | UNDETERMINED | False | False | INVALID | NOT_EVALUATED | NOT_EVALUATED | UNCERTIFIED | NOT_EVALUATED | NOT_EVALUATED | UNCERTIFIED |
| drums | UNDETERMINED | False | False | INVALID | NOT_EVALUATED | NOT_EVALUATED | UNCERTIFIED | NOT_EVALUATED | NOT_EVALUATED | UNCERTIFIED |
| ficus | UNDETERMINED | False | False | INVALID | NOT_EVALUATED | NOT_EVALUATED | UNCERTIFIED | NOT_EVALUATED | NOT_EVALUATED | UNCERTIFIED |

## Eight fixed training runs

All rows use final iteration 30,000. 400px quality below is the frozen foreground ROI, white background; black-background results and every view are retained in JSON.

| Scene | Seed | Complete | Gaussians | TRAIN mean PSNR | TRAIN SSIM | Validation mean PSNR | Validation SSIM | Eligible |
|---|---:|---|---:|---:|---:|---:|---:|---|
| lego | 1729 | True | 310475 | 22.090732 | 0.749387400 | 22.542845 | 0.756275679 | False |
| lego | 2718 | True | 312135 | 22.098015 | 0.749662142 | 22.560251 | 0.757338403 | False |
| chair | 1729 | True | 256690 | 20.231304 | 0.717416192 | 20.183717 | 0.703186917 | False |
| chair | 2718 | True | 243131 | 20.209106 | 0.717892362 | 20.154905 | 0.703109568 | False |
| drums | 1729 | True | 360012 | 19.554122 | 0.730178321 | 18.183033 | 0.671333227 | False |
| drums | 2718 | True | 354941 | 19.556211 | 0.730341434 | 18.190802 | 0.671295184 | False |
| ficus | 1729 | True | 284835 | 21.044935 | 0.740278190 | 20.547951 | 0.670980497 | False |
| ficus | 2718 | True | 281827 | 21.005194 | 0.739518550 | 20.557235 | 0.671438588 | False |

## Every controlled dose

A dose pass means all 32 TRAIN view/background comparisons, coverage and calibration passed. Invariance eligibility additionally requires the preregistered parent reconstruction quality. All doses are retained; none was selected for appearance.

| Scene | Dose name | Dose | Passing RGB pairs | Min PSNR | Min SSIM | Max P99 | Min parent mass | Min child mass | Dose pass | Invariance eligible |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| lego | redistribute_00 | 0.03125 | 32/32 | 64.857128 | 0.999963957 | 0.002762580 | 0.496601780 | 0.005765709 | True | False |
| lego | redistribute_01 | 0.06250 | 32/32 | 60.721763 | 0.999934194 | 0.004476917 | 0.496601780 | 0.015420698 | True | False |
| lego | redistribute_02 | 0.12500 | 32/32 | 56.126057 | 0.999865338 | 0.007650447 | 0.496601780 | 0.036912789 | True | False |
| lego | redistribute_03 | 0.25000 | 32/32 | 51.258765 | 0.999596842 | 0.013459253 | 0.496601780 | 0.083636030 | True | False |
| lego | redistribute_04 | 0.50000 | 32/32 | 47.554432 | 0.999014021 | 0.020556164 | 0.496601780 | 0.188625376 | True | False |
| lego | moment_split_00 | 0.02500 | 32/32 | 50.572073 | 0.999505693 | 0.014114434 | 0.496601780 | 0.094146873 | True | False |
| lego | moment_split_01 | 0.05000 | 32/32 | 50.209869 | 0.999453257 | 0.014577770 | 0.496601780 | 0.094372786 | True | False |
| lego | moment_split_02 | 0.10000 | 32/32 | 48.817568 | 0.999145077 | 0.015674329 | 0.496601780 | 0.094804035 | True | False |
| lego | moment_split_03 | 0.20000 | 32/32 | 46.446171 | 0.998452534 | 0.019538288 | 0.496601780 | 0.095424458 | True | False |
| chair | redistribute_00 | 0.03125 | 32/32 | 61.972993 | 0.999955465 | 0.004075811 | 0.498417269 | 0.005874548 | True | False |
| chair | redistribute_01 | 0.06250 | 32/32 | 58.138432 | 0.999931415 | 0.006353782 | 0.498417269 | 0.016070605 | True | False |
| chair | redistribute_02 | 0.12500 | 32/32 | 53.789607 | 0.999818390 | 0.010243535 | 0.498417269 | 0.037989632 | True | False |
| chair | redistribute_03 | 0.25000 | 32/32 | 49.211734 | 0.999475582 | 0.018048307 | 0.498417269 | 0.083986131 | True | False |
| chair | redistribute_04 | 0.50000 | 32/32 | 45.705633 | 0.998772178 | 0.027919869 | 0.498417269 | 0.187968367 | True | False |
| chair | moment_split_00 | 0.02500 | 32/32 | 48.685549 | 0.999367904 | 0.018748515 | 0.498417269 | 0.099517929 | True | False |
| chair | moment_split_01 | 0.05000 | 32/32 | 48.029990 | 0.999227506 | 0.019594282 | 0.498417269 | 0.099668249 | True | False |
| chair | moment_split_02 | 0.10000 | 32/32 | 47.061733 | 0.998931878 | 0.021296754 | 0.498417269 | 0.099976483 | True | False |
| chair | moment_split_03 | 0.20000 | 32/32 | 44.940615 | 0.998188602 | 0.026551023 | 0.498417269 | 0.100665555 | True | False |
| drums | redistribute_00 | 0.03125 | 32/32 | 60.487375 | 0.999946260 | 0.004650893 | 0.498543594 | 0.005346048 | True | False |
| drums | redistribute_01 | 0.06250 | 32/32 | 56.859391 | 0.999897191 | 0.006311920 | 0.498543594 | 0.015528458 | True | False |
| drums | redistribute_02 | 0.12500 | 32/32 | 52.279026 | 0.999786823 | 0.010024127 | 0.498543594 | 0.037265031 | True | False |
| drums | redistribute_03 | 0.25000 | 32/32 | 47.549919 | 0.999435919 | 0.017583954 | 0.498543594 | 0.084260804 | True | False |
| drums | redistribute_04 | 0.50000 | 32/32 | 43.768699 | 0.998668493 | 0.027554124 | 0.498543594 | 0.190202522 | True | False |
| drums | moment_split_00 | 0.02500 | 32/32 | 45.477169 | 0.999053634 | 0.019878342 | 0.498543594 | 0.100173268 | True | False |
| drums | moment_split_01 | 0.05000 | 32/32 | 43.544837 | 0.998680145 | 0.022378159 | 0.498543594 | 0.100662426 | True | False |
| drums | moment_split_02 | 0.10000 | 32/32 | 41.988133 | 0.998012166 | 0.029418455 | 0.498543594 | 0.101095795 | True | False |
| drums | moment_split_03 | 0.20000 | 26/32 | 39.908441 | 0.996432956 | 0.040103499 | 0.498543594 | 0.102128172 | False | False |
| ficus | redistribute_00 | 0.03125 | 32/32 | 58.250407 | 0.999942548 | 0.004734180 | 0.499329316 | 0.004090430 | False | False |
| ficus | redistribute_01 | 0.06250 | 32/32 | 54.750998 | 0.999870628 | 0.007160164 | 0.499329316 | 0.014218405 | True | False |
| ficus | redistribute_02 | 0.12500 | 32/32 | 52.069354 | 0.999733784 | 0.010161710 | 0.499329316 | 0.037934777 | True | False |
| ficus | redistribute_03 | 0.25000 | 32/32 | 49.536578 | 0.999437393 | 0.015570650 | 0.499329316 | 0.091074816 | True | False |
| ficus | redistribute_04 | 0.50000 | 32/32 | 46.866480 | 0.998887964 | 0.021411669 | 0.499329316 | 0.211683456 | True | False |
| ficus | moment_split_00 | 0.02500 | 32/32 | 49.192722 | 0.999282050 | 0.015981770 | 0.499329316 | 0.097596589 | True | False |
| ficus | moment_split_01 | 0.05000 | 32/32 | 48.240163 | 0.998899833 | 0.017147693 | 0.499329316 | 0.097424955 | True | False |
| ficus | moment_split_02 | 0.10000 | 32/32 | 45.597585 | 0.997641746 | 0.021576061 | 0.499329316 | 0.097371093 | True | False |
| ficus | moment_split_03 | 0.20000 | 32/32 | 43.395809 | 0.995934925 | 0.027953880 | 0.499329316 | 0.097774040 | True | False |

## Post-hoc sampling diagnosis

These are descriptive foreground-ROI white-background means for every seed and split. Native800 uses the canonical stock camera; downsampled400 area-resizes that rendered image. All black-background groups, worst-view metrics and every individual measurement remain in JSON. No diagnostic row changes eligibility.

| Scene | Seed | Split | Native800 PSNR | Native800 SSIM | Downsampled400 PSNR | Downsampled400 SSIM |
|---|---:|---|---:|---:|---:|---:|
| lego | 1729 | train | 34.679118 | 0.967280891 | 37.502349 | 0.986739985 |
| lego | 1729 | val | 32.653706 | 0.944592848 | 34.874757 | 0.974726890 |
| lego | 2718 | train | 34.726084 | 0.967197133 | 37.579650 | 0.986712011 |
| lego | 2718 | val | 32.664072 | 0.944225449 | 34.872193 | 0.974483831 |
| chair | 1729 | train | 32.609187 | 0.967878679 | 36.828172 | 0.987870272 |
| chair | 1729 | val | 29.424985 | 0.927841746 | 32.982582 | 0.966610147 |
| chair | 2718 | train | 32.564553 | 0.967520797 | 36.817409 | 0.987916287 |
| chair | 2718 | val | 29.443149 | 0.928217332 | 33.046870 | 0.967180405 |
| drums | 1729 | train | 22.941372 | 0.895462059 | 24.190079 | 0.912551679 |
| drums | 1729 | val | 19.739659 | 0.795916509 | 20.866587 | 0.832633033 |
| drums | 2718 | train | 22.928093 | 0.895410626 | 24.176005 | 0.912787982 |
| drums | 2718 | val | 19.717217 | 0.795484674 | 20.840208 | 0.832161081 |
| ficus | 1729 | train | 27.873225 | 0.954094514 | 29.032339 | 0.971511115 |
| ficus | 1729 | val | 24.038965 | 0.856540835 | 24.953044 | 0.906901495 |
| ficus | 2718 | train | 27.804258 | 0.953017181 | 28.962603 | 0.970746079 |
| ficus | 2718 | val | 24.025848 | 0.856027991 | 24.941293 | 0.906485988 |


## Scientific scope and manual status

G2 manual and G5 are UNCERTIFIED. The implementing assistant recorded 16 coarse TRAIN target candidates and 48 challenge rectangles before local outputs. These are not 12 verified cross-view spans per scene, independent annotations, or blind review. DEV and TEST photographs were not used for training, qualification, fitting or visual review.

Unreached: scene image-evidence ray profiles, H_img/axial scene inference, F/C and LOO scene repeatability, scene no-GS/PCA/shifted/random controls, surface-sample audit, DEV annotations, local glyph comparisons, 120-frame videos, independent visual review.

Synthetic unit tests establish software behavior only. They do not establish local observability, posterior invariance, GS benefit, useful glyphs or NPR quality. No UDF, curves, connected linelets, Beziers or final strokes were trained/extracted. No mesh was read.

The source, complete eight-run logs, final PLY paths/hashes, quality renders, every dose, all native arrays and access traces are inventoried in MANIFEST.json. Large files remain server-side. REPRODUCE.md records the exact protocol and commands. VERIFICATION.json records checks; TDD_LEDGER.md preserves observed RED/GREEN failures.

No threshold, parent, dose or image split was changed after results. Any corrected sampling convention or different eligibility resolution requires a new preregistration and separate output directory. This run is retained.
