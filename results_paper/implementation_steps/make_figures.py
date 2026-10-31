#!/usr/bin/env python3
"""Figures for the implementation-history report (one figure per development step)."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

PAIR = "#2563eb"
OUTSIDER = "#dc2626"
SAME = "#d97706"
ASSIST = "#0f766e"
GREY = "#68707d"
V4_CONDITIONS = ["no_channel", "channel_optional", "channel_optional_hint", "channel_forced", "channel_forced_strategy"]
V4_LABELS = ["1. No\nchannel", "2. Optional", "3. Optional\n+ hint", "4. Forced", "5. Forced\n+ strategy"]


def ci(text: str) -> tuple[float, float, float]:
    """Parse '0.52 [0.20, 0.80]' or '+0.20 [+0.14     +0.25]'."""
    nums = [float(x) for x in re.findall(r"[-+]?\d+(?:\.\d+)?", text)]
    return (nums[0], nums[1], nums[2]) if len(nums) >= 3 else (nums[0], nums[0], nums[0])


def pct(text: str) -> float:
    return float(text.strip().rstrip("%").split()[0])


def style(ax, title):
    ax.set_title(title, fontsize=11, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def save(fig, name):
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=170)
    plt.close(fig)


# Step 1: v1 prompts, 7-8B models -------------------------------------------------
def step1():
    rows = list(csv.DictReader(open(RES / "llm_rps" / "summary.csv")))
    conds = ["independent", "channel", "channel_shared", "instructed"]
    labels = ["Independent", "Channel", "Channel +\nshared reward", "Instructed\nalternation"]
    models = [("qwen2.5_7b", "Qwen2.5-7B"), ("llama3.1_8b", "Llama-3.1-8B")]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    x = np.arange(len(conds))
    for i, (m, lab) in enumerate(models):
        sub = {r["condition"]: r for r in rows if r["model"] == m}
        adv = [ci(sub[c]["pair_advantage"]) for c in conds]
        ass = [ci(sub[c]["assist_rate_pct"])[0] for c in conds]
        pf = [int(sub[c]["parse_failures"]) for c in conds]
        col = [PAIR, GREY][i]
        axes[0].errorbar(x + (i - 0.5) * 0.2, [a[0] for a in adv],
                         yerr=[[a[0] - a[1] for a in adv], [a[2] - a[0] for a in adv]],
                         fmt="o", color=col, capsize=3, label=lab)
        axes[1].bar(x + (i - 0.5) * 0.38, ass, 0.38, color=col, label=lab)
        axes[2].bar(x + (i - 0.5) * 0.38, pf, 0.38, color=col, label=lab)
    axes[0].axhline(0, color="k", lw=0.8)
    style(axes[0], "Pair advantage (A+B)/2 − C, points/round")
    style(axes[1], "Assistance rate, % of rounds")
    style(axes[2], "Move parse failures (10 games × 100 rounds)")
    for ax in axes:
        ax.set_xticks(x, labels, fontsize=8)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Step 1 — v1 prompts, 7–8B models: assistance can be instructed, but never pays", x=0.01, ha="left")
    save(fig, "step1_v1_small_models")


# Step 2: Qwen2.5-14B pot runs, 20 games × 100 rounds -----------------------------
def step2():
    text = (RES / "analyse_14B_pot_runs.md").read_text()
    sections = re.split(r"^### \d+\. ", text, flags=re.M)[1:]
    names, scores, same, strat = [], [], [], []
    for sec in sections:
        title = sec.splitlines()[0].split(" (")[0]
        title = title.replace("indice public", "public hint").replace("indice", "hint").replace("réflexion", "reflection")
        runs = [l for l in sec.splitlines() if re.match(r"\|\s*\d+\s*\|", l)]
        a = np.array([[float(c) for c in l.split("|")[2:5]] for l in runs])
        sm = [pct(l.split("|")[7]) for l in runs]
        names.append(title)
        scores.append(a.mean(axis=0))
        same.append(np.mean(sm))
        strat.append(Counter(l.split("|")[6].strip() for l in runs))
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw={"width_ratios": [1, 1.4]})
    x = np.arange(len(names))
    s = np.array(scores)
    for j, (lab, col) in enumerate([("A", PAIR), ("B", "#60a5fa"), ("C (outsider)", OUTSIDER)]):
        axes[0].bar(x + (j - 1) * 0.27, s[:, j], 0.27, color=col, label=lab)
    axes[0].set_xticks(x, [n.replace(" + ", "\n+ ") for n in names], fontsize=8)
    axes[0].legend(frameon=False, fontsize=8)
    style(axes[0], "Mean final score per player (100 rounds)")
    groups = {
        "Same move (fixed or varied block)": lambda k: k.startswith("Bloc"),
        "Assistance (one-way or both ways)": lambda k: "sacrifie" in k or "Assistance" in k,
        "Synchronised cycle": lambda k: k.startswith("Cycle"),
        "Mixed": lambda k: k.startswith("Mixte"),
    }
    colors = [SAME, ASSIST, "#7c3aed", GREY]
    bottom = np.zeros(len(names))
    for (g, f), col in zip(groups.items(), colors):
        vals = np.array([sum(v for k, v in c.items() if f(k)) for c in strat], dtype=float)
        vals = vals / np.array([sum(c.values()) for c in strat]) * 100
        axes[1].bar(x, vals, 0.6, bottom=bottom, color=col, label=g)
        bottom += vals
    axes[1].set_xticks(x, [n.replace(" + ", "\n+ ") for n in names], fontsize=8)
    axes[1].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1, 1))
    style(axes[1], "Strategy the pair converged to, % of games")
    fig.suptitle("Step 2 — Qwen2.5-14B, 20 games × 100 rounds: with a channel, the pair forms a same-move block and C wins",
                 x=0.01, ha="left")
    save(fig, "step2_qwen14b_same_move_block")


# Step 3: v2-chat vs v3 smoke tests (32B, 1 game × 5 rounds per cell) -------------
def step3():
    text = (RES / "llm_rps_v2" / "smoke" / "REPORT.md").read_text()
    overview, pooled = defaultdict(list), {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 7 and "pot_plan" in cells[1]:
            version = "v3" if "v3" in cells[1] else ("v2-chat (old limits)" if "old" in cells[1] else "v2-chat")
            for cond, sc in zip(V4_CONDITIONS, cells[2:]):
                a, b, c = [float(v) for v in sc.split("/")]
                overview[(version, cond)].append(((a + b) / 2 - c) / 5)
        if len(cells) == 7 and cells[0] in V4_CONDITIONS and cells[1].isdigit():
            pooled[cells[0]] = (pct(cells[4]), pct(cells[5]), pct(cells[6]))
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.3))
    x = np.arange(5)
    for i, (v, col) in enumerate([("v2-chat (old limits)", "#cbd5e1"), ("v2-chat", GREY), ("v3", PAIR)]):
        vals = [np.mean(overview[(v, c)]) if overview[(v, c)] else np.nan for c in V4_CONDITIONS]
        axes[0].bar(x + (i - 1) * 0.27, vals, 0.27, color=col, label=v)
    axes[0].axhline(0, color="k", lw=0.8)
    axes[0].set_xticks(x, V4_LABELS, fontsize=8)
    axes[0].legend(frameon=False, fontsize=8)
    style(axes[0], "Pair advantage, points/round (mean of 1–3 smoke games)")
    p = np.array([pooled[c] for c in V4_CONDITIONS])
    axes[1].bar(x - 0.2, p[:, 0], 0.4, color=SAME, label="Same move (A = B)")
    axes[1].bar(x + 0.2, p[:, 1], 0.4, color=ASSIST, label="One partner hands the round to the other")
    axes[1].plot(x, p[:, 2], "k--o", ms=4, label="Nobody scores")
    axes[1].set_xticks(x, V4_LABELS, fontsize=8)
    axes[1].legend(frameon=False, fontsize=8)
    style(axes[1], "Round types, % (8 smoke games pooled per condition)")
    fig.suptitle("Step 3 — v2-chat / v3 smoke tests (32B): clearer rules did not remove the same-move trap; "
                 "the cycle hint was executed with errors", x=0.01, ha="left", fontsize=10)
    save(fig, "step3_v2chat_v3_smoke")


# Step 4: v4 full campaigns ---------------------------------------------------------
V4_DIRS = [("Qwen 2.5 32B", "20261025-1834_same_model_qwen32b_big-v4", PAIR),
           ("GLM-4 32B", "20261025-1837_same_model_glm32b_big-v4", ASSIST),
           ("Mixtral 8x7B", "20261025-1853_same_model_mixtral8x7b_big-v4", SAME)]


def v4_rows():
    out = {}
    for lab, d, col in V4_DIRS:
        rows = {r["condition"]: r for r in csv.DictReader(open(RES / "llm_rps_v2" / d / "summary.csv"))}
        out[lab] = rows
    return out


def step4():
    data = v4_rows()
    fig, axes = plt.subplots(2, 2, figsize=(14, 8.4))
    x = np.arange(5)
    for i, (lab, _, col) in enumerate(V4_DIRS):
        r = data[lab]
        adv = [ci(r[c]["A+B vs C /round"]) for c in V4_CONDITIONS]
        cs = [ci(r[c]["CS_AB"]) for c in V4_CONDITIONS]
        off = (i - 1) * 0.22
        for ax, vals in ((axes[0, 0], adv), (axes[0, 1], cs)):
            ax.errorbar(x + off, [v[0] for v in vals], yerr=[[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]],
                        fmt="o", color=col, capsize=3, label=lab)
        axes[1, 0].bar(x + off, [pct(r[c]["same move"]) for c in V4_CONDITIONS], 0.22, color=col, label=lab)
        c_share = []
        for c in V4_CONDITIONS:
            a, b, cc = [float(v) for v in r[c]["final A / B / C"].split("/")]
            c_share.append(cc / (a + b + cc) * 100)
        axes[1, 1].bar(x + off, c_share, 0.22, color=col, label=lab)
    for ax in axes[0]:
        ax.axhline(0, color="k", lw=0.8)
    axes[1, 1].axhline(100 / 3, color="k", lw=0.8, ls="--")
    axes[1, 1].text(4.45, 34.5, "fair share", fontsize=7, ha="right")
    style(axes[0, 0], "Pair advantage (A+B)/2 − C, points/round, 95% CI")
    style(axes[0, 1], "CS_AB (coordination gain vs shuffled moves), 95% CI")
    style(axes[1, 0], "Rounds where A and B play the same move, %")
    style(axes[1, 1], "Outsider C's share of all points, %")
    for ax in axes.flat:
        ax.set_xticks(x, V4_LABELS, fontsize=8)
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("Step 4 — v4 full campaigns (20 games × 60 rounds per cell): naive coordination backfires; "
                 "only Qwen executes the supplied strategy", x=0.01, ha="left")
    save(fig, "step4_v4_full_results")


# Synthesis: the same-move trap across all steps ------------------------------------
def synthesis():
    data = v4_rows()
    text = (RES / "analyse_14B_pot_runs.md").read_text()
    sec = re.split(r"^### \d+\. ", text, flags=re.M)[1]
    runs14 = [l for l in sec.splitlines() if re.match(r"\|\s*\d+\s*\|", l)]
    same14 = np.mean([pct(l.split("|")[7]) for l in runs14])
    sc14 = np.array([[float(c) for c in l.split("|")[2:5]] for l in runs14]).mean(axis=0)
    adv14 = ((sc14[0] + sc14[1]) / 2 - sc14[2]) / 100
    plan7 = {r["condition"]: r for r in csv.DictReader(next((RES / "llm_rps_plan").glob("*_pilot/summary.csv")).open())}
    steps = [("Step 1\nQwen-7B\nchannel", ci(plan7["channel"]["same_move_pct"])[0], ci(plan7["channel"]["pair_advantage_per_round"])[0]),
             ("Step 2\nQwen-14B\nchannel", same14, adv14)]
    sm = (RES / "llm_rps_v2" / "smoke" / "REPORT.md").read_text()
    m = re.search(r"\| channel_optional \| \d+ \| ([-+\d.]+) \| [^|]+\| (\d+)%", sm)
    steps.append(("Step 3\n32B smoke\noptional", float(m.group(2)), float(m.group(1))))
    for lab, _, _ in V4_DIRS:
        r = data[lab]["channel_optional"]
        steps.append((f"Step 4\n{lab}\noptional", pct(r["same move"]), ci(r["A+B vs C /round"])[0]))
    fig, ax = plt.subplots(figsize=(11, 4.2))
    x = np.arange(len(steps))
    ax.bar(x, [s[1] for s in steps], 0.55, color=SAME, label="Same move (A = B), %")
    ax.axhline(100 / 3, color="k", ls="--", lw=0.8)
    ax.text(len(steps) - 0.5, 35, "chance (independent play)", fontsize=7, ha="right")
    ax2 = ax.twinx()
    ax2.plot([i for i, s in enumerate(steps) if s[2] is not None], [s[2] for s in steps if s[2] is not None],
             "o", color=OUTSIDER, ms=8, label="Pair advantage, points/round")
    ax2.axhline(0, color=OUTSIDER, lw=0.6, alpha=0.5)
    ax2.set_ylabel("Pair advantage", color=OUTSIDER)
    ax.set_xticks(x, [s[0] for s in steps], fontsize=8)
    ax.set_ylabel("Same move, %")
    style(ax, "The same-move trap persists across every version and model size")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    save(fig, "synthesis_same_move_trap")


if __name__ == "__main__":
    step1()
    step2()
    step3()
    step4()
    synthesis()
    print("figures written to", OUT)
