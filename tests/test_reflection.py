import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from netinf.games.rps_pot import payoff_pot  # noqa: E402
from llm_rps import play  # noqa: E402


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, system="", temperature=1.0, seed=0, max_tokens=16):
        player = re.search(r"You are Player ([ABC])", system).group(1)
        if max_tokens == 300:
            round_no = int(re.search(r"Round (\d+) is over", prompt).group(1))
            text = f"REFLECT-{player}-{round_no}"
        elif max_tokens == 60:
            text = f"MSG-{player}"
        else:
            text = "R"
        self.calls.append({"prompt": prompt, "system": system, "max_tokens": max_tokens, "response": text})
        return text

    def calls_for(self, max_tokens):
        return [c for c in self.calls if c["max_tokens"] == max_tokens]


def _play(condition, rounds=2):
    fake = FakeLLM()
    game = play(fake, condition, rounds, run=0, temperature=1.0, rng=np.random.default_rng(0),
                payoff_fn=payoff_pot, reflect=True, reflection_max_tokens=300)
    return fake, game


def test_reflection_phase_is_private_and_uses_previous_reflection():
    fake, game = _play("channel")

    assert len(game["reflections"]) == 2
    assert game["reflections"][0] == {"A": "REFLECT-A-1", "B": "REFLECT-B-1", "C": "REFLECT-C-1"}
    assert game["reflections"][1] == {"A": "REFLECT-A-2", "B": "REFLECT-B-2", "C": "REFLECT-C-2"}

    round2_moves = [c for c in fake.calls_for(16) if "Round 2." in c["prompt"]]
    by_player = {re.search(r"You are Player ([ABC])", c["system"]).group(1): c for c in round2_moves}

    assert "REFLECT-A-1" in by_player["A"]["prompt"]
    assert "REFLECT-B-1" not in by_player["A"]["prompt"]
    assert "REFLECT-C-1" not in by_player["A"]["prompt"]
    assert "REFLECT-B-1" in by_player["B"]["prompt"]
    assert "REFLECT-A-1" not in by_player["B"]["prompt"]
    assert "REFLECT-C-1" in by_player["C"]["prompt"]
    assert "REFLECT-A-1" not in by_player["C"]["prompt"]
    assert "MSG-A" not in by_player["C"]["prompt"]

    round2_messages = [c for c in fake.calls_for(60) if "Round 2." in c["prompt"]]
    msg_by_player = {re.search(r"You are Player ([ABC])", c["system"]).group(1): c for c in round2_messages}
    assert "REFLECT-A-1" in msg_by_player["A"]["prompt"]
    assert "MSG-B" not in msg_by_player["A"]["prompt"]
    assert "REFLECT-B-1" in msg_by_player["B"]["prompt"]
    assert "MSG-A" in msg_by_player["B"]["prompt"]

    a_reflection_round2 = [c for c in fake.calls_for(300) if "REFLECT-A-2" in c["response"]][0]
    assert "REFLECT-A-1" in a_reflection_round2["prompt"]
    assert "REFLECT-B-1" not in a_reflection_round2["prompt"]
    assert "MSG-A" in a_reflection_round2["prompt"]
    assert "MSG-B" in a_reflection_round2["prompt"]
    assert "What message will you send next round?" in a_reflection_round2["prompt"]


def test_independent_has_no_messages_and_no_message_plan():
    fake, game = _play("independent")

    assert fake.calls_for(60) == []
    assert len(game["reflections"]) == 2
    for call in fake.calls_for(300):
        assert "What message will you send next round?" not in call["prompt"]
    a_move_round2 = [c for c in fake.calls_for(16)
                     if "Round 2." in c["prompt"] and "You are Player A" in c["system"]][0]
    assert "REFLECT-A-1" in a_move_round2["prompt"]
    assert "MSG-A" not in a_move_round2["prompt"]
