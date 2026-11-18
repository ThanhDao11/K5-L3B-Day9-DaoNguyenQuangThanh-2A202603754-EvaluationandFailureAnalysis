"""M6 probability checks against explicit draws, including invalid inputs."""
from itertools import combinations

import pytest

from lab9 import stats

pytestmark = pytest.mark.student


def test_pass_k_matches_enumerated_draws_and_ordering():
    for n in range(1, 8):
        for c in range(n + 1):
            population = [True] * c + [False] * (n - c)
            for k in range(1, n + 1):
                draws = list(combinations(population, k))
                at = stats.pass_at_k(n, c, k)
                hat = stats.pass_hat_k(n, c, k)
                assert at == pytest.approx(sum(any(draw) for draw in draws) / len(draws))
                assert hat == pytest.approx(sum(all(draw) for draw in draws) / len(draws))
                assert hat <= c / n + 1e-12
                assert c / n <= at + 1e-12


@pytest.mark.parametrize("args", [
    (0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 6, 1), (5, 2, 0), (3, 1, 4),
    (5.0, 2, 1), (5, 2.5, 1), (5, 2, 1.0), (True, 1, 1), (5, False, 1),
    (5, 2, True), (5, 2, float("nan")),
])
def test_both_estimators_reject_invalid_counts(args):
    for fn in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            fn(*args)
