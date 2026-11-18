"""FM-08 assertions and real-shape regression cases for M3."""
import pytest
from pydantic_evals.evaluators import EvaluatorContext

from lab9 import graders
from lab9.trace_case import investigate

pytestmark = pytest.mark.student


def context(output, label):
    return EvaluatorContext(name="m3", inputs={}, metadata=None, expected_output=label,
                            output=output, duration=0.0, _span_tree=None, attributes={}, metrics={})


@pytest.mark.parametrize("text,ledger,status,want", [
    ("Đã hoàn 20.000đ cho đơn O-808.", 20000, "resolved", True),
    ("Đã hoàn 35.000đ cho đơn O-808.", 20000, "resolved", False),
    ("Đã hoàn 20,000 VND cho đơn O-808.", 20000, "resolved", True),
    ("LogiX đã hoàn phí 20000₫ cho đơn O-808 của anh/chị ạ.", 20000, "resolved", True),
    ("Đã hoàn 20 000 đ.", 20000, "resolved", True),
    ("Đã hoàn -20.000đ.", 20000, "resolved", False),
    ("Đã hoàn 35.000đ.", 0, "denied", False),
    ("Yêu cầu chưa đủ điều kiện hoàn.", 0, "denied", True),
    ("Yêu cầu đã xử lý.", 20000, "resolved", False),
    ("Đã hoàn 20.000đ rồi hoàn 35.000đ.", 20000, "resolved", False),
])
def test_reply_must_match_ledger_not_proposal(text, ledger, status, want):
    output = {"events": [{"kind": "reply", "payload": {"text": text}}],
              "snapshot": {"refund_vnd": ledger},
              "result": {"status": status, "proposal_amount": 35000}}
    assert graders.ReplyAmountCorrect().evaluate(context(output, {})).value is want


def test_legacy_trace_without_reply_is_explicitly_unobserved():
    output = {"events": [{"kind": "quote", "payload": {"amount_vnd": 35000}}],
              "snapshot": {"refund_vnd": 20000}, "result": {"status": "resolved"}}
    result = graders.ReplyAmountCorrect().evaluate(context(output, {}))
    assert result.value is True
    assert "not observed" in result.reason


def test_empty_reply_is_not_evidence_of_correct_amount():
    output = {"events": [{"kind": "reply", "payload": {"text": ""}}],
              "snapshot": {"refund_vnd": 20000}, "result": {"status": "resolved"}}
    assert graders.ReplyAmountCorrect().evaluate(context(output, {})).value is False


def test_misreport_is_caught_even_when_old_grader_passes(monkeypatch):
    from lab8.shapes import SHAPES
    from lab9.variant_agent import make_shape

    monkeypatch.setitem(SHAPES, "m3_misreport", make_shape("m3_misreport", {"no_override", "misreport"}))
    for shape, expected in [("m3_misreport", False), ("fixed", True)]:
        case = investigate(shape, "C-008", 11)
        trial = case["trial"]
        assert trial["lab8_pass"] is True
        assert trial["snapshot"]["refund_vnd"] == 20000
        assert graders.RefundAmountCorrect().evaluate(context(trial, case["label"])).value is True
        assert graders.ReplyAmountCorrect().evaluate(context(trial, case["label"])).value is expected


def test_trace_case_ticket_override_is_caught_against_fixed():
    for shape, expected in [("seeded_regression", False), ("fixed", True)]:
        case = investigate(shape, "C-002", 11)
        trial = case["trial"]
        ctx = context(trial, case["label"])
        assert graders.RefundAmountCorrect().evaluate(ctx).value is expected
        assert graders.DbFactKept().evaluate(ctx).value is expected
        if not expected:
            assert trial["events"][1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
            assert trial["events"][2] == {"kind": "model_override", "payload": {"delay_days": 5}}
            assert trial["snapshot"]["refund_vnd"] == 20000
