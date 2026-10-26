#!/usr/bin/env python3
"""Compare A-B action dependence in no_channel and channel_optional v4 campaigns.

Uses only the Python standard library so the analysis can run without the research
environment's NumPy stack. The main statistic is plug-in I(A;B | S), with S the
previous round's joint action (and a separate start-of-game state). It also
computes a soft estimate from the logged three-move distributions at MOVE:.

Usage from the repository root:
    python coalition_metrics/04_gcg_suffix/analyze.py
    python coalition_metrics/04_gcg_suffix/analyze.py --permutations 1000 --bootstrap 2000
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CAMPAIGNS = {
    "Qwen2.5-32B": "20261025-1834_same_model_qwen32b_big-v4",
    "GLM-4-32B": "20261025-1837_same_model_glm32b_big-v4",
    "Mixtral-8x7B": "20261025-1853_same_model_mixtral8x7b_big-v4",
}
CONDITIONS = ("no_channel", "channel_optional")
MOVE_NAMES = ("Rock", "Paper", "Scissors")
START_STATE = (-1, -1, -1)


def entropy_mi(counts: Counter[tuple[int, int]]) -> float:
    n = sum(counts.values())
    if not n:
        return float("nan")
    pa = [0, 0, 0]
    pb = [0, 0, 0]
    for (a, b), count in counts.items():
        pa[a] += count
        pb[b] += count
    return sum(
        count / n * math.log2(count * n / (pa[a] * pb[b]))
        for (a, b), count in counts.items()
        if count and pa[a] and pb[b]
    )


def mutual_information(rows: list[dict]) -> float:
    return entropy_mi(Counter((row["a"], row["b"]) for row in rows))


def conditional_mi(rows: list[dict]) -> float:
    """Plug-in CMI in bits: sum_s p(s) KL[p(A,B|s) || p(A|s)p(B|s)]."""
    counts: dict[tuple[int, ...], Counter[tuple[int, int]]] = defaultdict(Counter)
    n = len(rows)
    if not n:
        return float("nan")
    for row in rows:
        counts[row["state"]][(row["a"], row["b"])] += 1
    total = 0.0
    for state_counts in counts.values():
        ns = sum(state_counts.values())
        pa = [0, 0, 0]
        pb = [0, 0, 0]
        for (a, b), count in state_counts.items():
            pa[a] += count
            pb[b] += count
        for (a, b), count in state_counts.items():
            total += count / n * math.log2(count * ns / (pa[a] * pb[b]))
    return total


def soft_conditional_mi(rows: list[dict]) -> float:
    """CMI of expected pair distributions formed from p_A x p_B at each context.

    This is a proxy based on logged MOVE: top-logprobs, not a full sequence-policy
    distribution. Rows without both move distributions are excluded.
    """
    valid = [r for r in rows if r["p_a"] is not None and r["p_b"] is not None]
    n = len(valid)
    if not n:
        return float("nan")
    by_state: dict[tuple[int, ...], list[dict]] = defaultdict(list)
    for row in valid:
        by_state[row["state"]].append(row)
    total = 0.0
    for group in by_state.values():
        joint = [[0.0] * 3 for _ in range(3)]
        for row in group:
            for a in range(3):
                for b in range(3):
                    joint[a][b] += row["p_a"][a] * row["p_b"][b]
        ns = float(len(group))
        joint = [[v / ns for v in line] for line in joint]
        pa = [sum(joint[a]) for a in range(3)]
        pb = [sum(joint[a][b] for a in range(3)) for b in range(3)]
        cmi_s = 0.0
        for a in range(3):
            for b in range(3):
                p = joint[a][b]
                if p > 0 and pa[a] > 0 and pb[b] > 0:
                    cmi_s += p * math.log2(p / (pa[a] * pb[b]))
        total += ns / n * cmi_s
    return total


def pooled_soft_mi(rows: list[dict]) -> tuple[float, int]:
    """MI of the pooled expected pair law, for the 8-10 round pilot only.

    Each row contributes p_A x p_B; averaging these pair laws retains the
    contexts' probability mixtures. This is a short-window diagnostic, not
    Bonjour's state-conditioned behavioural estimator.
    """
    valid = [r for r in rows if r["p_a"] is not None and r["p_b"] is not None]
    if not valid:
        return float("nan"), 0
    joint = [[0.0] * 3 for _ in range(3)]
    for row in valid:
        for a in range(3):
            for b in range(3):
                joint[a][b] += row["p_a"][a] * row["p_b"][b] / len(valid)
    pa = [sum(joint[a]) for a in range(3)]
    pb = [sum(joint[a][b] for a in range(3)) for b in range(3)]
    mi = sum(
        p * math.log2(p / (pa[a] * pb[b]))
        for a, line in enumerate(joint)
        for b, p in enumerate(line)
        if p > 0 and pa[a] > 0 and pb[b] > 0
    )
    return mi, len(valid)


def read_games(model: str, campaign: str, condition: str) -> dict[int, dict]:
    folder = ROOT / "results" / "llm_rps_v2" / campaign / "games"
    files = sorted(glob.glob(str(folder / f"{condition}_run*.json")))
    games: dict[int, dict] = {}
    for filename in files:
        match = re.search(r"run(\d+)\.json$", filename)
        if not match:
            continue
        run_id = int(match.group(1))
        game = json.loads(Path(filename).read_text())
        rounds = game["rounds"]
        rows: list[dict] = []
        previous = START_STATE
        available = 0
        total_mass = 0.0
        mass_n = 0
        for round_record in rounds:
            actions = round_record["moves"]
            distributions = round_record.get("move_dist") or {}
            parsed = {}
            for seat in ("A", "B"):
                item = distributions.get(seat)
                if item and all(name in item for name in MOVE_NAMES):
                    values = [max(0.0, float(item[name])) for name in MOVE_NAMES]
                    norm = sum(values)
                    if norm > 0:
                        parsed[seat] = [x / norm for x in values]
                        available += 1
                        if item.get("mass") is not None:
                            total_mass += float(item["mass"])
                            mass_n += 1
                        continue
                parsed[seat] = None
            rows.append({
                "round": int(round_record.get("round", len(rows) + 1)),
                "state": previous,
                "a": int(actions[0]),
                "b": int(actions[1]),
                "p_a": parsed["A"],
                "p_b": parsed["B"],
            })
            previous = tuple(int(x) for x in actions)
        games[run_id] = {
            "rows": rows,
            "coverage": available / max(1, 2 * len(rows)),
            "mean_mass": total_mass / mass_n if mass_n else float("nan"),
        }
    return games


def flatten(games: dict[int, dict], run_ids: list[int] | None = None) -> list[dict]:
    ids = sorted(games) if run_ids is None else run_ids
    return [row for run_id in ids for row in games[run_id]["rows"]]


def permute_b_within_state(rows: list[dict], rng: random.Random) -> list[dict]:
    grouped: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        grouped[row["state"]].append(i)
    b_values = [row["b"] for row in rows]
    for indices in grouped.values():
        values = [b_values[i] for i in indices]
        rng.shuffle(values)
        for i, value in zip(indices, values):
            b_values[i] = value
    return [dict(row, b=b_values[i]) for i, row in enumerate(rows)]


def permutation_result(rows: list[dict], n_perm: int, rng: random.Random) -> tuple[float, float, float]:
    observed = conditional_mi(rows)
    null = [conditional_mi(permute_b_within_state(rows, rng)) for _ in range(n_perm)]
    null.sort()
    p_value = (1 + sum(x >= observed for x in null)) / (n_perm + 1)
    q95 = null[min(len(null) - 1, int(0.95 * len(null)))] if null else float("nan")
    return sum(null) / len(null), q95, p_value


def bootstrap_delta(
    games_no: dict[int, dict], games_optional: dict[int, dict], n_boot: int, rng: random.Random
) -> tuple[float, float]:
    common = sorted(set(games_no) & set(games_optional))
    if not common:
        return float("nan"), float("nan")
    deltas = []
    for _ in range(n_boot):
        sample = [rng.choice(common) for _ in common]
        no_rows = flatten(games_no, sample)
        optional_rows = flatten(games_optional, sample)
        deltas.append(conditional_mi(optional_rows) - conditional_mi(no_rows))
    deltas.sort()
    return deltas[int(0.025 * n_boot)], deltas[min(n_boot - 1, int(0.975 * n_boot))]


def select_round_window(games: dict[int, dict], first: int = 8, last: int = 10) -> dict[int, dict]:
    """Keep rounds numbered 8-10 (inclusive), preserving complete run groups."""
    return {
        run: {**game, "rows": [r for r in game["rows"] if first <= r["round"] <= last]}
        for run, game in games.items()
    }


def bootstrap_window_delta(
    no_games: dict[int, dict], optional_games: dict[int, dict], n_boot: int, rng: random.Random
) -> tuple[float, float]:
    common = sorted(set(no_games) & set(optional_games))
    if not common:
        return float("nan"), float("nan")
    deltas = []
    for _ in range(n_boot):
        sample = [rng.choice(common) for _ in common]
        no_mi, _ = pooled_soft_mi(flatten(no_games, sample))
        opt_mi, _ = pooled_soft_mi(flatten(optional_games, sample))
        deltas.append(opt_mi - no_mi)
    deltas.sort()
    return deltas[int(0.025 * n_boot)], deltas[min(n_boot - 1, int(0.975 * n_boot))]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--permutations", type=int, default=500)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261026)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    summary_rows = []
    game_rows = []
    delta_rows = []
    window_rows = []
    all_data: dict[tuple[str, str], dict[int, dict]] = {}

    for model, campaign in CAMPAIGNS.items():
        for condition in CONDITIONS:
            games = read_games(model, campaign, condition)
            all_data[(model, condition)] = games
            rows = flatten(games)
            null_mean, null_q95, p_value = permutation_result(rows, args.permutations, rng)
            summary_rows.append({
                "model": model,
                "campaign": campaign,
                "condition": condition,
                "games": len(games),
                "rounds": len(rows),
                "MI_AB_unconditional_bits": f"{mutual_information(rows):.6f}",
                "I_AB_given_prev_joint_action_bits": f"{conditional_mi(rows):.6f}",
                "permutation_null_mean_bits": f"{null_mean:.6f}",
                "permutation_null_q95_bits": f"{null_q95:.6f}",
                "permutation_p": f"{p_value:.6f}",
                "soft_I_AB_given_prev_bits": f"{soft_conditional_mi(rows):.6f}",
                "move_probability_coverage_AB": f"{sum(g['coverage'] for g in games.values()) / max(1, len(games)):.6f}",
                "mean_logged_probability_mass": f"{sum(g['mean_mass'] for g in games.values()) / max(1, len(games)):.6f}",
            })
            for run_id, game in sorted(games.items()):
                game_rows.append({
                    "model": model,
                    "condition": condition,
                    "run": run_id,
                    "rounds": len(game["rows"]),
                    "MI_AB_unconditional_bits": f"{mutual_information(game['rows']):.6f}",
                    "I_AB_given_prev_joint_action_bits": f"{conditional_mi(game['rows']):.6f}",
                    "soft_I_AB_given_prev_bits": f"{soft_conditional_mi(game['rows']):.6f}",
                    "move_probability_coverage_AB": f"{game['coverage']:.6f}",
                    "mean_logged_probability_mass": f"{game['mean_mass']:.6f}",
                })

        no_data = all_data[(model, "no_channel")]
        optional_data = all_data[(model, "channel_optional")]
        no_rows, optional_rows = flatten(no_data), flatten(optional_data)
        lo, hi = bootstrap_delta(no_data, optional_data, args.bootstrap, rng)
        delta_rows.append({
            "model": model,
            "games_paired": len(set(no_data) & set(optional_data)),
            "delta_I_AB_given_prev_bits_optional_minus_no": f"{conditional_mi(optional_rows) - conditional_mi(no_rows):.6f}",
            "paired_game_bootstrap_95_lo": f"{lo:.6f}",
            "paired_game_bootstrap_95_hi": f"{hi:.6f}",
            "delta_soft_I_optional_minus_no": f"{soft_conditional_mi(optional_rows) - soft_conditional_mi(no_rows):.6f}",
        })

        no_window = select_round_window(no_data)
        optional_window = select_round_window(optional_data)
        no_window_rows = flatten(no_window)
        optional_window_rows = flatten(optional_window)
        no_window_mi, no_n = pooled_soft_mi(no_window_rows)
        optional_window_mi, optional_n = pooled_soft_mi(optional_window_rows)
        window_lo, window_hi = bootstrap_window_delta(
            no_window, optional_window, args.bootstrap, rng
        )
        window_rows.append({
            "model": model,
            "rounds_inclusive": "8-10",
            "games_no_channel": len(no_window),
            "games_channel_optional": len(optional_window),
            "valid_contexts_no_channel": no_n,
            "valid_contexts_channel_optional": optional_n,
            "pooled_soft_MI_no_channel_bits": f"{no_window_mi:.6f}",
            "pooled_soft_MI_channel_optional_bits": f"{optional_window_mi:.6f}",
            "delta_optional_minus_no_bits": f"{optional_window_mi - no_window_mi:.6f}",
            "paired_run_bootstrap_95_lo": f"{window_lo:.6f}",
            "paired_run_bootstrap_95_hi": f"{window_hi:.6f}",
            "interpretation": "exploratory pooled probability-law diagnostic; not state-conditioned CMI",
        })

    write_csv(OUT / "condition_summary.csv", summary_rows, list(summary_rows[0]))
    write_csv(OUT / "game_metrics.csv", game_rows, list(game_rows[0]))
    write_csv(OUT / "paired_differences.csv", delta_rows, list(delta_rows[0]))
    write_csv(OUT / "fast_window_summary.csv", window_rows, list(window_rows[0]))
    print(f"Wrote analysis CSVs to {OUT}")


if __name__ == "__main__":
    main()
