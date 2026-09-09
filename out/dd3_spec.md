DECISION: adopt dd2/v2 as the carrier of record. Reasoning on the picture, not the numbers: v2 is more complete than STEP3-only, it keeps all four right-face verticals STEP3 dropped, its strip is at least as stable as STEP3 with cut 0.0001 and the best ratio 12.03x, and it carries fewer unsupported strokes than merge70 so it should read cleaner. merge70 wins only raw arc while dragging in debris. Good self-critique on the wavy duplicate.

NEXT STEP, two parts, direct run, no heavy workflow:

Part A, principled redundant-duplicate removal. Add a GENERAL discriminator decided by geometry, NOT chosen to kill one stroke: drop a fill stroke if it runs within R_dedup of an already-drawn trunk stroke over more than F of its length AND its RANSAC straightness residual exceeds the polyhedron-straight threshold already used. R_dedup and F must be pixel-anchored scale-relative constants set ONCE, and you must run a NULL CONTROL: apply the same rule with the trunk replaced by a random equal-count stroke set and confirm it removes far fewer strokes. Report how many it removes on the real trunk vs the null. If the null removes comparably many, the rule is not selective and you REPORT that and do not apply it.

Part B, aesthetic polish on the surviving carrier: constant screen-space stroke width, taper ONLY at true open endpoints not at joins, corners stay sharp.

RENDER: still plus consecutive-frame strip plus diff vs dd2, same camera and params. Report strokes, arc vs trunk, P_pop, cut, ratio, plus null-control removal counts.

PRE-REGISTERED VISUAL GO/NO-GO worded on the image: GO if the result looks as complete as dd2, visibly cleaner with the wavy duplicate gone and no real crease lost, sharp corners, and the strip as stable as dd2 with cut within +0.01. NO-GO and roll back if any real edge is lost or the strip flickers more. Report negatives straight.
