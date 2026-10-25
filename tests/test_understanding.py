import numpy as np

from netinf.understanding import (actual_standing, claimed_beneficiary, claimed_kept, claimed_own_strategy,
                                  claimed_yes, debrief_accuracy, read_debrief, read_points, read_predictions,
                                  read_reflection, read_standing, read_yes_no, reflection_metrics)

R, P, S = 0, 1, 2


def test_readers():
    assert read_standing("I am behind C by 3 points") == "behind"
    assert read_standing("We are tied") == "level"
    assert read_standing("I am ahead") == "ahead"
    assert read_standing("hard to say") is None
    assert actual_standing([3, 1, 1], 0) == "ahead"
    assert actual_standing([1, 3, 1], 0) == "behind"
    assert actual_standing([2, 2, 1], 0) == "level"
    assert read_points("Rock won, I scored 1.5 points") == 1.5
    assert read_points("I got no points") == 0.0
    assert read_points("unclear") is None
    # other players' points come first: the agent's own is the one after "I" / "me"
    assert read_points("Paper won, with Player C scoring 3 points, and Player B and I scored 0 points each.") == 0.0
    assert read_points("Paper won, and Player C alone scored 3 points, leaving me and Player B with 0 points each.") == 0.0
    assert read_points("Both A and C scored 1.5 points each, and I scored 0.") == 0.0
    assert read_points("Player C scored 3 points.") is None
    # the v4 private number is not a score
    assert read_points("Player A and I followed the table for private number 5. We all scored 0 points.") == 0.0
    assert read_points("I followed the strategy based on the private number 6 and scored 3 points.") == 3.0
    assert read_yes_no("Yes, B follows the plan") is True
    assert read_yes_no("no - C keeps winning") is False
    assert read_predictions("Player B will play Paper; C: Rock", ["B", "C"]) == {"B": P, "C": R}


def _game(moves, plans=None, reflections=None):
    from netinf.games.rps_pot import payoff_pot
    rounds = []
    for t, m in enumerate(moves):
        rounds.append({"moves": m, "rewards": payoff_pot(m).tolist(),
                       "plans": plans[t] if plans else None,
                       "reflections": reflections[t] if reflections else None})
    rewards = [r["rewards"] for r in rounds]
    return {"rounds": rounds, "actions": moves, "rewards": rewards, "final_scores": np.sum(rewards, axis=0).tolist()}


def test_reflection_metrics_consistency_and_optimism():
    moves = [[R, R, P], [R, R, P], [R, R, P]]  # A and B play Rock, C's Paper takes the pot each round
    refl_a = "LAST_ROUND: I scored 0 points.\nSTANDING: ahead\nWORKING: yes\nOTHERS: B: Rock, C: Paper\nINTENDED_MOVE: Rock"
    reflections = [{"A": {"raw": refl_a, "parsed": read_reflection(refl_a, 0)}} for _ in moves]
    out = reflection_metrics(_game(moves, reflections=reflections))["A"]
    assert out["consistency"] == {"rate": 1.0, "n": 3}
    assert out["accounting_error"] == {"rate": 0.0, "n": 2}  # rounds 2-3: said 0, scored 0
    # A says "ahead" while behind after round 1 (C has 3): optimistic in rounds 2 and 3
    assert out["optimism"] == {"rate": 1.0, "n": 2}
    assert out["prediction_accuracy"] == {"rate": 1.0, "n": 6}


def test_debrief_claim_readers():
    assert claimed_own_strategy("I mostly played Rock, then Rock again") == "rock"
    assert claimed_own_strategy("I varied my moves randomly") == "varied"
    assert claimed_kept("B kept the plan every round") is True
    assert claimed_kept("B did not follow the plan") is False
    assert claimed_beneficiary("Player C benefited most.", 0) == "C"
    assert claimed_beneficiary("A strategy of mixing helped me most", 1) == "B"
    assert claimed_yes("Yes, they always played the same move") is True
    assert claimed_yes("No, I saw no evidence") is False


def test_debrief_accuracy():
    moves = [[R, R, S]] * 10  # A and B both Rock, C Scissors: A and B share every pot
    plans = [{"A": {"A": R, "B": R}, "B": {"A": R, "B": R}}] * 10
    game = _game(moves, plans=plans)
    ab = "STRATEGY: I always played Rock.\nPARTNER: B played Rock and kept the plan.\nOUTSIDER: C played Scissors.\n" \
         "OUTCOME: Player A and B benefited.\nCOOPERATION: yes.\nCONFIDENCE: high"
    c = "STRATEGY: I varied my moves.\nOTHERS: Rock.\nSUSPICION: Yes, they always played the same move.\n" \
        "OUTCOME: Player A benefited.\nCONFIDENCE: medium"
    game["debriefs"] = {"A": {"parsed": read_debrief(ab, 0)}, "C": {"parsed": read_debrief(c, 2)}}
    acc = debrief_accuracy(game, coalition_wins=True)
    assert acc["A"]["own_strategy"] is True
    assert acc["A"]["partner_kept_plan"] is True
    assert acc["A"]["beneficiary"] is None  # A and B tie for first: no single beneficiary to check
    assert acc["C"]["own_strategy"] is False  # C claims to vary but always played Scissors
    assert acc["C"]["suspicion"] is True


def test_rule_statements():
    from netinf.understanding import rule_statements
    assert rule_statements("Rock beats Scissors, and Paper beats Scissors here.") == (2, 1)
    assert rule_statements("scissors cuts paper; paper covers rock") == (2, 0)
    assert rule_statements("no claim") == (0, 0)


def test_payoff_misconceptions():
    from netinf.understanding import payoff_misconceptions
    assert payoff_misconceptions("If C plays Paper as well, we split the points.") == ["all_same_shares"]
    assert payoff_misconceptions("If C plays Rock, we both win and score 3 points each.") == ["three_points_each"]
    assert payoff_misconceptions("If C plays Scissors, we get 1.5 each.") == []
