Orchestrator approval — apply the strictly-better single-column Fig 1 variant + fix two stale docs. Shipping-polish only; retrain pivot is already KILLED and banked.

1. Apply SHIP_PDF_STATUS.md §0.4: change Fig 1 from
   \begin{figure*}[t] ... \includegraphics[width=0.36\textwidth]{assets/fig1_teaser.png} ... \end{figure*}
   to
   \begin{figure}[t] ... \includegraphics[width=\columnwidth]{assets/fig1_teaser.png} ... \end{figure}
   Leave Fig 5 at 0.53. Change ONLY Fig 1's float class + width. Touch no prose, no other float, no assets, no scripts.

2. Rebuild main.pdf in the `latex` conda env (tectonic). Re-verify ALL frozen guardrails on the BUILT artifact:
   - gate: content_pages==8, references_start_page==9, conservation PASS 304/304 & 133/133, unresolved_refs==0
   - G1: the 180-word red-team threshold paragraph present verbatim in body (reading-order pdftotext)
   - G2: Fig 9 still width=0.98\textwidth, printed ~7.00in unchanged, supp_floats.tex untouched
   - Fig 1 now single-column, printed ~3.487in, on p1
   If ANY guardrail fails, REVERT to the shipped 0.36 figure* config and report the failure — do not force it.

3. Fix the two stale docs flagged in SHIP_PDF_STATUS §8:
   - out/CROWNJEWEL_FIGSET.md: correct the false "no LaTeX toolchain / conda bin/ empty" claim (tectonic 0.17.0 in env `latex`, 0.16.9 in env `tex`).
   - out/LATEX_ASSEMBLY_CHECK.md: "all 13 assets" -> 15; add Fig 9 and Tab 5 to the supplementary-float enumeration and to the per-float reference-count list (each md 1 / pdf_ref 1).

4. Update out/SHIP_PDF_STATUS.md to reflect single-column Fig 1 as the shipped config. Report the final gate JSON.

Invariants: mesh EVAL-ONLY, no method-path/scripts change, no banked number altered, no fabrication, held-out eval preserved. Stage explicitly (NEVER git add -A — main.log & ship_*_spec.md stay untracked).
