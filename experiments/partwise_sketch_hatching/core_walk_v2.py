"""Versioned P0 crease repair. Original core.py remains byte-for-byte frozen."""
from core import *  # Reuse unchanged geometry, fields, rendering, and metrics.


def transport_tangent(mesh, face, neighbor, edge, direction):
    """Rotate the tangent about the shared edge, mapping oriented face normals."""
    ids = mesh["faces"][face]
    axis = unit(mesh["vertices"][ids[(edge+2) % 3]] -
                mesh["vertices"][ids[(edge+1) % 3]])
    n0, n1 = mesh["normals"][[face, neighbor]]
    cosine = float(np.clip(n0@n1, -1., 1.))
    sine = float(axis@np.cross(n0, n1))
    rotated = (cosine*direction + sine*np.cross(axis, direction) +
               (1-cosine)*axis*(axis@direction))
    return tangent(n1, rotated)


def bary_derivative(mesh, face, direction):
    d = mesh["pinv"][face]@direction
    return np.array([-d.sum(), d[0], d[1]])


def walk(mesh, face, bary, part, style, layer, angle, length, step, sign,
         audit=None):
    """Integrate with exact edge anchors and measured, never invented, progress.

    A crease transports the prior direction before orienting the local line field.
    An incompatible entry field or ambiguous vertex ends the half-path. These
    terminations are exposed to the caller, not hidden by nudges or iteration caps.
    """
    if step <= 0 or length < 0:
        raise ValueError("walk requires positive step and nonnegative length")
    bary = np.asarray(bary, float).copy()
    ff, bb = [face], [bary.copy()]
    scale = max(1., float(np.linalg.norm(np.ptp(mesh["vertices"], axis=0))))
    arc_eps = 64*np.finfo(float).eps*scale
    bary_eps = 1e-12
    arc = 0.
    previous = None
    crossings = 0
    zero_edge_states = {}
    reason = "iteration_cap"
    for iteration in range(800):
        remain = length-arc
        if remain <= arc_eps:
            reason = "length_reached"
            break
        x = bary@mesh["tri"][face]
        direction = field(mesh, face, x, style, part, layer, angle)*sign
        if previous is not None and direction@previous < 0:
            direction = -direction
        db = bary_derivative(mesh, face, direction)
        times = np.full(3, np.inf)
        negative = db < -bary_eps
        times[negative] = -bary[negative]/db[negative]
        edge = int(np.argmin(times))
        hit = float(times[edge])
        h = min(step, remain)
        crossing = hit <= h
        travel = max(0., hit) if crossing else h
        new = bary+travel*db
        new[np.abs(new) < bary_eps] = 0.
        if new.min() < -bary_eps:
            raise RuntimeError("walk escaped its face")
        new = np.maximum(new, 0.)
        new /= new.sum()
        point = new@mesh["tri"][face]
        measured = float(np.linalg.norm(point-x))
        if abs(measured-travel) > 1e-10*scale:
            raise RuntimeError("geometric arc and unit-tangent travel disagree")
        if measured > arc_eps:
            ff.append(face); bb.append(new.copy())
            arc += measured
        elif not crossing:
            reason = "no_progress"
            break
        bary = new
        previous = direction
        if length-arc <= arc_eps:
            reason = "length_reached"
            break
        if not crossing:
            continue
        if np.count_nonzero(bary <= bary_eps) >= 2:
            reason = "ambiguous_vertex"
            break
        neighbor = int(mesh["adj"][face, edge])
        if neighbor < 0:
            reason = "physical_boundary"
            break
        if mesh["parts"][neighbor] != part:
            reason = "part_boundary"
            break
        state = (face, neighbor)
        if state in zero_edge_states and arc-zero_edge_states[state] <= arc_eps:
            reason = "no_progress_cycle"
            break
        zero_edge_states[state] = arc
        transported = transport_tangent(mesh, face, neighbor, edge, direction)
        next_bary = barycentric(mesh, neighbor, point)
        if next_bary.min() < -bary_eps:
            raise RuntimeError("shared edge does not lie in adjacent face")
        next_bary[np.abs(next_bary) < bary_eps] = 0.
        next_bary = np.maximum(next_bary, 0.)
        next_bary /= next_bary.sum()
        entry = np.flatnonzero(mesh["adj"][neighbor] == face)
        if len(entry) != 1:
            raise RuntimeError("ambiguous mesh adjacency")
        next_direction = field(mesh, neighbor, point, style, part, layer, angle)*sign
        alignment = float(next_direction@transported)
        if abs(alignment) <= bary_eps:
            reason = "ambiguous_field_alignment"
            break
        if alignment < 0:
            next_direction = -next_direction
        next_db = bary_derivative(mesh, neighbor, next_direction)
        if next_db[entry[0]] <= bary_eps:
            reason = "incompatible_entry_field"
            break
        # Duplicate boundary coordinates encode a change of owning triangle.
        # They add zero geometric arc and are not an interior nudge.
        face = neighbor
        bary = next_bary
        previous = transported
        ff.append(face); bb.append(bary.copy())
        crossings += 1
    if audit is not None:
        audit.update({"reason": reason, "requested_length_world": float(length),
                      "arc_world": float(arc), "remaining_world": max(0., float(length-arc)),
                      "iterations": iteration+1, "crossings": crossings,
                      "samples": len(ff), "numerical_arc_epsilon_world": arc_eps})
    return ff, bb


def generate_strokes(mesh, cfg, style="mixed", only_part=None, angle=0., counts=None):
    # Sampling, IDs, style rules and ink are identical to the frozen implementation.
    strokes = []
    counts = counts or cfg["strokes"]["counts_by_part"]
    for part in (1, 2, 3):
        if only_part is not None and only_part != part:
            continue
        rng = np.random.default_rng(np.random.SeedSequence([cfg["seed"], part]))
        candidates = np.flatnonzero(mesh["parts"] == part)
        prob = mesh["areas"][candidates]; prob = prob/prob.sum()
        layers = 2 if style == "cross" or (style == "mixed" and part == 3) else 1
        for i in range(int(counts[str(part)])):
            face = int(rng.choice(candidates, p=prob))
            q = rng.random(2); sq = np.sqrt(q[0])
            bary = np.array([1-sq, sq*(1-q[1]), sq*q[1]])
            length = cfg["strokes"]["length_by_part"][str(part)]
            for layer in range(layers):
                audits = [{}, {}]
                fa, ba = walk(mesh, face, bary, part, style, layer, angle, length/2,
                              cfg["strokes"]["step_world"], -1, audits[0])
                fb, bb = walk(mesh, face, bary, part, style, layer, angle, length/2,
                              cfg["strokes"]["step_world"], 1, audits[1])
                faces = np.array(fa[::-1]+fb[1:], np.int32)
                barys = np.array(ba[::-1]+bb[1:])
                n = mesh["normals"][face]
                light = unit([-1, 2, 1])
                ink = .30+.55*(1-max(0., float(n@light)))
                strokes.append({"id": f"p{part}:seed{i:04d}:layer{layer}",
                                "part": part, "style": style, "angle": angle, "layer": layer,
                                "faces": faces, "bary": barys, "ink": ink,
                                "walk_audit": audits, "seed_face": face, "seed_bary": bary.copy()})
    return strokes


def edit_part(mesh, strokes, cfg, part, angle, counts=None):
    old = [s for s in strokes if s["part"] != part]
    return sorted(old+generate_strokes(mesh, cfg, "mixed", part, angle, counts),
                  key=lambda s: s["id"])
