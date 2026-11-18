"""Proposal correctness is independent of the amount the host commits."""
import pytest
from pydantic_evals.evaluators import EvaluatorContext

from lab9 import graders
from lab9.trace_case import investigate

pytestmark = pytest.mark.student


def context(output, label):
    return EvaluatorContext(name="proposal", inputs={}, metadata=None, expected_output=label,
                            output=output, duration=0.0, _span_tree=None, attributes={}, metrics={})


@pytest.mark.parametrize("proposal,expected,ledger,want", [
    (0, 35000, 0, False), (35000, 35000, 0, True),
    (35000, 35000, 20000, True), (0, 0, 0, True),
    (None, 0, 0, False), ("35000", 35000, 35000, False),
    (False, 0, 0, False), (-1, 0, 0, False),
])
def test_proposal_is_compared_with_label_not_ledger(proposal, expected, ledger, want):
    trial = {"result": {"proposal_amount": proposal}, "snapshot": {"refund_vnd": ledger}}
    result = graders.ProposalAmountCorrect().evaluate(context(trial, {"proposal_amount": expected}))
    assert result.value is want
    if not want:
        assert result.reason


def test_pre_deduction_to_zero_is_caught_while_ledger_is_correct():
    for shape, want in [("seeded_regression", False), ("fixed", True)]:
        case = investigate(shape, "C-013", 11)
        ctx = context(case["trial"], case["label"])
        assert graders.RefundAmountCorrect().evaluate(ctx).value is True
        assert graders.ProposalAmountCorrect().evaluate(ctx).value is want
