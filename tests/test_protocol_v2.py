import pytest

from netinf.protocol_v2 import (chat_block, drop_empty_lines, first_speaker, history_block, is_skip, outcome_line,
                                parse_headings, parse_plan, parse_tagged_move, unknown_fields)

R, P, S = 0, 1, 2


@pytest.mark.parametrize("moves, rewards, expected", [
    ([R, S, R], [1.5, 0, 1.5], "Round 7: A=Rock, B=Scissors, C=Rock -> Rock wins, shared by A and C. Points: A 1.5, B 0, C 1.5"),
    ([P, R, R], [3, 0, 0], "Round 7: A=Paper, B=Rock, C=Rock -> Paper wins, A alone. Points: A 3, B 0, C 0"),
    ([R, R, R], [0, 0, 0], "Round 7: A=Rock, B=Rock, C=Rock -> all the same, nobody scores. Points: A 0, B 0, C 0"),
    ([R, P, S], [0, 0, 0], "Round 7: A=Rock, B=Paper, C=Scissors -> all different, nobody scores. Points: A 0, B 0, C 0"),
])
def test_outcome_line(moves, rewards, expected):
    assert outcome_line(7, moves, rewards) == expected


def test_history_and_chat_blocks():
    hist = [{"outcome": f"Round {i}"} for i in range(1, 8)]
    assert history_block(hist, 5).split("\n") == [f"Round {i}" for i in range(3, 8)]
    assert history_block([], 5) == "(no round played yet)"
    assert chat_block([]) == "(no messages yet)"
    assert chat_block([{"from": "A", "text": "hi"}]) == "A: hi"


def test_speaker_alternates():
    assert [first_speaker(r) for r in (1, 2, 3, 4)] == [0, 1, 0, 1]


@pytest.mark.parametrize("text, skip", [("SKIP", True), (" skip. ", True), ("**SKIP**", True),
                                        ("I will skip the details", False), ("Let's play Rock", False)])
def test_is_skip(text, skip):
    assert is_skip(text) is skip


def test_parse_tagged_move_takes_last_tag():
    assert parse_tagged_move("I think Paper... MOVE: Rock") == R
    assert parse_tagged_move("MOVE: Paper\nwait\nMOVE: **Scissors**") == S
    assert parse_tagged_move("move: s") == S
    assert parse_tagged_move("I play Rock") is None
    assert parse_tagged_move("INTENDED_MOVE: Paper", "INTENDED_MOVE") == P
    assert parse_tagged_move("INTENDED_MOVE: Paper") is None  # not a MOVE: line
    assert parse_tagged_move("INTENDED_MOVE: Paper\nMOVE: Rock") == R


def test_parse_plan():
    assert parse_plan("PLAN: A=Rock, B=Scissors") == {"A": R, "B": S}
    assert parse_plan("Sure. PLAN: A = paper, B: rock") == {"A": P, "B": R}
    assert parse_plan("PLAN: A=Rock") == {"A": R, "B": None}


def test_parse_headings():
    text = "LAST_ROUND: I scored 3 points.\n**STANDING:** ahead\nWORKING: yes, it works\nINTENDED_MOVE: Rock"
    h = parse_headings(text, ["LAST_ROUND", "STANDING", "WORKING", "OTHERS", "INTENDED_MOVE"])
    assert h["LAST_ROUND"] == "I scored 3 points."
    assert h["STANDING"] == "ahead"
    assert h["OTHERS"] == ""
    assert h["INTENDED_MOVE"] == "Rock"


def test_unknown_fields_catches_typos():
    prompts = {"a": "{scoreboard} {round}", "b": "{scorebord}", "_note": "{ignored}"}
    assert unknown_fields(prompts, {"scoreboard", "round"}) == {"b": {"scorebord"}}


def test_drop_empty_lines():
    assert drop_empty_lines("a\n\n  \nb\n") == "a\nb"


def _tokens(pieces, top_at=None, top=None):
    return [{"token": p, "top": top if i == top_at else []} for i, p in enumerate(pieces)]


def test_move_distribution_reads_the_token_after_the_tag():
    import math
    from netinf.protocol_v2 import move_distribution
    top = [["Rock", math.log(0.6)], [" Paper", math.log(0.2)], ["Sc", math.log(0.1)], ["**", math.log(0.05)]]
    toks = _tokens(["I think", " Paper.", "\n", "MO", "VE", ":", " **", "Rock", "**"], top_at=7, top=top)
    d = move_distribution(toks, "MOVE")
    assert abs(d["Rock"] - 0.6 / 0.9) < 1e-9 and abs(d["Scissors"] - 0.1 / 0.9) < 1e-9
    assert abs(d["mass"] - 0.9) < 1e-9
    # MOVE: must not match INTENDED_MOVE:, and missing tags or logprobs give None
    assert move_distribution(_tokens(["INTENDED_MOVE", ":", " Rock"], 2, top), "MOVE") is None
    assert move_distribution(_tokens(["INTENDED_MOVE", ":", " Rock"], 2, top), "INTENDED_MOVE")["Rock"] > 0.6
    assert move_distribution(_tokens(["MOVE", ":", " Rock"]), "MOVE") is None
    assert move_distribution([], "MOVE") is None
