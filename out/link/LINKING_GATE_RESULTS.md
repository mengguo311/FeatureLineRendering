# AGGRESSIVE 3D LINKING — precision-safe continuity gate (kill-test)

**VERDICT: MARGINAL** — frozen rule: GO iff a bridge-ON operating point has C up >= +25% on chair AND lego, P@1.5 drop <= 0.010 chair / 0.015 lego, Phi_pop <= 1.05x baseline; NO-GO iff every setting reaching +25% fails precision or temporal. GO fails on the CONTINUITY criterion only: best bridge-ON points chair dmax3x_bridgeON_tau0.5 (+20.9%, dP +0.0002, Phi x0.761), lego dmax3x_bridgeON_tau0.5 (+13.8%, dP -0.0029, Phi x0.976). Settings reaching +25%: chair: ['dmax3x_bridgeOFF_tau0.5'] (failing P/temporal: none); lego: none (failing P/temporal: none). The NO-GO clause is NOT met by its letter (no +25% setting fails precision or temporal; lego never reaches +25%), so the verdict is MARGINAL — orchestrator + agy reconcile.

## chair

Shipped input `linelets_chair_gated_test.npz` (16039 kept linelets -> 1166 chains); median full linelet length **0.01825** world; r_surf 0.01875; tau_edge (p25 of vertex multi-view RAW DexiNed) **0.2795**; tangent-gating arms (tau_angle:tau_col) [[0.7, 0.7], [0.5, 0.5]] (0.7 primary, 0.5 = banked chaining looseness); orbit 240 frames TEST 5->15.

| variant | links / candidates (geom, depth, evidence) | C (3D arc/stroke) | dC | P@1.5 | dP | R@1.5 | dR | Phi_pop | x banked | P_pop(count) | gate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **baseline (shipped chains)** | — | 0.06774 (n=1166) | — | 0.6582 | — | 0.5128 | — | 0.0459 | 1.000 | 0.0705 | — |
| dmax1x_bridgeON_tau0.7 | 7/2008 (16, 13, 7) | 0.06823 (n=1159) | +0.7% | 0.6583 | +0.0001 | 0.5128 | +0.0000 | 0.0452 | 0.985 | 0.0695 | fail |
| dmax1x_bridgeOFF_tau0.7 | 12/2008 (16, 13, 13) | 0.06858 (n=1154) | +1.2% | 0.6581 | -0.0001 | 0.5128 | +0.0000 | 0.0451 | 0.982 | 0.0694 | fail |
| dmax2x_bridgeON_tau0.7 | 39/10949 (119, 82, 44) | 0.07092 (n=1127) | +4.7% | 0.6589 | +0.0007 | 0.5138 | +0.0011 | 0.0422 | 0.918 | 0.0657 | fail |
| dmax2x_bridgeOFF_tau0.7 | 64/10949 (119, 82, 82) | 0.07309 (n=1102) | +7.9% | 0.6592 | +0.0010 | 0.5142 | +0.0014 | 0.0407 | 0.885 | 0.0642 | fail |
| dmax3x_bridgeON_tau0.7 | 70/26241 (322, 216, 119) | 0.07422 (n=1096) | +9.6% | 0.6569 | -0.0013 | 0.5153 | +0.0025 | 0.0403 | 0.878 | 0.0656 | fail |
| dmax3x_bridgeOFF_tau0.7 | 111/26241 (322, 216, 216) | 0.07834 (n=1055) | +15.6% | 0.6584 | +0.0001 | 0.5157 | +0.0029 | 0.0393 | 0.855 | 0.0637 | fail |
| dmax1x_bridgeON_tau0.5 | 27/2008 (59, 48, 31) | 0.06969 (n=1139) | +2.9% | 0.6585 | +0.0003 | 0.5130 | +0.0003 | 0.0427 | 0.930 | 0.0667 | fail |
| dmax1x_bridgeOFF_tau0.5 | 39/2008 (59, 48, 48) | 0.07056 (n=1127) | +4.2% | 0.6585 | +0.0002 | 0.5130 | +0.0003 | 0.0424 | 0.922 | 0.0657 | fail |
| dmax2x_bridgeON_tau0.5 | 93/10949 (368, 272, 152) | 0.07565 (n=1073) | +11.7% | 0.6596 | +0.0014 | 0.5155 | +0.0027 | 0.0380 | 0.827 | 0.0634 | fail |
| dmax2x_bridgeOFF_tau0.5 | 150/10949 (368, 272, 272) | 0.08124 (n=1016) | +19.9% | 0.6607 | +0.0025 | 0.5162 | +0.0035 | 0.0358 | 0.778 | 0.0611 | fail |
| dmax3x_bridgeON_tau0.5 | 146/26241 (887, 612, 349) | 0.08188 (n=1020) | +20.9% | 0.6585 | +0.0002 | 0.5179 | +0.0051 | 0.0350 | 0.761 | 0.0618 | fail |
| dmax3x_bridgeOFF_tau0.5 | 216/26241 (887, 612, 612) | 0.08989 (n=950) | +32.7% | 0.6600 | +0.0018 | 0.5188 | +0.0060 | 0.0353 | 0.768 | 0.0614 | fail |

## lego

Shipped input `linelets_lego_gated_test.npz` (25279 kept linelets -> 1895 chains); median full linelet length **0.01749** world; r_surf 0.01759; tau_edge (p25 of vertex multi-view RAW DexiNed) **0.2715**; tangent-gating arms (tau_angle:tau_col) [[0.7, 0.7], [0.5, 0.5]] (0.7 primary, 0.5 = banked chaining looseness); orbit 240 frames TEST 5->15.

| variant | links / candidates (geom, depth, evidence) | C (3D arc/stroke) | dC | P@1.5 | dP | R@1.5 | dR | Phi_pop | x banked | P_pop(count) | gate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **baseline (shipped chains)** | — | 0.06557 (n=1895) | — | 0.6085 | — | 0.2417 | — | 0.0414 | 1.000 | 0.0594 | — |
| dmax1x_bridgeON_tau0.7 | 8/1925 (20, 9, 8) | 0.06590 (n=1887) | +0.5% | 0.6085 | -0.0001 | 0.2418 | +0.0000 | 0.0415 | 1.001 | 0.0595 | fail |
| dmax1x_bridgeOFF_tau0.7 | 9/1925 (20, 9, 9) | 0.06594 (n=1886) | +0.6% | 0.6085 | -0.0001 | 0.2418 | +0.0000 | 0.0415 | 1.002 | 0.0595 | fail |
| dmax2x_bridgeON_tau0.7 | 34/9301 (96, 51, 39) | 0.06720 (n=1861) | +2.5% | 0.6082 | -0.0003 | 0.2420 | +0.0003 | 0.0404 | 0.975 | 0.0579 | fail |
| dmax2x_bridgeOFF_tau0.7 | 46/9301 (96, 51, 51) | 0.06780 (n=1849) | +3.4% | 0.6082 | -0.0004 | 0.2421 | +0.0004 | 0.0405 | 0.976 | 0.0581 | fail |
| dmax3x_bridgeON_tau0.7 | 74/21806 (236, 116, 94) | 0.06962 (n=1821) | +6.2% | 0.6072 | -0.0014 | 0.2433 | +0.0016 | 0.0400 | 0.966 | 0.0567 | fail |
| dmax3x_bridgeOFF_tau0.7 | 88/21806 (236, 116, 116) | 0.07041 (n=1807) | +7.4% | 0.6073 | -0.0012 | 0.2437 | +0.0020 | 0.0401 | 0.966 | 0.0569 | fail |
| dmax1x_bridgeON_tau0.5 | 26/1925 (53, 31, 26) | 0.06665 (n=1869) | +1.6% | 0.6083 | -0.0002 | 0.2418 | +0.0001 | 0.0413 | 0.996 | 0.0589 | fail |
| dmax1x_bridgeOFF_tau0.5 | 30/1925 (53, 31, 31) | 0.06682 (n=1865) | +1.9% | 0.6083 | -0.0002 | 0.2418 | +0.0001 | 0.0419 | 1.012 | 0.0594 | fail |
| dmax2x_bridgeON_tau0.5 | 86/9301 (240, 138, 106) | 0.06977 (n=1809) | +6.4% | 0.6081 | -0.0005 | 0.2424 | +0.0007 | 0.0413 | 0.996 | 0.0570 | fail |
| dmax2x_bridgeOFF_tau0.5 | 109/9301 (240, 138, 138) | 0.07097 (n=1786) | +8.2% | 0.6082 | -0.0004 | 0.2427 | +0.0010 | 0.0421 | 1.016 | 0.0577 | fail |
| dmax3x_bridgeON_tau0.5 | 161/21806 (612, 329, 246) | 0.07463 (n=1734) | +13.8% | 0.6056 | -0.0029 | 0.2442 | +0.0025 | 0.0404 | 0.976 | 0.0575 | fail |
| dmax3x_bridgeOFF_tau0.5 | 203/21806 (612, 329, 329) | 0.07733 (n=1692) | +17.9% | 0.6065 | -0.0021 | 0.2455 | +0.0037 | 0.0412 | 0.994 | 0.0587 | fail |

Per-scene JSON: `out/link/linkgate_<scene>.json`; viz `out/link/linkgate_<scene>_viz_v25.png` (shipped vs best bridge-ON variant, bridges in orange).