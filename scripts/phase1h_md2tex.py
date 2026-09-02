"""PHASE 1h — deterministic md->tex converter for PAPER_DRAFT.md (assembly only).

NO content authoring: every prose sentence is transcribed verbatim from the .md content
region (title .. end of Appendix A; the repo assembly banner, duplicate title headers and
the grouping header are dropped — they are .md build metadata, not paper prose; every
other paragraph including the per-section italic meta notes is kept verbatim).
Emits paper/abstract.tex + paper/body.tex. Fig/Tab prose references become \\ref{}s;
citation anchors in the text are KEPT verbatim (a \\cite is appended, never substituted)
so the md->PDF number multiset stays conserved.
"""
import os
import re
import sys

TIER1 = os.path.expanduser("~/3dgs_line/tier1")
SRC = os.path.join(TIER1, "out/PAPER_DRAFT.md")
OUTDIR = os.path.join(TIER1, "paper")

UNI = [("—", "---"), ("–", "--"), ("×", "$\\times$"), ("≥", "$\\geq$"),
       ("≤", "$\\leq$"), ("≈", "$\\approx$"), ("→", "$\\rightarrow$"),
       ("·", "$\\cdot$"), ("°", "$^{\\circ}$"), ("α", "$\\alpha$"),
       ("−", "$-$"), ("é", "\\'e"), ("½", "$\\tfrac12$"), ("§", "\\S")]

# first-BODY-mention citation anchors: (literal text, cite key)
CITES = [("3D Gaussian\nSplatting (3DGS)", "kerbl3dgs"),
         ("Classical (Canny)", "canny1986"),
         ("(DexiNed, TEED,\nPiDiNet)", "dexined,teed,pidinet"),
         ("EMAP (\"3D Neural Edge\nReconstruction\", CVPR 2024)", "emap"),
         ("**SketchSplat** [arXiv 2503.14786]", "sketchsplat"),
         ("frozen zero-shot DINOv2 features", "dinov2"),
         ("two static NeRF-synthetic scenes", "nerf"),
         ]


def esc(t):
    """Escape LaTeX specials in plain text (math/tokens handled around this)."""
    t = t.replace("\\", "\\textbackslash{}")
    for a, b in [("%", "\\%"), ("&", "\\&"), ("#", "\\#"), ("_", "\\_"),
                 ("$", "\\$"), ("{", "\\{"), ("}", "\\}"), ("~", "\\textasciitilde{}"),
                 ("^", "\\textasciicircum{}")]:
        t = t.replace(a, b)
    return t


def inline(t):
    """md inline -> tex, on one paragraph of raw md text."""
    toks = {}

    def stash(s):
        k = f"@@TOK{len(toks)}@@"
        toks[k] = s
        return k

    # code spans first (verbatim, escaped)
    t = re.sub(r"`([^`]+)`", lambda m: stash("\\texttt{" + esc(m.group(1)) + "}"), t)
    # citation anchors: append \cite AFTER the kept-verbatim anchor text
    for lit, key in CITES:
        if lit in t:
            rep = lit + f"@@CITE:{key}@@"
            t = t.replace(lit, rep, 1)
    # unicode -> tex tokens
    for a, b in UNI:
        t = t.replace(a, stash(b))
    # Fig/Tab references -> \ref tokens ("Fig 6b" handled by trailing letter grp)
    t = re.sub(r"Figs? (\d)([ab])?",
               lambda m: stash("Fig.~\\ref{fig:%s}%s" % (m.group(1), m.group(2) or "")), t)
    t = re.sub(r"Tab (\d)",
               lambda m: stash("Tab.~\\ref{tab:%s}" % m.group(1)), t)
    # escape the rest
    t = esc(t)
    # md emphasis (after escaping; * survives esc)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", t)
    t = re.sub(r"\*([^*]+)\*", r"\\emph{\1}", t)
    # restore tokens & cites
    for k, v in toks.items():
        t = t.replace(k, v)
    t = re.sub(r"@@CITE:([a-z0-9,]+)@@", r"~\\cite{\1}", t)
    return t


def main():
    lines = open(SRC).read().splitlines()
    # content region: skip top title/meta; start at '## Abstract' (the real one),
    # stop before the assets table
    try:
        start = lines.index("## Abstract")
    except ValueError:
        sys.exit("no '## Abstract' header")
    stop = lines.index("## Figure & table assets")
    body = lines[start:stop]

    # split into paragraphs, tracking headers; a '## ' line is ALWAYS its own
    # paragraph even when the next line follows without a blank (header + meta note)
    paras, cur = [], []
    for ln in body:
        if ln.strip() == "" or ln.strip() == "---":
            if cur:
                paras.append("\n".join(cur))
                cur = []
        elif ln.startswith("## "):
            if cur:
                paras.append("\n".join(cur))
                cur = []
            paras.append(ln)
        else:
            cur.append(ln)
    if cur:
        paras.append("\n".join(cur))

    abstract, out = [], []
    mode = None
    enum_open = False
    for p in paras:
        h = re.match(r"^## (.+)$", p.split("\n")[0])
        if h and p.count("\n") == 0:
            title = h.group(1)
            if title == "Abstract":
                mode = "abstract"
                continue
            if re.match(r"^Abstract & §1", title):
                continue
            m = re.match(r"^(?:§(\d) — |(\d)\. )(.+)$", title)
            if m:                                     # \section
                name = m.group(3)
                mode = "body"
                if enum_open:
                    out.append("\\end{enumerate}")
                    enum_open = False
                out.append("\\section{%s}" % inline(name))
                continue
            m = re.match(r"^(\d)\.(\d) (.+)$", title)
            if m:                                     # \subsection
                out.append("\\subsection{%s}" % inline(m.group(3)))
                continue
            m = re.match(r"^Appendix A — (.+)$", title)
            if m:
                out.append("\\appendices")
                out.append("\\section{%s}" % inline(m.group(1)))
                continue
            sys.exit("unhandled header: " + title)
        # enumerate items (contributions)
        m = re.match(r"^(\d)\. (.*)$", p, re.S)
        if m and mode == "body":
            if not enum_open:
                out.append("\\begin{enumerate}")
                enum_open = True
            item = re.sub(r"\n   ", "\n", m.group(2))
            out.append("\\item " + inline(item))
            continue
        if enum_open:
            out.append("\\end{enumerate}")
            enum_open = False
        tgt = abstract if mode == "abstract" else out
        tgt.append(inline(p))
        tgt.append("")
    if enum_open:
        out.append("\\end{enumerate}")

    out = inject_floats(out)
    # split at \appendix: references go between the main body and Appendix A
    ai = out.index("\\appendices")
    main_body, appendix = out[:ai], out[ai:]

    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "abstract.tex"), "w").write("\n".join(abstract) + "\n")
    open(os.path.join(OUTDIR, "body_main.tex"), "w").write("\n".join(main_body) + "\n")
    open(os.path.join(OUTDIR, "body_appendix.tex"), "w").write("\n".join(appendix) + "\n")
    supp = (["\\section*{Supplementary figures and tables}",
             "\\noindent\\emph{Referenced from the main text; numbering matches the "
             "in-text references.}", ""] + SUPP)
    open(os.path.join(OUTDIR, "supp_floats.tex"), "w").write("\n".join(supp) + "\n")
    print(f"wrote paper/abstract.tex ({len(abstract)}), "
          f"paper/body_main.tex ({len(main_body)}), "
          f"paper/body_appendix.tex ({len(appendix)}), paper/supp_floats.tex")


def fig(n, path, cap, width=1.0, pl="t", col=False):
    env = "figure" if col else "figure*"
    wid = "\\columnwidth" if col else f"{width}\\textwidth"
    return (f"\\begin{{{env}}}[{pl}]\\centering"
            f"\\setcounter{{figure}}{{{n - 1}}}"
            f"\\includegraphics[width={wid}]{{{path}}}"
            f"\\caption{{{cap}}}\\label{{fig:{n}}}\\end{{{env}}}")


def tab(n, path, cap, width=1.0, pl="t"):
    return (f"\\begin{{table*}}[{pl}]\\centering"
            f"\\setcounter{{table}}{{{n - 1}}}"
            f"\\caption{{{cap}}}\\label{{tab:{n}}}"
            f"\\includegraphics[width={width}\\textwidth]{{{path}}}\\end{{table*}}")


FIG2 = ("\\begin{figure*}[t]\\centering\\setcounter{figure}{1}"
        "\\begin{minipage}{0.475\\textwidth}\\centering"
        "\\includegraphics[width=\\textwidth]{assets/pareto_chair.png}\\\\(a) chair"
        "\\end{minipage}\\hfill"
        "\\begin{minipage}{0.475\\textwidth}\\centering"
        "\\includegraphics[width=\\textwidth]{assets/pareto_lego.png}\\\\(b) lego"
        "\\end{minipage}"
        "\\caption{PARETO-1 precision/line-density operating frontiers: (a) chair, "
        "(b) lego.}\\label{fig:2}\\end{figure*}")

# MAIN-BODY floats (anchor searched in paragraph text, block inserted BEFORE it).
# Low-load-bearing floats live in SUPP below (after References, before Appendix A) to
# meet the 8-content-page budget WITHOUT cutting any prose; explicit \setcounter keeps
# every number identical to the .md's Fig/Tab numbering regardless of placement.
FLOATS = [
    ("\\section{Introduction}",
     fig(1, "assets/fig1_teaser.png",
         "Teaser: object-space strokes versus per-frame line detection, with a "
         "two-frame overlap visualizing stroke identity across a camera step.", 0.7)),
    ("\\ref{fig:2}", FIG2),
    ("\\ref{fig:3}",
     fig(3, "assets/fig3_pareto2.png",
         "Per-condition worst-case stability advantage against the oracle-flow "
         "accumulated baseline; the gate-breaching lego$\\times$T3 cell is flagged "
         "as the reported floor.", col=True)),
    ("\\ref{fig:5}",
     fig(5, "assets/fig5_survival.png",
         "Stroke-survival curves P(life${}>{}$K) for the six scene$\\times$trajectory "
         "conditions: object-space strokes persist for tens-to-hundreds of frames; "
         "per-frame strokes essentially never do.", 0.7)),
    ("\\ref{fig:6}",
     fig(6, "assets/fig6_ceiling.png",
         "Act 1: the carrier coverage ceiling, and the recovery ladder from "
         "single-view lifting to multi-view triangulation.", 0.66)),
]

# Supplementary floats (referenced from the main text; placed after References with
# their md numbering preserved via \setcounter — standard supplementary convention).
SUPP = [
    tab(1, "assets/tab1_stroke_ratios.png",
        "Matched-stroke E-warp ratios across scenes, trajectories and detectors.",
        0.8, pl="t"),
    tab(2, "assets/tab2_floor_anatomy.png",
        "Floor anatomy of the pooled-mean statistic.", 0.62, pl="t"),
    tab(3, "assets/tab3_kgeom.png",
        "K\\textsubscript{geom}: geometric cues on the miss-set.", 0.55, pl="t"),
    tab(4, "assets/tab4_gate_ledger.png",
        "The frozen-gate ledger: every pre-registered gate, its bar, its measured "
        "value, and its disposition.", 0.62, pl="t"),
    fig(4, "assets/fig4_pareto3.png",
        "Disocclusion decomposition of the hardest cell: the advantage is interior, "
        "reverses inside disocclusion regions, and the mechanism gate lands NO-GO.",
        0.75, pl="t"),
    fig(7, "assets/fig7_semantic.png",
        "Act 3: frozen-DINOv2 crease-probability read-out and probe AUCs.",
        0.85, pl="t"),
    fig(8, "assets/fig8_supervision.png",
        "Act 4: the mesh-free supervision collapse, and the asymmetric cross-scene "
        "transfer.", 0.75, pl="t"),
]


def inject_floats(out):
    res = list(out)
    for anchor, block in FLOATS:
        for i, p in enumerate(res):
            if anchor in p and not p.startswith("\\begin{figure")\
               and not p.startswith("\\begin{table"):
                if anchor.startswith("\\section") or anchor.startswith("\\subsection"):
                    res.insert(i + 1, block)     # teaser/Fig8: after the header
                else:
                    res.insert(i, block)
                break
        else:
            sys.exit(f"float anchor not found: {anchor}")
    return res


if __name__ == "__main__":
    main()
