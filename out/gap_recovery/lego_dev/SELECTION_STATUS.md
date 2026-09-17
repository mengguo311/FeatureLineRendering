# Frozen automatic selection, before validation/final cameras

Selection executed at `20148465e5aaf7fa0677517f2754555a34ef6e5f`, 11.124 s.
405 geometric hypotheses; 67 pass image gates, 306 lack three supported views,
18 have depth/background veto, 14 fail support-rate consistency.
Object-only selects 20; object+image selects 20. Both use <1.03% added visible length
on every fit view; the 20-bridge cap binds before the 5% ink cap.

**The experiment already cannot pass the preregistered G1 gate:** only b71 of
{71,152,153} is selected by object+image. b152 has 3/8 supporting qualified fit
views (37.5%); b153 has 2/7 (28.6%). Their geometry passed the same object gates.
This does not establish whether those failures arise from imperfect 3D hypotheses,
nearest-edge tangent ambiguity, or the visual G1 interpretation. No rescue tuning.

The complete fixed-path video and held-out TRAIN validation will still be generated
to finish the negative experiment and inspect every bridge. No second scene.
Human G1 annotation was consulted only for this report, after automatic selection.
