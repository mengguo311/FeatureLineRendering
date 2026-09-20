"""Mask selection only; consumes saved scores and support without modification."""
import numpy as np

from src.density_ridge_lines import pooled_select, clean_mask

SCENES = ('lego', 'chair', 'drums', 'ficus')
BUDGETS = (.06, .12, .20, .35)


def assert_nested(masks):
    """Fail on any removed pixel between consecutive budgets (first axis)."""
    assert np.asarray(masks).dtype == np.bool_, 'Expected boolean masks'
    assert not np.any(masks[:-1] & ~masks[1:]), 'Masks are not nested'


def select_sweep(scores, supports):
    """Return per-scene (budget,H,W) raw/clean masks and pooled metadata."""
    if len(scores) != len(supports) or not scores:
        raise ValueError('Expected corresponding nonempty score/support lists')
    for score, support in zip(scores, supports):
        if score.shape != support.shape or score.ndim != 2:
            raise ValueError('Expected matching 2D score/support grids')
        if support.dtype != np.bool_ or not np.isfinite(score).all():
            raise ValueError('Expected finite scores and boolean support')
    total = sum(int(s.sum()) for s in supports)
    raw = [[] for _ in scores]; cleaned = [[] for _ in scores]; selections = []
    for budget in BUDGETS:
        masks, meta = pooled_select(scores, supports, int(budget * total))
        meta.update(budget=budget, support_pixels=total,
                    candidate_exhausted=meta['selected'] < meta['requested'])
        for i, mask in enumerate(masks):
            raw[i].append(mask)
            cleaned[i].append(clean_mask(mask, min_area=12))
        selections.append(meta)
    raw = [np.stack(m) for m in raw]; cleaned = [np.stack(m) for m in cleaned]
    for r, c in zip(raw, cleaned):
        assert_nested(r); assert_nested(c)
        assert not np.any(c & ~r)
    return raw, cleaned, selections
