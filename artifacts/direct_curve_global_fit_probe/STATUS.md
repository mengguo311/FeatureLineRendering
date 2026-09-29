# Direct curve probe status — 2026-09-29T12:27:59.359167+00:00

COMPLETE: engineering-valid NO_GO for Lego, Chair, Drums and Ficus under the frozen configuration. All 144 fits and both four-scene evaluations are sealed. Original Lego fit arrays/hashes and prior attempts are preserved; PROTOCOL.md and INPUTS.json are unchanged.

Verification: 570 delivery checks and 873 run/rerun checks per scene passed. All 656 replay calibrations have zero RGB/alpha/wrapper error at unchanged 1/255 gate. Tests: 225 passed, one expected skip. All 776 PNGs and 16 videos decoded. Internal review covered all 32 C views and 264 primary arc frames; no independent human validation.

GPU-hour charges (both runs plus historical allowances): Lego 7.996, Chair 6.756, Drums 4.313, Ficus 3.451; each below 12. All scheduler/evaluation/monitor/review workers completed. CPU verification supervisor 1828843 completed with exit 0; scheduler PIDs were 1766378/1766379. No science job remains active.

Report: REPORT.md; gallery: index.html; proof: proof/VERIFICATION.json; delivery receipt: DELIVERY_RESUME.json. Raw sealed data and traces: out/direct_curve_global_fit_probe/. First administrative verification failure preserved and documented in DELIVERY_VERIFICATION_ATTEMPTS.md; successful proof is scheduler/resume_20260929_v2/verification_v2. Publication branch: direct-curve-global-fit-probe (see git log/origin for commit state).
