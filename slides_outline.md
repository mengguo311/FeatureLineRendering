# Proposal Defense — Slide Outline (English)

**Hybrid Object-/Image-Space Feature-Line Rendering for 3D Gaussian Splatting**
M1 proposal · Umetani Lab · ~15–18 min, ~15 slides

> Convention: each slide lists the **on-slide content** (keep it terse) and *Speaker notes* (what you say). `[FIG x]` = drop in the matching PNG from `figures/`.
> Figures: A=image-space detail, B=object-space detail, C=comparison (main), D=flicker, E=pipeline.

---

### Slide 1 — Title
- Title, your name, Umetani Lab, date.
- Subtitle: *Real-time, temporally stable line drawing for 3DGS — without mesh reconstruction or retraining.*

*Notes:* One sentence of who you are and the one-line goal.

---

### Slide 2 — The pitch (problem in one sentence)
- "I want **clean, stable feature lines** (silhouettes, creases, corners) on **3D Gaussian Splatting** scenes, **in real time**."
- Show a teaser: a 3DGS render → desired line-drawing look.
- The catch: 3DGS gives us neither a surface nor temporal structure to draw lines from.

*Notes:* Sell the application first (stylization, technical illustration, AR/VR NPR, comprehension). Then say "why it's not solved."

---

### Slide 3 — Background: what 3DGS is (and isn't)
- 3DGS = millions of **unstructured, semi-transparent Gaussian splats** (each: position μ, covariance Σ, opacity α, color SH).
- Real-time, photorealistic, easy to capture.
- **No explicit surface, no topology, no connectivity** — unlike a triangle mesh.

*Notes:* Emphasize the single fact the whole talk hinges on: *no connectivity*. That is why classical line methods don't port over.

---

### Slide 4 — Background: feature-line rendering, two paradigms
- **Image-space** (Saito–Takahashi '90): edge detection on a depth/normal **G-buffer**. Works on *any* representation.
- **Object-space** (silhouettes, suggestive contours, apparent ridges): from surface geometry/connectivity. Precise + stable.
- Each has a fatal weakness *for 3DGS* → next slide.

*Notes:* Name-drop the lineage so the committee sees you know the field. Set up the dichotomy you'll fuse.

---

### Slide 5 — The gap (motivation) — `[FIG C]`
- **(a) Image-space on 3DGS:** universal, but **noisy, jagged, semantically flat** (can't tell silhouette from crease) + **flickers**.
- **(b) Object-space:** clean, **temporally stable**, semantically labelled — **but needs a mesh, which 3DGS lacks.**
- → Neither alone is enough. **This tension is the research.**

*Notes:* This is your money slide. Be explicit and honest: panel (b) is shown on a *mesh* because object-space line drawing **cannot** run on a Gaussian soup — that impossibility is precisely the gap you fill.

---

### Slide 6 — The flicker problem — `[FIG D]`
- Two adjacent frames (camera moved 2.5°), pure image-space lines, overlaid.
- **Red = pixels that change between frames ≈ 52.5%** of all edge pixels.
- No 3D structural tracking ⇒ edges re-detected independently each frame ⇒ they swim/flicker.

*Notes:* Temporal stability is your headline contribution; this slide is the evidence that the naive approach fails it. The 52.5% number is quotable.

---

### Slide 7 — Research goal & requirements
- **Goal:** a hybrid pipeline that is **cleaner than image-space alone** and **more complete than object-space alone**.
- Hard constraints: **(1)** no mesh / no surface reconstruction, **(2)** no retraining of the 3DGS model, **(3)** real-time, **(4)** temporally stable.

*Notes:* State the constraints as commitments — they are what make the work non-trivial and what reviewers will test you on.

---

### Slide 8 — Related work & novelty positioning
- Three pillars (cite): image-space NPR (Saito–Takahashi) · object-space lines (suggestive contours, apparent ridges) · 3DGS geometry/normals (2DGS, SuGaR, DN-Splatter).
- Closest: **EdgeGaussians / LineGS / SketchSplat** — use covariance to **reconstruct 3D edges**.
- **Our difference:** we don't reconstruct geometry; we use covariance as a **render-time stabilizer**, fused with image-space, for **temporally coherent** lines. *No published hybrid does this.*

*Notes:* Pre-empt "isn't this EdgeGaussians?" — different goal (reconstruction vs. stylized stable rendering). Mention the survey caveat: you'll do a final NPAR/Expressive proceedings check before submission.

---

### Slide 9 — Proposed approach: overview — `[FIG E]`
- Two branches off one pretrained 3DGS scene:
  - **Object-space (offline):** covariance → 3D edge candidates.
  - **Image-space (per-frame):** G-buffer → raw edges.
- **Fusion:** 3D candidates **gate + temporally anchor** the 2D edges → clean, stable lines.

*Notes:* Walk the diagram left-to-right once. Stress: object branch runs **once per scene**; per-frame cost is just the G-buffer pass + a couple of screen-space passes ⇒ real-time.

---

### Slide 10 — Method I: object-space candidates from covariance
- Per Gaussian: normal n = eigenvector of smallest eigenvalue of Σ (thin axis).
- Build KNN graph over centers (topology *substitute*, **not a mesh**).
- **Local normal-structure tensor** T = Σ wⱼ nⱼ nⱼᵀ, eigenvalues λ₁≥λ₂≥λ₃:
  - λ₁≫λ₂≈λ₃ → flat (no line)
  - λ₁≈λ₂≫λ₃ → **crease**
  - λ₁≈λ₂≈λ₃ → **corner**
  - + view term |n·v|≈0 → **silhouette**

*Notes:* This is the technical crux — one principled, topology-free operator yields all three feature types and sidesteps "what is a crease without a surface?". Flag the risk you've thought about: blobby Gaussians give bad normals → anisotropy filtering + depth-normal fallback.

---

### Slide 11 — Method II: image-space G-buffer edges — `[FIG A]`
- Render depth + normal buffers via the existing splatting pipeline.
- Sobel/Canny → raw edge response (depth discontinuity = silhouettes/occlusion; normal discontinuity = creases).
- Cheap, dense, but noisy & unanchored (from Slide 6).

*Notes:* Keep short. Point out the buffers come free from rendering; mention DN-Splatter/RaDe-GS if base normals are noisy.

---

### Slide 12 — Method III: signal-specific fusion + temporal anchoring
- Project 3D candidates to screen (z-tested against depth buffer).
- **Signal-specific gate** (not one global gate):
  - crease/corner → **gated/confirmed** by object-space candidates (kills texture/noise edges).
  - silhouette → carried by **image-space depth discontinuity** (view-dependent, may have no 3D anchor).
- **Temporal anchoring:** 2D detections snap to view-independent 3D anchors that reproject smoothly + cross-frame hysteresis ⇒ no flicker.

*Notes:* The two ideas that make this better than "weighted average": (1) *signal-specific* fusion (so you don't suppress silhouettes), (2) *3D anchoring* for stability. These are your defensible novelties.

---

### Slide 13 — Evaluation plan — `[FIG D]` (as metric illustration)
- **Temporal stability:** exact-reprojection flicker metric — warp frame t→t−1 with *known camera + depth* (no optical flow needed), measure edge disagreement in co-visible regions.
- **Quality:** completeness vs. object-space-only; cleanliness/noise vs. image-space-only.
- **Baselines:** (1) pure image-space on 3DGS G-buffer, (2) mesh-then-NPR (SuGaR/2DGS → suggestive contours), (3) EdgeGaussians rendered as lines.
- **Scenes:** 3–4 standard 3DGS datasets (e.g., Mip-NeRF360, Tanks&Temples).

*Notes:* The exact-reprojection metric is a strength — you have ground-truth motion, so the flicker measure is rigorous and reproducible. Mention an optional small user study.

---

### Slide 14 — Expected contributions
- **C1.** Topology-free object-space feature-line operator (normal-structure tensor on the covariance field) — no mesh, no retraining.
- **C2.** Signal-specific fusion of 3D candidates with image-space G-buffer edges.
- **C3.** Temporal coherence via 3D anchoring + a rigorous exact-reprojection flicker metric.
- **C4.** Real-time, drop-in on any pretrained 3DGS scene.

*Notes:* Read these as the "if I succeed, these are the takeaways." Keep them crisp; they double as your paper's contribution bullets.

---

### Slide 15 — Timeline, scope & risks
- **MVP first:** creases+corners via structure tensor → gate Canny on G-buffer → flicker metric → 3–4 scenes. (Silhouettes image-space-only at first.)
- Then: silhouette handling, stylization, ablations, write-up.
- **Risks & mitigations:** noisy normals (anisotropy filter / depth fallback) · novelty due-diligence (NPAR/Expressive sweep) · scope (MVP gating).
- M1-year milestones (quarters).

*Notes:* Showing a de-risked MVP path signals you can actually finish. End on the milestone table.

---

### Slide 16 — Summary / Q&A
- One line: *3D structure (object-space) + pixel precision (image-space) → clean, stable, real-time feature lines for 3DGS, no mesh, no retraining.*
- `[FIG C]` + `[FIG E]` thumbnails as the closing visual.

*Notes:* Restate the one-sentence thesis; invite questions.

---

## Figure → slide map
| Figure | File | Slides |
|---|---|---|
| C (comparison) | `figures/fig_C_comparison.png` | 5, 16 |
| D (flicker) | `figures/fig_D_flicker.png` | 6, 13 |
| E (pipeline) | `figures/fig_E_pipeline.png` | 9, 16 |
| A (image-space detail) | `figures/fig_A_image_space.png` | 11 |
| B (object-space detail) | `figures/fig_B_object_space.png` | (backup / appendix) |

*Speaker notes are in English for an English delivery; say the word if you want them in 中文/日本語. I can also render this outline into an actual `.pptx`.*
