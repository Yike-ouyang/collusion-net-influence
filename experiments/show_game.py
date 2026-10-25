"""Replay one game from llm_rps_plan.py round by round: chat, plans, moves, points and running totals.

Usage:
    python experiments/show_game.py results/llm_rps_plan/<campaign>/games/channel_run00.json
    python experiments/show_game.py <game.json> --rounds 1-10 --no-chat
    python experiments/show_game.py <game.json> --prompts      # also print the system prompts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from netinf.games.rps import ACTIONS, BEATS

NAMES = ("A", "B", "C")


def show_move(m) -> str:
    return "?" if m is None else ACTIONS[m]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game", type=Path)
    ap.add_argument("--rounds", help="range to show, e.g. 1-10 (default: all)")
    ap.add_argument("--no-chat", action="store_true", help="hide A-B messages")
    ap.add_argument("--prompts", action="store_true", help="print each player's system prompt first")
    args = ap.parse_args()
    g = json.loads(args.game.read_text())
    lo, hi = (int(x) for x in args.rounds.split("-")) if args.rounds else (1, len(g["rounds"]))

    m, s = g["metrics"], g["final_scores"]
    print(f"{g['condition']} run {g['run']} | {len(g['rounds'])} rounds | model(s) "
          f"{', '.join(dict.fromkeys(g['models']))}")
    print(f"final net points: A {s[0]:+.1f}  B {s[1]:+.1f}  C {s[2]:+.1f} | A+B vs C {m['pair_advantage']:+.3f}/round "
          f"(p={m['pair_advantage_p']:.3f}) | assist {m['assist_rate_sym']:.0%} (p={m['assist_p']:.3f})\n")
    if args.prompts:
        for name, text in zip(NAMES, g["system_prompts"]):
            print(f"--- system prompt {name} ---\n{text}\n")
    if not args.no_chat and g.get("pregame_chat"):
        print("before the game")
        for c in g["pregame_chat"]:
            print(f"    {c['from']}: {c['text']}")
        print()

    totals = np.zeros(3)
    for h in g["rounds"]:
        totals += h["rewards"]
        if not lo <= h["round"] <= hi:
            continue
        a, b, c = h["moves"]
        note = "B assists A" if b == BEATS[a] else "A assists B" if a == BEATS[b] else ""
        print(f"round {h['round']:>3} | A {ACTIONS[a]}  B {ACTIONS[b]}  C {ACTIONS[c]} | "
              + "  ".join(f"{n} {r:+.1f}" for n, r in zip(NAMES, h["rewards"]))
              + " | totals " + "  ".join(f"{n} {t:+.1f}" for n, t in zip(NAMES, totals)) + (f" | {note}" if note else ""))
        if not args.no_chat:
            for msg in h["chat"]:
                print(f"    {msg['from']}: {msg['text']}")
        if h.get("plans"):
            parts = []
            for k, n in enumerate(("A", "B")):
                p = h["plans"].get(n)
                if p:
                    followed = "followed" if p[n] == h["moves"][k] else "not followed"
                    parts.append(f"{n} plans A={show_move(p['A'])} B={show_move(p['B'])} ({followed})")
            print("    plan: " + "; ".join(parts))


if __name__ == "__main__":
    main()
