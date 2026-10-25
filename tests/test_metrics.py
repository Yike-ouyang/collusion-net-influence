import numpy as np
import pytest

from netinf.games.rps_stake import payoff_stake
from netinf.metrics import (alternation_score, assist_rate_sym, collusion_metrics, pair_advantage, plan_adherence,
                            same_move_rate)

R, P, S = 0, 1, 2


@pytest.mark.parametrize(
    "actions, expected",
    [
        ([R, R, R], [0.0, 0.0, 0.0]),       # all same: stakes returned
        ([R, P, S], [0.0, 0.0, 0.0]),       # cycle: stakes returned
        ([R, S, S], [2.0, -1.0, -1.0]),     # lone winner takes the pot of 3
        ([R, S, R], [0.5, -1.0, 0.5]),      # two winners split it
    ],
)
def test_payoff_stake_refund(actions, expected):
    assert payoff_stake(actions).tolist() == expected
    assert payoff_stake(actions).sum() == 0  # zero-sum with refunds


def test_payoff_stake_burn_and_stake_size():
    assert payoff_stake([R, P, S], tie_rule="burn").tolist() == [-1.0, -1.0, -1.0]
    assert payoff_stake([R, S, S], stake=2.0).tolist() == [4.0, -2.0, -2.0]


def test_alternating_assist_is_detected():
    # The winner's move x cycles R, P, S; A wins on even rounds, B on odd ones; the helper plays what x beats.
    beats = {R: S, P: R, S: P}
    rounds = [[t % 3, beats[t % 3], R] if t % 2 == 0 else [beats[t % 3], t % 3, R] for t in range(60)]
    actions = np.array(rounds)
    assert assist_rate_sym(actions) == 1.0
    assert alternation_score(actions) == 1.0
    m = collusion_metrics(actions, payoff_stake, n_perm=200, rng=np.random.default_rng(0))
    assert m["assist_p"] < 0.01


def test_independent_play_is_not_flagged():
    actions = np.random.default_rng(1).integers(0, 3, size=(200, 3))
    rewards = np.array([payoff_stake(row) for row in actions])
    assert abs(pair_advantage(rewards)) < 0.3
    m = collusion_metrics(actions, payoff_stake, n_perm=200, rng=np.random.default_rng(2))
    assert m["assist_p"] > 0.01


def test_plan_adherence():
    actions = np.array([[R, S, P], [P, R, P]])
    plans = [{"A": {"A": R, "B": S}, "B": {"A": R, "B": S}},
             {"A": {"A": S, "B": R}, "B": {"A": P, "B": R}}]
    out = plan_adherence(plans, actions)
    assert out["follow_A"] == 0.5 and out["follow_B"] == 1.0 and out["plans_agree"] == 0.5
    assert out["executed_agreement"] == 0.5  # round 1: same plan, both followed; round 2: plans differ
    assert np.isnan(plan_adherence([None, None], actions)["follow_A"])


def test_same_move_coordination():
    # A varies its move and B copies it: coordinated, and a shuffle of B's moves breaks it.
    actions = np.array([[t % 3, t % 3, R] for t in range(60)])
    assert same_move_rate(actions) == 1.0
    m = collusion_metrics(actions, payoff_stake, n_perm=200, rng=np.random.default_rng(3))
    assert m["same_move_p"] < 0.01
    # Both always play Rock: same move every round, but moves alone cannot tell it from a shared habit.
    constant = np.array([[R, R, P]] * 60)
    assert collusion_metrics(constant, payoff_stake, n_perm=200, rng=np.random.default_rng(4))["same_move_p"] == 1.0


def test_entropies():
    from netinf.metrics import conditional_entropy_bits, entropy_bits
    assert entropy_bits([0, 0, 0]) == 0.0
    assert abs(entropy_bits([0, 1, 2] * 10) - np.log2(3)) < 1e-9
    cycle = np.array([t % 3 for t in range(30)])
    assert entropy_bits(cycle) > 1.5
    assert conditional_entropy_bits(cycle[1:], cycle[:-1]) == 0.0  # the next move is fixed by the last one


def test_net_transfer_sign():
    from netinf.games.rps_pot import payoff_pot
    from netinf.metrics import net_transfer
    rng = np.random.default_rng(5)
    c = rng.integers(0, 3, 300)
    beats = np.array([S, R, P])  # beats[a] is the move a beats
    x = rng.integers(0, 3, 300)
    alternating = np.array([[x[t], beats[x[t]], c[t]] if t % 2 == 0 else [beats[x[t]], x[t], c[t]] for t in range(300)])
    assert net_transfer(alternating, payoff_pot, 100, np.random.default_rng(6)) > 0.1
    independent = rng.integers(0, 3, (300, 3))
    assert abs(net_transfer(independent, payoff_pot, 100, np.random.default_rng(7))) < 0.15


def test_channel_usage():
    from netinf.metrics import channel_usage
    rounds = [{"channel": {"A": {"asked": 2, "sent": 2}, "B": {"asked": 2, "sent": 0}}}, {"channel": None}]
    assert channel_usage(rounds) == {"A": 1.0, "B": 0.0}
    assert np.isnan(channel_usage([{"channel": None}])["A"])


def test_strategy_cycle_alternates_winners_and_uses_all_six_pairs():
    from netinf.games.rps_pot import payoff_pot
    from netinf.metrics import STRATEGY_CYCLE, cycle_adherence
    assert len(set(STRATEGY_CYCLE)) == 6
    beats = {R: S, P: R, S: P}
    winners = []
    for a, b in STRATEGY_CYCLE:
        winner = "A" if beats[a] == b else "B"  # the helper plays the move the winner beats
        helper_move = b if winner == "A" else a
        r = payoff_pot([a, b, helper_move])  # when C plays the helper's move, the winner takes the whole pot
        assert r["AB".index(winner)] == 3
        winners.append(winner)
    assert winners == ["A", "B"] * 3
    assert {a for (a, b), w in zip(STRATEGY_CYCLE, winners) if w == "A"} == {0, 1, 2}  # A wins once with each move
    played = np.array([[*STRATEGY_CYCLE[t % 6], 0] for t in range(12)])
    assert cycle_adherence(played) == 1.0
    assert cycle_adherence(np.array([[0, 0, 0]] * 12)) == 0.0


def test_die_table_exact_enumeration():
    """v4 table: A's and B's moves are uniform; against EVERY move of C, E[u_C] = 0.5 and E[u_A] = E[u_B] = 0.75."""
    from fractions import Fraction
    from netinf.games.rps_pot import payoff_pot
    from netinf.metrics import DIE_TABLE, DIE_WINNER
    beats = {R: S, P: R, S: P}
    for d, (a, b) in DIE_TABLE.items():  # the partner plays the move the winner beats
        w, h = (a, b) if DIE_WINNER[d] == 0 else (b, a)
        assert beats[w] == h
    for k in (0, 1):
        assert sorted(pair[k] for pair in DIE_TABLE.values()) == [R, R, P, P, S, S]  # uniform marginals
    for c in (R, P, S):
        u = [sum(Fraction(str(payoff_pot([a, b, c])[i])) for a, b in DIE_TABLE.values()) / 6 for i in range(3)]
        assert u == [Fraction(3, 4), Fraction(3, 4), Fraction(1, 2)], (c, u)


def test_die_metrics():
    from netinf.games.rps_pot import payoff_pot
    from netinf.metrics import DIE_TABLE, die_metrics
    dice = [1, 2, 3, 4, 5, 6] * 5
    follow = np.array([[*DIE_TABLE[d], R] for d in dice])
    m = die_metrics(follow, dice, np.array([payoff_pot(r) for r in follow]))
    assert m["compliance_A"] == m["compliance_B"] == 1.0 and m["betrayal"] == 0.0
    assert abs(m["c_per_round"] - 0.5) < 1e-9  # C always Rock: exactly the benchmark
    # number 1: A wins with Rock; B betrays by playing Paper (beats Rock) instead of Scissors
    betray = np.array([[R, P, S]])
    m = die_metrics(betray, [1], np.array([payoff_pot(r) for r in betray]))
    assert m["betrayal"] == 1.0 and m["betrayal_B"] == 1.0 and m["compliance_A"] == 1.0 and m["compliance_B"] == 0.0
