# CAMERA_READY_CHECKLIST — read-only integrity pass (camera_ready_spec.md)

Invariants honored: no experiment recomputed or unfrozen; no result json touched; no
headline number altered; mesh-never-in-method-path untouched. Fixes below are prose/
reference drift only, each logged.

## 1. Figure/table completeness — **PASS** (1 fix, 2 notes)
All 13 assets exist on disk: fig1_teaser, pareto_{chair,lego} (=Fig 2), fig3_pareto2,
fig4_pareto3, fig5_survival, fig6_ceiling, fig7_semantic, fig8_supervision,
tab1_stroke_ratios, tab2_floor_anatomy, tab3_kgeom, tab4_gate_ledger.
Reference counts in PAPER_DRAFT.md: Fig 1×1, Fig 2×5, Fig 3×2, Fig 4×2, Fig 5×2, Fig 6×4,
Fig 7×2, Fig 8×1, Tab 1×3, Tab 2×1, Tab 3×3, Tab 4×1 (after FIX-A). Embedded caption
numbers match assigned numbers for Figs 1,3–8 and Tabs 1–4.
- **FIX-A**: Tab 4 had zero body references (its "(Tab 4)" citation was lost in the
  cold-read rewrite of §7) — restored in §7's gates sentence.
- Note 1: the two Fig-2 pngs carry no embedded "Fig 2" caption number (titles are
  scene-descriptive); not a wrong number — left as-is, renumbering would require
  re-rendering, out of scope for a read-only pass.
- Note 2: assets table lists Tab 1–4 as one combined row; per-asset rows exist for figures.

## 2. Number-consistency grep — **PASS** (0 fixes; 1 false positive logged)
Occurrence counts in PAPER_DRAFT.md (all qualified in-passage, verified programmatically
with context windows; identical results across the SEC*/ABSTRACT source drafts):
1.72–8.35×: 4 (each with gate-breach + 0.6371 + n=2 in-passage — re-verified after
re-assembly: 4/4 PASS) · 0.8401: 6 and 0.9044: 7 (every one with the collapse/guarded
context) · 0.3964: 6 (all GT-mesh framing) · 0.7908: 3 (all paired with 0.5572) ·
0.407: 2 (both same-sentence "worse") · ≥9.8×: 5 · 1.98×: 4 (all "interior").
- False positive logged, no change: the checker flagged §4.2's "≥9.8× less than per-frame
  Canny and PiDiNet" as missing "memoryless" — the qualifier is the subsection's own title
  ("Against memoryless per-frame detection", 3 lines above) and the sentence names the
  memoryless detectors explicitly.

## 3. Section-assembly check — **PASS** (1 fix)
Order verified: Title → Abstract → §1 (with contribution box) → §2 → §3 (3.1–3.5) →
§4 (4.1–4.5) → §5 (5.1–5.5) → §6 → §7 → assets table. No duplicate or missing section.
- **FIX-B**: CONTRIB_BOX.md had drifted from the paper's post-cold-read bullets — it still
  carried the banned "frozen conservative floor" phrasing and the "primitive" noun.
  Synced: gate-breach wording, finding-noun, n=2 + precision-bound qualifier added.
  Box and abstract claims now consistent.

## 4. Trace-chain spot check — **PASS** (3/3)
| claim (paper) | source file | value |
|---|---|---|
| §4.4 interior pop rates 0.0425 vs 0.0214 (1.98×) | pareto3_lego_T3_disocc.json | 0.0425 / 0.0214 / 1.98 ✓ |
| §5.4 best mesh-free anywhere: photometric 0.7326 (chair) / 0.5637 (lego) | dexprimary_p1d.json | 0.7326 / 0.5637 ✓ |
| §4.3 shared-point P ranges + counts 9/8/3/5 of 21 | pareto2_verdict.json | chair 0.28–0.59, lego 0.62–0.64, counts ✓ (after FIX-C) |

## 5. Fix log — 3 fixes, all prose/reference drift, zero value changes to banked numbers
- FIX-A (§7 source + assembly): "(the full ledger is Tab 4)" reference restored.
- FIX-B (CONTRIB_BOX.md): synced to canonical post-cold-read wording (see §3 above).
- FIX-C (§4.3 source + assembly): chair shared-point range corrected from "0.30–0.59"
  (a T1-only span, my transcription error) to the source-exact joint span "0.28–0.59",
  and lego stated as "0.62–0.64" instead of "≈0.63" — corrections TOWARD the source
  (pareto2_verdict.json), not alterations of any banked value.

## Verdict: **PASS** — 3 drifts found and fixed at source, re-assembled, re-verified.
