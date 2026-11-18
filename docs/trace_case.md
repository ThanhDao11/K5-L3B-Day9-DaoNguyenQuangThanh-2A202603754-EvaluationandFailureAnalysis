# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace, ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi bạn 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run `E-seeded_regression-20261118-8392`, `src/reports/eval_seeded_regression.json`. |
| Triệu chứng | Ledger hoàn 20.000đ thay vì 0; status resolved thay vì denied. RefundAmountCorrect, DbFactKept và TrialPass fail. |
| Bước sai đầu tiên | Event 3, `model_override`, payload `{"delay_days": 5}`. |
| Vì sao là bước *đầu tiên* | Event 1 handoff đúng claim; event 2 đọc DB delay_days=2. Event 3 mới ghi đè bằng ticket, dẫn tới quote sai ở event 4. |
| Failure mode | FM-03 ticket_trust, xem `docs/failure_taxonomy.md`. |
| Đối chứng | `fixed C-002@11`, run `E-fixed-20261118-8392`: không override; event 3 quote=0, reason=no_entitlement; ledger=0, status=denied. |
| Regression test | `tests/test_lab9_reply_amount.py::test_trace_case_ticket_override_is_caught_against_fixed`: xác nhận grader trả False cho bản lỗi và True cho fixed. |
| Chưa chắc chắn | Trace chỉ chứng minh bước sai đầu tiên quan sát được; MockLLM không đại diện tần suất lỗi LLM thật. Reply khớp ledger không chứng minh quyết định hoàn đúng. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- “Bước sai đầu tiên” phải dẫn số event cụ thể, không phải “agent bị nhầm”.
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
