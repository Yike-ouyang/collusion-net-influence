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
