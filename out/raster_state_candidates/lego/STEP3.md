# Step 3: TRAIN aggregation checkpoint

Actual elapsed: 17.60 s. Full real B/C/D produce 712/293/2,938 clusters;
accepted support medians are 3/4/4 TRAIN views. All become fixed initial 3D
linelets with stored IDs, support views, covariance, source tags and tangent fit.

Matched observation comparisons (real / ID shuffle / spatial shift):

| Source | Observations per arm | Accepted real | ID shuffle | Shift |
|---|---:|---:|---:|---:|
| top-k B | 7,119 | 586 | 0 | 184 |
| RGB C | 4,107 | 293 | 0 | 34 |
| union D | 37,706 | 2,717 | 0 | 1,573 |

The preregistered 1.5x descriptive persistence effect holds (3.18x/8.62x/1.73x).
This is not a statistical significance result or a visual GO. N1 is a deliberately
limited control: it breaks the identity grouping requirement while keeping anchors.
N2 is stronger: many unrelated image responses still form persistent clusters.

Personally inspected the full four-view `step3/aggregation_train.png`.
The union outlines parts of the roof/arm/body but remains a field of short broken
marks. Shifted fields also trace some object extent. No semantic or downstream
benefit is established yet. Continue all six frozen downstream arms without tuning.
