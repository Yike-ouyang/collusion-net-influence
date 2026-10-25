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
