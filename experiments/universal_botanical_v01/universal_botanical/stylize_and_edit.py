"""Universal Cross-Species Botanical Stylization, Manifold Deformation, Horticultural Pruning & Apical Sprouting Engine.

Operates on ANY UniversalBotanicalModel with zero scene-name hardcoding:
1. Six Artistic Style Presets + Three Same-Plant Multi-Style Compositions (Sector Symphony, Neighbor-Contrast Mosaic,
   and Sumi-e Monochrome Crown with Vivid Hero Bouquets) using exact Periodic B-Spline polar contour coordinates.
2. Scale-Free Inextensible Petiole-Hinged 3D Manifold Deformation with Exact Jacobian Covariance Transport
   (Sigma'_k = J_k Sigma_k J_k^T) and guaranteed 0.000000 drift on all containers, wooden stands, and ground beds.
3. Horticultural Organ Pruning / Crown Windowing to expose occluded inner canopy organs cleanly.
4. Data-Driven Inverse Organ Allometry & Procedural Apical Sprouting / Budding (matching each plant's empirical
   organ aspect ratio, cusp taper, and upper-crown vivid chromaticity).
"""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from .adaptive_lamina_and_graph import build_cov6_from_sq
from .schema_and_io import (
    LABEL_BASAL_SUPPORT,
    LABEL_STATIC_STAND_OR_TABLE,
    LABEL_STEM_SKELETON,
    AdaptiveOrganPatch,
    SceneGaussianCloud,
    StemSplineChain,
    UniversalBotanicalModel,
    eval_clamped_bspline,
    eval_periodic_cubic_bspline_1d,
    fit_clamped_bspline_3d,
)

SH_C0 = 0.28209479177387814

PRESET_CLASSIC_6: tuple[str, ...] = (
    "ghibli_gouache",
    "sumie_ink_wash",
    "ukiyoe_papercut",
    "pointillist_stipple",
    "sakura_watercolor",
    "cyanotype_celadon",
)

PRESET_AVANT_GARDE_6: tuple[str, ...] = (
    "vangogh_impasto",
    "copperplate_hatching",
    "stained_glass_cloisonne",
    "pop_halftone_risograph",
    "neon_venation_xray",
    "maki_e_gold_lacquer",
)

PRESET_ORDER: tuple[str, ...] = PRESET_CLASSIC_6 + PRESET_AVANT_GARDE_6

PRESET_TITLES: dict[str, str] = {
    "ghibli_gouache": "Ghibli Gouache",
    "sumie_ink_wash": "Sumi-e Ink Wash",
    "ukiyoe_papercut": "Ukiyo-e Woodblock",
    "pointillist_stipple": "3D Pointillist",
    "sakura_watercolor": "Sakura Pastel",
    "cyanotype_celadon": "Cyanotype Celadon",
    "vangogh_impasto": "Van Gogh Impasto",
    "copperplate_hatching": "Copperplate Etch",
    "stained_glass_cloisonne": "Stained Cloisonne",
    "pop_halftone_risograph": "Pop Halftone Riso",
    "neon_venation_xray": "Venation X-Ray",
    "maki_e_gold_lacquer": "Maki-e SH3 Lacquer",
}


# ---------------------------------------------------------------------------
# 1. Periodic-Spline-Aware Anatomical Coordinates (s_01, t_norm, rho)
# ---------------------------------------------------------------------------


def compute_universal_organ_polar_coords(
    model: UniversalBotanicalModel,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute anatomical base-to-apex s in [0,1], lateral t_norm, and Periodic-Spline margin fraction rho."""
    n = len(model.cloud.means)
    s_01 = np.zeros(n, dtype=np.float32)
    t_norm = np.zeros(n, dtype=np.float32)
    rho = np.zeros(n, dtype=np.float32)
    means64 = model.cloud.means.astype(np.float64)

    for org in model.organs:
        k_idx = org.kernel_indices
        if len(k_idx) == 0:
            continue
        pts = means64[k_idx]
        s_val = np.clip(((pts - org.p_base[None, :]) @ org.e1) / max(org.length, 1e-4), 0.0, 1.0)
        rel_c = pts - org.centroid[None, :]
        u_n = (rel_c @ org.e1) / max(0.5 * org.length, 1e-4)
        v_n = (rel_c @ org.e2) / max(0.5 * org.width, 1e-4)

        s_01[k_idx] = s_val.astype(np.float32)
        t_norm[k_idx] = np.clip(v_n, -1.5, 1.5).astype(np.float32)

        if org.organ_kind == "LAMINAR_BLADE":
            th = np.arctan2(v_n, u_n)
            r_env = eval_periodic_cubic_bspline_1d(org.periodic_ctrl_r, th)
            if org.apex_cusp_gamma > 1e-3:
                cusp_mod = np.maximum(1.0 - org.apex_cusp_gamma * (np.abs(np.cos(th)) ** 3) * 0.28, 0.35)
                v_eff = v_n / cusp_mod
            else:
                v_eff = v_n
            rho_val = np.hypot(u_n, v_eff) / np.maximum(r_env, 0.28)
        else:
            half_t = max(0.5 * max(org.thickness, 4.0 * model.p_med), 1e-4)
            w_n = (rel_c @ org.e3) / half_t
            rho_val = np.sqrt((u_n ** 2 + v_n ** 2 + 0.45 * (w_n ** 2)) / 1.45)

        rho[k_idx] = np.clip(rho_val, 0.0, 1.35).astype(np.float32)

    return s_01, t_norm, rho


# ---------------------------------------------------------------------------
# 2. Six Artistic Style Presets & Three Same-Plant Multi-Style Composers
# ---------------------------------------------------------------------------


def _harmonize_support_stand_and_stems(
    model: UniversalBotanicalModel,
    theme: str = "studio_cel",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Harmonize static stand, container/ground-bed, and stem skeleton without bleeding foliage paint onto vessels."""
    rgb = model.cloud.rgb_dc.copy()
    op = model.cloud.opacities.copy()
    sc = model.cloud.scales.copy()
    shs = model.cloud.shs.copy()

    lum = (0.299 * rgb[:, 0] + 0.587 * rgb[:, 1] + 0.114 * rgb[:, 2])[:, None]
    stand_m = model.kernel_labels == LABEL_STATIC_STAND_OR_TABLE
    sup_m = model.kernel_labels == LABEL_BASAL_SUPPORT
    stem_m = model.kernel_labels == LABEL_STEM_SKELETON
    bg_dom = stand_m | sup_m | stem_m

    if theme == "sumie_monochrome":
        rgb[stand_m] = np.clip(0.14 + 0.45 * lum[stand_m], 0.0, 1.0)
        rgb[sup_m] = np.clip(0.10 + 0.42 * lum[sup_m], 0.0, 1.0)
        rgb[stem_m] = np.clip(np.array([0.23, 0.21, 0.19], dtype=np.float32) * (0.55 + 0.85 * lum[stem_m]), 0.0, 1.0)
        shs[bg_dom, 1:, :] *= 0.05
    elif theme == "cyanotype":
        rgb[stand_m] = np.clip(np.array([0.08, 0.16, 0.30], dtype=np.float32) * (0.65 + 0.85 * lum[stand_m]), 0.0, 1.0)
        rgb[sup_m] = np.clip(np.array([0.09, 0.20, 0.38], dtype=np.float32) * (0.65 + 0.85 * lum[sup_m]), 0.0, 1.0)
        rgb[stem_m] = np.clip(np.array([0.16, 0.32, 0.52], dtype=np.float32) * (0.60 + 0.85 * lum[stem_m]), 0.0, 1.0)
        shs[bg_dom, 1:, :] *= 0.05
    elif theme == "urushi_museum":
        rgb[stand_m] = np.clip(np.array([0.10, 0.09, 0.11], dtype=np.float32) * (0.60 + 0.80 * lum[stand_m]), 0.0, 1.0)
        rgb[sup_m] = np.clip(np.array([0.08, 0.07, 0.09], dtype=np.float32) * (0.55 + 0.85 * lum[sup_m]), 0.0, 1.0)
        rgb[stem_m] = np.clip(np.array([0.38, 0.28, 0.14], dtype=np.float32) * (0.55 + 0.90 * lum[stem_m]), 0.0, 1.0)
        shs[bg_dom, 1:, :] *= 0.15
    elif theme == "parchment_sepia":
        rgb[stand_m] = np.clip(np.array([0.42, 0.35, 0.26], dtype=np.float32) * (0.65 + 0.70 * lum[stand_m]), 0.0, 1.0)
        rgb[sup_m] = np.clip(np.array([0.36, 0.30, 0.22], dtype=np.float32) * (0.65 + 0.75 * lum[sup_m]), 0.0, 1.0)
        rgb[stem_m] = np.clip(np.array([0.28, 0.21, 0.15], dtype=np.float32) * (0.60 + 0.75 * lum[stem_m]), 0.0, 1.0)
        shs[bg_dom, 1:, :] *= 0.05
    else:
        # Preserve authentic container/ground hue with gentle cel-shaded contrast
        cel_w = np.where(lum > 0.46, 1.06, 0.86).astype(np.float32)
        rgb[stand_m] = np.clip((0.08 + 0.82 * rgb[stand_m]) * cel_w[stand_m], 0.0, 1.0)
        rgb[sup_m] = np.clip((0.08 + 0.82 * rgb[sup_m]) * cel_w[sup_m], 0.0, 1.0)
        rgb[stem_m] = np.clip((0.12 + 0.78 * rgb[stem_m]) * cel_w[stem_m], 0.0, 1.0)
        shs[bg_dom, 1:, :] *= 0.35

    shs[bg_dom, 0, :] = ((rgb[bg_dom] - 0.5) / SH_C0).astype(np.float32)
    return rgb, op, sc, shs


def _style_organ_kernel_subset(
    preset_name: str,
    k_idx: np.ndarray,
    model: UniversalBotanicalModel,
    s_01: np.ndarray,
    t_norm: np.ndarray,
    rho: np.ndarray,
    z_lo: float,
    z_hi: float,
    org_z_lut: np.ndarray,
    org_e3_lut: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray | None, float, np.ndarray | None]:
    """Return (rgb, opacity, scales, quats_override, sh_ac_keep, sh_ac_override_15) for subset k_idx."""
    if len(k_idx) == 0:
        return (
            np.zeros((0, 3), dtype=np.float32),
            np.zeros((0,), dtype=np.float32),
            np.zeros((0, 3), dtype=np.float32),
            None,
            0.0,
            None,
        )

    oids = model.kernel_labels[k_idx]
    s = s_01[k_idx]
    t = t_norm[k_idx]
    r_m = rho[k_idx]
    base_rgb = model.cloud.rgb_dc[k_idx]
    lum = 0.299 * base_rgb[:, 0] + 0.587 * base_rgb[:, 1] + 0.114 * base_rgb[:, 2]
    op_raw = model.cloud.opacities[k_idx].copy()
    is_halo_floater = (op_raw < 0.048) | (r_m > 1.08)
    op_sharp = np.where(is_halo_floater, op_raw * 0.02, 1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 2.4)).astype(np.float32)
    sc = model.cloud.scales[k_idx].copy()

    sun_org = np.clip((org_z_lut[oids] - z_lo) / max(z_hi - z_lo, 1e-4), 0.0, 1.0).astype(np.float32)
    org_hash = (((oids.astype(np.int64) * 1103515245 + 12345) & 0x7FFFFFFF) / float(0x7FFFFFFF)).astype(np.float32)
    kern_hash = (((k_idx.astype(np.int64) * 2654435761) & 0x7FFFFFFF) / float(0x7FFFFFFF)).astype(np.float32)

    if preset_name == "ghibli_gouache":
        c_shadow = np.array([0.09, 0.39, 0.30], dtype=np.float32)
        c_mid = np.array([0.23, 0.64, 0.28], dtype=np.float32)
        c_sun = np.array([0.68, 0.87, 0.24], dtype=np.float32)
        warm = np.clip(0.52 * sun_org + 0.33 * s + 0.15 * org_hash, 0.0, 1.0)[:, None]
        col = np.where(
            warm < 0.5,
            (1.0 - 2.0 * warm) * c_shadow + 2.0 * warm * c_mid,
            (2.0 - 2.0 * warm) * c_mid + (2.0 - 2.0 * (1.0 - warm) - 1.0) * c_sun,
        )
        cel = np.where(lum > 0.50, 1.08, np.where(lum > 0.34, 0.94, 0.77)).astype(np.float32)[:, None]
        rim = np.clip((r_m - 0.84) / 0.16, 0.0, 1.0)[:, None]
        col = col * cel * (1.0 - 0.32 * rim)
        max_ax = np.argmax(sc, axis=1)
        sc[np.arange(len(k_idx)), max_ax] *= 1.05
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_sharp, sc, None, 0.08, None

    if preset_name == "sumie_ink_wash":
        ink_density = np.clip(
            0.34 * (1.0 - sun_org)
            + 0.34 * (1.0 - lum)
            + 0.46 * np.clip((r_m - 0.75) / 0.23, 0.0, 1.0)
            + 0.16 * (1.0 - s),
            0.0,
            1.0,
        )
        gray = 0.85 - 0.76 * (ink_density ** 1.15)
        col = np.stack([gray * 0.98, gray * 0.99, gray * 0.95], axis=-1)
        is_faint = op_raw < 0.022
        gamma_ink = 1.6 + 3.0 * ink_density
        op_ink = np.where(is_faint, op_raw * 0.05, 1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), gamma_ink))
        return np.clip(col, 0.0, 1.0).astype(np.float32), np.clip(op_ink, 1e-4, 0.99).astype(np.float32), sc, None, 0.0, None

    if preset_name == "ukiyoe_papercut":
        band_sel = 0.58 * sun_org + 0.42 * org_hash
        c_verm = np.array([0.88, 0.28, 0.17], dtype=np.float32)
        c_gold = np.array([0.94, 0.70, 0.18], dtype=np.float32)
        c_pine = np.array([0.13, 0.47, 0.43], dtype=np.float32)
        col = np.where(
            (band_sel > 0.64)[:, None],
            c_verm[None, :],
            np.where((band_sel > 0.34)[:, None], c_gold[None, :], c_pine[None, :]),
        )
        two_tone = np.where(s > 0.54, 1.05, 0.91).astype(np.float32)[:, None]
        keyline = (r_m > 0.85).astype(np.float32)[:, None]
        c_key = np.array([0.11, 0.10, 0.14], dtype=np.float32)[None, :]
        col = np.clip(col * two_tone, 0.0, 1.0) * (1.0 - 0.74 * keyline) + c_key * (0.74 * keyline)
        op_cut = np.where(op_raw < 0.024, op_raw * 0.04, 1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 5.2))
        return np.clip(col, 0.0, 1.0).astype(np.float32), np.clip(op_cut, 1e-4, 0.995).astype(np.float32), sc, None, 0.0, None

    if preset_name == "pointillist_stipple":
        c_viridian = np.array([0.10, 0.72, 0.49], dtype=np.float32)
        c_cadmium = np.array([0.97, 0.80, 0.16], dtype=np.float32)
        c_lavender = np.array([0.54, 0.37, 0.88], dtype=np.float32)
        c_coral = np.array([0.96, 0.42, 0.33], dtype=np.float32)
        col = np.where(
            (kern_hash < 0.50)[:, None],
            c_viridian[None, :],
            np.where(
                (kern_hash < 0.80)[:, None],
                (1.0 - sun_org[:, None]) * c_cadmium[None, :] + sun_org[:, None] * c_coral[None, :],
                c_lavender[None, :],
            ),
        )
        order_ax = np.argsort(sc, axis=1)
        ar = np.arange(len(k_idx))
        sc[ar, order_ax[:, 2]] *= 0.56
        sc[ar, order_ax[:, 1]] *= 0.62
        op_dots = np.where(op_raw < 0.026, op_raw * 0.03, np.clip(1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 6.8), 0.0, 0.98))
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_dots.astype(np.float32), sc, None, 0.0, None

    if preset_name == "sakura_watercolor":
        is_blossom = (0.65 * sun_org + 0.35 * org_hash) > 0.34
        c_petal_base = np.array([0.89, 0.39, 0.56], dtype=np.float32)
        c_petal_tip = np.array([0.99, 0.82, 0.88], dtype=np.float32)
        c_bud_base = np.array([0.34, 0.65, 0.37], dtype=np.float32)
        c_bud_tip = np.array([0.71, 0.89, 0.52], dtype=np.float32)
        col_blos = (1.0 - s[:, None]) * c_petal_base[None, :] + s[:, None] * c_petal_tip[None, :]
        col_bud = (1.0 - s[:, None]) * c_bud_base[None, :] + s[:, None] * c_bud_tip[None, :]
        col = np.where(is_blossom[:, None], col_blos, col_bud)
        rim = np.clip((r_m - 0.82) / 0.17, 0.0, 1.0)[:, None]
        c_plum = np.array([0.54, 0.19, 0.35], dtype=np.float32)[None, :]
        col = col * (0.86 + 0.26 * lum[:, None])
        col = (1.0 - 0.46 * rim) * col + (0.46 * rim) * c_plum
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_sharp, sc, None, 0.06, None

    if preset_name == "cyanotype_celadon":
        c_prussian = np.array([0.07, 0.22, 0.49], dtype=np.float32)
        c_celadon = np.array([0.27, 0.69, 0.73], dtype=np.float32)
        c_ivory = np.array([0.86, 0.95, 0.97], dtype=np.float32)
        t_prog = np.clip(0.60 * s + 0.40 * sun_org, 0.0, 1.0)[:, None]
        col = np.where(
            t_prog < 0.55,
            (1.0 - t_prog / 0.55) * c_prussian + (t_prog / 0.55) * c_celadon,
            (1.0 - (t_prog - 0.55) / 0.45) * c_celadon + ((t_prog - 0.55) / 0.45) * c_ivory,
        )
        outer_line = (r_m > 0.88).astype(np.float32)[:, None]
        inner_glow = ((r_m > 0.75) & (r_m <= 0.88)).astype(np.float32)[:, None]
        col = col * (1.0 - 0.36 * inner_glow) + c_ivory[None, :] * (0.36 * inner_glow)
        col = col * (1.0 - 0.66 * outer_line) + c_prussian[None, :] * (0.66 * outer_line)
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_sharp, sc, None, 0.0, None

    if preset_name == "vangogh_impasto":
        # Post-Impressionist Swirling Oil Impasto: directional 3D brushstroke Gaussians + cobalt/chrome-yellow ridges!
        swirl = np.sin(14.0 * t + 6.5 * s + 5.0 * org_hash)
        c_cobalt = np.array([0.09, 0.27, 0.80], dtype=np.float32)
        c_starry = np.array([0.99, 0.82, 0.13], dtype=np.float32)
        c_cypress = np.array([0.11, 0.56, 0.44], dtype=np.float32)
        c_ochre = np.array([0.93, 0.52, 0.14], dtype=np.float32)

        col = np.where(
            (swirl > 0.36)[:, None],
            (1.0 - sun_org[:, None]) * c_ochre[None, :] + sun_org[:, None] * c_starry[None, :],
            np.where((swirl > -0.28)[:, None], c_cypress[None, :], c_cobalt[None, :]),
        )
        # Impasto paint ridge highlights & Prussian dark brush grooves
        groove = (np.abs(swirl) < 0.08).astype(np.float32)[:, None]
        col = col * (0.90 + 0.25 * kern_hash[:, None]) * (1.0 - 0.52 * groove)
        # Physically stretch & swirl 3D Gaussian ellipsoids into oriented oil-paint brushstrokes!
        order_ax = np.argsort(sc, axis=1)
        ar = np.arange(len(k_idx))
        sc[ar, order_ax[:, 2]] *= 1.46
        sc[ar, order_ax[:, 1]] *= 0.38
        psi_vortex = 0.62 * np.sin(5.8 * s + 3.4 * t)
        nrm_axis = org_e3_lut[oids]
        R_swirl = Rotation.from_rotvec(psi_vortex[:, None] * nrm_axis)
        q0 = model.cloud.quats_wxyz[k_idx]
        r_orig = Rotation.from_quat(np.column_stack([q0[:, 1], q0[:, 2], q0[:, 3], q0[:, 0]]))
        xyzw_s = (R_swirl * r_orig).as_quat()
        quats_swirl = np.column_stack([xyzw_s[:, 3], xyzw_s[:, 0], xyzw_s[:, 1], xyzw_s[:, 2]]).astype(np.float32)
        op_imp = np.where(op_raw < 0.024, op_raw * 0.05, np.clip(1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 5.5), 0.0, 0.99))
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_imp.astype(np.float32), sc, quats_swirl, 0.05, None

    if preset_name == "copperplate_hatching":
        # 18th-Century Botanical Copperplate Engraving: antique rag-parchment + iron-gall burin cross-hatching!
        c_parchment = np.array([0.96, 0.91, 0.80], dtype=np.float32)
        c_sepia_ink = np.array([0.15, 0.11, 0.09], dtype=np.float32)
        c_tint = np.array([0.78, 0.84, 0.68], dtype=np.float32)  # subtle hand-tinted herbarium wash

        midrib = np.abs(t) < 0.065
        hatch_primary = np.cos(34.0 * t + 9.0 * s) > 0.46
        hatch_cross = (lum < 0.46) & (np.cos(28.0 * s - 19.0 * t) > 0.48)
        rim_ink = r_m > 0.83
        ink_mask = (midrib | hatch_primary | hatch_cross | rim_ink).astype(np.float32)[:, None]

        paper = (1.0 - 0.28 * s[:, None]) * c_parchment[None, :] + (0.28 * s[:, None]) * c_tint[None, :]
        col = (1.0 - 0.86 * ink_mask) * paper + (0.86 * ink_mask) * c_sepia_ink[None, :]
        order_ax = np.argsort(sc, axis=1)
        ar = np.arange(len(k_idx))
        sc[ar, order_ax[:, 2]] *= 1.28
        sc[ar, order_ax[:, 1]] *= 0.44
        op_etch = np.where(op_raw < 0.024, op_raw * 0.05, np.clip(1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 4.5), 0.0, 0.99))
        return np.clip(col, 0.0, 1.0).astype(np.float32), op_etch.astype(np.float32), sc, None, 0.0, None

    if preset_name == "stained_glass_cloisonne":
        # Gothic Stained Glass & Cloisonne Enamel: 8 Voronoi jewel panes per organ + burnished-gold/lead-came seams!
        seeds_st = np.array(
            [[0.18, -0.45], [0.22, 0.45], [0.45, -0.55], [0.48, 0.0], [0.46, 0.55], [0.74, -0.38], [0.76, 0.38], [0.88, 0.0]],
            dtype=np.float32,
        )
        jewels = np.array(
            [
                [0.92, 0.14, 0.26],  # Ruby crimson
                [0.07, 0.78, 0.45],  # Cathedral emerald
                [0.12, 0.40, 0.95],  # Cobalt sapphire
                [0.98, 0.68, 0.10],  # Amber topaz
                [0.68, 0.20, 0.90],  # Royal amethyst
                [0.08, 0.84, 0.82],  # Turquoise enamel
                [0.96, 0.38, 0.16],  # Carnelian orange
                [0.42, 0.86, 0.22],  # Peridot lime
            ],
            dtype=np.float32,
        )
        # Deterministic per-organ cyclic shift of jewel palette
        d2 = (s[:, None] - seeds_st[None, :, 0]) ** 2 + (0.65 * (t[:, None] - seeds_st[None, :, 1])) ** 2
        idx_sort = np.argsort(d2, axis=1)
        ar = np.arange(len(k_idx))
        d_first = np.sqrt(d2[ar, idx_sort[:, 0]])
        d_second = np.sqrt(d2[ar, idx_sort[:, 1]])
        pane_id = (idx_sort[:, 0] + (oids % 8)) % 8
        pane_col = jewels[pane_id] * (0.85 + 0.30 * np.clip(1.0 - 1.8 * d_first, 0.0, 1.0)[:, None])

        # Internal cloisonne wire seam + outer B-spline lead came!
        is_wire = ((d_second - d_first) < 0.055) | (r_m > 0.83)
        c_wire = np.array([0.16, 0.12, 0.06], dtype=np.float32)[None, :]
        c_gold_glint = np.array([0.88, 0.72, 0.24], dtype=np.float32)[None, :]
        wire_col = np.where((s > 0.5)[:, None], 0.55 * c_wire + 0.45 * c_gold_glint, c_wire)
        w_f = is_wire.astype(np.float32)[:, None]
        col = (1.0 - w_f) * pane_col + w_f * wire_col
        op_glass = np.where(is_halo_floater, op_raw * 0.02, np.where(is_wire, np.maximum(op_sharp, 0.95), op_sharp * 0.85))
        return np.clip(col, 0.0, 1.0).astype(np.float32), np.clip(op_glass, 1e-4, 0.99).astype(np.float32), sc, None, 0.04, None

    if preset_name == "pop_halftone_risograph":
        # Roy Lichtenstein / Fluorescent Risograph Halftone Pop-Art: Ben-Day dot matrix + bold comic ink contour!
        sel = (oids + (sun_org * 3.0).astype(np.int32)) % 3
        c_mag = np.array([0.98, 0.17, 0.57], dtype=np.float32)
        c_cyn = np.array([0.06, 0.83, 0.95], dtype=np.float32)
        c_yel = np.array([0.99, 0.88, 0.11], dtype=np.float32)
        c_cream = np.array([0.99, 0.97, 0.91], dtype=np.float32)

        base_pop = np.where((sel == 0)[:, None], c_mag[None, :], np.where((sel == 1)[:, None], c_cyn[None, :], c_yel[None, :]))
        dot_grid = (np.cos(28.0 * s) * np.cos(22.0 * t)) > 0.22
        use_dots = dot_grid & (s < 0.78)
        col = np.where(use_dots[:, None], c_cream[None, :], base_pop)
        comic_rim = (r_m > 0.83).astype(np.float32)[:, None]
        col = (1.0 - 0.90 * comic_rim) * col + (0.90 * comic_rim) * np.array([[0.06, 0.06, 0.08]], dtype=np.float32)
        op_pop = np.where(is_halo_floater, op_raw * 0.02, 1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 5.6))
        return np.clip(col, 0.0, 1.0).astype(np.float32), np.clip(op_pop, 1e-4, 0.995).astype(np.float32), sc, None, 0.0, None

    if preset_name == "neon_venation_xray":
        # Bioluminescent Venation X-Ray Glass: semi-transparent abyssal lamina + glowing electric vascular network!
        midrib = np.abs(t) < 0.072
        sec_veins = np.abs(np.sin(15.5 * (s - 0.36 * np.abs(t)))) > 0.89
        margin_glow = r_m > 0.83
        is_vein = midrib | sec_veins | margin_glow

        c_lamina = np.array([0.06, 0.28, 0.38], dtype=np.float32)
        c_vein_cyan = np.array([0.22, 0.98, 0.92], dtype=np.float32)
        c_vein_gold = np.array([0.96, 0.94, 0.36], dtype=np.float32)
        vein_col = (1.0 - s[:, None]) * c_vein_cyan[None, :] + s[:, None] * c_vein_gold[None, :]

        col = np.where(is_vein[:, None], vein_col, c_lamina[None, :] * (0.75 + 0.50 * sun_org[:, None]))
        # Translucent 3D glass interior so underlying veins & inner stems glow right through!
        op_xray = np.where(
            is_halo_floater,
            op_raw * 0.02,
            np.where(is_vein, np.maximum(op_sharp, 0.95), op_sharp * 0.30),
        )
        return np.clip(col, 0.0, 1.0).astype(np.float32), np.clip(op_xray, 1e-4, 0.99).astype(np.float32), sc, None, 0.0, None

    if preset_name == "maki_e_gold_lacquer":
        # Japanese Urushi Black-Gold Maki-e Lacquer + True View-Dependent Iridescent Mother-of-Pearl (Raden) SH3!
        c_urushi = np.array([0.08, 0.07, 0.10], dtype=np.float32)
        c_gold_24k = np.array([0.96, 0.78, 0.22], dtype=np.float32)
        c_pearl_dc = np.array([0.28, 0.56, 0.62], dtype=np.float32)

        gold_dust = (r_m > 0.80) | (np.abs(t) < 0.06) | ((s > 0.64) & (kern_hash > 0.38))
        raden_inlay = (~gold_dust) & (s > 0.24) & (s < 0.68) & (np.abs(t) > 0.20) & (((oids + (t > 0).astype(np.int32)) % 2) == 0)

        col = np.where(
            gold_dust[:, None],
            c_gold_24k[None, :] * (0.85 + 0.22 * lum[:, None]),
            np.where(raden_inlay[:, None], c_pearl_dc[None, :], c_urushi[None, :] * (0.80 + 0.60 * lum[:, None])),
        )
        # Inject true view-dependent iridescent Spherical Harmonics (degree 1 & 2) on Raden mother-of-pearl & gold!
        sh_irid = np.zeros((len(k_idx), 15, 3), dtype=np.float32)
        inlay_f = (raden_inlay & (~is_halo_floater)).astype(np.float32)
        gold_f = (gold_dust & (~is_halo_floater)).astype(np.float32)
        # Degree-1 directional color shift: X->magenta, Y->emerald-cyan, Z->warm gold!
        sh_irid[:, 0, :] = inlay_f[:, None] * np.array([[0.55, -0.30, 0.45]], dtype=np.float32)
        sh_irid[:, 1, :] = (inlay_f[:, None] * np.array([[-0.35, 0.60, 0.40]]) + gold_f[:, None] * np.array([[0.35, 0.28, 0.05]])).astype(np.float32)
        sh_irid[:, 2, :] = (inlay_f[:, None] * np.array([[0.25, 0.45, -0.45]]) + gold_f[:, None] * np.array([[0.40, 0.32, 0.08]])).astype(np.float32)
        sh_irid[:, 4, :] = inlay_f[:, None] * np.array([[0.42, -0.25, 0.50]], dtype=np.float32)
        op_lacq = np.where(is_halo_floater, op_raw * 0.02, 1.0 - np.power(np.clip(1.0 - op_raw, 1e-5, 1.0), 5.0))
        return np.clip(col, 0.0, 1.0).astype(np.float32), np.clip(op_lacq, 1e-4, 0.995).astype(np.float32), sc, None, 0.0, sh_irid

    raise ValueError(f"Unknown preset_name: {preset_name}")


def compose_stylized_universal_plant(
    model: UniversalBotanicalModel,
    organ_style_map: dict[int, str] | str,
    support_theme: str | None = None,
    precomputed_polar: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> tuple[UniversalBotanicalModel, dict[str, int]]:
    """Return a styled UniversalBotanicalModel (with full SH3, quaternion & cov6 consistency) where each organ gets its own preset."""
    if support_theme is None:
        if organ_style_map == "sumie_ink_wash":
            support_theme = "sumie_monochrome"
        elif organ_style_map == "cyanotype_celadon":
            support_theme = "cyanotype"
        elif organ_style_map == "copperplate_hatching":
            support_theme = "parchment_sepia"
        elif organ_style_map in ("maki_e_gold_lacquer", "neon_venation_xray"):
            support_theme = "urushi_museum"
        else:
            support_theme = "studio_cel"

    s_01, t_norm, rho = precomputed_polar if precomputed_polar is not None else compute_universal_organ_polar_coords(model)
    rgb_out, op_out, sc_out, shs_out = _harmonize_support_stand_and_stems(model, theme=support_theme)
    quats_out = model.cloud.quats_wxyz.copy()

    if not model.organs:
        return model, {}

    z_orgs = np.array([o.centroid[2] for o in model.organs], dtype=np.float32)
    z_lo = float(np.percentile(z_orgs, 5.0))
    z_hi = float(np.percentile(z_orgs, 95.0))
    max_oid = max(o.organ_id for o in model.organs)
    org_z_lut = np.zeros(max_oid + 1, dtype=np.float32)
    org_e3_lut = np.tile(np.array([[0.0, 0.0, 1.0]], dtype=np.float64), (max_oid + 1, 1))
    for o in model.organs:
        org_z_lut[o.organ_id] = float(o.centroid[2])
        org_e3_lut[o.organ_id] = o.e3 / max(float(np.linalg.norm(o.e3)), 1e-12)

    preset_to_oids: dict[str, list[int]] = {p: [] for p in PRESET_ORDER}
    if isinstance(organ_style_map, str):
        for o in model.organs:
            preset_to_oids.setdefault(organ_style_map, []).append(o.organ_id)
    else:
        for o in model.organs:
            p_n = organ_style_map.get(o.organ_id, "ghibli_gouache")
            preset_to_oids.setdefault(p_n, []).append(o.organ_id)

    style_counts: dict[str, int] = {}
    geom_changed = False
    for pname, oids in preset_to_oids.items():
        if not oids:
            continue
        style_counts[pname] = len(oids)
        k_idx = np.flatnonzero(np.isin(model.kernel_labels, oids))
        c_sub, op_sub, sc_sub, q_sub, sh_ac, sh_override = _style_organ_kernel_subset(
            pname, k_idx, model, s_01, t_norm, rho, z_lo, z_hi, org_z_lut, org_e3_lut
        )
        rgb_out[k_idx] = c_sub
        op_out[k_idx] = op_sub
        if not np.allclose(sc_sub, sc_out[k_idx]):
            geom_changed = True
            sc_out[k_idx] = sc_sub
        if q_sub is not None:
            geom_changed = True
            quats_out[k_idx] = q_sub
        shs_out[k_idx, 0, :] = ((c_sub - 0.5) / SH_C0).astype(np.float32)
        if sh_override is not None:
            shs_out[k_idx, 1:, :] = sh_override
        else:
            shs_out[k_idx, 1:, :] *= sh_ac

    cov6_out = build_cov6_from_sq(sc_out, quats_out) if geom_changed else model.cloud.cov6.copy()
    # Strictly preserve bit-exact geometry & covariance on static support & stand
    static_m = (model.kernel_labels == LABEL_BASAL_SUPPORT) | (model.kernel_labels == LABEL_STATIC_STAND_OR_TABLE)
    cov6_out[static_m] = model.cloud.cov6[static_m]
    quats_out[static_m] = model.cloud.quats_wxyz[static_m]
    sc_out[static_m] = model.cloud.scales[static_m]

    styled_cloud = SceneGaussianCloud(
        means=model.cloud.means.copy(),
        scales=sc_out,
        quats_wxyz=quats_out,
        cov6=cov6_out,
        surfel_normals=model.cloud.surfel_normals.copy(),
        opacities=op_out,
        rgb_dc=rgb_out,
        shs=shs_out,
    )
    return replace(model, cloud=styled_cloud), style_counts


def build_mixed_crown_sectors(model: UniversalBotanicalModel) -> dict[int, str]:
    """Scale-free 6-sector spatial crown symphony using plant-adaptive quantiles (works at any scene scale!)."""
    if not model.organs:
        return {}
    ctrs = np.array([o.centroid for o in model.organs], dtype=np.float64)
    center_xy = np.median(ctrs[:, :2], axis=0)
    horiz = (ctrs[:, 0] - center_xy[0]) + 0.35 * (ctrs[:, 1] - center_xy[1])
    h_q33, h_q67 = np.percentile(horiz, [33.3, 66.7])
    z_med = float(np.median(ctrs[:, 2]))

    smap: dict[int, str] = {}
    for o, hv, zv in zip(model.organs, horiz, ctrs[:, 2]):
        if zv >= z_med:
            smap[o.organ_id] = "ukiyoe_papercut" if hv < h_q33 else ("sakura_watercolor" if hv < h_q67 else "sumie_ink_wash")
        else:
            smap[o.organ_id] = "ghibli_gouache" if hv < h_q33 else ("pointillist_stipple" if hv < h_q67 else "cyanotype_celadon")
    return smap


def build_mixed_neighbor_mosaic(
    model: UniversalBotanicalModel,
    palette: tuple[str, ...] = PRESET_CLASSIC_6,
) -> dict[int, str]:
    """Greedy 3D kNN graph-coloring mosaic so adjacent leaves/blossom clusters always receive contrasting styles!"""
    if not model.organs:
        return {}
    ctrs = np.array([o.centroid for o in model.organs], dtype=np.float64)
    tree = cKDTree(ctrs)
    k_nb = min(len(palette), len(ctrs))
    _, nbrs = tree.query(ctrs, k=k_nb)
    if nbrs.ndim == 1:
        nbrs = nbrs[:, None]

    smap: dict[int, str] = {}
    usage = {p: 0 for p in palette}
    order = np.argsort(ctrs[:, 2] * 2.0 + ctrs[:, 0])
    for idx_i in order:
        oid = model.organs[int(idx_i)].organ_id
        used_nb = {
            smap[model.organs[int(nb)].organ_id]
            for nb in nbrs[int(idx_i), 1:]
            if model.organs[int(nb)].organ_id in smap
        }
        cands = [p for p in palette if p not in used_nb] or list(palette)
        chosen = min(cands, key=lambda p: (usage[p], palette.index(p)))
        smap[oid] = chosen
        usage[chosen] += 1
    return smap


def build_12style_neighbor_kaleidoscope(model: UniversalBotanicalModel) -> dict[int, str]:
    """Mode I: Full 12-Style 3D Graph-Colored Kaleidoscope (all 12 classic + avant-garde NPR styles on ONE plant!)."""
    return build_mixed_neighbor_mosaic(model, palette=PRESET_ORDER)


def build_12style_phyllotactic_spiral(model: UniversalBotanicalModel) -> dict[int, str]:
    """Mode II: 12-Sector Azimuth x Elevation Spiral Gallery uniting all 12 NPR styles into coherent bouquets."""
    if not model.organs:
        return {}
    ctrs = np.array([o.centroid for o in model.organs], dtype=np.float64)
    med_xy = np.median(ctrs[:, :2], axis=0)
    z_med = float(np.median(ctrs[:, 2]))
    angs = np.arctan2(ctrs[:, 1] - med_xy[1], ctrs[:, 0] - med_xy[0])  # [-pi, pi]
    # Use rank quantiles on angles inside lower & upper crown so all 12 styles get balanced representation even on asymmetric plants!
    smap: dict[int, str] = {}
    lower_idxs = np.flatnonzero(ctrs[:, 2] < z_med)
    upper_idxs = np.flatnonzero(ctrs[:, 2] >= z_med)
    for half_offset, idxs in ((0, lower_idxs), (6, upper_idxs)):
        if len(idxs) == 0:
            continue
        ang_order = np.argsort(angs[idxs])
        for rank, pos in enumerate(ang_order):
            sector = min(5, int((rank * 6) // max(len(idxs), 1)))
            smap[model.organs[int(idxs[pos])].organ_id] = PRESET_ORDER[half_offset + sector]
    return smap


def build_12style_museum_cabinet(model: UniversalBotanicalModel) -> dict[int, str]:
    """Mode III: Sumi-e Ink & Copperplate Etch Museum Ground + 10 Vivid Avant-Garde Jewel Bouquets on ONE plant!"""
    if not model.organs:
        return {}
    ctrs = np.array([o.centroid for o in model.organs], dtype=np.float64)
    tree = cKDTree(ctrs)
    # Alternating Sumi-e ink wash and Copperplate parchment etching on inner/background organs
    smap: dict[int, str] = {
        o.organ_id: ("copperplate_hatching" if (i % 2 == 0) else "sumie_ink_wash")
        for i, o in enumerate(model.organs)
    }
    outer_pos = [i for i, o in enumerate(model.organs) if o.visibility_tier == "OUTER_ENCLOSED"]
    if len(outer_pos) < 10:
        outer_pos = list(range(len(model.organs)))

    hero_styles = [p for p in PRESET_ORDER if p not in ("sumie_ink_wash", "copperplate_hatching")]
    # Pick 10 maximally spread outer seed organs via farthest-point sampling!
    chosen_seeds = [outer_pos[int(np.argmax(ctrs[outer_pos, 2]))]]
    while len(chosen_seeds) < min(10, len(outer_pos)):
        best_cand = outer_pos[0]
        best_min_d = -1.0
        for cand in outer_pos:
            d_min = min(float(np.linalg.norm(ctrs[cand] - ctrs[s_i])) for s_i in chosen_seeds)
            if d_min > best_min_d:
                best_min_d = d_min
                best_cand = cand
        chosen_seeds.append(best_cand)

    k_bouquet = max(2, min(8, len(model.organs) // 18))
    for seed_idx, h_style in zip(chosen_seeds, hero_styles):
        _, b_idxs = tree.query(ctrs[seed_idx], k=min(k_bouquet, len(ctrs)))
        for bi in np.atleast_1d(b_idxs):
            org = model.organs[int(bi)]
            if org.visibility_tier != "DEEP_OCCLUDED":
                smap[org.organ_id] = h_style
    return smap


def build_12style_height_spectrum(model: UniversalBotanicalModel) -> dict[int, str]:
    """Mode IV: 12-Stratum Root-to-Apex Artistic Evolution (Copperplate & Sumi-e base -> Avant-Garde X-Ray & Maki-e crown)."""
    if not model.organs:
        return {}
    spectrum_order = (
        "copperplate_hatching",
        "sumie_ink_wash",
        "cyanotype_celadon",
        "ghibli_gouache",
        "vangogh_impasto",
        "pointillist_stipple",
        "ukiyoe_papercut",
        "sakura_watercolor",
        "pop_halftone_risograph",
        "stained_glass_cloisonne",
        "neon_venation_xray",
        "maki_e_gold_lacquer",
    )
    ctrs = np.array([o.centroid for o in model.organs], dtype=np.float64)
    # Slight diagonal tilt (z + 0.18*x) so strata flow organically across crown tiers
    score = ctrs[:, 2] + 0.18 * ctrs[:, 0]
    order = np.argsort(score)
    smap: dict[int, str] = {}
    n = len(order)
    for rank, idx_i in enumerate(order):
        band = min(11, int((rank * 12) // max(n, 1)))
        smap[model.organs[int(idx_i)].organ_id] = spectrum_order[band]
    return smap


def build_mixed_sumie_hero_focus(model: UniversalBotanicalModel) -> dict[int, str]:
    """Sumi-e monochrome ink plant with 4 vivid stylized outer hero bouquets."""
    if not model.organs:
        return {}
    ctrs = np.array([o.centroid for o in model.organs], dtype=np.float64)
    tree = cKDTree(ctrs)
    smap = {o.organ_id: "sumie_ink_wash" for o in model.organs}

    outer_pos = [i for i, o in enumerate(model.organs) if o.visibility_tier == "OUTER_ENCLOSED"]
    if len(outer_pos) < 4:
        outer_pos = list(range(len(model.organs)))
    out_c = ctrs[outer_pos]
    x_lo, x_hi = np.percentile(out_c[:, 0], [16.0, 84.0])
    y_lo, y_hi = np.percentile(out_c[:, 1], [18.0, 82.0])
    z_lo, z_mid, z_hi = np.percentile(out_c[:, 2], [25.0, 58.0, 88.0])

    targets = np.array([[x_lo, 0.0, z_hi], [x_hi, y_lo, z_mid], [0.0, y_hi, z_mid], [x_lo * 0.7, y_lo * 0.7, z_lo]])
    heroes = ["ukiyoe_papercut", "sakura_watercolor", "cyanotype_celadon", "ghibli_gouache"]
    k_grp = max(3, min(14, len(model.organs) // 9))
    for tgt, hp in zip(targets, heroes):
        _, seed_i = tree.query(tgt, k=1)
        _, b_idxs = tree.query(ctrs[int(seed_i)], k=min(k_grp, len(ctrs)))
        for bi in np.atleast_1d(b_idxs):
            org = model.organs[int(bi)]
            if org.visibility_tier != "DEEP_OCCLUDED":
                smap[org.organ_id] = hp
    return smap


# ---------------------------------------------------------------------------
# 3. Scale-Free Inextensible Organ Manifold Deformation + Jacobian Transport
# ---------------------------------------------------------------------------


@dataclass
class UniversalDeformRig:
    """Scale-free petiole-hinged anatomical coordinate rig for all M organs in any plant species."""

    num_organs: int
    organ_ids: np.ndarray       # (M,) int32
    oid_to_slot: np.ndarray     # (max_oid + 1,) int32
    p_base: np.ndarray          # (M, 3) float64 clamped hinge at s = 0
    e1: np.ndarray              # (M, 3) float64 proximal -> distal unit axis
    e2: np.ndarray              # (M, 3) float64 bilateral width unit axis
    e3: np.ndarray              # (M, 3) float64 normal unit axis (e1 x e2 = e3)
    blade_len: np.ndarray       # (M,) float64 L_o
    blade_half_w: np.ndarray    # (M,) float64 B_o = 0.5 * W_o
    fol_idx: np.ndarray         # (K,) int32 indices of organ Gaussians (kernel_labels >= 0)
    fol_slots: np.ndarray       # (K,) int32 slot index in 0..M-1
    u_k: np.ndarray             # (K,) float64 longitudinal coord from p_base
    v_k: np.ndarray             # (K,) float64 lateral coord
    w_k: np.ndarray             # (K,) float64 thickness offset
    phase_seed: np.ndarray      # (M,) float64 deterministic phase


@dataclass
class UniversalOrganDeformSpec:
    """Scale-free dimensionless 3D deformation parameters per organ."""

    flap_rad: np.ndarray        # (M,) float64 bending angle in (e1, e3) plane (rad)
    sweep_rad: np.ndarray       # (M,) float64 lateral sweep angle in (e1, e2) plane (rad)
    twist_rad: np.ndarray       # (M,) float64 helical twist angle base->tip (rad)
    cup_angle_rad: np.ndarray   # (M,) float64 dimensionless edge C-curl angle psi_max (rad); kappa = psi_max / B_o!
    len_scale: np.ndarray       # (M,) float64 longitudinal scale
    wid_base: np.ndarray        # (M,) float64 base width scale
    wid_tip_add: np.ndarray     # (M,) float64 distal obovate expansion
    wave_amp_rad: np.ndarray    # (M,) float64 aero-flutter wave amplitude (rad)
    wave_freq: float = 7.0
    wave_time: float = 0.0


def build_universal_deform_rig(model: UniversalBotanicalModel) -> UniversalDeformRig:
    """Build exact SO(3)-orthogonalized petiole-hinged coordinate rig for any UniversalBotanicalModel."""
    m = len(model.organs)
    max_oid = max((o.organ_id for o in model.organs), default=0)
    oid_to_slot = np.full(max_oid + 1, -1, dtype=np.int32)
    organ_ids = np.zeros(m, dtype=np.int32)
    p_base = np.zeros((m, 3), dtype=np.float64)
    e1 = np.zeros((m, 3), dtype=np.float64)
    e2 = np.zeros((m, 3), dtype=np.float64)
    e3 = np.zeros((m, 3), dtype=np.float64)
    blade_len = np.zeros(m, dtype=np.float64)
    blade_half_w = np.zeros(m, dtype=np.float64)
    phase_seed = np.zeros(m, dtype=np.float64)

    for slot, org in enumerate(model.organs):
        oid_to_slot[org.organ_id] = slot
        organ_ids[slot] = org.organ_id
        el = org.e1 / max(float(np.linalg.norm(org.e1)), 1e-12)
        en = org.e3 / max(float(np.linalg.norm(org.e3)), 1e-12)
        ew = np.cross(en, el)
        ew /= max(float(np.linalg.norm(ew)), 1e-12)
        en = np.cross(el, ew)
        en /= max(float(np.linalg.norm(en)), 1e-12)

        p_base[slot] = org.p_base
        e1[slot] = el
        e2[slot] = ew
        e3[slot] = en
        blade_len[slot] = max(org.length, 4.0 * model.p_med)
        blade_half_w[slot] = max(0.5 * org.width, 2.5 * model.p_med)
        phase_seed[slot] = 2.0 * math.pi * (((slot * 2654435761) & 0xFFFFFFFF) / float(0x100000000))

    fol_idx = np.flatnonzero(model.kernel_labels >= 0).astype(np.int32)
    fol_slots = oid_to_slot[model.kernel_labels[fol_idx]] if len(fol_idx) > 0 else np.zeros(0, dtype=np.int32)
    valid = fol_slots >= 0
    fol_idx = fol_idx[valid]
    fol_slots = fol_slots[valid]

    means64 = model.cloud.means.astype(np.float64)
    rel = means64[fol_idx] - p_base[fol_slots]
    u_k = np.sum(rel * e1[fol_slots], axis=1)
    v_k = np.sum(rel * e2[fol_slots], axis=1)
    w_k = np.sum(rel * e3[fol_slots], axis=1)

    return UniversalDeformRig(
        num_organs=m,
        organ_ids=organ_ids,
        oid_to_slot=oid_to_slot,
        p_base=p_base,
        e1=e1,
        e2=e2,
        e3=e3,
        blade_len=blade_len,
        blade_half_w=blade_half_w,
        fol_idx=fol_idx,
        fol_slots=fol_slots,
        u_k=u_k,
        v_k=v_k,
        w_k=w_k,
        phase_seed=phase_seed,
    )


def make_identity_deform_spec(num_organs: int) -> UniversalOrganDeformSpec:
    z = np.zeros(num_organs, dtype=np.float64)
    o = np.ones(num_organs, dtype=np.float64)
    return UniversalOrganDeformSpec(
        flap_rad=z.copy(),
        sweep_rad=z.copy(),
        twist_rad=z.copy(),
        cup_angle_rad=z.copy(),
        len_scale=o.copy(),
        wid_base=o.copy(),
        wid_tip_add=z.copy(),
        wave_amp_rad=z.copy(),
    )


def build_deform_preset_spec(
    model: UniversalBotanicalModel,
    rig: UniversalDeformRig,
    mode_name: str,
    strength: float = 1.0,
) -> UniversalOrganDeformSpec:
    """Create scale-free, gravity-consistent 3D deformation preset specs for ANY plant species."""
    m = rig.num_organs
    spec = make_identity_deform_spec(m)
    if m == 0 or mode_name == "rest_pose":
        return spec

    # Project world downward gravity vector (0, 0, -1) onto each organ's transverse bending plane (e2, e3)
    # so EVERY leaf droops physically downward (-Z), regardless of whether it grew horizontally or vertically!
    g_e3 = -rig.e3[:, 2]  # component of -Z along e3
    g_e2 = -rig.e2[:, 2]  # component of -Z along e2
    g_norm = np.maximum(np.hypot(g_e3, g_e2), 0.25)
    down_flap_dir = g_e3 / g_norm
    down_sweep_dir = g_e2 / g_norm

    z_vals = np.array([o.centroid[2] for o in model.organs], dtype=np.float64)
    z_med = float(np.median(z_vals))
    is_laminar = np.array([o.organ_kind == "LAMINAR_BLADE" for o in model.organs], dtype=bool)
    # Volumetric flower clusters bend gently without strong sheet curling
    cup_mask = np.where(is_laminar, 1.0, 0.22)

    if mode_name == "gravity_wilt":
        ang = math.radians(48.0 * strength)
        spec.flap_rad = ang * down_flap_dir
        spec.sweep_rad = ang * 0.55 * down_sweep_dir
        spec.cup_angle_rad = 0.65 * strength * cup_mask
        spec.twist_rad = math.radians(14.0 * strength) * np.sin(rig.phase_seed)
        return spec

    if mode_name == "boat_cup_twist":
        spec.cup_angle_rad = 0.92 * strength * cup_mask
        spec.twist_rad = math.radians(44.0 * strength) * np.where(np.cos(rig.phase_seed) >= 0, 1.0, -1.0)
        spec.flap_rad = math.radians(12.0 * strength) * down_flap_dir
        return spec

    if mode_name == "slender_lanceolate":
        spec.len_scale = np.full(m, 1.0 + 0.18 * strength, dtype=np.float64)
        spec.wid_base = np.full(m, 1.0 - 0.42 * strength, dtype=np.float64)
        spec.flap_rad = math.radians(20.0 * strength) * down_flap_dir
        spec.cup_angle_rad = 0.35 * strength * cup_mask
        return spec

    if mode_name == "broad_rosette":
        spec.wid_base = np.full(m, 1.0 + 0.12 * strength, dtype=np.float64)
        spec.wid_tip_add = np.full(m, 0.44 * strength, dtype=np.float64) * np.where(is_laminar, 1.0, 0.45)
        # Gentle sunward opening arch (+Z)
        spec.flap_rad = -math.radians(16.0 * strength) * down_flap_dir
        spec.cup_angle_rad = -0.25 * strength * cup_mask
        return spec

    if mode_name == "same_plant_phenology":
        upper = z_vals >= z_med
        # Upper crown blooms sunward & expands; lower crown wilts downward & curls!
        spec.flap_rad = np.where(upper, -math.radians(18.0 * strength) * down_flap_dir, math.radians(52.0 * strength) * down_flap_dir)
        spec.sweep_rad = np.where(upper, 0.0, math.radians(26.0 * strength) * down_sweep_dir)
        spec.wid_tip_add = np.where(upper, 0.36 * strength, -0.18 * strength)
        spec.cup_angle_rad = np.where(upper, -0.20 * strength, 0.78 * strength) * cup_mask
        spec.twist_rad = np.where(upper, math.radians(8.0 * strength), math.radians(28.0 * strength)) * np.sin(rig.phase_seed)
        return spec

    raise ValueError(f"Unknown deformation mode_name: {mode_name}")


def _precompute_universal_spine_lut(
    rig: UniversalDeformRig,
    spec: UniversalOrganDeformSpec,
    s_max: float = 1.40,
    n_grid: int = 40,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    s_grid = np.linspace(0.0, s_max, n_grid, dtype=np.float64)
    ds = s_grid[1] - s_grid[0]
    s_c = np.minimum(s_grid, 1.0)[None, :]
    cant_prof = 2.0 * s_c - (s_c ** 2)

    flap = spec.flap_rad[:, None] * cant_prof
    if np.any(np.abs(spec.wave_amp_rad) > 1e-6):
        ph = spec.wave_freq * s_grid[None, :] - spec.wave_time + rig.phase_seed[:, None]
        flap = flap + spec.wave_amp_rad[:, None] * (s_grid[None, :] ** 1.5) * np.sin(ph)

    sweep = spec.sweep_rad[:, None] * (s_c ** 1.35)
    twist = spec.twist_rad[:, None] * (s_c ** 1.15)

    cf, sf = np.cos(flap)[..., None], np.sin(flap)[..., None]
    cs, ss = np.cos(sweep)[..., None], np.sin(sweep)[..., None]
    e1, e2, e3 = rig.e1[:, None, :], rig.e2[:, None, :], rig.e3[:, None, :]

    e_horiz = cs * e1 + ss * e2
    T_lut = cf * e_horiz + sf * e3
    E_lat = -ss * e1 + cs * e2
    E_nrm = np.cross(T_lut, E_lat)

    ct, st = np.cos(twist)[..., None], np.sin(twist)[..., None]
    B_lut = ct * E_lat + st * E_nrm
    N_lut = -st * E_lat + ct * E_nrm

    gamma_lut = np.zeros_like(T_lut)
    gamma_lut[:, 1:, :] = np.cumsum(0.5 * (T_lut[:, :-1, :] + T_lut[:, 1:, :]), axis=1) * ds
    return s_grid, gamma_lut, B_lut, N_lut


def _eval_universal_deform_pts(
    slots: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
    w: np.ndarray,
    rig: UniversalDeformRig,
    spec: UniversalOrganDeformSpec,
    s_grid: np.ndarray,
    gamma_lut: np.ndarray,
    B_lut: np.ndarray,
    N_lut: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    L_b = rig.blade_len[slots]
    B_h = rig.blade_half_w[slots]
    u_pos = np.maximum(u, 0.0)
    u_neg = np.minimum(u, 0.0)
    s = np.clip(u_pos / L_b, 0.0, s_grid[-1] - 1e-7)

    inv_ds = 1.0 / (s_grid[1] - s_grid[0])
    idx_f = s * inv_ds
    i0 = np.floor(idx_f).astype(np.int32)
    i1 = np.minimum(i0 + 1, len(s_grid) - 1)
    al = (idx_f - i0)[:, None]

    gam_s = (1.0 - al) * gamma_lut[slots, i0] + al * gamma_lut[slots, i1]
    B_s = (1.0 - al) * B_lut[slots, i0] + al * B_lut[slots, i1]
    N_s = (1.0 - al) * N_lut[slots, i0] + al * N_lut[slots, i1]
    B_s /= np.maximum(np.linalg.norm(B_s, axis=1, keepdims=True), 1e-12)
    N_s /= np.maximum(np.linalg.norm(N_s, axis=1, keepdims=True), 1e-12)

    s_01 = np.clip(s, 0.0, 1.0)
    lam_v = np.maximum(spec.wid_base[slots] + spec.wid_tip_add[slots] * (s_01 ** 0.85), 0.25)
    v_scaled = lam_v * v

    # Scale-free curvature kappa = cup_angle_rad / (lam_v * B_h)!
    cup_ramp = np.clip(s / 0.22, 0.0, 1.0)
    kap = (spec.cup_angle_rad[slots] * cup_ramp) / np.maximum(lam_v * B_h, 1e-3)
    psi = np.clip(kap * v_scaled, -1.35, 1.35)
    curved = np.abs(kap) > 1e-3
    kap_safe = np.where(curved, kap, 1.0)
    v_tilde = np.where(curved, np.sin(psi) / kap_safe, v_scaled)
    w_cup = np.where(curved, (1.0 - np.cos(psi)) / kap_safe, 0.0)

    N_tilde = -np.sin(psi)[:, None] * B_s + np.cos(psi)[:, None] * N_s
    lam_u = spec.len_scale[slots]
    spine_xyz = rig.p_base[slots] + (lam_u * L_b)[:, None] * gam_s + (lam_u * u_neg)[:, None] * rig.e1[slots]
    pts_out = spine_xyz + v_tilde[:, None] * B_s + w_cup[:, None] * N_s + w[:, None] * N_tilde
    return pts_out, N_tilde


def deform_universal_organ_manifold(
    model: UniversalBotanicalModel,
    rig: UniversalDeformRig,
    spec: UniversalOrganDeformSpec,
    transport_covariance: bool = True,
) -> tuple[UniversalBotanicalModel, dict[str, float]]:
    """Deform all plant organs with clamped petiole hinges, arc-length conservation & exact Jacobian covariance transport."""
    if rig.num_organs == 0 or len(rig.fol_idx) == 0:
        return model, {"static_max_drift_pmed": 0.0, "arclength_rel_err_pct": 0.0, "tip_mean_disp_cm": 0.0}

    s_grid, gamma_lut, B_lut, N_lut = _precompute_universal_spine_lut(rig, spec)
    slots = rig.fol_slots
    u0, v0, w0 = rig.u_k, rig.v_k, rig.w_k

    pts_new, n_tilde = _eval_universal_deform_pts(slots, u0, v0, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)

    means_out = model.cloud.means.copy()
    means_out[rig.fol_idx] = pts_new.astype(np.float32)
    cov6_out = model.cloud.cov6.copy()
    scales_out = model.cloud.scales.copy()
    quats_out = model.cloud.quats_wxyz.copy()
    nrms_out = model.cloud.surfel_normals.copy()

    if transport_covariance:
        eps = max(float(model.p_med) * 0.12, 2e-4)
        p_uhi, _ = _eval_universal_deform_pts(slots, u0 + eps, v0, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
        p_ulo, _ = _eval_universal_deform_pts(slots, u0 - eps, v0, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
        d_du = (p_uhi - p_ulo) / (2.0 * eps)

        p_vhi, _ = _eval_universal_deform_pts(slots, u0, v0 + eps, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
        p_vlo, _ = _eval_universal_deform_pts(slots, u0, v0 - eps, w0, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
        d_dv = (p_vhi - p_vlo) / (2.0 * eps)

        nu = np.linalg.norm(d_du, axis=1, keepdims=True)
        nv = np.linalg.norm(d_dv, axis=1, keepdims=True)
        d_du = d_du * (np.clip(nu, 0.42, 2.25) / np.maximum(nu, 1e-9))
        d_dv = d_dv * (np.clip(nv, 0.42, 2.25) / np.maximum(nv, 1e-9))

        F_loc = np.stack([d_du, d_dv, n_tilde], axis=2)
        E_fr = np.stack([rig.e1[slots], rig.e2[slots], rig.e3[slots]], axis=2)
        J_mat = (F_loc @ E_fr.transpose(0, 2, 1)).astype(np.float32)

        c6 = model.cloud.cov6[rig.fol_idx]
        Sig0 = np.zeros((len(c6), 3, 3), dtype=np.float32)
        Sig0[:, 0, 0], Sig0[:, 0, 1], Sig0[:, 0, 2] = c6[:, 0], c6[:, 1], c6[:, 2]
        Sig0[:, 1, 0], Sig0[:, 1, 1], Sig0[:, 1, 2] = c6[:, 1], c6[:, 3], c6[:, 4]
        Sig0[:, 2, 0], Sig0[:, 2, 1], Sig0[:, 2, 2] = c6[:, 2], c6[:, 4], c6[:, 5]

        Sig1 = J_mat @ Sig0 @ J_mat.transpose(0, 2, 1)
        Sig1 = 0.5 * (Sig1 + Sig1.transpose(0, 2, 1))
        cov6_out[rig.fol_idx] = Sig1[:, [0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]]
        nrms_out[rig.fol_idx] = n_tilde.astype(np.float32)

        evals, evecs = np.linalg.eigh(Sig1.astype(np.float64))
        scales_out[rig.fol_idx] = np.sqrt(np.maximum(evals, 1e-14)).astype(np.float32)
        # Ensure proper right-handed rotation matrices (det == +1) for PLY quaternion export
        det_sgn = np.linalg.det(evecs) < 0.0
        evecs[det_sgn, :, 0] *= -1.0
        xyzw = Rotation.from_matrix(evecs).as_quat()
        quats_out[rig.fol_idx] = np.column_stack([xyzw[:, 3], xyzw[:, 0], xyzw[:, 1], xyzw[:, 2]]).astype(np.float32)

    # Hard invariant: exact 0.000000 displacement on static support, stand & stem skeleton!
    rigid_m = model.kernel_labels < 0
    means_out[rigid_m] = model.cloud.means[rigid_m]
    cov6_out[rigid_m] = model.cloud.cov6[rigid_m]
    scales_out[rigid_m] = model.cloud.scales[rigid_m]
    quats_out[rigid_m] = model.cloud.quats_wxyz[rigid_m]

    # Physics conservation audit: spine arc-length relative error & tip displacement
    idx_s1 = int(np.argmin(np.abs(s_grid - 1.0)))
    seg_lens = np.linalg.norm(np.diff(gamma_lut[:, : idx_s1 + 1, :], axis=1), axis=2).sum(axis=1)
    target_s = float(s_grid[idx_s1])
    arclen_rel_err_pct = 100.0 * float(np.median(np.abs(seg_lens - target_s) / max(target_s, 1e-6)))

    tip_slots = np.arange(rig.num_organs, dtype=np.int32)
    tips_rest = rig.p_base + rig.blade_len[:, None] * rig.e1
    tips_def, _ = _eval_universal_deform_pts(
        tip_slots, rig.blade_len, np.zeros(rig.num_organs), np.zeros(rig.num_organs),
        rig, spec, s_grid, gamma_lut, B_lut, N_lut,
    )
    tip_disp_cm = 100.0 * float(np.mean(np.linalg.norm(tips_def - tips_rest, axis=1)))
    static_m = (model.kernel_labels == LABEL_BASAL_SUPPORT) | (model.kernel_labels == LABEL_STATIC_STAND_OR_TABLE)
    static_drift = float(np.max(np.linalg.norm(means_out[static_m] - model.cloud.means[static_m], axis=1)) / model.p_med) if np.any(static_m) else 0.0

    # Update organ frames approximately so hybrid spline renderer also tracks gentle morphs if invoked
    ctr_slots = np.arange(rig.num_organs, dtype=np.int32)
    u_ctr = np.array([(o.centroid - o.p_base) @ o.e1 for o in model.organs], dtype=np.float64)
    v_ctr = np.array([(o.centroid - o.p_base) @ o.e2 for o in model.organs], dtype=np.float64)
    w_ctr = np.array([(o.centroid - o.p_base) @ o.e3 for o in model.organs], dtype=np.float64)
    new_ctrs, new_e3 = _eval_universal_deform_pts(ctr_slots, u_ctr, v_ctr, w_ctr, rig, spec, s_grid, gamma_lut, B_lut, N_lut)
    new_organs = []
    for slot, org in enumerate(model.organs):
        e1_d = tips_def[slot] - rig.p_base[slot]
        e1_d /= max(float(np.linalg.norm(e1_d)), 1e-12)
        e3_d = new_e3[slot] / max(float(np.linalg.norm(new_e3[slot])), 1e-12)
        e2_d = np.cross(e3_d, e1_d)
        e2_d /= max(float(np.linalg.norm(e2_d)), 1e-12)
        e3_d = np.cross(e1_d, e2_d)
        new_organs.append(
            replace(
                org,
                centroid=new_ctrs[slot],
                e1=e1_d,
                e2=e2_d,
                e3=e3_d,
                length=org.length * float(spec.len_scale[slot]),
                width=org.width * float(spec.wid_base[slot] + 0.5 * spec.wid_tip_add[slot]),
            )
        )

    out_cloud = SceneGaussianCloud(
        means=means_out,
        scales=scales_out,
        quats_wxyz=quats_out,
        cov6=cov6_out,
        surfel_normals=nrms_out,
        opacities=model.cloud.opacities.copy(),
        rgb_dc=model.cloud.rgb_dc.copy(),
        shs=model.cloud.shs.copy(),
    )
    stats = {
        "static_max_drift_pmed": round(static_drift, 6),
        "arclength_rel_err_pct": round(arclen_rel_err_pct, 5),
        "tip_mean_disp_cm": round(tip_disp_cm, 2),
    }
    return replace(model, cloud=out_cloud, organs=new_organs), stats


# ---------------------------------------------------------------------------
# 4. Horticultural Organ Pruning / Crown Windowing & Procedural Apical Sprouting
# ---------------------------------------------------------------------------


def apply_horticultural_organ_pruning(
    model: UniversalBotanicalModel,
    cam_center: np.ndarray,
    prune_fraction: float = 0.22,
) -> tuple[UniversalBotanicalModel, set[int], dict[str, Any]]:
    """Selectively prune a coherent front-crown window of outer organs to expose occluded inner structures cleanly."""
    if len(model.organs) < 4:
        return model, set(), {"pruned_organs": 0, "pruned_kernels": 0}

    ctrs = np.array([o.centroid for o in model.organs], dtype=np.float64)
    plant_ctr = np.median(ctrs, axis=0)
    to_cam = cam_center - plant_ctr
    to_cam_xy = to_cam[:2] / max(float(np.linalg.norm(to_cam[:2])), 1e-8)

    # Score outer/mid organs in a coherent front-left horticultural window so pruning opens a dramatic view into the inner plant!
    perp_xy = np.array([-to_cam_xy[1], to_cam_xy[0]])
    front_proj = (ctrs[:, :2] - plant_ctr[:2]) @ to_cam_xy
    side_proj = (ctrs[:, :2] - plant_ctr[:2]) @ perp_xy
    z_rel = (ctrs[:, 2] - np.percentile(ctrs[:, 2], 15.0)) / max(float(np.ptp(ctrs[:, 2])), 1e-3)

    scores = front_proj + 0.35 * side_proj + 0.15 * np.abs(z_rel - 0.55)
    eligible = [i for i, o in enumerate(model.organs) if o.visibility_tier != "DEEP_OCCLUDED"]
    if not eligible:
        eligible = list(range(len(model.organs)))

    n_prune = max(1, min(len(eligible) - 2, int(round(prune_fraction * len(model.organs)))))
    ranked = sorted(eligible, key=lambda i: -float(scores[i]))
    pruned_oids = {model.organs[i].organ_id for i in ranked[:n_prune]}

    keep_k = ~np.isin(model.kernel_labels, list(pruned_oids))
    old_to_new = np.full(len(model.cloud.means), -1, dtype=np.int32)
    old_to_new[keep_k] = np.arange(int(keep_k.sum()), dtype=np.int32)

    kept_organs = []
    for o in model.organs:
        if o.organ_id in pruned_oids:
            continue
        new_ki = old_to_new[o.kernel_indices]
        kept_organs.append(replace(o, kernel_indices=new_ki[new_ki >= 0]))

    new_lbl = model.kernel_labels[keep_k].copy()
    new_sup = replace(
        model.support,
        support_kernel_mask=(new_lbl == LABEL_BASAL_SUPPORT),
        stand_kernel_mask=(new_lbl == LABEL_STATIC_STAND_OR_TABLE),
    )
    new_cloud = SceneGaussianCloud(
        means=model.cloud.means[keep_k].copy(),
        scales=model.cloud.scales[keep_k].copy(),
        quats_wxyz=model.cloud.quats_wxyz[keep_k].copy(),
        cov6=model.cloud.cov6[keep_k].copy(),
        surfel_normals=model.cloud.surfel_normals[keep_k].copy(),
        opacities=model.cloud.opacities[keep_k].copy(),
        rgb_dc=model.cloud.rgb_dc[keep_k].copy(),
        shs=model.cloud.shs[keep_k].copy(),
    )
    pruned_model = UniversalBotanicalModel(
        scene_name=model.scene_name,
        p_med=model.p_med,
        support=new_sup,
        stem_chains=list(model.stem_chains),
        organs=kept_organs,
        cloud=new_cloud,
        kernel_labels=new_lbl,
        stem_owner=model.stem_owner[keep_k].copy(),
    )
    stats = {
        "pruned_organs": len(pruned_oids),
        "remaining_organs": len(kept_organs),
        "pruned_kernels": int((~keep_k).sum()),
        "remaining_kernels": int(keep_k.sum()),
    }
    return pruned_model, pruned_oids, stats


def apply_procedural_apical_sprouting(
    model: UniversalBotanicalModel,
    num_loci: int = 10,
    buds_per_locus: int = 4,
    growth_progress: float = 1.0,
) -> tuple[UniversalBotanicalModel, dict[str, Any]]:
    """Discover species-specific organ allometry & chromaticity and sprout tender apical shoots & young organs!"""
    prog = float(np.clip(growth_progress, 0.05, 1.0))
    if not model.organs:
        return model, {"new_shoots": 0, "new_organs": 0, "added_kernels": 0}

    outer_orgs = [o for o in model.organs if o.visibility_tier == "OUTER_ENCLOSED"] or list(model.organs)
    med_len = float(np.median([o.length for o in outer_orgs]))
    med_wl = float(np.clip(np.median([o.width / max(o.length, 1e-4) for o in outer_orgs]), 0.24, 0.92))
    med_cusp = float(np.median([o.apex_cusp_gamma for o in outer_orgs]))
    k_ctrl = len(model.organs[0].periodic_ctrl_r)
    mean_ctrl = np.median(np.array([o.periodic_ctrl_r for o in outer_orgs]), axis=0)

    # Data-driven upper-crown tender chromaticity: boost freshness/luminance of the plant's own vivid upper organs!
    upper_rgbs = np.array([o.mean_rgb for o in sorted(outer_orgs, key=lambda x: -x.centroid[2])[: max(4, len(outer_orgs) // 3)]])
    med_rgb = np.median(upper_rgbs, axis=0)
    h_base, s_base, v_base = colorsys.rgb_to_hsv(float(med_rgb[0]), float(med_rgb[1]), float(med_rgb[2]))
    # Shift slightly toward luminous tender bud hue while preserving whether the plant is green, sakura-pink, or bronze-coral!
    if 0.16 <= h_base <= 0.48:
        # Green foliage species -> fresh spring chartreuse-jade tender shoots!
        h_bud = max(0.21, h_base - 0.04)
        s_bud = min(0.82, max(s_base * 1.15, 0.58))
        v_bud = min(0.94, max(v_base * 1.32, 0.78))
    else:
        # Ornamental blossom / bronze / warm species -> radiant luminous bud/petal tint!
        h_bud = h_base
        s_bud = min(0.78, max(s_base * 1.12, 0.48))
        v_bud = min(0.96, max(v_base * 1.25, 0.84))
    bud_tip_rgb = np.array(colorsys.hsv_to_rgb(h_bud, s_bud * 0.78, v_bud), dtype=np.float32)
    bud_base_rgb = np.array(colorsys.hsv_to_rgb((h_bud + 0.03) % 1.0, min(0.90, s_bud * 1.08), v_bud * 0.76), dtype=np.float32)
    shoot_rgb = np.array([0.44, 0.62, 0.28], dtype=np.float32) if (0.16 <= h_base <= 0.48) else np.array([0.48, 0.34, 0.26], dtype=np.float32)

    # Select well-spaced upper-crown apical loci
    ctrs = np.array([o.centroid for o in model.organs], dtype=np.float64)
    plant_xy = np.median(ctrs[:, :2], axis=0)
    z_span = max(float(np.ptp(ctrs[:, 2])), 0.15)
    z_cut = float(np.percentile(ctrs[:, 2], 76.0))
    cand_idxs = np.flatnonzero(ctrs[:, 2] >= z_cut).tolist()
    cand_idxs.sort(key=lambda i: -float(ctrs[i, 2]))

    chosen_loci: list[np.ndarray] = []
    min_sep = max(0.14 * float(np.linalg.norm(np.ptp(ctrs[:, :2], axis=0))), 8.0 * model.p_med)
    for ci in cand_idxs:
        pt = ctrs[ci]
        if all(float(np.linalg.norm(pt - prev)) >= min_sep for prev in chosen_loci):
            chosen_loci.append(pt)
            if len(chosen_loci) >= num_loci:
                break

    next_oid = max(o.organ_id for o in model.organs) + 1
    next_cid = (max(s.chain_id for s in model.stem_chains) + 1) if model.stem_chains else 0

    new_means_l, new_scales_l, new_quats_l, new_nrms_l = [], [], [], []
    new_op_l, new_rgb_l, new_lbl_l, new_stem_own_l = [], [], [], []
    new_stems = list(model.stem_chains)
    new_organs = list(model.organs)

    shoot_h = np.clip(0.85 * med_len, 0.05 * z_span, 0.16 * z_span) * prog
    leaf_L = np.clip(0.72 * med_len, 8.0 * model.p_med, 0.14 * z_span) * (0.35 + 0.65 * prog)
    leaf_W = max(leaf_L * med_wl, 5.0 * model.p_med)

    # Prebuild canonical 2D leaf sample grid inside unit circle
    ug = np.linspace(-0.92, 0.92, 9)
    vg = np.linspace(-0.92, 0.92, 7)
    UU, VV = np.meshgrid(ug, vg)
    uu_f, vv_f = UU.ravel(), VV.ravel()
    inside = (uu_f ** 2 + vv_f ** 2) <= 0.95
    uu_f, vv_f = uu_f[inside], vv_f[inside]

    cur_n = len(model.cloud.means)
    added_k = 0

    for li, base_pt in enumerate(chosen_loci):
        out_dir = base_pt[:2] - plant_xy
        out_n = float(np.linalg.norm(out_dir))
        rad_xy = (out_dir / out_n) if out_n > 1e-4 else np.array([math.cos(li * 2.4), math.sin(li * 2.4)])

        # Curved tender apical shoot spline
        s_t = np.linspace(0.0, 1.0, 14)
        sh_pts = (
            base_pt[None, :]
            + (s_t[:, None] * shoot_h) * np.array([[0.22 * rad_xy[0], 0.22 * rad_xy[1], 1.0]])
            + ((s_t ** 2)[:, None] * 0.18 * shoot_h) * np.array([[rad_xy[0], rad_xy[1], 0.0]])
        )
        ctrl_s = fit_clamped_bspline_3d(sh_pts, num_ctrl=4, reg=1e-2)
        cid = next_cid
        next_cid += 1
        new_stems.append(
            StemSplineChain(
                chain_id=cid, level=1, parent_chain_id=-1, parent_u=1.0,
                ctrl_points=ctrl_s, radius_base=1.8 * model.p_med, radius_tip=1.1 * model.p_med,
                supported_kernel_count=len(sh_pts), basal_anchored=False,
            )
        )

        # Add shoot Gaussians
        n_sh = len(sh_pts)
        new_means_l.append(sh_pts.astype(np.float32))
        new_scales_l.append(np.tile(np.array([[1.1 * model.p_med, 1.1 * model.p_med, 2.2 * model.p_med]], dtype=np.float32), (n_sh, 1)))
        new_quats_l.append(np.tile(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32), (n_sh, 1)))
        new_nrms_l.append(np.tile(np.array([[rad_xy[0], rad_xy[1], 0.0]], dtype=np.float32), (n_sh, 1)))
        new_op_l.append(np.full(n_sh, 0.90, dtype=np.float32))
        new_rgb_l.append(np.tile(shoot_rgb[None, :], (n_sh, 1)))
        new_lbl_l.append(np.full(n_sh, LABEL_STEM_SKELETON, dtype=np.int32))
        new_stem_own_l.append(np.full(n_sh, cid, dtype=np.int32))
        added_k += n_sh

        # Sprout buds_per_locus young phyllotactic leaves along upper half of shoot!
        for bi in range(buds_per_locus):
            u_attach = 0.45 + 0.52 * (bi / max(buds_per_locus - 1, 1))
            p_att, _ = eval_clamped_bspline(ctrl_s, np.array([u_attach]))
            p_att = p_att[0]
            az = li * 1.7 + bi * math.radians(137.507764)
            pitch = math.radians(38.0 + 10.0 * (bi / max(buds_per_locus, 1)))
            e1_b = np.array([math.cos(pitch) * math.cos(az), math.cos(pitch) * math.sin(az), math.sin(pitch)], dtype=np.float64)
            e1_b /= np.linalg.norm(e1_b)
            up_ref = np.array([0.0, 0.0, 1.0], dtype=np.float64)
            e2_b = np.cross(up_ref, e1_b)
            e2_b /= max(float(np.linalg.norm(e2_b)), 1e-8)
            e3_b = np.cross(e1_b, e2_b)

            # Scale transverse width by species periodic envelope + cusp taper
            th_g = np.arctan2(vv_f, uu_f)
            r_g = eval_periodic_cubic_bspline_1d(mean_ctrl, th_g)
            u_loc = uu_f * r_g * (0.5 * leaf_L)
            v_loc = vv_f * r_g * (0.5 * leaf_W) * (1.0 - 0.25 * med_cusp * (np.abs(np.cos(th_g)) ** 3))
            # Gentle graceful young-leaf arch
            s_01_g = np.clip((u_loc / max(leaf_L, 1e-4)) + 0.5, 0.0, 1.0)
            w_loc = -0.10 * leaf_L * (s_01_g ** 2) + 0.08 * leaf_W * ((v_loc / max(0.5 * leaf_W, 1e-4)) ** 2)

            ctr_b = p_att + 0.5 * leaf_L * e1_b
            pts_b = ctr_b[None, :] + u_loc[:, None] * e1_b[None, :] + v_loc[:, None] * e2_b[None, :] + w_loc[:, None] * e3_b[None, :]
            nb = len(pts_b)

            # Orient surfel quaternion to frame [e1_b, e2_b, e3_b]
            Rm_b = np.column_stack([e1_b, e2_b, e3_b])
            qb_xyzw = Rotation.from_matrix(Rm_b).as_quat()
            qb_wxyz = np.array([qb_xyzw[3], qb_xyzw[0], qb_xyzw[1], qb_xyzw[2]], dtype=np.float32)

            sc_u = max(leaf_L / 7.2, 0.9 * model.p_med)
            sc_v = max(leaf_W / 6.2, 0.8 * model.p_med)
            sc_w = max(0.35 * model.p_med, 1e-4)
            col_b = (1.0 - s_01_g[:, None]) * bud_base_rgb[None, :] + s_01_g[:, None] * bud_tip_rgb[None, :]

            oid = next_oid
            next_oid += 1
            k_indices_b = np.arange(cur_n + added_k, cur_n + added_k + nb, dtype=np.int32)
            added_k += nb

            new_means_l.append(pts_b.astype(np.float32))
            new_scales_l.append(np.tile(np.array([[sc_u, sc_v, sc_w]], dtype=np.float32), (nb, 1)))
            new_quats_l.append(np.tile(qb_wxyz[None, :], (nb, 1)))
            new_nrms_l.append(np.tile(e3_b.astype(np.float32)[None, :], (nb, 1)))
            new_op_l.append(np.full(nb, 0.92, dtype=np.float32))
            new_rgb_l.append(np.clip(col_b, 0.0, 1.0).astype(np.float32))
            new_lbl_l.append(np.full(nb, oid, dtype=np.int32))
            new_stem_own_l.append(np.full(nb, -1, dtype=np.int32))

            new_organs.append(
                AdaptiveOrganPatch(
                    organ_id=oid,
                    organ_kind="LAMINAR_BLADE",
                    visibility_tier="OUTER_ENCLOSED",
                    parent_chain_id=cid,
                    p_base=p_att,
                    centroid=ctr_b,
                    e1=e1_b,
                    e2=e2_b,
                    e3=e3_b,
                    length=float(leaf_L),
                    width=float(leaf_W),
                    thickness=float(2.0 * sc_w),
                    periodic_ctrl_r=mean_ctrl.copy(),
                    apex_cusp_gamma=med_cusp,
                    camber_coef8=np.array([0.0, 0.0, 0.0, -0.10 / max(leaf_L, 1e-3), 0.0, 0.08 / max(leaf_W, 1e-3), 0.0, 0.0]),
                    kernel_indices=k_indices_b,
                    mean_rgb=col_b.mean(axis=0).astype(np.float32),
                )
            )

    if added_k == 0:
        return model, {"new_shoots": 0, "new_organs": 0, "added_kernels": 0}

    add_means = np.vstack(new_means_l)
    add_scales = np.vstack(new_scales_l)
    add_quats = np.vstack(new_quats_l)
    add_cov6 = build_cov6_from_sq(add_scales, add_quats)
    add_nrms = np.vstack(new_nrms_l)
    add_op = np.concatenate(new_op_l)
    add_rgb = np.vstack(new_rgb_l)
    add_shs = np.zeros((added_k, 16, 3), dtype=np.float32)
    add_shs[:, 0, :] = ((add_rgb - 0.5) / SH_C0).astype(np.float32)

    out_cloud = SceneGaussianCloud(
        means=np.vstack([model.cloud.means, add_means]),
        scales=np.vstack([model.cloud.scales, add_scales]),
        quats_wxyz=np.vstack([model.cloud.quats_wxyz, add_quats]),
        cov6=np.vstack([model.cloud.cov6, add_cov6]),
        surfel_normals=np.vstack([model.cloud.surfel_normals, add_nrms]),
        opacities=np.concatenate([model.cloud.opacities, add_op]),
        rgb_dc=np.vstack([model.cloud.rgb_dc, add_rgb]),
        shs=np.concatenate([model.cloud.shs, add_shs], axis=0),
    )
    lbl_final = np.concatenate([model.kernel_labels, np.concatenate(new_lbl_l)])
    out_sup = replace(
        model.support,
        support_kernel_mask=(lbl_final == LABEL_BASAL_SUPPORT),
        stand_kernel_mask=(lbl_final == LABEL_STATIC_STAND_OR_TABLE),
    )
    out_model = UniversalBotanicalModel(
        scene_name=model.scene_name,
        p_med=model.p_med,
        support=out_sup,
        stem_chains=new_stems,
        organs=new_organs,
        cloud=out_cloud,
        kernel_labels=lbl_final,
        stem_owner=np.concatenate([model.stem_owner, np.concatenate(new_stem_own_l)]),
    )
    stats = {
        "discovered_median_organ_length_cm": round(100.0 * med_len, 2),
        "discovered_median_wl_ratio": round(med_wl, 3),
        "new_shoots": len(chosen_loci),
        "new_organs": len(chosen_loci) * buds_per_locus,
        "added_kernels": int(added_k),
    }
    return out_model, stats
