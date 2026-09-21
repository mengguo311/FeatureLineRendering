Stopped at G0: **ENGINEERING_NOT_READY**. The first eight front-to-back contributors capture only 24–46% of foreground alpha across the four frozen scenes. No G1 line-quality conclusion or G2/G3 persistence claim is supported.

The native reader, replay, original-ID/depth checks and full-intrinsics calibration pass. The frozen coverage gate fails in all four scenes. No detector, lifting, paths or orbit was implemented after the failure.

- [Protocol](PROTOCOL.md) and [exact inputs/cameras](INPUTS.json)
- [Gate results](GATES.json), [verification](VERIFICATION.json), [access audit](ACCESS_AUDIT.json)
- [Visual review](VISUAL_REVIEW.json) and complete sheets: [Lego](lego_g0.png), [Chair](chair_g0.png), [Drums](drums_g0.png), [Ficus](ficus_g0.png)
- [RED/GREEN command journal](TDD.jsonl), [final source hashes](FINAL_SOURCES.json), [changed files](CHANGED_FILES.txt)

Full operational report: `/home/u00134/codex_astra_topk_layered_probe_report.md`.
Raw arrays, two complete deterministic runs and native-open traces: `out/topk_layered_probe/`.
164 tests pass; all 13 scientific output files are byte-identical across the rerun, with array semantics and PNG decoding verified. TEST data remained sealed in the audited scientific workers. No commit or push.
