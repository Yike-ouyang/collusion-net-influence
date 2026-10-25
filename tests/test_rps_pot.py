import pytest

from netinf.games.rps_pot import payoff_pot
from netinf.labels import colluded


@pytest.mark.parametrize(
    "actions, expected",
    [
        ([0, 0, 0], [0.0, 0.0, 0.0]),       # all same: pot lost
        ([0, 1, 2], [0.0, 0.0, 0.0]),       # cycle: no winner, pot lost
        ([0, 2, 2], [3.0, 0.0, 0.0]),       # lone Rock beats two Scissors
        ([0, 2, 0], [1.5, 0.0, 1.5]),       # two Rocks split the pot
        ([1, 0, 0], [3.0, 0.0, 0.0]),       # lone Paper beats two Rocks
        ([2, 1, 2], [1.5, 0.0, 1.5]),       # two Scissors split the pot
    ],
)
def test_payoff_pot(actions, expected):
    assert payoff_pot(actions).tolist() == expected


def test_pot_size_is_configurable():
    assert payoff_pot([0, 2, 2], pot=6.0).tolist() == [6.0, 0.0, 0.0]
    assert payoff_pot([0, 2, 0], pot=6.0).tolist() == [3.0, 0.0, 3.0]


def test_behavioural_label_uses_assists():
    always_assist = [[0, 2, 0]] * 100
    never_assist = [[0, 0, 0]] * 100
    assert colluded(always_assist)[0] is True
    assert colluded(never_assist)[0] is False


def test_alternating_simulation_metrics_and_detector():
    import numpy as np

    from netinf import detect, influence_matrix, net_influence
    from netinf.games.rps import BEATS
    from netinf.games.rps_pot import simulate_alternating

    rng = np.random.default_rng(0)
    actions, rewards = simulate_alternating(1_000, rng)
    b_to_a = actions[:, 1] == np.vectorize(BEATS.get)(actions[:, 0])
    a_to_b = actions[:, 0] == np.vectorize(BEATS.get)(actions[:, 1])
    assert (b_to_a ^ a_to_b).all()  # exactly one assist every round
    assert b_to_a[:4].tolist() == [True, False, True, False]
    assert rewards[:, :2].mean() > rewards[:, 2].mean()
    # The detector sees the dependence even though the assist direction alternates.
    net = net_influence(influence_matrix(actions[1:], actions[:-1]))
    assert detect(net) == (0, 1)


def test_any_assist_label_uses_two_thirds_baseline():
    from netinf.labels import colluded_any

    always_different = [[0, 2, 0]] * 100
    same_moves = [[0, 0, 0]] * 100
    assert colluded_any(always_different)[0] is True
    assert colluded_any(same_moves)[0] is False
