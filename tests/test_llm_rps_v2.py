"""Engine tests with a scripted fake LLM: no network, no model."""

import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import llm_rps_v2 as v2  # noqa: E402


class FakeLLM:
    """Answers by request type; B always skips the chat in optional conditions."""

    def __init__(self):
        self.calls = []

    def generate(self, prompt, system="", temperature=1.0, seed=0, max_tokens=512):
        me = re.search(r"You are Player ([ABC])", system).group(1)
        self.calls.append((me, prompt, max_tokens))
        if "Write one message" in prompt:
            return "SKIP" if me == "B" and "SKIP" in prompt else f"{me}: let's both play Rock."
        if "PLAN: A=<" in prompt:
            return "PLAN: A=Rock, B=Rock"
        if "Choose your move" in prompt:
            return "Thinking...\nMOVE: " + {"A": "Rock", "B": "Rock", "C": "Paper"}[me]
        if "INTENDED_MOVE:" in prompt:
            return ("LAST_ROUND: I scored 0 points.\nSTANDING: level\nWORKING: no\nOTHERS: A: Rock, B: Rock, C: Paper\n"
                    "INTENDED_MOVE: Rock")
        if "MOVE: <" in prompt:
            return "Thinking...\nMOVE: " + {"A": "Rock", "B": "Rock", "C": "Paper"}[me]
        if "The game is over" in prompt:
            return "STRATEGY: I played Rock.\nOUTCOME: Player C benefited.\nSUSPICION: Yes.\nCONFIDENCE: high"
        raise AssertionError(f"unexpected request: {prompt[:80]}")


def cfg(**kw):
    args = v2.parser().parse_args(["--rounds", "4", "--perms", "70"])
    for k, v in kw.items():
        setattr(args, k, v)
    return args


@pytest.mark.parametrize("condition", list(v2.CONDITIONS))
def test_play_every_condition(condition):
    llm, c = FakeLLM(), cfg()
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    game = v2.play([llm] * 3, v2.Protocol(prompts, condition, c), 0, c, np.random.default_rng(0))
    assert game["actions"] == [[0, 0, 1]] * 4  # A, B Rock; C Paper
    assert game["final_scores"] == [0, 0, 12]
    assert set(game["debriefs"]) == {"A", "B", "C"}
    assert game["rounds"][0]["outcome"].startswith("Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone")
    # the scoreboard is on top of every chat, plan, reflection and move request
    assert all(p.startswith("ROUND ") for _, p, _ in llm.calls if "The game is over" not in p)
    channel = v2.CONDITIONS[condition]["channel"]
    rounds = game["rounds"]
    if channel is None:
        assert all(r["chat"] == [] and r["plans"] is None for r in rounds)
        assert not any("Write one message" in p for _, p, _ in llm.calls)
    else:
        assert [r["first_speaker"] for r in rounds] == ["A", "B", "A", "B"]
        assert all(t == c.msg_tokens for who, p, t in llm.calls if "Write one message" in p)
    if channel == "optional":
        # B skips; in rounds where B writes first and A then writes, the turn is not a double skip
        assert all(r["channel"]["B"]["sent"] == 0 for r in rounds)
        assert all(r["plans"] is None for r in rounds)  # plans only with --plan
    if channel == "forced":
        assert all(r["plans"]["A"]["A"] == 0 for r in rounds)
        assert game["failures"].get("forced_skip", 0) == 0
    m = v2.game_metrics(game, 70, np.random.default_rng(1))
    assert m["pair_advantage"] == pytest.approx(-3.0)
    assert m["same_move_rate"] == 1.0


def test_double_skip_ends_the_chat():
    class Silent(FakeLLM):
        def generate(self, prompt, system="", temperature=1.0, seed=0, max_tokens=512):
            if "Write one message" in prompt:
                self.calls.append(("?", prompt, max_tokens))
                return "SKIP"
            return super().generate(prompt, system, temperature, seed, max_tokens)

    llm, c = Silent(), cfg()
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    game = v2.play([llm] * 3, v2.Protocol(prompts, "channel_optional", c), 0, c, np.random.default_rng(0))
    # 2 negotiation turns, but both skip in turn 1: only 2 message requests per round
    assert sum("Write one message" in p for _, p, _ in llm.calls) == 2 * 4
    assert game["rounds"][0]["channel"] == {"A": {"asked": 1, "sent": 0, "skipped": 1},
                                            "B": {"asked": 1, "sent": 0, "skipped": 1}}


def test_uniform_c_makes_no_call_for_c():
    llm, c = FakeLLM(), cfg(c_player="uniform")
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    game = v2.play([llm, llm, None], v2.Protocol(prompts, "no_channel", c), 0, c, np.random.default_rng(0))
    assert not any(who == "C" for who, _, _ in llm.calls)
    assert set(game["debriefs"]) == {"A", "B"}


def test_mixed_models_rotate_over_the_six_seatings():
    c = cfg(design="mixed_models", lineup="m1@u,m2@u,m3@u")
    seatings = {tuple(s[0] for s in v2.seat_models(c, run)) for run in range(6)}
    assert len(seatings) == 6
    assert v2.seat_models(cfg(c_player="uniform", model="m", base_url="u"), 0)[2] is None


def test_prompt_checker_rejects_typos(tmp_path):
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    v2.check_prompts(prompts, cfg())  # the shipped file is clean
    prompts["move_ask"] = "{scorebord}\nMOVE: <Rock|Paper|Scissors>"
    with pytest.raises(SystemExit, match="scorebord"):
        v2.check_prompts(prompts, cfg())


def test_render_and_estimate_are_static():
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    text = v2.render_all(prompts, cfg(), list(v2.CONDITIONS))
    assert "TIP: partners can gain at C's expense" in text and "reply exactly SKIP" in text
    assert "calls / game" in v2.estimate(prompts, cfg(), list(v2.CONDITIONS))


def test_full_game_record_is_json_serialisable():
    import json
    llm, c = FakeLLM(), cfg()
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    rng = np.random.default_rng(0)
    game = v2.play([llm] * 3, v2.Protocol(prompts, "channel_forced", c), 0, c, rng)
    game["metrics"] = v2.game_metrics(game, 70, rng)
    game["detection"] = v2.score(np.array(game["actions"]), 70, rng)
    game["reflection_metrics"] = v2.reflection_metrics(game)
    game["debrief_accuracy"] = v2.debrief_accuracy(game, False)
    back = json.loads(json.dumps(game))
    assert back["reflection_metrics"]["A"]["consistency"]["rate"] == 1.0
    assert back["debrief_accuracy"]["C"]["suspicion"] is False  # C said yes, A+B did not win


def test_analyze_v2_end_to_end(tmp_path, monkeypatch, capsys):
    import json
    import matplotlib
    matplotlib.use("Agg")
    import analyze_v2
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    camp = tmp_path / "camp"
    (camp / "games").mkdir(parents=True)
    for cond in ("no_channel", "channel_forced"):
        for run in range(2):
            c, rng = cfg(), np.random.default_rng(run)
            game = v2.play([FakeLLM()] * 3, v2.Protocol(prompts, cond, c), run, c, rng)
            game.update(condition=cond, run=run, campaign="camp", design="same_model",
                        seats={"A": "fake", "B": "fake", "C": "fake"})
            game["metrics"] = v2.game_metrics(game, 70, rng)
            game["detection"] = v2.score(np.array(game["actions"]), 70, rng)
            game["reflection_metrics"] = v2.reflection_metrics(game)
            game["debrief_accuracy"] = v2.debrief_accuracy(game, False)
            (camp / "games" / f"{cond}_run{run:02d}.json").write_text(json.dumps(game))
    monkeypatch.setattr(sys, "argv", ["analyze_v2.py", str(camp)])
    analyze_v2.main()
    printed = capsys.readouterr().out
    assert "COALITION, PLANS AND DETECTION" in printed and "channel_forced" in printed
    for name in ("report.md", "summary.csv", "games.csv", "by_model.csv", "coalition_by_condition.png"):
        assert (camp / name).exists()
    assert (tmp_path / "history.csv").read_text().count("same_model") == 2


def test_chat_variant_shows_the_chat_to_a_and_b_only():
    chat_file = v2.DEFAULT_PROMPTS.with_name("pot_plan_v2_chat.json")
    for path, expect in ((v2.DEFAULT_PROMPTS, False), (chat_file, True)):
        llm, c = FakeLLM(), cfg()
        prompts = v2.load_prompts(path, [])
        v2.check_prompts(prompts, c)
        v2.play([llm] * 3, v2.Protocol(prompts, "channel_optional", c), 0, c, np.random.default_rng(0))
        moves = [(who, p) for who, p, _ in llm.calls if "Choose your move" in p]
        assert all(("A: let's both play Rock." in p) == expect for who, p in moves if who in "AB")  # label added by chat_block
        assert not any("Private chat" in p for who, p in moves if who == "C")
    llm, c = FakeLLM(), cfg()
    v2.play([llm] * 3, v2.Protocol(v2.load_prompts(chat_file, []), "no_channel", c), 0, c, np.random.default_rng(0))
    assert not any("Private chat" in p for _, p, _ in llm.calls)


class FullFake(FakeLLM):
    """Exposes generate_full: messages hit max_tokens, moves carry logprobs."""

    def generate_full(self, prompt, system="", temperature=1.0, seed=0, max_tokens=512, top_logprobs=0):
        text = self.generate(prompt, system, temperature, seed, max_tokens)
        tokens = []
        if top_logprobs and "MOVE:" in text:
            head, _, move = text.rpartition("MOVE:")
            tokens = [{"token": head + "MOVE:", "top": []},
                      {"token": " " + move.strip(), "top": [[move.strip(), -0.2], ["Scissors", -2.0]]}]
        return {"text": text, "finish_reason": "length" if "Write one message" in prompt else "stop",
                "tokens": tokens, "prompt_tokens": len(prompt) // 4, "completion_tokens": 5}


def test_truncations_logprobs_and_prompt_lengths_are_logged():
    llm, c = FullFake(), cfg()
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    game = v2.play([llm] * 3, v2.Protocol(prompts, "channel_forced", c), 0, c, np.random.default_rng(0))
    assert game["failures"]["truncated_msg"] == 4 * 2 * 2  # 4 rounds x 2 turns x 2 partners
    assert "truncated_move" not in game["failures"]
    d = game["rounds"][0]["move_dist"]["C"]
    assert d["Paper"] > 0.8 and d["Scissors"] > 0
    assert game["rounds"][0]["reflections"]["A"]["intended_dist"]["Rock"] > 0.8  # read at INTENDED_MOVE:
    assert set(game["max_prompt_tokens"]) >= {"msg", "plan", "reflection", "move", "debrief"}
    assert game["temperature"] == 1.0


def test_parse_spec_with_revision():
    assert v2.parse_spec("Qwen/Q@https://x/v1#abc") == ("Qwen/Q", "https://x/v1", "abc")
    assert v2.parse_spec("m@u") == ("m", "u", "")
    with pytest.raises(SystemExit):
        v2.parse_spec("no-url")


def test_chat_variant_only_adds_the_chat_to_ab_reflection_and_move():
    """D1: pot_plan_v2_chat.json = spec prompts + the private-chat block, nothing else, nobody else."""
    spec = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    chat = v2.load_prompts(v2.DEFAULT_PROMPTS.with_name("pot_plan_v2_chat.json"), [])
    assert {k for k in spec if spec[k] != chat[k]} == {"_about", "reflection_ask", "move_ask"}
    for key in ("reflection_ask", "move_ask"):
        assert chat[key].replace("{chat_section}\n", "", 1) == spec[key]
    c = cfg()
    for cond in v2.CONDITIONS:
        st = v2.sample_state(6, True)
        st["chat"] = st["all_chat"][-2:]
        a, b = v2.Protocol(spec, cond, c), v2.Protocol(chat, cond, c)
        for k in range(3):
            assert a.system(k) == b.system(k)
            for key in ("reflection_ask", "move_ask"):
                x, y = a.user(key, k, st), b.user(key, k, st)
                if k == 2 or v2.CONDITIONS[cond]["channel"] is None:
                    assert x == y
                else:
                    block = f"Private chat with Player {'AB'[1 - k]} this round:\n" + "\n".join(
                        f"{m['from']}: {m['text']}" for m in st["chat"])
                    assert y.replace(block + "\n", "", 1) == x


def test_handcheck_sample_is_blind_and_score_computes_agreement(tmp_path):
    import csv
    import json
    import handcheck_v2 as hc
    prompts = v2.load_prompts(v2.DEFAULT_PROMPTS, [])
    camp = tmp_path / "camp"
    (camp / "games").mkdir(parents=True)
    for run in range(12):
        c, rng = cfg(), np.random.default_rng(run)
        game = v2.play([FakeLLM()] * 3, v2.Protocol(prompts, "channel_forced", c), run, c, rng)
        game.update(condition="channel_forced", run=run, design="same_model", seats={n: "fake" for n in "ABC"})
        game["metrics"] = v2.game_metrics(game, 70, rng)
        game["debrief_accuracy"] = v2.debrief_accuracy(game, False)
        (camp / "games" / f"channel_forced_run{run:02d}.json").write_text(json.dumps(game))
    out = tmp_path / "hc"
    hc.main(["sample", str(camp), "--n", "10", "--seed", "0", "--out", str(out)])
    first = (out / "sheet.csv").read_text()
    hc.main(["sample", str(camp), "--n", "10", "--seed", "0", "--out", str(out)])
    assert (out / "sheet.csv").read_text() == first  # fixed seed: same games
    sheet = list(csv.DictReader(open(out / "sheet.csv")))
    assert "rule" not in sheet[0] and len({r["game"] for r in sheet}) == 10  # blind: no rule labels in the sheet
    rules = {(r["game"], r["player"], r["claim"]): r["rule"] for r in csv.DictReader(open(out / "rule_labels.csv"))}
    for r in sheet:  # a "human" who agrees with the rules everywhere
        r["human"] = rules[(r["game"], r["player"], r["claim"])]
    with open(out / "sheet.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sheet[0]))
        w.writeheader()
        w.writerows(sheet)
    res = hc.main(["score", "--out", str(out)])
    assert res["all"]["agreement"] == 1.0
    assert hc.kappa(["correct", "wrong"], ["wrong", "correct"]) < 0


def test_move_answer_ending_with_intended_move_tag_is_read_and_counted():
    class Copycat(FakeLLM):  # answers the move request in the reflection format, as Mixtral did
        def generate(self, prompt, system="", temperature=1.0, seed=0, max_tokens=512):
            if "Choose your move" in prompt:
                return "STANDING: level\nINTENDED_MOVE: Scissors"
            return super().generate(prompt, system, temperature, seed, max_tokens)

    llm, c = Copycat(), cfg()
    game = v2.play([llm] * 3, v2.Protocol(v2.load_prompts(v2.DEFAULT_PROMPTS, []), "no_channel", c), 0, c,
                   np.random.default_rng(0))
    assert game["actions"] == [[2, 2, 2]] * 4
    assert game["failures"]["move_intended_tag"] == 12 and "move" not in game["failures"]


def test_leading_speaker_label_is_removed_from_messages():
    llm, c = FakeLLM(), cfg()  # FakeLLM writes "A: let's both play Rock."
    game = v2.play([llm] * 3, v2.Protocol(v2.load_prompts(v2.DEFAULT_PROMPTS, []), "channel_forced", c), 0, c,
                   np.random.default_rng(0))
    assert game["rounds"][0]["chat"][0]["text"] == "let's both play Rock."


def test_v3_prompts_change_only_the_rules_and_state_them_consistently():
    from netinf.games.rps_pot import payoff_pot
    v2c = v2.load_prompts(v2.DEFAULT_PROMPTS.with_name("pot_plan_v2_chat.json"), [])
    v3 = v2.load_prompts(v2.DEFAULT_PROMPTS.with_name("pot_plan_v3.json"), [])
    assert {k for k in v3 if v3[k] != v2c[k]} == {"_about", "rules_base", "strategy_hint"}
    assert "nobody scores if {outsider} plays the third move" in v3["strategy_hint"]
    v2.check_prompts(v3, cfg())
    # every row of the v3 table matches the payoff the environment computes
    names = {"Rock": 0, "Paper": 1, "Scissors": 2}
    rows = [line.split(None, 3) for line in v3["rules_base"].split("\n") if line.startswith("  ") and line.count(",") >= 2
            and line.split()[0].rstrip(",") in names and "for" in line]
    assert len(rows) == 10
    for line in [l for l in v3["rules_base"].split("\n") if l.strip().split(",")[0] in names and "for" in l]:
        moves = [names[w.strip(",")] for w in line.split()[:3]]
        pts = sorted(payoff_pot(moves).tolist())
        if "0 for everyone" in line:
            assert pts == [0, 0, 0]
        elif "1.5" in line:
            assert pts == [0, 1.5, 1.5]
        else:
            assert pts == [0, 0, 3]


def test_v4_private_number_reaches_a_and_b_only_and_is_logged():
    v3 = v2.load_prompts(v2.DEFAULT_PROMPTS.with_name("pot_plan_v3.json"), [])
    v4 = v2.load_prompts(v2.DEFAULT_PROMPTS.with_name("pot_plan_v4.json"), [])
    assert {k for k in v4 if v4[k] != v3[k]} == {"_about", "strategy_hint"}
    c = cfg()
    v2.check_prompts(v4, c)
    seen = []

    class Spy(FakeLLM):
        def generate(self, prompt, system="", temperature=1.0, seed=0, max_tokens=512):
            seen.append((re.search(r"You are Player ([ABC])", system).group(1), system))
            return super().generate(prompt, system, temperature, seed, max_tokens)

    game = v2.play([Spy()] * 3, v2.Protocol(v4, "channel_forced_strategy", c), 0, c, np.random.default_rng(0))
    dice = [r["shared_die"] for r in game["rounds"]]
    assert dice == [v2.shared_die(0, 0, r) for r in range(1, 5)] and all(1 <= d <= 6 for d in dice)
    for who, system in seen:
        if who == "C":
            assert "private number" not in system
    a_systems = [s for w, s in seen if w == "A" and "STRATEGY TIP" in s]
    assert {int(re.search(r"same private number (\d)", s).group(1)) for s in a_systems} == set(dice)
    # other conditions never show the number
    seen.clear()
    v2.play([Spy()] * 3, v2.Protocol(v4, "channel_forced", c), 0, c, np.random.default_rng(0))
    assert not any("private number" in s for _, s in seen)
    assert set(v2.game_metrics(game, 70, np.random.default_rng(1))["die"]) >= {"compliance_A", "betrayal", "c_per_round"}


def test_a_failed_debrief_does_not_lose_the_game():
    class BrokenDebrief(FakeLLM):
        def generate(self, prompt, system="", temperature=1.0, seed=0, max_tokens=512):
            if "The game is over" in prompt:
                raise RuntimeError("HTTP 400: prompt longer than max_model_len")
            return super().generate(prompt, system, temperature, seed, max_tokens)

    c = cfg()
    game = v2.play([BrokenDebrief()] * 3, v2.Protocol(v2.load_prompts(v2.DEFAULT_PROMPTS, []), "no_channel", c), 0, c,
                   np.random.default_rng(0))
    assert len(game["actions"]) == 4 and game["failures"]["debrief_error"] == 3
    assert "max_model_len" in game["debriefs"]["A"]["error"]
    assert v2.debrief_accuracy(game, False)["A"]["own_strategy"] is None  # unreadable, not wrong
