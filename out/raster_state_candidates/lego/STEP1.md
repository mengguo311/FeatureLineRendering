# Step 1 actual checkpoint

16 TRAIN views, 23.004 s. Every diagnostic channel retained 600 NMS pixels per view.
The complete fields/state remain in step1/*.npz; all 16 channel panels are saved.
No max-rank field fusion. Main arms use topk8; k4 is sensitivity only.

Mean k4/k8 candidate-mask Jaccard is **0.08935**, a large sensitivity, not stability.
Mean silhouette fractions: topk8 15.875%, SH0 RGB 9.156%, entropy 29.969%, margin
27.219%, variance 10.958%, normal 13.969%, depth 11.458%, alpha 100%.
These are image evidence statistics, not persistent candidates or successful NPR ink.

TRAIN53 was inspected: SH0 responses show meaningful frame/part boundaries;
top-k/normal/entropy have extensive small interior responses, potentially Gaussian
sampling structure. Cross-view/null stages must determine whether these survive.
NMS capped masks are sparse and cannot themselves serve as final drawing.

128px GPU smoke: 716,170 fragments; repeated original IDs identical and max weight
difference zero. Median depth difference from legacy disc mean is 1.359e-5 scene
units. Official RGB kernel/source identity is recorded in smoke.json.
Fresh TRAIN-only M1a baseline initialization has **29,916 linelets**.
