# SHIP-BLOCKER CLOSE: rebuild the camera-ready PDF for real

The frozen-thesis paper is content-complete and gate-validated at the .md level
(304/304 numeral conservation). The ONLY open ship-blocker: this machine has no
LaTeX, so paper/main.pdf is STALE and cannot be rebuilt. Fig9 + Tab5 (crown-jewel
figset, just committed) live in the .tex sources but are ABSENT from the compiled
PDF. Close this with a REAL build, no fabrication.

## Task
1. Install a no-root LaTeX toolchain into the vfsdgs env. Try in order, stop at first success:
   a. `conda install -n vfsdgs -c conda-forge tectonic -y`  (tectonic = single-binary, self-fetching packages)
   b. if conda solve too slow/fails: `mamba install ...` or download the static tectonic release binary to ~/bin.
   If ALL fail (no network to conda-forge / crates cache): STOP, write out/SHIP_PDF_STATUS.md documenting exactly what failed, and leave Fig9/Tab5 in SUPP. Do NOT fabricate a PDF or a page count.
2. On success: rebuild paper/main.pdf from the current .tex sources (tectonic paper/main.tex, or the projects existing build script if one exists). Resolve refs (run twice if needed).
3. VERIFY, report each as a real number from the built PDF (pdfinfo / pdftotext page count):
   - total pages, CONTENT pages (before References), and whether Fig9 + Tab5 actually render (grep pdftotext for their captions).
   - Re-run scripts/phase1h_gate.py against the freshly-built PDF; report numeral conservation (expect 304/304 to hold; the 2 new floats should flip from pdf-ref 0 -> present).
4. DECISION on Fig9 placement (frozen go/no-go, protect the 8-content-page budget):
   - Fig9 currently sits in SUPP (after References) = conservative, budget-safe. KEEP IT THERE.
   - ONLY promote Fig9 to the main body IF the rebuilt PDF verifiably stays <= 8 CONTENT pages with it in the body. If promotion pushes content pages to 9, REVERT to SUPP. Do not guess — measure on the real build.
5. Write out/SHIP_PDF_STATUS.md with the verified page counts, float-presence checks, gate result, and the placement decision. Commit is handled by the orchestrator.

## Invariants
Mesh EVAL-ONLY. No banked number altered. No fabricated page count / gate result — every number from a real pdfinfo/pdftotext/gate run. If you cannot build, say so plainly.
