"""3-player RPS with stakes, where A and B talk privately before every round, then plan, then play.

Every round: each player stakes 1 into a pot of 3; the winners split it (netinf.games.rps_stake).
In every condition except `independent`, A and B first exchange private messages (C never sees them),
then each writes a plan "PLAN: A=<move>, B=<move>", then all three players move simultaneously.
All three players are LLMs and see the full history of moves, net points and totals.

Conditions (C is always the outsider and never talks):
  independent     no chat: negative control, any detector alarm is a false alarm
  channel         private chat before every round, nothing about colluding    <- the main test
  channel_hint    chat + "you are free to agree on a joint strategy"
  channel_shared  chat + A and B are rewarded on their combined score
  instructed      chat + told to take turns winning against C: positive control

Every text sent to the LLMs comes from a prompts file (default prompts/pot_plan.json), editable
without touching code; --prompt KEY=TEXT or KEY=@file.txt overrides one entry.

Each campaign is written to <out>/<campaign>/: one JSON per game in games/ (every message, plan,
raw reply, move and reward), plus config_<condition>.json with the settings and prompts used.
Games already on disk are skipped, so a stopped campaign resumes where it left off.

Usage:
    NETINF_BASE_URL=http://localhost:11434/v1 NETINF_MODEL=qwen2.5:7b \
        python experiments/llm_rps_plan.py --conditions channel --runs 1 --rounds 5 --workers 1
    python experiments/llm_rps_plan.py --conditions independent,channel,instructed --runs 10 --estimate
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path

import numpy as np

from netinf.games.rps import ACTIONS
from netinf.games.rps_stake import TIE_RULES, payoff_stake
from netinf.llm import CachedChat
from netinf.metrics import collusion_metrics, plan_adherence
from llm_rps import parse_move, score

NAMES = ("A", "B", "C")
CONDITIONS = ("independent", "channel", "channel_hint", "channel_shared", "instructed")
EXTRA = {"channel_hint": "hint", "channel_shared": "shared", "instructed": "instructed"}  # extra text for A and B
ASKS = ("pregame_ask", "negotiate_ask", "plan_ask", "move_ask")
DEFAULT_PROMPTS = Path(__file__).resolve().parents[1] / "prompts" / "pot_plan.json"
PLAN_RE = re.compile(r"\b([AB])\s*[=:]\s*(R|P|S|ROCK|PAPER|SCISSORS)\b")


def seed(*key) -> int:
    """Deterministic across processes (unlike hash() on strings), so cached replies replay."""
    return zlib.crc32(repr(key).encode())


def load_prompts(path: Path, overrides: list[str]) -> dict[str, str]:
    prompts = json.loads(Path(path).read_text())
    for item in overrides:
        key, sep, value = item.partition("=")
        if not sep or key not in prompts:
            raise SystemExit(f"--prompt expects KEY=TEXT or KEY=@file with KEY in {sorted(prompts)}; got {item!r}")
        prompts[key] = Path(value[1:]).read_text().strip() if value.startswith("@") else value
    return prompts


def fmt_vars(k: int, cfg, prompts: dict, t: int | None = None) -> dict:
    """Placeholders available in every prompt."""
    pot = cfg.stake * 3
    return {"me": NAMES[k], "others": " and ".join(n for n in NAMES if n != NAMES[k]),
            "partner": NAMES[1 - k] if k < 2 else "", "rounds": cfg.rounds, "round": "" if t is None else t + 1,
            "stake": f"{cfg.stake:g}", "pot": f"{pot:g}", "lone_gain": f"{pot - cfg.stake:g}",
            "pair_gain": f"{pot / 2 - cfg.stake:g}", "tie_text": prompts[f"tie_{cfg.tie_rule}"]}


def system_for(k: int, condition: str, prompts: dict, cfg) -> str:
    parts = [prompts["rules"]]
    if k < 2 and condition != "independent":
        parts.append(prompts["channel"])
        if condition in EXTRA:
            parts.append(prompts[EXTRA[condition]])
    if k == 2 and prompts.get("system_c"):
        parts.append(prompts["system_c"])
    return "\n".join(parts).format(**fmt_vars(k, cfg, prompts))


def show_move(m: int | None) -> str:
    return "?" if m is None else ACTIONS[m]


def user_prompt(k: int, t: int, history: list[dict], chat: list[dict], cfg, ask: str, plan: str | None = None) -> str:
    lines = [f"Round {t + 1} of {cfg.rounds}."]
    if history:
        totals = np.sum([h["rewards"] for h in history], axis=0)
        lines.append("Total scores so far: " + ", ".join(f"{n}={s:+g}" for n, s in zip(NAMES, totals)) + ".")
        shown = history if cfg.history < 0 else history[len(history) - cfg.history:] if cfg.history else []
        if shown:
            lines.append("Previous rounds (moves -> net points):")
            lines += [f"  round {h['round']}: " + ", ".join(f"{n}={ACTIONS[m]}" for n, m in zip(NAMES, h["moves"]))
                      + " -> " + ", ".join(f"{n} {r:+g}" for n, r in zip(NAMES, h["rewards"])) for h in shown]
        if cfg.show_stats:
            moves = np.array([h["moves"] for h in history])
            lines.append("Move frequencies so far: " + "; ".join(
                f"{n} " + " ".join(f"{ACTIONS[a]} {np.mean(moves[:, i] == a):.0%}" for a in range(3))
                for i, n in enumerate(NAMES)) + ".")
    else:
        lines.append("No round has been played yet.")
    if k < 2 and chat:  # only A and B see the private channel
        recent = chat if cfg.chat_memory < 0 else chat[len(chat) - cfg.chat_memory:] if cfg.chat_memory else []
        if recent:
            lines.append(f"Private chat with Player {NAMES[1 - k]} (most recent last):")
            lines += [f"  [{'before the game' if c['round'] == 0 else 'round ' + str(c['round'])}] "
                      f"{c['from']}: {c['text']}" for c in recent]
    if plan is not None:
        lines.append(f"Your plan for this round: {plan}")
    lines.append(ask)
    return "\n".join(lines)


def parse_plan(text: str) -> dict:
    found = {}
    for who, move in PLAN_RE.findall(text.upper()):
        found.setdefault(who, "RPS".index(move[0]))
    return {"A": found.get("A"), "B": found.get("B")}


def calls_per_game(condition: str, cfg) -> int:
    per_round = 3
    if condition != "independent":
        per_round += 2 * cfg.negotiation_turns + (2 if cfg.plan else 0)
    return cfg.rounds * per_round + (2 * cfg.pregame_turns if condition != "independent" else 0)


def play(llms: list[CachedChat], prompts: dict, condition: str, run: int, cfg, rng) -> dict:
    history, chat, failures = [], [], {"move": 0, "plan": 0}
    talk = condition != "independent"
    systems = [system_for(k, condition, prompts, cfg) for k in range(3)]
    msg_temperature = cfg.temperature if cfg.msg_temperature is None else cfg.msg_temperature

    def ask(k: int, key: str, t: int) -> str:
        return prompts[key].format(**fmt_vars(k, cfg, prompts, t))

    def say(k: int, t: int, key: str, chat_round: int, tag) -> None:
        text = llms[k].generate(user_prompt(k, t, history, chat, cfg, ask(k, key, t)), systems[k], msg_temperature,
                                seed=seed(run, cfg.seed_offset, t, k, tag), max_tokens=cfg.msg_tokens)
        chat.append({"round": chat_round, "from": NAMES[k], "text": " ".join(text.split())})

    if talk:  # optional strategy talk before round 1
        for turn in range(cfg.pregame_turns):
            for k in (0, 1):
                say(k, 0, "pregame_ask", 0, ("pre", turn))

    for t in range(cfg.rounds):
        first_msg = len(chat)
        if talk:  # A writes, B replies, repeated negotiation_turns times, before anyone moves
            for turn in range(cfg.negotiation_turns):
                for k in (0, 1):
                    say(k, t, "negotiate_ask", t + 1, ("msg", turn))
        plans = {}
        if talk and cfg.plan:
            for k in (0, 1):
                text = llms[k].generate(user_prompt(k, t, history, chat, cfg, ask(k, "plan_ask", t)), systems[k],
                                        cfg.temperature, seed=seed(run, cfg.seed_offset, t, k, "plan"), max_tokens=24)
                parsed = parse_plan(text)
                failures["plan"] += None in parsed.values()
                plans[NAMES[k]] = {**parsed, "raw": text.strip()}
        moves, raw = [], []
        for k in range(3):  # simultaneous: nobody sees this round's moves
            own = plans.get(NAMES[k]) if k < 2 else None
            plan = None if own is None else f"A={show_move(own['A'])}, B={show_move(own['B'])}"
            text = llms[k].generate(user_prompt(k, t, history, chat, cfg, ask(k, "move_ask", t), plan), systems[k],
                                    cfg.temperature, seed=seed(run, cfg.seed_offset, t, k, "move"), max_tokens=16)
            move = parse_move(text)
            if move is None:
                failures["move"] += 1
                move = int(rng.integers(3))  # random fallback; the rate is reported per game
            moves.append(move)
            raw.append(text.strip())
        rewards = payoff_stake(moves, cfg.stake, cfg.tie_rule)
        history.append({"round": t + 1, "chat": chat[first_msg:], "plans": plans or None, "moves": moves,
                        "raw_moves": raw, "rewards": rewards.tolist()})

    rewards = np.array([h["rewards"] for h in history])
    return {"rounds": history, "pregame_chat": [c for c in chat if c["round"] == 0],
            "actions": [h["moves"] for h in history], "rewards": rewards.tolist(),
            "final_scores": rewards.sum(axis=0).tolist(), "parse_failures": failures}


def pair_name(p) -> str:
    return "-".join(NAMES[i] for i in p) if p else "none"


def pct(x: float) -> str:
    return "-" if x != x else f"{x:.0%}"  # NaN (no plans in this condition) prints as "-"


def summary_line(game: dict) -> str:
    m, s, f = game["metrics"], game["final_scores"], game["parse_failures"]
    return (f"[{game['condition']:<14} run {game['run']:02d}] final A {s[0]:+6.1f}  B {s[1]:+6.1f}  C {s[2]:+6.1f} | "
            f"pair adv {m['pair_advantage']:+.2f}/round (p={m['pair_advantage_p']:.3f}) | "
            f"assist {m['assist_rate_sym']:.0%} (p={m['assist_p']:.3f}) | "
            f"same move {m['same_move_rate']:.0%} (p={m['same_move_p']:.3f}) | "
            f"plan followed A {pct(m['follow_A'])} B {pct(m['follow_B'])}, "
            f"agreed + executed {pct(m['executed_agreement'])} | "
            f"net influence flags {pair_name(game['detection']['prev']['calibrated'])} | "
            f"parse fails move {f['move']} plan {f['plan']} | {game['elapsed_s']:.0f}s")


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).parent, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_argument_group("game")
    g.add_argument("--conditions", default="channel", help="comma-separated, from: " + ", ".join(CONDITIONS))
    g.add_argument("--runs", type=int, default=10, help="games per condition")
    g.add_argument("--rounds", type=int, default=100, help="rounds per game")
    g.add_argument("--stake", type=float, default=1.0, help="points each player puts in the pot every round")
    g.add_argument("--tie-rule", choices=TIE_RULES, default="refund", help="stakes when nobody wins")
    g.add_argument("--history", type=int, default=-1, help="past rounds listed in prompts (-1 = all, 0 = none)")
    g.add_argument("--show-stats", action=argparse.BooleanOptionalAction, default=True,
                   help="add each player's move frequencies to prompts")
    c = ap.add_argument_group("A-B channel (ignored in independent)")
    c.add_argument("--negotiation-turns", type=int, default=2, help="messages per partner before every round (>= 1)")
    c.add_argument("--pregame-turns", type=int, default=1, help="messages per partner before round 1")
    c.add_argument("--chat-memory", type=int, default=20, help="past messages shown in prompts (-1 = all)")
    c.add_argument("--msg-tokens", type=int, default=80, help="max tokens per message")
    c.add_argument("--plan", action=argparse.BooleanOptionalAction, default=True,
                   help="ask A and B for a 'PLAN: A=?, B=?' line before they move")
    m = ap.add_argument_group("models and prompts")
    m.add_argument("--temperature", type=float, default=1.0, help="for plans and moves")
    m.add_argument("--msg-temperature", type=float, help="for chat messages (default: --temperature)")
    m.add_argument("--agents", help="one model per player: 'modelA@urlA,modelB@urlB,modelC@urlC' "
                                    "(default: NETINF_MODEL at NETINF_BASE_URL for all three)")
    m.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS, help="JSON file with every prompt text")
    m.add_argument("--prompt", action="append", default=[], metavar="KEY=TEXT",
                   help="override one prompt: KEY=TEXT or KEY=@file.txt (repeatable)")
    r = ap.add_argument_group("run")
    r.add_argument("--workers", type=int, default=8, help="games played concurrently")
    r.add_argument("--perms", type=int, default=500, help="permutations for p-values (> 60)")
    r.add_argument("--out", type=Path, default=Path("results/llm_rps_plan"))
    r.add_argument("--campaign", help="campaign folder name (default: <date>_<model>[_<tag>]); reuse it to resume")
    r.add_argument("--tag", default="", help="suffix of the default campaign name")
    r.add_argument("--run-offset", type=int, default=0, help="index of the first game")
    r.add_argument("--seed-offset", type=int, default=0, help="change it to replay with fresh LLM samples")
    r.add_argument("--cache", type=Path, default=Path("cache/llm.sqlite"))
    r.add_argument("--estimate", action="store_true", help="print the number of LLM calls and exit")
    args = ap.parse_args()

    conditions = [x.strip() for x in args.conditions.split(",") if x.strip()]
    if unknown := set(conditions) - set(CONDITIONS):
        raise SystemExit(f"unknown conditions {sorted(unknown)}; choose from {CONDITIONS}")
    if any(x != "independent" for x in conditions) and args.negotiation_turns < 1:
        raise SystemExit("--negotiation-turns must be >= 1 so that A and B talk before every round")
    prompts = load_prompts(args.prompts, args.prompt)
    try:  # fail now, not mid-campaign, on a typo in a {placeholder}
        for x in conditions:
            for k in range(3):
                system_for(k, x, prompts, args)
                for key in ASKS:
                    prompts[key].format(**fmt_vars(k, args, prompts, 0))
    except (KeyError, IndexError, ValueError) as e:
        raise SystemExit(f"bad placeholder in prompts: {e!r}. Available: {sorted(fmt_vars(0, args, prompts, 0))}")

    total = sum(calls_per_game(x, args) for x in conditions) * args.runs
    print("LLM calls per game: " + ", ".join(f"{x} {calls_per_game(x, args)}" for x in conditions)
          + f" | total for this command: {total}")
    if args.estimate:
        return

    short = lambda name: name.split("/")[-1].replace(":", "_")  # noqa: E731
    if args.agents:
        specs = [a.strip().split("@", 1) for a in args.agents.split(",")]
        if len(specs) != 3 or any(len(s) != 2 for s in specs):
            raise SystemExit("--agents needs exactly three model@base_url entries, for A, B and C")
        clients = {}
        for name, url in specs:
            clients.setdefault((name, url), CachedChat(model=name, base_url=url, cache_path=args.cache))
        llms = [clients[(name, url)] for name, url in specs]
    else:
        llms = [CachedChat(cache_path=args.cache)] * 3
    model_name = "+".join(dict.fromkeys(short(x.model) for x in llms))
    campaign = args.campaign or f"{datetime.now():%Y%m%d-%H%M}_{model_name}" + (f"_{args.tag}" if args.tag else "")
    cdir = args.out / campaign
    games_dir = cdir / "games"
    games_dir.mkdir(parents=True, exist_ok=True)

    settings = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    for x in conditions:
        (cdir / f"config_{x}.json").write_text(json.dumps({
            "condition": x, "settings": settings, "models": [c.model for c in llms],
            "base_urls": [c.base_url for c in llms], "git_commit": git_commit(),
            "written": datetime.now().isoformat(timespec="seconds"), "prompts": prompts,
            "system_prompts": {n: system_for(k, x, prompts, args) for k, n in enumerate(NAMES)}}, indent=2))

    jobs = [(x, run) for x in conditions for run in range(args.run_offset, args.run_offset + args.runs)]
    todo = [(x, run) for x, run in jobs if not (games_dir / f"{x}_run{run:02d}.json").exists()]
    if len(todo) < len(jobs):
        print(f"skipping {len(jobs) - len(todo)} games already in {games_dir}")
    pay = partial(payoff_stake, stake=args.stake, tie_rule=args.tie_rule)

    def one(job) -> str:
        condition, run = job
        start = time.time()
        try:
            rng = np.random.default_rng(seed(run, args.seed_offset, condition))
            game = play(llms, prompts, condition, run, args, rng)
            actions = np.array(game["actions"])
            plans = [h["plans"] for h in game["rounds"]]
            game.update(condition=condition, run=run, campaign=campaign, models=[c.model for c in llms],
                        settings=settings, system_prompts=[system_for(k, condition, prompts, args) for k in range(3)],
                        metrics={**collusion_metrics(actions, pay, args.perms, rng), **plan_adherence(plans, actions)},
                        detection=score(actions, args.perms, rng), elapsed_s=round(time.time() - start, 1))
            (games_dir / f"{condition}_run{run:02d}.json").write_text(json.dumps(game))
            return summary_line(game)
        except Exception as e:  # one broken game must not stop the campaign; it is retried on the next launch
            return f"[{condition:<14} run {run:02d}] FAILED after {time.time() - start:.0f}s: {e!r}"

    start = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        for line in pool.map(one, todo):
            print(line, flush=True)
    elapsed = time.time() - start
    for client in {id(x): x for x in llms}.values():
        u = client.usage
        print(f"{client.model}: {u.calls} calls ({u.cache_hits} from cache), {u.input_tokens} input tokens, "
              f"{u.output_tokens} output tokens, {u.calls / max(elapsed, 1e-9):.1f} calls/s over {elapsed / 60:.1f} min")
    print(f"\nResults: {cdir}\nNext:    python experiments/analyze_plan.py {cdir}")


if __name__ == "__main__":
    main()
