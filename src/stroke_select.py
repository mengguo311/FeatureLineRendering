"""VRSS: deterministic global whole-path selection. NumPy only; no geometry IO.

Relations are AND bundles; alternate bundles for the same evidence use max,
not sum. Missing evidence stays in the per-view normalizer. This is a bounded
heuristic, not an exact integer-program solver or a submodularity claim.
"""
import itertools
import time
import numpy as np


def mean_lowest(q, fraction=.25):
    q = np.asarray(q, float)
    return float(np.sort(q)[:max(1, int(np.ceil(len(q)*fraction)))].mean())


class Objective:
    def __init__(self, unary, costs, relations=(), relation_counts=None, overlap=(),
                 alpha=.5, beta=.1, tail_fraction=.25):
        self.u = np.asarray(unary, float)  # [view, path], already normalized
        self.costs = np.asarray(costs, float)
        self.V, self.N = self.u.shape
        if self.costs.shape != (self.N,) or np.any(self.costs < 0):
            raise ValueError('invalid costs')
        if not np.isfinite(self.u).all() or not np.isfinite(self.costs).all():
            raise ValueError('nonfinite objective')
        self.relations = list(relations)
        self.counts = np.maximum(1, np.asarray(relation_counts if relation_counts is not None else np.ones(self.V), float))
        self.overlap = list(overlap)  # (view, path i, path j, normalized length)
        self.alpha, self.beta, self.tail_fraction = alpha, beta, tail_fraction
        self.bundles = sorted({tuple(sorted(b['ids'])) for e in self.relations for b in e['bundles']})
        self.by_id = [set() for _ in range(self.N)]
        for ei, e in enumerate(self.relations):
            for b in e['bundles']:
                if len(b['ids']) not in (2, 3) or len(set(b['ids'])) != len(b['ids']):
                    raise ValueError('relation bundle must contain 2 or 3 distinct paths')
                for i in b['ids']:
                    self.by_id[i].add(ei)
        self.ov_by_id = [set() for _ in range(self.N)]
        for k, (_, i, j, _) in enumerate(self.overlap):
            self.ov_by_id[i].add(k); self.ov_by_id[j].add(k)

    def relation_value(self, e, x):
        return max([b['score'] for b in e['bundles'] if all(x[i] for i in b['ids'])] + [0.])

    def parts(self, x):
        x = np.asarray(x, bool)
        u = self.u[:, x].sum(1)
        r, d = np.zeros(self.V), np.zeros(self.V)
        for e in self.relations:
            r[e['view']] += self.relation_value(e, x) / self.counts[e['view']]
        for v, i, j, value in self.overlap:
            if x[i] and x[j]:
                d[v] += value
        return u, r, d

    def q(self, x, mode='D'):
        u, r, d = self.parts(x)
        if mode == 'A':
            return u
        if mode == 'B':
            return u - self.beta*d
        return self.alpha*u + (1-self.alpha)*r - self.beta*d

    def scalar(self, q, mode):
        return float(np.mean(q)) if mode in ('A', 'C') else mean_lowest(q, self.tail_fraction)

    def changed_q(self, x, q, add, remove=(), mode='D'):
        """Exact sparse delta including alternative max-bundles and overlap."""
        y = x.copy(); y[list(remove)] = False; y[list(add)] = True
        changed = np.flatnonzero(y != x)
        sign = y[changed].astype(float) - x[changed].astype(float)
        du = self.u[:, changed] @ sign
        out = q.copy() + du * (1. if mode in ('A', 'B') else self.alpha)
        if mode not in ('A', 'B'):
            affected = set().union(*(self.by_id[i] for i in changed)) if len(changed) else set()
            for ei in sorted(affected):
                e = self.relations[ei]; v = e['view']
                out[v] += (1-self.alpha)*(self.relation_value(e, y)-self.relation_value(e, x))/self.counts[v]
        if mode != 'A':
            affected = set().union(*(self.ov_by_id[i] for i in changed)) if len(changed) else set()
            for oi in sorted(affected):
                v, i, j, value = self.overlap[oi]
                out[v] -= self.beta*value*(int(y[i] and y[j])-int(x[i] and x[j]))
        return out


def select(obj, budget, mode='D', max_greedy_steps=2048, max_swap_passes=2,
           swap_shortlist=32):
    """All feasible singleton/bundle greedy actions; bounded 1↔1/1↔2/2↔1 swaps.

    Adds the best gain/cost action even when nonpositive to keep density matched.
    Zero-cost (never visible in TRAIN) paths are excluded, never obtained for free.
    """
    if mode not in 'ABCD':
        raise ValueError(mode)
    t0 = time.perf_counter(); x = np.zeros(obj.N, bool)
    valid = obj.costs > 1e-12
    independent = obj.u.mean(0) / np.maximum(obj.costs, 1e-12)
    order = np.argsort(-independent, kind='stable')
    spent = 0.; steps = 0; swaps = 0
    if mode == 'A':
        for i in order:
            if valid[i] and spent+obj.costs[i] <= budget+1e-12:
                x[i] = True; spent += obj.costs[i]; steps += 1
    else:
        actions = [(int(i),) for i in range(obj.N) if valid[i]]
        if mode != 'B':
            actions += [b for b in obj.bundles if all(valid[list(b)])]
        q = obj.q(x, mode)
        for step in range(max_greedy_steps):
            current = obj.scalar(q, mode); best = None; seen = set()
            for bundle in actions:
                add = tuple(i for i in bundle if not x[i])
                if not add or add in seen:
                    continue
                seen.add(add); cost = obj.costs[list(add)].sum()
                if spent+cost > budget+1e-12:
                    continue
                nq = obj.changed_q(x, q, add, mode=mode)
                gain = obj.scalar(nq, mode)-current
                key = (gain/cost, gain, tuple(-i for i in add))
                if best is None or key > best[0]:
                    best = (key, add, cost, nq)
            if best is None:
                break
            _, add, cost, q = best
            x[list(add)] = True; spent += cost; steps += 1
        # Bound work independently of candidate size. Equal deterministic unary
        # shortlist for all ablations; no post-hoc image-based tuning.
        for _ in range(max_swap_passes):
            inside = [int(i) for i in order[::-1] if x[i]][:swap_shortlist]
            outside = [int(i) for i in order if not x[i] and valid[i]][:swap_shortlist]
            adds = [(i,) for i in outside]
            if mode != 'B':
                adds += [b for b in obj.bundles if len(b)==2 and all(i in outside for i in b)]
            else:
                adds += list(itertools.combinations(outside[:8], 2))
            removes = [(i,) for i in inside] + list(itertools.combinations(inside[:8], 2))
            current = obj.scalar(q, mode); best = None
            for add in adds:
                for rem in removes:
                    if len(add)+len(rem)>3:
                        continue
                    cost = spent + obj.costs[list(add)].sum()-obj.costs[list(rem)].sum()
                    # No swap may buy quality by materially reducing ink budget.
                    if cost > budget+1e-12 or cost < min(spent, budget*.9875)-1e-12:
                        continue
                    nq = obj.changed_q(x, q, add, rem, mode)
                    gain = obj.scalar(nq, mode)-current
                    if gain > 1e-12 and (best is None or gain > best[0]):
                        best = (gain, add, rem, cost, nq)
            if best is None:
                break
            _, add, rem, spent, q = best
            x[list(rem)] = False; x[list(add)] = True; swaps += 1
        # Fill remaining feasible slack after the bounded swaps.
        for i in order:
            if not x[i] and valid[i] and spent+obj.costs[i] <= budget+1e-12:
                x[i] = True; spent += obj.costs[i]
    u, r, d = obj.parts(x); q = obj.q(x, 'D')
    audit = {'selector':mode, 'selected_ids':np.flatnonzero(x).tolist(),
        'n_selected':int(x.sum()), 'cost':float(obj.costs[x].sum()), 'budget':float(budget),
        'pool_cost':float(obj.costs.sum()), 'spent_fraction_of_pool':float(obj.costs[x].sum()/max(obj.costs.sum(),1e-12)),
        'U':u.tolist(),'R':r.tolist(),'D_overlap':d.tolist(),'q_common':q.tolist(),
        'q_common_mean':float(q.mean()),'q_common_worst25':mean_lowest(q, obj.tail_fraction),
        'optimized_objective':obj.scalar(obj.q(x, mode), mode),
        'greedy_steps':steps,'swaps':swaps,'seconds':time.perf_counter()-t0}
    assert audit['cost'] <= budget+1e-9
    return x, audit
