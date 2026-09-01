# §7 — Conclusion (DRAFT v1)

We set out to extract clean, temporally stable 3D feature lines from a frozen 3DGS, and we
report exactly what that produced — two contributions, each scoped to what was measured.

**A stability primitive.** Object-space feature lines whose rendered strokes are
**1.72–8.35×** more temporally stable per condition than an oracle-flow temporally
accumulated 2D baseline — **5.19× or better in three of four scene×trajectory conditions,
with the 1.72× adversarial cell as the frozen conservative floor** — and ≥9.8× more stable
than memoryless per-frame detection, at matched precision *and* matched line density. The
stability is invariant to the acceptance threshold across the full sweep where measured,
consistent with it being a property of the object-space parameterization rather than of
line selection. The claim ships with its measured envelope: the advantage is interior
(1.98×), reverses inside disocclusion regions, and is valid for frozen reconstructions of
static scenes with known poses.

**A boundary forensics.** The primitive's precision is *not* solved, and the four-act
characterization of why is itself a contribution: coverage is capped by the frozen carrier
(0.7908/0.5572); the missing creases carry no geometric signal even under the GT mesh
(AUC 0.3964); the discriminating signal exists in frozen semantic features (0.8401/0.9044)
— and collapses under mesh-free supervision through a pre-registered gate (0.6371 vs a
0.72 bar), leaving cross-scene transfer (0.8245, one direction) as the tested route
forward. Precision on textured surfaces is supervision-bound under our frozen protocol;
we ship the boundary, measured, rather than a patch.

Methodologically, every gate in this study was frozen before its numbers existed and
evaluated on its letter; the unfavorable outcomes — including the two failed stability
gates and the supervision-bound NO-GO — are reported with the same prominence as the
favorable ones, because several of this paper's most useful sentences (the quantization
floor, the disocclusion reversal, the oracle-baseline gap) exist only because a failed
gate was dissected instead of defended. We believe the resulting object — a stability
primitive with a measured boundary — is more useful to build on than either an
undisclosed-limit system or an unmeasured negative.
